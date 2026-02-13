from pydantic import BaseModel, Field


class AudioMetadata(BaseModel):
    filename: str
    duration: float
    sample_rate: int
    channels: int
    format: str


class RhythmAnalysis(BaseModel):
    bpm: float
    bpm_confidence: float = Field(ge=0, le=1)
    beats: list[float]
    downbeats: list[float]
    time_signature: int = 4
    tempo_stable: bool = True
    tempo_curve: dict[str, list[float]] | None = None


class EnergyBands(BaseModel):
    bass: list[float]
    low_mid: list[float]
    mid: list[float]
    high_mid: list[float]
    treble: list[float]


class SpectralAnalysis(BaseModel):
    times: list[float]
    rms: list[float]
    spectral_centroid: list[float]
    spectral_flux: list[float]
    spectral_rolloff: list[float]
    mfcc: list[list[float]]
    energy_bands: EnergyBands


class TonalAnalysis(BaseModel):
    key: str
    scale: str
    key_confidence: float = Field(ge=0, le=1)
    chromagram: list[list[float]]


class MoodAnalysis(BaseModel):
    valence: float = Field(ge=-1, le=1)
    energy: float = Field(ge=0, le=1)
    danceability: float = Field(ge=0, le=1)
    tags: list[str]


class HarmonicPercussive(BaseModel):
    harmonic_energy: list[float]
    percussive_energy: list[float]


class SectionData(BaseModel):
    boundaries: list[float]
    labels: list[str]
    confidence: list[float]
    similarities: list[list[float]]


class AudioAnalysisResult(BaseModel):
    metadata: AudioMetadata
    rhythm: RhythmAnalysis
    sections: SectionData
    spectral: SpectralAnalysis
    tonal: TonalAnalysis
    mood: MoodAnalysis
    onsets: list[float]
    harmonic_percussive: HarmonicPercussive
