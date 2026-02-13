# Audio Analysis Pipeline

## Overview

Audio analysis is the foundation of the entire visualizer. We extract rhythmic, tonal, structural, and timbral features from the uploaded audio to drive every visual element. Analysis happens in two parallel stages: fast client-side analysis for immediate preview, and deep server-side analysis for production rendering.

---

## Client-Side Analysis (Browser)

### Essentia.js (WebAssembly)

Primary library for in-browser analysis. Runs entirely on the client — no upload required for initial analysis.

**Features extracted:**
| Feature | Method | Use in Visualizer |
|---------|--------|-------------------|
| BPM / Tempo | `RhythmExtractor` | Base pulse for all rhythmic visual elements |
| Beat positions | `BeatTrackerMultiFeature` | Precise timestamps for visual "hits" (flash, scale, color shift) |
| Key / Scale | `KeyExtractor` | Inform color palette selection (major = bright, minor = dark) |
| Spectral centroid | `SpectralCentroid` | Brightness/sharpness of visual elements |
| Spectral energy bands | `EnergyBandRatio` | Drive specific visual layers (bass → background, mids → midground, highs → foreground) |
| Onset detection | `OnsetDetection` | Trigger particle bursts, shape transitions |

**Performance characteristics:**
- WASM bundle: ~2-5 MB (loaded once, cached)
- Analysis of a 4-minute track: ~3-8 seconds on modern hardware
- Real-time feature extraction during playback: achievable at 60fps

### Meyda (Supplementary)

Lightweight per-frame feature extraction during audio playback to supplement Essentia.js with timbral features.

**Features extracted:**
| Feature | Use in Visualizer |
|---------|-------------------|
| RMS (loudness) | Overall intensity / brightness |
| MFCC (13 coefficients) | Timbral texture — map to shader parameters |
| Spectral flux | Rate of spectral change → visual turbulence |
| Spectral rolloff | High-frequency content → sparkle/shimmer effects |
| Spectral flatness | Noise vs. tonal → organic vs. geometric shapes |
| ZCR (zero crossing rate) | Percussive vs. harmonic → sharp vs. smooth edges |

**Performance:**
- ~288 operations/sec (3.3x real-time)
- Negligible bundle size
- Runs in Web Audio API processing graph via `MeydaAnalyzer`

### Web Audio API (Native)

Used for:
- Audio playback and routing
- Real-time FFT data via `AnalyserNode` (powers the live spectrum display)
- Audio buffer decoding for offline analysis

---

## Server-Side Analysis (Python)

### Librosa

Deep structural analysis that runs after the user uploads audio for production rendering.

**Features extracted:**
| Feature | Method | Use in Visualizer |
|---------|--------|-------------------|
| Section segmentation | `librosa.segment.recurrence_matrix` + spectral clustering | Define visual "scenes" — each section gets its own theme |
| Chromagram | `librosa.feature.chroma_cqt` | Harmonic content over time — map to color hue rotation |
| Detailed onset envelope | `librosa.onset.onset_strength` | Fine-grained visual reactivity curve |
| Mel spectrogram | `librosa.feature.melspectrogram` | Full spectral representation for heatmap/landscape visuals |
| Harmonic/percussive separation | `librosa.effects.hpss` | Separate visual layers for harmonic (flowing) vs. percussive (impact) |
| Tempo curve | `librosa.feature.tempogram` | Detect tempo changes for dynamic visual pacing |
| Energy contour | RMS energy over time | Drive overall visual intensity / brightness envelope |

**Section detection pipeline:**
```
1. Compute mel spectrogram
2. Build recurrence matrix (self-similarity)
3. Apply spectral clustering to identify repeating structures
4. Label sections by similarity (A, B, C...) and position (intro, verse, chorus, bridge, outro)
5. Estimate section labels using heuristics:
   - First unique section → intro
   - Most repeated section → chorus
   - Section before chorus → verse (pre-chorus if short)
   - Unique section in latter half → bridge
   - Final section → outro
6. Return section boundaries with labels and confidence scores
```

**Expected accuracy:** 70-85% on pop/rock/electronic. Lower on jazz, classical, and experimental genres. The timeline UI allows manual correction.

### Essentia (Python)

Supplementary to Librosa for features Librosa doesn't cover well:

| Feature | Method | Use |
|---------|--------|-----|
| Mood classification | Pre-trained ML models | Inform LLM analysis and visual theme suggestions |
| Genre classification | Pre-trained ML models | Constrain visualization style suggestions |
| Danceability | `Danceability` algorithm | Scale of visual motion/energy |
| Vocal/instrumental ratio | Activity detection | When to emphasize lyrics vs. abstract visuals |

