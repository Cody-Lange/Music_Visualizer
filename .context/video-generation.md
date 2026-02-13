# Video Generation Pipeline

## Overview

Video generation is split into two modes: a real-time procedural preview in the browser, and a production render on the server using Remotion. Both modes consume the same audio analysis data and render spec, ensuring what you preview is what you get.

---

## Real-Time Preview (Browser)

The browser preview provides instant visual feedback while the user refines their visualization concept. It runs at interactive frame rates (30-60fps) using Web Audio API + Three.js/Canvas.

### Architecture

```
Web Audio API AnalyserNode
        │
        ├──→ FFT data (frequency domain)
        ├──→ Time domain data (waveform)
        │
        ▼
Audio Feature Router
        │
        ├──→ Bass energy ──→ Background layer
        ├──→ Mid energy ──→ Midground layer
        ├──→ Treble energy ──→ Foreground layer
        ├──→ Beat triggers ──→ Pulse/flash effects
        ├──→ RMS ──→ Global brightness
        └──→ Spectral centroid ──→ Color temperature
                │
                ▼
    Three.js Scene / Canvas 2D / WebGL Shader
                │
                ▼
        <canvas> element (displayed to user)
```

### Visual Layers

The preview renderer supports composited visual layers:

| Layer | Z-Index | Content | Driven By |
|-------|---------|---------|-----------|
| Background | 0 | AI keyframe images (if available), solid color, or gradient | Section theme, color palette |
| Atmosphere | 1 | Fog, glow, ambient particles | RMS energy, spectral flatness |
| Midground | 2 | Geometric shapes, flowing lines, waveform viz | Mid-frequency energy, harmonic content |
| Foreground | 3 | Particles, sparks, reactive elements | Treble energy, percussive energy |
| Lyrics | 4 | Timed text overlay | Lyrics word timestamps |
| Effects | 5 | Flash on beat, screen shake, color shift | Beat onsets, section transitions |

### Visual Templates

Pre-built templates give users a starting point. Each template defines the visual components for each layer:

| Template | Style | Best For |
|----------|-------|----------|
| **Nebula** | Particle systems + volumetric fog | Ambient, electronic, dream pop |
| **Geometric** | Rotating polyhedra + wireframe meshes | EDM, house, techno |
| **Waveform** | Stylized audio waveform + spectrum bars | Hip-hop, rock, pop |
| **Cinematic** | AI keyframes + slow zoom/pan + film grain | Ballads, cinematic scores |
| **Retro** | Pixel art + CRT scanlines + neon colors | Synthwave, retrowave, 80s |
| **Nature** | Organic flows + fractal patterns + earth tones | Folk, acoustic, world music |
| **Abstract** | Shader-based generative art | Experimental, jazz, classical |
| **Urban** | Glitch effects + typography + concrete textures | Rap, grime, trap |

Templates are fully customizable — they serve as a starting point that the LLM can suggest modifications to.

---

## Production Render (Server — Remotion)

### Why Remotion

- **React-based**: Visual components are React components — same ecosystem as the frontend
- **Frame-accurate**: Every frame is deterministic. Beat at 1.234s = frame 37 at 30fps. No timing drift
- **Audio built-in**: `visualizeAudio()`, `useAudioData()`, `getWaveformPortion()` provide per-frame audio data
- **Three.js integration**: `@remotion/three` provides `<ThreeCanvas>` synced to `useCurrentFrame()`
- **Scalable**: Supports AWS Lambda for parallel rendering (optional)

### Render Composition Structure

```tsx
// Simplified Remotion composition structure
const MusicVisualizerComposition: React.FC<{
  renderSpec: RenderSpec;
  audioAnalysis: AudioAnalysis;
  lyrics: LyricsData;
}> = ({ renderSpec, audioAnalysis, lyrics }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Get current section based on time
  const currentSection = getCurrentSection(renderSpec.sections, currentTime);

  // Get audio features for this exact frame
  const audioFeatures = getAudioFeaturesAtTime(audioAnalysis, currentTime);

  // Get beat state (is this frame on a beat?)
  const beatState = getBeatState(audioAnalysis.rhythm.beats, currentTime);

  return (
    <AbsoluteFill>
      {/* Layer 0: Background */}
      <BackgroundLayer
        section={currentSection}
        aiKeyframe={currentSection.keyframeUrl}
        transition={getTransitionProgress(renderSpec.sections, currentTime)}
      />

      {/* Layer 1: Atmosphere */}
      <AtmosphereLayer
        energy={audioFeatures.rms}
        spectralFlatness={audioFeatures.spectralFlatness}
        palette={currentSection.colorPalette}
      />

      {/* Layer 2: Midground reactive elements */}
      <MidgroundLayer
        midEnergy={audioFeatures.energyBands.mid}
        harmonicEnergy={audioFeatures.harmonicEnergy}
        style={currentSection.motionStyle}
      />

      {/* Layer 3: Foreground particles */}
      <ForegroundLayer
        trebleEnergy={audioFeatures.energyBands.treble}
        percussiveEnergy={audioFeatures.percussiveEnergy}
        beatHit={beatState.isOnBeat}
      />

      {/* Layer 4: Lyrics overlay */}
      {renderSpec.lyrics.display && (
        <LyricsOverlay
          lyrics={lyrics}
          currentTime={currentTime}
          style={renderSpec.lyrics.style}
          animation={renderSpec.lyrics.animation}
        />
      )}

      {/* Layer 5: Beat effects */}
      <BeatEffectsLayer
        beatState={beatState}
        onsetStrength={audioFeatures.onsetStrength}
        sectionTransition={isNearSectionBoundary(renderSpec.sections, currentTime)}
      />
    </AbsoluteFill>
  );
};
```

