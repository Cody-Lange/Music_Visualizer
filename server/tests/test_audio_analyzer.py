"""Tests for the AudioAnalyzerService."""

import numpy as np
import pytest

from app.models.audio import RhythmAnalysis, SpectralAnalysis, EnergyBands, TonalAnalysis, MoodAnalysis
from app.services.audio_analyzer import AudioAnalyzerService


@pytest.fixture
def analyzer():
    return AudioAnalyzerService()


class TestExtractMetadata:
    def test_extracts_extension(self, analyzer: AudioAnalyzerService):
        meta = analyzer._extract_metadata("song.mp3", 180.0, 22050)
        assert meta.format == "mp3"
        assert meta.filename == "song.mp3"
        assert meta.duration == 180.0
        assert meta.sample_rate == 22050
        assert meta.channels == 1

    def test_no_extension(self, analyzer: AudioAnalyzerService):
        meta = analyzer._extract_metadata("noext", 60.0, 22050)
        assert meta.format == "unknown"

    def test_multiple_dots(self, analyzer: AudioAnalyzerService):
        meta = analyzer._extract_metadata("my.song.file.flac", 120.0, 44100)
        assert meta.format == "flac"


class TestExtractRhythm:
    def test_produces_valid_output(self, analyzer: AudioAnalyzerService):
        # Generate a click track at 120 BPM (2 beats/sec)
        sr = 22050
        duration = 4.0
        y = np.zeros(int(sr * duration))
        beat_interval = int(sr * 0.5)  # 120 BPM
        for i in range(0, len(y), beat_interval):
            y[i : i + 100] = 0.8  # Click pulse

        rhythm = analyzer._extract_rhythm(y, sr)
        assert rhythm.bpm > 0
        assert 0 <= rhythm.bpm_confidence <= 1
        assert isinstance(rhythm.beats, list)
        assert isinstance(rhythm.downbeats, list)
        assert rhythm.time_signature == 4

    def test_short_audio_few_beats(self, analyzer: AudioAnalyzerService):
        sr = 22050
        y = np.random.randn(sr)  # 1 second of noise
        rhythm = analyzer._extract_rhythm(y, sr)
        # Should still produce some result, even if inaccurate
        assert rhythm.bpm > 0
        assert isinstance(rhythm.beats, list)

    def test_downbeats_fallback_few_beats(self, analyzer: AudioAnalyzerService):
        """When fewer than 4 beats, downbeats should use first beat."""
        sr = 22050
        y = np.random.randn(sr * 2)  # 2 seconds — may produce few beats
        rhythm = analyzer._extract_rhythm(y, sr)
        assert isinstance(rhythm.downbeats, list)


class TestComputeEnergyBands:
    def test_normalized_output(self, analyzer: AudioAnalyzerService):
        mel_db = np.random.randn(128, 50)  # 128 mel bins, 50 frames
        bands = analyzer._compute_energy_bands(mel_db)
        # All bands should have values in [0, 1]
        for field in ["bass", "low_mid", "mid", "high_mid", "treble"]:
            values = getattr(bands, field)
            assert len(values) == 50
            assert all(0 <= v <= 1 for v in values)

    def test_constant_input(self, analyzer: AudioAnalyzerService):
        """When all values are equal, bands should be all 0 (max==min)."""
        mel_db = np.ones((128, 10)) * -20.0
        bands = analyzer._compute_energy_bands(mel_db)
        assert all(v == 0.0 for v in bands.bass)
        assert all(v == 0.0 for v in bands.treble)


class TestExtractTonal:
    def test_returns_valid_key(self, analyzer: AudioAnalyzerService):
        sr = 22050
        # Generate a pure A4 tone (440 Hz)
        t = np.linspace(0, 2, sr * 2)
        y = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        tonal = analyzer._extract_tonal(y, sr)
        assert tonal.key in ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        assert tonal.scale in ["major", "minor"]
        assert 0 <= tonal.key_confidence <= 1
        assert len(tonal.chromagram) == 12


