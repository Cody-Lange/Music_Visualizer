"""Audio analysis service using Librosa for deep MIR feature extraction."""

import logging

import librosa
import numpy as np

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

logger = logging.getLogger(__name__)

# Analysis frame rate — controls time resolution of spectral features
HOP_LENGTH = 512
ANALYSIS_SR = 22050
N_MFCC = 13


class AudioAnalyzerService:
    """Performs comprehensive audio analysis using Librosa."""

    def analyze(self, audio_path: str, filename: str) -> AudioAnalysisResult:
        logger.info("Starting analysis for %s", filename)

        y, sr = librosa.load(audio_path, sr=ANALYSIS_SR, mono=True)
        duration = float(librosa.get_duration(y=y, sr=sr))

        metadata = self._extract_metadata(filename, duration, sr)
        rhythm = self._extract_rhythm(y, sr)
        spectral = self._extract_spectral(y, sr)
        tonal = self._extract_tonal(y, sr)
        onsets = self._extract_onsets(y, sr)
        hp = self._extract_harmonic_percussive(y, sr)
        sections = self._extract_sections(y, sr, duration)
        mood = self._estimate_mood(rhythm, spectral, tonal)

        logger.info("Analysis complete for %s (%.1fs, %.1f BPM)", filename, duration, rhythm.bpm)

        return AudioAnalysisResult(
            metadata=metadata,
            rhythm=rhythm,
            sections=sections,
            spectral=spectral,
            tonal=tonal,
            mood=mood,
            onsets=onsets,
            harmonic_percussive=hp,
        )

    def _extract_metadata(self, filename: str, duration: float, sr: int) -> AudioMetadata:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
        return AudioMetadata(
            filename=filename,
            duration=duration,
            sample_rate=sr,
            channels=1,  # mono after loading
            format=ext,
        )

    def _extract_rhythm(self, y: np.ndarray, sr: int) -> RhythmAnalysis:
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP_LENGTH)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=HOP_LENGTH).tolist()

        # Estimate tempo as scalar
        bpm = float(np.atleast_1d(tempo)[0])

        # Estimate downbeats (every 4th beat for 4/4 time)
        downbeats = beat_times[::4] if len(beat_times) >= 4 else beat_times[:1]

        # Check tempo stability via tempogram
        tempogram = librosa.feature.tempogram(y=y, sr=sr, hop_length=HOP_LENGTH)
        tempo_std = float(np.std(np.argmax(tempogram, axis=0)))
        tempo_stable = tempo_std < 5.0

        return RhythmAnalysis(
            bpm=round(bpm, 1),
            bpm_confidence=min(1.0, 1.0 - tempo_std / 20.0),
            beats=beat_times,
            downbeats=downbeats,
            time_signature=4,
            tempo_stable=tempo_stable,
        )

    def _extract_spectral(self, y: np.ndarray, sr: int) -> SpectralAnalysis:
        # Frame times
        n_frames = 1 + len(y) // HOP_LENGTH
        times = librosa.frames_to_time(np.arange(n_frames), sr=sr, hop_length=HOP_LENGTH).tolist()

        # RMS energy
        rms = librosa.feature.rms(y=y, hop_length=HOP_LENGTH)[0]

        # Spectral features
        cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH)[0]
        flux = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP_LENGTH)
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=HOP_LENGTH)[0]

        # MFCCs
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC, hop_length=HOP_LENGTH)

        # Energy bands via mel filterbank
        mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=HOP_LENGTH, n_mels=128)
        mel_db = librosa.power_to_db(mel_spec, ref=np.max)
        energy_bands = self._compute_energy_bands(mel_db)

        # Truncate to consistent length
        min_len = min(len(times), rms.shape[0], cent.shape[0], flux.shape[0], rolloff.shape[0])

        return SpectralAnalysis(
            times=times[:min_len],
            rms=self._to_list(rms[:min_len]),
            spectral_centroid=self._to_list(cent[:min_len]),
            spectral_flux=self._to_list(flux[:min_len]),
            spectral_rolloff=self._to_list(rolloff[:min_len]),
            mfcc=[self._to_list(mfcc[i, :min_len]) for i in range(N_MFCC)],
            energy_bands=energy_bands,
        )

    def _compute_energy_bands(self, mel_db: np.ndarray) -> EnergyBands:
        """Split mel spectrogram into 5 energy bands."""
        n_mels = mel_db.shape[0]
        # Approximate frequency band splits for 128 mel bins
        splits = [0, int(n_mels * 0.08), int(n_mels * 0.16), int(n_mels * 0.4), int(n_mels * 0.7), n_mels]

        bands = []
        for i in range(5):
            band_energy = np.mean(mel_db[splits[i]:splits[i + 1], :], axis=0)
            # Normalize to 0-1
            band_min, band_max = band_energy.min(), band_energy.max()
            if band_max > band_min:
                band_energy = (band_energy - band_min) / (band_max - band_min)
            else:
                band_energy = np.zeros_like(band_energy)
            bands.append(band_energy)

        return EnergyBands(
            bass=self._to_list(bands[0]),
            low_mid=self._to_list(bands[1]),
            mid=self._to_list(bands[2]),
            high_mid=self._to_list(bands[3]),
            treble=self._to_list(bands[4]),
        )

    def _extract_tonal(self, y: np.ndarray, sr: int) -> TonalAnalysis:
        chromagram = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP_LENGTH)

        # Estimate key from chroma
        chroma_avg = np.mean(chromagram, axis=1)
        key_index = int(np.argmax(chroma_avg))
        key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        key = key_names[key_index]

        # Estimate major/minor by comparing major and minor profiles
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

        # Rotate profiles to match detected key
        shifted_chroma = np.roll(chroma_avg, -key_index)
        major_corr = float(np.corrcoef(shifted_chroma, major_profile)[0, 1])
        minor_corr = float(np.corrcoef(shifted_chroma, minor_profile)[0, 1])

        scale = "major" if major_corr >= minor_corr else "minor"
        confidence = max(major_corr, minor_corr)

        # Downsample chromagram for reasonable payload size (every 4th frame)
        chroma_downsampled = chromagram[:, ::4]

        return TonalAnalysis(
            key=key,
            scale=scale,
            key_confidence=max(0.0, min(1.0, confidence)),
            chromagram=[self._to_list(chroma_downsampled[i]) for i in range(12)],
        )

    def _extract_onsets(self, y: np.ndarray, sr: int) -> list[float]:
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=HOP_LENGTH)
        return librosa.frames_to_time(onset_frames, sr=sr, hop_length=HOP_LENGTH).tolist()

    def _extract_harmonic_percussive(self, y: np.ndarray, sr: int) -> HarmonicPercussive:
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        h_rms = librosa.feature.rms(y=y_harmonic, hop_length=HOP_LENGTH)[0]
        p_rms = librosa.feature.rms(y=y_percussive, hop_length=HOP_LENGTH)[0]

        return HarmonicPercussive(
            harmonic_energy=self._to_list(h_rms),
            percussive_energy=self._to_list(p_rms),
        )

    def _extract_sections(
        self, y: np.ndarray, sr: int, duration: float
    ) -> SectionData:
        """Detect structural sections using recurrence matrix + spectral clustering."""
        # Compute features for segmentation
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC, hop_length=HOP_LENGTH)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP_LENGTH)

        # Stack features
        features = np.vstack([
            librosa.util.normalize(mfcc),
            librosa.util.normalize(chroma),
        ])

        # Build recurrence matrix
        rec = librosa.segment.recurrence_matrix(features, mode="affinity", sym=True)

        # Use Laplacian segmentation
        try:
            # Target ~6-10 segments for a typical song
            n_segments = max(3, min(10, int(duration / 30)))
            bounds = librosa.segment.agglomerative(features, n_segments)
            bound_times = librosa.frames_to_time(bounds, sr=sr, hop_length=HOP_LENGTH).tolist()
        except Exception:
            # Fallback: evenly spaced boundaries
            n_segments = max(3, int(duration / 30))
            bound_times = [i * duration / n_segments for i in range(n_segments)]

        # Ensure boundaries start at 0
        if not bound_times or bound_times[0] > 0.5:
            bound_times = [0.0] + bound_times

        # Label sections heuristically
        labels = self._label_sections(bound_times, duration, features, sr)

        # Compute similarity between sections
        n = len(bound_times)
        similarities = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    similarities[i][j] = float(np.mean(rec[
                        max(0, bounds[i] if i < len(bounds) else 0):bounds[i + 1] if i + 1 < len(bounds) else rec.shape[0],
                        max(0, bounds[j] if j < len(bounds) else 0):bounds[j + 1] if j + 1 < len(bounds) else rec.shape[1],
                    ])) if i < len(bounds) and j < len(bounds) else 0.0

        confidence = [0.7] * len(bound_times)  # Placeholder confidences

        return SectionData(
            boundaries=bound_times,
            labels=labels,
            confidence=confidence,
            similarities=similarities.tolist(),
        )

    def _label_sections(
        self, boundaries: list[float], duration: float, features: np.ndarray, sr: int
    ) -> list[str]:
        """Heuristically label sections as intro, verse, chorus, bridge, outro."""
        n = len(boundaries)
        if n == 0:
            return []

        labels: list[str] = []
        verse_count = 0
        chorus_count = 0

        for i in range(n):
            start = boundaries[i]
            end = boundaries[i + 1] if i + 1 < n else duration
            length = end - start
            position_ratio = start / duration if duration > 0 else 0

            if i == 0 and length < 15:
                labels.append("intro")
            elif position_ratio > 0.85:
                labels.append("outro")
            elif i > 0 and i == n - 2 and length < 20:
                labels.append("bridge")
            elif i % 2 == 1 or (i > 0 and length > 25):
                chorus_count += 1
                labels.append(f"chorus_{chorus_count}" if chorus_count > 1 else "chorus")
            else:
                verse_count += 1
                labels.append(f"verse_{verse_count}" if verse_count > 1 else "verse")

        return labels

    def _estimate_mood(
        self, rhythm: RhythmAnalysis, spectral: SpectralAnalysis, tonal: TonalAnalysis
    ) -> MoodAnalysis:
        """Rough mood estimation from audio features."""
        # Energy from average RMS
        avg_rms = float(np.mean(spectral.rms)) if spectral.rms else 0.5
        energy = min(1.0, avg_rms * 3.0)

        # Valence: major keys tend positive, minor negative; high energy adds positivity
        base_valence = 0.3 if tonal.scale == "major" else -0.2
        valence = max(-1.0, min(1.0, base_valence + energy * 0.3))

        # Danceability from BPM range and tempo stability
        bpm = rhythm.bpm
        if 100 <= bpm <= 130:
            dance = 0.8
        elif 80 <= bpm <= 150:
            dance = 0.6
        else:
            dance = 0.3
        if rhythm.tempo_stable:
            dance = min(1.0, dance + 0.1)

        # Mood tags
        tags: list[str] = []
        if energy > 0.7:
            tags.append("energetic")
        elif energy < 0.3:
            tags.append("calm")
        if valence > 0.3:
            tags.append("uplifting")
        elif valence < -0.3:
            tags.append("melancholic")
        if dance > 0.7:
            tags.append("danceable")
        if bpm > 140:
            tags.append("fast")
        elif bpm < 80:
            tags.append("slow")
        if tonal.scale == "minor":
            tags.append("dark")

        return MoodAnalysis(
            valence=round(valence, 3),
            energy=round(energy, 3),
            danceability=round(dance, 3),
            tags=tags,
        )

    @staticmethod
    def _to_list(arr: np.ndarray) -> list[float]:
        return [round(float(x), 5) for x in arr]