### Render Pipeline

```
1. Receive render spec from client
2. Prepare assets:
   a. Audio file (converted to WAV if needed)
   b. AI keyframe images (downloaded/generated)
   c. Audio analysis JSON
   d. Lyrics JSON
3. Bundle Remotion composition with all data
4. Execute Remotion render:
   npx remotion render \
     --codec h264 \
     --image-format jpeg \
     --quality 80 \
     --frames-per-lambda 20 \
     MusicVisualizer \
     output.mp4
5. Stream progress via WebSocket (frame count / total frames)
6. Upload rendered MP4 to object storage
7. Return download URL to client
```

### Render Performance

| Resolution | FPS | Visual Complexity | Estimated Render Time (4-min song) |
|-----------|-----|-------------------|-----------------------------------|
| 720p | 30 | Procedural only (Tier 1) | 3-10 minutes |
| 1080p | 30 | Procedural + AI keyframes (Tier 2) | 5-15 minutes |
| 1080p | 60 | Procedural + AI keyframes (Tier 2) | 10-25 minutes |
| 4K | 30 | Full AI (Tier 3) | 30-60+ minutes |

Lambda parallelization can reduce these by 5-10x for Tier 1/2.

---

## Export Presets

Users can choose from pre-configured export settings:

| Preset | Resolution | Aspect Ratio | FPS | Target Platform |
|--------|-----------|--------------|-----|-----------------|
| **YouTube** | 1920x1080 | 16:9 | 30 | YouTube, Vimeo |
| **YouTube HD** | 1920x1080 | 16:9 | 60 | YouTube (high quality) |
| **TikTok / Reels** | 1080x1920 | 9:16 | 30 | TikTok, Instagram Reels, YouTube Shorts |
| **Instagram Square** | 1080x1080 | 1:1 | 30 | Instagram Feed |
| **Twitter/X** | 1280x720 | 16:9 | 30 | Twitter/X video |
| **4K** | 3840x2160 | 16:9 | 30 | High quality archive |
| **Custom** | User-defined | User-defined | User-defined | Any |

---

## Incremental Re-Rendering

When a user makes post-render edits, the system avoids full re-renders where possible:

### Strategies

1. **Section-level re-render**: If only one section changed (e.g., "change chorus colors to blue"), re-render only that section's frames and splice into the existing video via FFmpeg:
   ```
   ffmpeg -i original.mp4 -i rerendered_section.mp4 \
     -filter_complex "[0:v]trim=0:60[pre]; [1:v]...; [0:v]trim=90:180[post]; ..."
   ```

2. **Layer-level re-render**: If only lyrics styling changed, re-render the lyrics overlay layer and composite it onto the existing video.

3. **Full re-render**: If global parameters changed (template, overall style), a full re-render is needed.

### Edit Interpretation Flow

```
User: "Make the chorus more intense and add red tones"
  │
  ▼
Gemini Flash interprets:
  {
    "editType": "section_modification",
    "targetSections": ["chorus_1", "chorus_2"],
    "changes": {
      "colorPalette": { "add": ["#FF2D2D", "#CC0000"], "bias": "warm" },
      "intensity": { "multiplier": 1.5 },
      "effects": { "beatFlash": { "intensity": "high" } }
    }
  }
  │
  ▼
Render service determines: section-level re-render
  │
  ▼
Only chorus sections re-rendered → spliced into existing video
```

---

## Video Codec & Format

### Output Format

- **Container**: MP4 (H.264 video + AAC audio)
- **Video codec**: H.264 (libx264) — maximum compatibility
- **Audio codec**: AAC at 192kbps
- **Pixel format**: yuv420p (required for broad compatibility)
- **CRF**: 18 (high quality) to 23 (balanced quality/size)

### FFmpeg Final Encoding

```bash
ffmpeg -i remotion_output.mp4 -i original_audio.wav \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  -y output_final.mp4
```

The `-movflags +faststart` flag enables progressive playback (important for web delivery).
