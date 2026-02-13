# Music Visualizer

A web application that takes an audio file and a user prompt, analyzes the music (beats, sections, lyrics, mood), and generates a beat-synced visualization video. An LLM-powered conversational interface guides the user through creative direction, iterative refinement, rendering, and post-render editing.

## Features

- **Audio Analysis** — BPM, beats, sections, spectral features, key detection, mood estimation, energy profiles
- **Lyrics Extraction** — Multi-source (Genius API, Whisper transcription) with word-level timestamps
- **Thematic Analysis** — LLM-generated track description, themes, symbolism, pop culture references, per-section visualization suggestions
- **Conversational Refinement** — Iterative chat until the user is satisfied with the visualization plan
- **Real-Time Preview** — Procedural beat-synced visuals in the browser (Three.js / WebGL)
- **Production Render** — Remotion-based MP4 generation with AI keyframes
- **Post-Render Editing** — Natural language edit requests with incremental re-renders
- **10 Visual Templates** — Nebula, Geometric, Waveform, Cinematic, Retro, Nature, Abstract, Urban, Glitchbreak, 90s Anime
- **Export Presets** — YouTube (16:9), TikTok/Reels (9:16), Instagram (1:1), Twitter, 4K, custom
- **Timeline Editor** — Zoomable waveform, draggable beat/section markers, lyrics track
- **Vocal Separation** — Demucs for isolating vocals before transcription

## Architecture

```
Browser (React / TypeScript)            Server (Python / FastAPI)
─────────────────────────────           ─────────────────────────
Web Audio API  → playback / FFT        Librosa     → section detection
Meyda          → timbral features      Demucs      → vocal separation
Three.js       → real-time preview     Whisper     → lyrics transcription
Remotion       → video rendering       Genius API  → lyrics text
React UI  ←── WebSocket ──→            Gemini Flash → thematic analysis
                                       FFmpeg       → video encoding
```

## Project Structure

```
Music_Visualizer/
├── client/                 ← React frontend (Vite + TypeScript)
│   ├── src/
│   │   ├── components/     ← UI components (audio, chat, visualizer, timeline, export)
│   │   ├── hooks/          ← Custom React hooks (audio features, WebSocket)
│   │   ├── stores/         ← Zustand state management (6 stores)
│   │   ├── services/       ← API client, WebSocket handler
│   │   ├── lib/            ← Audio analysis wrappers
│   │   ├── types/          ← TypeScript type definitions
│   │   ├── remotion/       ← Remotion compositions and visual layers
│   │   └── tests/          ← Vitest test suites
│   └── package.json
├── server/                 ← Python backend (FastAPI)
│   ├── app/
│   │   ├── api/            ← Route handlers (audio, lyrics, chat, render)
│   │   ├── services/       ← Business logic (audio analyzer, lyrics, LLM, render)
│   │   ├── models/         ← Pydantic models (audio, lyrics, render, chat)
│   │   ├── tasks/          ← Celery background tasks
│   │   └── main.py         ← FastAPI entry point
│   └── tests/              ← Pytest test suites
├── .context/               ← Design documentation
├── docker-compose.yml
├── CLAUDE.md               ← Project guide for AI-assisted development
└── .env.example
```

## Quick Start

### Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- **FFmpeg** (for video rendering)
- **Redis** (for Celery task queue)

### Environment Variables

Copy `.env.example` and fill in your API keys:

```bash
cp .env.example .env
```

Required:
```
GOOGLE_AI_API_KEY=       # Gemini Flash (free tier)
GENIUS_API_TOKEN=        # Genius lyrics API
```

Optional (enhanced features):
```
OPENAI_API_KEY=          # Whisper API + DALL-E 3
MUSIXMATCH_API_KEY=      # Additional lyrics source
STABILITY_API_KEY=       # Alternative image generation
COMFYUI_API_URL=         # Self-hosted AI image/video generation
```

### Backend Setup

```bash
cd server
pip install -r requirements.txt
uvicorn app.main:app --reload          # Start FastAPI dev server on :8000
celery -A app.tasks worker             # Start Celery worker (separate terminal)
```

### Frontend Setup

```bash
cd client
npm install
npm run dev                            # Start Vite dev server on :5173
```

### Docker (All Services)

