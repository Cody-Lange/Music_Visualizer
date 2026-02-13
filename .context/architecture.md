# System Architecture

## Overview

The Music Visualizer is a hybrid client/server web application. The browser handles real-time audio analysis and preview rendering. The server handles deep analysis, lyrics processing, LLM conversations, and production video rendering.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     BROWSER (Client)                        │
│                                                             │
│  ┌──────────┐    ┌─────────────────┐    ┌───────────────┐  │
│  │  Audio    │───→│  Essentia.js    │───→│ Real-time     │  │
│  │  Upload   │    │  (WASM)         │    │ Preview       │  │
│  │          │    │  BPM, beats,    │    │ Three.js /    │  │
│  │          │    │  spectrum       │    │ Canvas / WebGL│  │
│  └──────────┘    └─────────────────┘    └───────────────┘  │
│       │                │                       ▲            │
│       │          ┌─────┴──────┐                │            │
│       │          │  Meyda     │          Visual params      │
│       │          │  (timbral) │          from audio          │
│       │          └────────────┘                              │
│       │                                                     │
│  ┌────┴─────────────────────────────────────────────────┐   │
│  │              Chat Interface (React)                   │   │
│  │  - Displays analysis results & suggestions            │   │
│  │  - User refinement via follow-up prompts              │   │
│  │  - Post-render edit prompts                           │   │
│  │  - WebSocket connection for real-time streaming        │   │
│  └───────────────────────┬──────────────────────────────┘   │
│                          │                                   │
│  ┌───────────────────────┴──────────────────────────────┐   │
│  │         Timeline / Waveform Editor (React)            │   │
│  │  - Zoomable waveform display                          │   │
│  │  - Beat markers (auto-detected, user-adjustable)      │   │
│  │  - Section boundaries (verse/chorus/bridge)           │   │
│  │  - Lyrics overlay with word-level timing              │   │
│  │  - Visual parameter keyframes                         │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
              REST API + WebSocket
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                     SERVER (Backend)                         │
│                                                             │
│  ┌───────────────────┐  ┌────────────────────────────────┐  │
│  │  FastAPI           │  │  Celery Workers                │  │
│  │  - /api/audio/*    │  │  - Audio analysis tasks        │  │
│  │  - /api/lyrics/*   │  │  - Lyrics transcription tasks  │  │
│  │  - /api/chat (WS)  │  │  - Video render tasks          │  │
│  │  - /api/render/*   │  │  - AI image generation tasks   │  │
│  │  - /api/export/*   │  │                                │  │
│  └───────┬───────────┘  └──────────┬─────────────────────┘  │
│          │                         │                         │
│  ┌───────┴─────────────────────────┴─────────────────────┐  │
│  │                  Service Layer                         │  │
│  │                                                       │  │
│  │  ┌─────────────────┐  ┌────────────────────────────┐  │  │
│  │  │ AudioAnalyzer   │  │ LyricsService              │  │  │
│  │  │ - Librosa       │  │ - Genius API               │  │  │
│  │  │ - Essentia (Py) │  │ - Musixmatch API           │  │  │
│  │  │ - Section detect│  │ - Whisper transcription     │  │  │
│  │  │ - Energy profile│  │ - Demucs vocal separation   │  │  │
│  │  └─────────────────┘  └────────────────────────────┘  │  │
│  │                                                       │  │
│  │  ┌─────────────────┐  ┌────────────────────────────┐  │  │
│  │  │ LLMService      │  │ RenderService              │  │  │
│  │  │ - Gemini Flash  │  │ - Remotion CLI             │  │  │
│  │  │ - Thematic      │  │ - FFmpeg                   │  │  │
│  │  │   analysis      │  │ - Frame composition        │  │  │
│  │  │ - Suggestions   │  │                            │  │  │
│  │  │ - Edit parsing  │  │                            │  │  │
│  │  └─────────────────┘  └────────────────────────────┘  │  │
│  │                                                       │  │
│  │  ┌─────────────────┐                                  │  │
│  │  │ AIImageService  │                                  │  │
│  │  │ - DALL-E 3      │                                  │  │
│  │  │ - Stable Diff   │                                  │  │
│  │  │ - ComfyUI API   │                                  │  │
│  │  └─────────────────┘                                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────┐  ┌──────────┐  ┌────────────────────────┐ │
│  │ Redis       │  │ SQLite / │  │ MinIO / S3             │ │
│  │ (task queue │  │ Postgres │  │ (audio uploads,        │ │
│  │  + cache)   │  │ (metadata│  │  rendered videos,      │ │
│  │             │  │  + state)│  │  AI keyframes)         │ │
│  └─────────────┘  └──────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Phase 1: Upload & Analysis

```
1. User uploads audio file (browser)
2. Client-side analysis begins immediately (Essentia.js):
   - BPM estimation
   - Beat positions (timestamps)
   - Spectral features per frame
   → Results displayed in real-time as waveform + beat markers
3. Audio file uploaded to server (multipart form)
4. Server queues deep analysis (Celery):
   a. Librosa: section segmentation, chromagram, detailed onset detection
   b. Demucs: vocal/instrument separation
   c. Whisper: lyrics transcription from isolated vocals (word-level timestamps)
   d. Genius/Musixmatch: lyrics fetch by metadata (if song identified)
   e. Cross-reference transcribed lyrics with fetched lyrics for accuracy
5. Analysis results streamed back via WebSocket as they complete
6. Client merges server analysis with client-side analysis
7. Timeline UI populated with beats, sections, and lyrics
```

### Phase 2: Thematic Analysis & Suggestions

```
1. Full analysis payload sent to Gemini Flash:
   - Audio metadata (BPM, key, energy profile, section structure)
   - Lyrics (with timestamps)
   - User's initial prompt/description
2. LLM generates structured response:
   - Track description and mood summary
   - Section-by-section breakdown with:
     - Emotional arc
     - Lyrical themes and symbolism
     - Pop culture references
     - Visualization suggestions (colors, motion, imagery, intensity)
   - Overall visual concept recommendation
3. Response streamed to chat UI via WebSocket
```

### Phase 3: Conversational Refinement

```
1. User responds with feedback/questions in chat
2. LLM has full context (analysis + prior messages)
3. LLM refines suggestions based on user input
4. Loop continues until user signals satisfaction
5. Final agreed-upon visualization plan is structured as a "render spec":
   {
     globalStyle: { ... },
     sections: [
       {
         startTime, endTime, label,
         visualTheme, colorPalette, motionStyle,
         intensity, aiPrompt (for keyframe generation),
         transitionIn, transitionOut
       },
       ...
     ],
     lyrics: { display: true, style: "...", animation: "..." },
     exportSettings: { resolution, fps, format, aspectRatio }
   }
```

### Phase 4: Rendering

```
1. Render spec submitted to server
2. Server orchestrates render pipeline:
   a. (Tier 2) AI keyframe generation at section boundaries
      - One image per section using the section's aiPrompt
      - Generated via DALL-E 3 API or ComfyUI
   b. Remotion composition assembled:
      - Audio track loaded
      - Beat data → visual keyframes
      - Section data → theme transitions
      - AI keyframes → background imagery with procedural interpolation
      - Lyrics → timed text overlays
      - Spectral data → real-time reactive elements (particles, shapes, glow)
   c. Remotion renders to MP4 via headless browser + FFmpeg
3. Progress streamed to client via WebSocket (% complete, current frame)
4. Rendered video stored in object storage
5. Download link sent to client
```

### Phase 5: Post-Render Editing

```
1. User watches rendered video in browser
2. User submits edit prompt in chat:
   "Make the chorus transition more explosive"
   "Change the verse colors to deep blue"
   "Add more particle effects during the bridge"
3. LLM interprets edit → modifies render spec
4. Only affected sections re-rendered (incremental rendering)
5. Updated video delivered to client
```

---

## API Design

### REST Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/audio/upload` | Upload audio file, returns job ID |
| GET | `/api/audio/{job_id}/analysis` | Get analysis results |
| GET | `/api/audio/{job_id}/waveform` | Get waveform data for visualization |
| POST | `/api/lyrics/fetch` | Fetch lyrics from external services |
| GET | `/api/lyrics/{job_id}` | Get transcribed/fetched lyrics |
| POST | `/api/render/start` | Submit render spec, returns render job ID |
| GET | `/api/render/{job_id}/status` | Get render progress |
| GET | `/api/render/{job_id}/download` | Download rendered video |
| POST | `/api/render/{job_id}/edit` | Submit edit to existing render |

### WebSocket Endpoints

| Path | Purpose |
|------|---------|
| `/ws/chat/{session_id}` | LLM conversation (streamed responses) |
| `/ws/progress/{job_id}` | Real-time progress updates for analysis/render jobs |

---

## State Management

### Client State (Zustand Stores)

| Store | Responsibilities |
|-------|-----------------|
| `audioStore` | Uploaded file, playback state, audio buffer |
| `analysisStore` | BPM, beats, sections, spectral data, lyrics |
| `chatStore` | Conversation history, render spec |
| `visualizerStore` | Preview parameters, active template, visual overrides |
| `renderStore` | Render job status, progress, download URL |
| `exportStore` | Export settings (resolution, fps, aspect ratio, format) |

### Server State

| Storage | Data |
|---------|------|
| Redis | Celery task state, WebSocket session mapping, analysis cache |
| SQLite/Postgres | Session metadata, render specs, user preferences |
| MinIO/S3 | Audio files, rendered videos, AI-generated keyframes |

---

## Error Handling Strategy

1. **Client-side analysis failure**: Fall back to server-side only analysis; show degraded waveform
2. **Lyrics not found**: Inform user; offer manual lyrics input; proceed with audio-only analysis
3. **Whisper transcription low confidence**: Flag uncertain segments; show confidence scores; allow manual correction
4. **LLM API failure**: Retry with exponential backoff (3 attempts); fall back to template-based suggestions
5. **Render failure**: Save progress; allow resume; provide error details in chat
6. **AI image generation failure**: Fall back to Tier 1 procedural visuals for affected sections

---

## Security Considerations

- Audio files validated on upload (file type, size limits, magic bytes)
- Rate limiting on all API endpoints
- WebSocket connections authenticated via session tokens
- Uploaded files scanned and stored in isolated object storage
- No user audio data shared with third parties beyond necessary API calls (Whisper, Genius)
- LLM prompts sanitized to prevent injection
- CORS configured for frontend origin only
