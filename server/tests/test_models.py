"""Tests for Pydantic models — validation constraints, defaults, serialization."""

import pytest
from pydantic import ValidationError

from app.models.audio import (
    AudioAnalysisResult,
    AudioMetadata,
    EnergyBands,
    HarmonicPercussive,
    MoodAnalysis,
    RhythmAnalysis,
    SectionData,
    SpectralAnalysis,
    TonalAnalysis,
)
from app.models.lyrics import LyricsData, LyricsLine, LyricsMetadata, LyricsWord, LyricsFetchRequest
from app.models.render import (
    ExportSettings,
    GlobalStyle,
    LyricsDisplayConfig,
    RenderEditRequest,
    RenderRequest,
    RenderSpec,
    SectionSpec,
)
from app.models.chat import ChatMessage, AnalysisProgress, RenderProgress


# ── Audio Models ──────────────────────────────────────────────


class TestRhythmAnalysis:
    def test_valid_confidence(self):
        r = RhythmAnalysis(bpm=120, bpm_confidence=0.85, beats=[1.0], downbeats=[1.0])
        assert r.bpm_confidence == 0.85

    def test_confidence_at_bounds(self):
        r = RhythmAnalysis(bpm=120, bpm_confidence=0.0, beats=[], downbeats=[])
        assert r.bpm_confidence == 0.0
        r = RhythmAnalysis(bpm=120, bpm_confidence=1.0, beats=[], downbeats=[])
        assert r.bpm_confidence == 1.0

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            RhythmAnalysis(bpm=120, bpm_confidence=1.5, beats=[], downbeats=[])
        with pytest.raises(ValidationError):
            RhythmAnalysis(bpm=120, bpm_confidence=-0.1, beats=[], downbeats=[])

    def test_defaults(self):
        r = RhythmAnalysis(bpm=100, bpm_confidence=0.5, beats=[], downbeats=[])
        assert r.time_signature == 4
        assert r.tempo_stable is True
        assert r.tempo_curve is None


class TestMoodAnalysis:
    def test_valid_ranges(self):
        m = MoodAnalysis(valence=-0.5, energy=0.8, danceability=0.7, tags=["energetic"])
        assert m.valence == -0.5
        assert m.energy == 0.8

    def test_valence_out_of_range(self):
        with pytest.raises(ValidationError):
            MoodAnalysis(valence=-1.5, energy=0.5, danceability=0.5, tags=[])
        with pytest.raises(ValidationError):
            MoodAnalysis(valence=1.5, energy=0.5, danceability=0.5, tags=[])

    def test_energy_out_of_range(self):
        with pytest.raises(ValidationError):
            MoodAnalysis(valence=0, energy=-0.1, danceability=0.5, tags=[])
        with pytest.raises(ValidationError):
            MoodAnalysis(valence=0, energy=1.1, danceability=0.5, tags=[])

    def test_danceability_out_of_range(self):
        with pytest.raises(ValidationError):
            MoodAnalysis(valence=0, energy=0.5, danceability=-0.1, tags=[])

    def test_boundary_values(self):
        m = MoodAnalysis(valence=-1.0, energy=0.0, danceability=0.0, tags=[])
        assert m.valence == -1.0
        m = MoodAnalysis(valence=1.0, energy=1.0, danceability=1.0, tags=[])
        assert m.energy == 1.0


class TestTonalAnalysis:
    def test_key_confidence_validation(self):
        t = TonalAnalysis(key="C", scale="major", key_confidence=0.9, chromagram=[])
        assert t.key_confidence == 0.9

    def test_key_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            TonalAnalysis(key="C", scale="major", key_confidence=1.5, chromagram=[])


class TestAudioAnalysisResult:
    def test_full_model_serialization(self):
        result = AudioAnalysisResult(
            metadata=AudioMetadata(filename="test.mp3", duration=180.0, sample_rate=22050, channels=1, format="mp3"),
            rhythm=RhythmAnalysis(bpm=120, bpm_confidence=0.9, beats=[0.5, 1.0], downbeats=[0.5]),
            sections=SectionData(boundaries=[0.0, 60.0], labels=["intro", "verse"], confidence=[0.8, 0.7], similarities=[[1.0, 0.3], [0.3, 1.0]]),
            spectral=SpectralAnalysis(times=[0.0], rms=[0.5], spectral_centroid=[2000.0], spectral_flux=[0.1], spectral_rolloff=[8000.0], mfcc=[[0.1]], energy_bands=EnergyBands(bass=[0.8], low_mid=[0.5], mid=[0.4], high_mid=[0.3], treble=[0.2])),
            tonal=TonalAnalysis(key="C", scale="major", key_confidence=0.85, chromagram=[[0.5] * 12]),
            mood=MoodAnalysis(valence=0.3, energy=0.7, danceability=0.6, tags=["energetic"]),
            onsets=[0.5, 1.0, 1.5],
            harmonic_percussive=HarmonicPercussive(harmonic_energy=[0.4], percussive_energy=[0.3]),
        )
        data = result.model_dump()
        assert data["metadata"]["filename"] == "test.mp3"
        assert data["rhythm"]["bpm"] == 120
        assert len(data["onsets"]) == 3


# ── Lyrics Models ─────────────────────────────────────────────