---

## Analysis Output Schema

All analysis results are unified into a single JSON structure shared between client and server:

```typescript
interface AudioAnalysis {
  metadata: {
    filename: string;
    duration: number;       // seconds
    sampleRate: number;
    channels: number;
    format: string;         // "mp3", "wav", "flac", etc.
  };

  rhythm: {
    bpm: number;
    bpmConfidence: number;  // 0-1
    beats: number[];        // timestamps in seconds
    downbeats: number[];    // timestamps of downbeats (beat 1 of each measure)
    timeSignature: number;  // 4, 3, 6, etc.
    tempoStable: boolean;   // whether BPM is consistent throughout
    tempoCurve?: {          // if tempo varies
      times: number[];
      bpms: number[];
    };
  };

  sections: {
    boundaries: number[];   // timestamps of section starts
    labels: string[];       // "intro", "verse", "chorus", "bridge", "outro", etc.
    confidence: number[];   // confidence per section boundary
    similarities: number[][]; // which sections are repeats of each other
  };

  spectral: {
    // Per-frame data (at ~30-60fps resolution)
    times: number[];
    rms: number[];              // loudness envelope
    spectralCentroid: number[]; // brightness
    spectralFlux: number[];     // rate of change
    spectralRolloff: number[];  // high frequency content
    mfcc: number[][];           // 13 coefficients per frame
    energyBands: {
      bass: number[];           // 20-250 Hz
      lowMid: number[];         // 250-500 Hz
      mid: number[];            // 500-2000 Hz
      highMid: number[];        // 2000-4000 Hz
      treble: number[];         // 4000-20000 Hz
    };
  };

  tonal: {
    key: string;            // "C", "F#", etc.
    scale: string;          // "major", "minor"
    keyConfidence: number;
    chromagram: number[][];  // 12 pitch classes over time
  };

  mood: {
    valence: number;        // -1 (sad) to 1 (happy)
    energy: number;         // 0 (calm) to 1 (energetic)
    danceability: number;   // 0-1
    tags: string[];         // ["melancholic", "uplifting", "aggressive", etc.]
  };

  onsets: number[];         // all detected onset timestamps

  harmonicPercussive: {
    harmonicEnergy: number[];  // per-frame harmonic energy
    percussiveEnergy: number[]; // per-frame percussive energy
  };
}
```

---

## Audio Feature → Visual Parameter Mapping

This is the core mapping that drives the procedural visualization engine:

| Audio Feature | Visual Parameter | Mapping |
|--------------|-----------------|---------|
| Beat onset | Scale pulse / flash | Trigger on each beat; intensity ∝ onset strength |
| Bass energy | Background movement | Low-frequency energy → slow zoom / displacement |
| Mid energy | Midground shapes | Mid-frequency energy → shape size / rotation speed |
| Treble energy | Foreground particles | High-frequency energy → particle count / speed |
| RMS (loudness) | Overall brightness | Linear mapping with gamma correction |
| Spectral centroid | Color temperature | Low centroid → warm (reds/oranges), high → cool (blues/whites) |
| Spectral flux | Visual turbulence | High flux → rapid changes, distortion, glitch effects |
| MFCC coefficients | Shader parameters | Map 13 MFCCs to various shader uniforms for timbral texture |
| Key/scale | Color palette base | Major keys → brighter palettes, minor → darker/moodier |
| Section changes | Scene transitions | Cross-fade, morph, or cut between visual themes |
| Harmonic energy | Flowing/organic elements | Curves, waves, smooth motion |
| Percussive energy | Impact elements | Sharp edges, flashes, geometric bursts |
| Tempo stability | Motion smoothness | Stable tempo → consistent motion; variable → erratic |

---

## Performance Optimization

### Client-Side
- **Web Workers**: Run Essentia.js analysis in a Web Worker to keep UI responsive
- **Chunked processing**: Analyze audio in chunks for progress reporting
- **Caching**: Cache analysis results in IndexedDB keyed by audio file hash
- **Downsampling**: For real-time preview, use lower resolution spectral data (30fps vs. 60fps)

### Server-Side
- **Parallel analysis**: Run Librosa, Essentia, and Demucs in parallel Celery tasks
- **Audio preprocessing**: Convert to WAV (mono, 22050 Hz) once; all analyzers use the same preprocessed file
- **Incremental results**: Stream partial results via WebSocket as each analyzer completes
- **Result caching**: Cache analysis results by audio file content hash in Redis (TTL: 24 hours)
