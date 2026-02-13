export interface AudioMetadata {
  filename: string;
  duration: number;
  sampleRate: number;
  channels: number;
  format: string;
}

export interface RhythmAnalysis {
  bpm: number;
  bpmConfidence: number;
  beats: number[];
  downbeats: number[];
  timeSignature: number;
  tempoStable: boolean;
  tempoCurve?: {
    times: number[];
    bpms: number[];
  };
}

export interface SectionData {
  boundaries: number[];
  labels: string[];
  confidence: number[];
  similarities: number[][];
}

export interface EnergyBands {
  bass: number[];
  lowMid: number[];
  mid: number[];
  highMid: number[];
  treble: number[];
}

export interface SpectralAnalysis {
  times: number[];
  rms: number[];
  spectralCentroid: number[];
  spectralFlux: number[];
  spectralRolloff: number[];
  mfcc: number[][];
  energyBands: EnergyBands;
}

export interface TonalAnalysis {
  key: string;
  scale: string;
  keyConfidence: number;
  chromagram: number[][];
}

export interface MoodAnalysis {
  valence: number;
  energy: number;
  danceability: number;
  tags: string[];
}

export interface HarmonicPercussive {
  harmonicEnergy: number[];
  percussiveEnergy: number[];
}

export interface AudioAnalysis {
  metadata: AudioMetadata;
  rhythm: RhythmAnalysis;
  sections: SectionData;
  spectral: SpectralAnalysis;
  tonal: TonalAnalysis;
  mood: MoodAnalysis;
  onsets: number[];
  harmonicPercussive: HarmonicPercussive;
}

export interface AudioFeaturesAtTime {
  rms: number;
  spectralCentroid: number;
  spectralFlux: number;
  spectralRolloff: number;
  spectralFlatness: number;
  energyBands: {
    bass: number;
    lowMid: number;
    mid: number;
    highMid: number;
    treble: number;
  };
  harmonicEnergy: number;
  percussiveEnergy: number;
  onsetStrength: number;
}

export interface BeatState {
  isOnBeat: boolean;
  beatIndex: number;
  timeSinceLastBeat: number;
  timeToNextBeat: number;
  beatIntensity: number;
}