class TestLyricsModels:
    def test_lyrics_word_defaults(self):
        w = LyricsWord(text="hello", start_time=0.0, end_time=0.5)
        assert w.confidence == 1.0
        assert w.line_index == 0

    def test_lyrics_word_confidence_validation(self):
        with pytest.raises(ValidationError):
            LyricsWord(text="hello", start_time=0.0, end_time=0.5, confidence=1.5)

    def test_lyrics_data_source_literal(self):
        data = LyricsData(
            source="genius",
            lines=[],
            words=[],
            metadata=LyricsMetadata(has_sync=False),
        )
        assert data.source == "genius"
        assert data.language == "en"

    def test_lyrics_data_invalid_source(self):
        with pytest.raises(ValidationError):
            LyricsData(source="invalid", lines=[], words=[], metadata=LyricsMetadata())

    def test_lyrics_fetch_request_optional_job_id(self):
        req = LyricsFetchRequest(title="Song", artist="Artist")
        assert req.job_id is None

        req = LyricsFetchRequest(title="Song", artist="Artist", job_id="abc123")
        assert req.job_id == "abc123"


# ── Render Models ─────────────────────────────────────────────


class TestRenderModels:
    def test_section_spec_defaults(self):
        s = SectionSpec(label="chorus", start_time=30.0, end_time=60.0)
        assert s.color_palette == ["#7C5CFC", "#1A1A28"]
        assert s.motion_style == "slow-drift"
        assert s.intensity == 0.5
        assert s.transition_in == "cross-dissolve"
        assert s.visual_elements == []

    def test_section_spec_intensity_validation(self):
        with pytest.raises(ValidationError):
            SectionSpec(label="x", start_time=0, end_time=10, intensity=1.5)
        with pytest.raises(ValidationError):
            SectionSpec(label="x", start_time=0, end_time=10, intensity=-0.1)

    def test_section_spec_intensity_bounds(self):
        s = SectionSpec(label="x", start_time=0, end_time=10, intensity=0.0)
        assert s.intensity == 0.0
        s = SectionSpec(label="x", start_time=0, end_time=10, intensity=1.0)
        assert s.intensity == 1.0

    def test_export_settings_defaults(self):
        e = ExportSettings()
        assert e.resolution == (1920, 1080)
        assert e.fps == 30
        assert e.aspect_ratio == "16:9"
        assert e.format == "mp4"
        assert e.quality == "high"

    def test_export_settings_invalid_fps(self):
        with pytest.raises(ValidationError):
            ExportSettings(fps=25)  # Not in Literal[24, 30, 60]

    def test_export_settings_invalid_aspect_ratio(self):
        with pytest.raises(ValidationError):
            ExportSettings(aspect_ratio="4:3")

    def test_global_style_defaults(self):
        g = GlobalStyle()
        assert g.template == "shader"
        assert g.shader_description == ""
        assert g.style_modifiers == []
        assert g.lyrics_display.enabled is True
        assert g.lyrics_display.font == "sans"

    def test_global_style_new_templates(self):
        g = GlobalStyle(template="glitchbreak")
        assert g.template == "glitchbreak"
        g = GlobalStyle(template="90s-anime")
        assert g.template == "90s-anime"

    def test_global_style_invalid_template(self):
        with pytest.raises(ValidationError):
            GlobalStyle(template="invalid_template")

    def test_lyrics_display_config_defaults(self):
        c = LyricsDisplayConfig()
        assert c.size == "medium"
        assert c.animation == "fade-word"
        assert c.shadow is True

    def test_render_spec_defaults(self):
        r = RenderSpec()
        assert r.global_style.template == "shader"
        assert r.sections == []
        assert r.export_settings.resolution == (1920, 1080)

    def test_render_spec_full(self):
        spec = RenderSpec(
            global_style=GlobalStyle(template="cinematic"),
            sections=[SectionSpec(label="intro", start_time=0, end_time=30)],
            export_settings=ExportSettings(fps=60),
        )
        assert spec.global_style.template == "cinematic"
        assert len(spec.sections) == 1
        assert spec.export_settings.fps == 60

    def test_render_request(self):
        req = RenderRequest(
            job_id="abc",
            render_spec=RenderSpec(),
        )
        assert req.job_id == "abc"

    def test_render_edit_request_optional_spec(self):
        req = RenderEditRequest(edit_description="make it blue")
        assert req.render_spec is None

        req = RenderEditRequest(edit_description="more bass", render_spec=RenderSpec())
        assert req.render_spec is not None


# ── Chat Models ───────────────────────────────────────────────


class TestChatModels:
    def test_chat_message_roles(self):
        for role in ("user", "assistant", "system"):
            msg = ChatMessage(role=role, content="test")
            assert msg.role == role

    def test_chat_message_invalid_role(self):
        with pytest.raises(ValidationError):
            ChatMessage(role="admin", content="test")

    def test_analysis_progress(self):
        p = AnalysisProgress(step="uploading", progress=50.0, message="Uploading...")
        assert p.step == "uploading"

    def test_analysis_progress_invalid_step(self):
        with pytest.raises(ValidationError):
            AnalysisProgress(step="invalid_step", progress=0, message="")

    def test_render_progress_defaults(self):
        p = RenderProgress(status="idle")
        assert p.percentage == 0
        assert p.current_frame is None
        assert p.download_url is None
        assert p.error is None

    def test_render_progress_invalid_status(self):
        with pytest.raises(ValidationError):
            RenderProgress(status="invalid")