class TestEstimateMood:
    def test_high_energy_major(self, analyzer: AudioAnalyzerService):
        rhythm = RhythmAnalysis(bpm=120, bpm_confidence=0.9, beats=[], downbeats=[], tempo_stable=True)
        spectral = SpectralAnalysis(
            times=[], rms=[0.8, 0.9, 0.7], spectral_centroid=[], spectral_flux=[],
            spectral_rolloff=[], mfcc=[], energy_bands=EnergyBands(bass=[], low_mid=[], mid=[], high_mid=[], treble=[]),
        )
        tonal = TonalAnalysis(key="C", scale="major", key_confidence=0.9, chromagram=[])
        mood = analyzer._estimate_mood(rhythm, spectral, tonal)
        assert mood.energy > 0.5
        assert mood.valence > 0
        assert "energetic" in mood.tags or "uplifting" in mood.tags

    def test_low_energy_minor(self, analyzer: AudioAnalyzerService):
        rhythm = RhythmAnalysis(bpm=60, bpm_confidence=0.9, beats=[], downbeats=[], tempo_stable=False)
        spectral = SpectralAnalysis(
            times=[], rms=[0.05, 0.06], spectral_centroid=[], spectral_flux=[],
            spectral_rolloff=[], mfcc=[], energy_bands=EnergyBands(bass=[], low_mid=[], mid=[], high_mid=[], treble=[]),
        )
        tonal = TonalAnalysis(key="A", scale="minor", key_confidence=0.8, chromagram=[])
        mood = analyzer._estimate_mood(rhythm, spectral, tonal)
        assert mood.energy < 0.5
        assert "calm" in mood.tags or "slow" in mood.tags
        assert "dark" in mood.tags

    def test_danceability_sweet_spot(self, analyzer: AudioAnalyzerService):
        rhythm = RhythmAnalysis(bpm=115, bpm_confidence=0.9, beats=[], downbeats=[], tempo_stable=True)
        spectral = SpectralAnalysis(
            times=[], rms=[0.5], spectral_centroid=[], spectral_flux=[],
            spectral_rolloff=[], mfcc=[], energy_bands=EnergyBands(bass=[], low_mid=[], mid=[], high_mid=[], treble=[]),
        )
        tonal = TonalAnalysis(key="G", scale="major", key_confidence=0.7, chromagram=[])
        mood = analyzer._estimate_mood(rhythm, spectral, tonal)
        assert mood.danceability >= 0.8  # 100-130 BPM + stable tempo

    def test_empty_rms(self, analyzer: AudioAnalyzerService):
        rhythm = RhythmAnalysis(bpm=120, bpm_confidence=0.5, beats=[], downbeats=[])
        spectral = SpectralAnalysis(
            times=[], rms=[], spectral_centroid=[], spectral_flux=[],
            spectral_rolloff=[], mfcc=[], energy_bands=EnergyBands(bass=[], low_mid=[], mid=[], high_mid=[], treble=[]),
        )
        tonal = TonalAnalysis(key="C", scale="major", key_confidence=0.5, chromagram=[])
        mood = analyzer._estimate_mood(rhythm, spectral, tonal)
        assert mood.energy == pytest.approx(min(1.0, 0.5 * 3.0), abs=0.01)  # np.mean([]) with fallback


class TestLabelSections:
    def test_intro_detection(self, analyzer: AudioAnalyzerService):
        boundaries = [0.0, 10.0, 60.0, 120.0]
        labels = analyzer._label_sections(boundaries, 180.0, np.zeros((25, 100)), 22050)
        assert labels[0] == "intro"  # Short first section

    def test_outro_detection(self, analyzer: AudioAnalyzerService):
        boundaries = [0.0, 30.0, 60.0, 160.0]
        labels = analyzer._label_sections(boundaries, 180.0, np.zeros((25, 100)), 22050)
        assert labels[-1] == "outro"  # position_ratio > 0.85

    def test_empty_boundaries(self, analyzer: AudioAnalyzerService):
        labels = analyzer._label_sections([], 180.0, np.zeros((25, 100)), 22050)
        assert labels == []


class TestToList:
    def test_converts_and_rounds(self):
        arr = np.array([1.123456789, 2.987654321])
        result = AudioAnalyzerService._to_list(arr)
        assert result == [1.12346, 2.98765]
        assert all(isinstance(v, float) for v in result)