```bash
docker compose up                      # Start server, worker, redis, client
docker compose up -d                   # Start detached
docker compose down                    # Stop all services
```

## Development

### Frontend Commands

```bash
cd client
npm run dev          # Start dev server with HMR
npm run build        # Production build (tsc + vite)
npm run test         # Run Vitest test suites
npm run test:watch   # Run tests in watch mode
npm run lint         # Run ESLint
npm run format       # Run Prettier
```

### Backend Commands

```bash
cd server
uvicorn app.main:app --reload     # Dev server with auto-reload
pytest                            # Run test suites
pytest -v                         # Verbose test output
ruff check .                      # Lint
ruff format .                     # Format
mypy .                            # Type check
```

## Testing

### Backend Tests (pytest)

The server has comprehensive test coverage across models, services, and API routes:

| Test File | What It Covers |
|-----------|---------------|
| `test_models.py` | Pydantic model validation — field constraints, defaults, Literal types, serialization |
| `test_storage.py` | JobStore CRUD operations, thread safety (concurrent access) |
| `test_audio_analyzer.py` | Audio metadata extraction, rhythm analysis, energy bands, tonal analysis, mood estimation, section labeling |
| `test_lyrics_service.py` | Lyrics parsing, header/footer stripping, word splitting, edge cases |
| `test_render_service.py` | FFmpeg filter building, section colors, template color lookup |
| `test_config.py` | Settings computed properties (CORS, upload limits, directory paths) |
| `test_api_audio.py` | Upload validation (format, size), analysis endpoints, waveform endpoint |
| `test_api_lyrics.py` | Lyrics fetch/get endpoints, job attachment |
| `test_api_render.py` | Render start/status/download/edit endpoints |
| `test_health.py` | Health check endpoint |

### Frontend Tests (Vitest)

The client has test coverage for all stores, utility functions, and core services:

| Test File | What It Covers |
|-----------|---------------|
| `stores/audio-store.test.ts` | File management, URL lifecycle, volume clamping, reset |
| `stores/analysis-store.test.ts` | Analysis/lyrics state, progress tracking |
| `stores/chat-store.test.ts` | Message management, streaming state, session IDs |
| `stores/export-store.test.ts` | Preset switching, resolution/fps/aspect ratio, custom mode |
| `stores/render-store.test.ts` | Render lifecycle (idle → rendering → complete/error) |
| `stores/visualizer-store.test.ts` | Template selection, preview state |
| `utils/audio-helpers.test.ts` | Section lookup, beat state detection, feature interpolation (binary search) |
| `lib/audio-context.test.ts` | Energy band extraction, frequency band normalization |
| `services/websocket.test.ts` | WebSocket connection, message handling, disconnect/reconnect |

## Tech Stack

### Frontend
- **React 18** with TypeScript (strict mode)
- **Vite** — build tool and dev server
- **Zustand** — state management (6 domain stores)
- **TanStack Query** — server state caching
- **Three.js / React Three Fiber** — 3D visualizations
- **Meyda** — real-time audio feature extraction
- **Remotion** — programmatic video rendering
- **Tailwind CSS** — utility-first styling
- **Vitest** — test runner

### Backend
- **FastAPI** — async Python web framework
- **Librosa** — audio analysis (BPM, sections, spectral features)
- **lyricsgenius** — Genius API client
- **google-generativeai** — Gemini Flash 2.0 LLM
- **Celery + Redis** — background task queue
- **FFmpeg** — video encoding
- **Pydantic** — data validation and serialization
- **pytest** — test runner

## Design Documentation

Detailed design documents are in the `.context/` directory:

| Document | Topic |
|----------|-------|
| `architecture.md` | System architecture, data flow, API design |
| `tech-stack.md` | Technology choices, dependencies, infrastructure |
| `audio-analysis.md` | Analysis pipeline, output schema, audio-to-visual mapping |
| `lyrics-extraction.md` | Multi-source lyrics pipeline, thematic analysis prompts |
| `video-generation.md` | Remotion render, visual templates, export presets |
| `ai-visuals.md` | Tiered AI visual generation (procedural → keyframes → full AI) |
| `conversational-loop.md` | LLM conversation phases, render spec schema |
| `api-integrations.md` | Third-party APIs, auth, rate limits, costs |
| `ui-ux-design.md` | UI layout, design system, accessibility |

## License

This project is for personal/educational use.
