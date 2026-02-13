# Music Visualizer — Project Guide

## What This Project Is

A web application that takes an audio file and a user prompt, analyzes the music (beats, sections, lyrics, mood), and generates a beat-synced visualization video. An LLM-powered conversational interface guides the user through thematic analysis, creative direction, iterative refinement, rendering, and post-render editing.

## Design Documentation

All detailed design documents live in `.context/`. Read the relevant document before working on that area of the codebase.

| Document | What It Covers |
|----------|---------------|
| [`.context/architecture.md`](.context/architecture.md) | System architecture, data flow (upload → analysis → chat → render → edit), API design, state management, error handling |
| [`.context/tech-stack.md`](.context/tech-stack.md) | All technology choices, monorepo structure, dependency versions, infrastructure |
| [`.context/audio-analysis.md`](.context/audio-analysis.md) | Audio analysis pipeline — Essentia.js (client), Librosa/Essentia (server), feature extraction, output schema, audio→visual parameter mapping |
| [`.context/lyrics-extraction.md`](.context/lyrics-extraction.md) | Lyrics pipeline — Genius API, Musixmatch, Demucs vocal separation, Whisper transcription, cross-referencing, thematic analysis prompt design |
| [`.context/video-generation.md`](.context/video-generation.md) | Video rendering — real-time preview (Three.js/Canvas), Remotion production render, visual templates, export presets, incremental re-rendering |
| [`.context/ai-visuals.md`](.context/ai-visuals.md) | AI image/video generation — Tier 1 (procedural), Tier 2 (AI keyframes + interpolation), Tier 3 (full AI video via Deforum/AnimateDiff), cost estimates |
| [`.context/conversational-loop.md`](.context/conversational-loop.md) | LLM conversation design — all 5 phases (analysis, refinement, confirmation, rendering, editing), prompt templates, context management, render spec schema |
| [`.context/api-integrations.md`](.context/api-integrations.md) | All third-party APIs — Gemini Flash, Genius, Musixmatch, Whisper, DALL-E 3, Stability AI, ComfyUI — auth, rate limits, costs, env vars |
| [`.context/ui-ux-design.md`](.context/ui-ux-design.md) | UI layout, user flow, component specs, visual design system (colors, typography), responsive design, accessibility, loading/error states |

## Architecture Summary

```
Browser (React/TypeScript)           Server (Python/FastAPI)
─────────────────────────           ────────────────────────
Essentia.js (WASM) ──→ BPM/beats   Librosa ──→ section detection
Meyda ──→ timbral features          Demucs ──→ vocal separation
Web Audio API ──→ playback/FFT      Whisper ──→ lyrics transcription
Three.js / Canvas ──→ preview       Genius/Musixmatch ──→ lyrics fetch
React chat UI ←──WebSocket──→       Gemini Flash ──→ thematic analysis
                                    Remotion ──→ video rendering
                                    DALL-E 3 / ComfyUI ──→ AI keyframes
```

## Monorepo Structure

```
Music_Visualizer/
├── CLAUDE.md              ← You are here
├── .context/              ← Design docs (read before coding)
├── client/                ← React frontend (Vite + TypeScript)
│   ├── src/
│   │   ├── components/    ← UI components (audio, chat, visualizer, timeline, export)
│   │   ├── hooks/         ← Custom React hooks
│   │   ├── stores/        ← Zustand state management
│   │   ├── services/      ← API client, WebSocket handlers
│   │   ├── lib/           ← Audio analysis wrappers (Essentia.js, Meyda)
│   │   ├── types/         ← TypeScript type definitions
│   │   └── remotion/      ← Remotion compositions and visual components
│   └── package.json
├── server/                ← Python backend (FastAPI)
│   ├── app/
│   │   ├── api/           ← Route handlers (audio, lyrics, chat, render, export)
│   │   ├── services/      ← Business logic (audio_analyzer, lyrics, llm, render, ai_image)
│   │   ├── models/        ← Pydantic models
│   │   ├── tasks/         ← Celery background tasks
│   │   └── main.py        ← FastAPI entry point
│   └── pyproject.toml
├── docker-compose.yml
└── .env.example
```

## Key Design Decisions

### LLM: Gemini Flash (Free Tier)
- Model: `gemini-2.0-flash` via Google AI Studio API
- Used for: thematic analysis, visualization suggestions, conversational refinement, edit interpretation
- Free tier: 15 RPM / 1M TPM / 1,500 requests/day
- See `.context/api-integrations.md` for details

### Audio Analysis: Hybrid Client + Server
- **Client (Essentia.js)**: Instant BPM/beat detection, spectral features — no upload needed for preview
- **Server (Librosa)**: Deep structural analysis (section segmentation), higher accuracy
- See `.context/audio-analysis.md` for the full feature list and output schema

### Video: Tiered Visual System
- **Tier 1**: Procedural (Three.js/Canvas/WebGL shaders driven by audio features) — real-time, free
- **Tier 2**: AI keyframes at section boundaries + procedural interpolation — 10-20 images/song
- **Tier 3** (Phase 2): Full AI video via Deforum/AnimateDiff/ComfyUI — GPU-intensive
- See `.context/ai-visuals.md` for implementation details

### Video Rendering: Remotion
- React components rendered frame-by-frame → MP4
- Built-in audio visualization (`visualizeAudio()`)
- Three.js integration via `@remotion/three`
- Frame-accurate beat sync (deterministic rendering)
- See `.context/video-generation.md` for composition structure and render pipeline

### Lyrics: Multi-Source with Cross-Reference
- Genius API → lyrics text
- Demucs → vocal separation → Whisper → word-level timestamps
- Cross-reference for accuracy
- Fallback: manual lyrics input + forced alignment
- See `.context/lyrics-extraction.md` for the full pipeline

## Core Features

1. **Audio analysis** — BPM, beats, sections, spectral features, key, mood, energy profile
2. **Lyrics extraction** — multi-source (Genius, Musixmatch, Whisper) with word-level timestamps
3. **Thematic analysis** — LLM-generated track description, themes, symbolism, pop culture references, per-section visualization suggestions
4. **Conversational refinement** — iterative chat until user is satisfied with visualization plan
5. **Real-time preview** — procedural beat-synced visuals in browser (Three.js/Canvas)
6. **Production render** — Remotion-based MP4 generation with AI keyframes
7. **Post-render editing** — natural language edit requests → incremental re-renders
8. **Visual templates** — Nebula, Geometric, Waveform, Cinematic, Retro, Nature, Abstract, Urban
9. **Export presets** — YouTube (16:9), TikTok/Reels (9:16), Instagram (1:1), Twitter, 4K, custom
10. **Timeline editor** — zoomable waveform, draggable beat/section markers, lyrics track, keyframe thumbnails
11. **Vocal separation** — Demucs for isolating vocals before transcription
12. **Template system** — pre-built visual styles as starting points, fully customizable via chat

## Development Commands

### Frontend (client/)
```bash
npm install          # Install dependencies
npm run dev          # Start Vite dev server
npm run build        # Production build
npm run test         # Run Vitest
npm run lint         # Run ESLint
npm run format       # Run Prettier
```

### Backend (server/)
```bash
pip install -r requirements.txt   # Install dependencies
uvicorn app.main:app --reload     # Start FastAPI dev server
celery -A app.tasks worker        # Start Celery worker
pytest                            # Run tests
ruff check .                      # Lint
ruff format .                     # Format
mypy .                            # Type check
```

### Docker
```bash
docker compose up        # Start all services
docker compose up -d     # Start detached
docker compose down      # Stop all services
```

## Environment Variables

Required:
```
GOOGLE_AI_API_KEY=       # Gemini Flash
GENIUS_API_TOKEN=        # Genius lyrics
```

Optional (enhanced features):
```
OPENAI_API_KEY=          # Whisper API + DALL-E 3
MUSIXMATCH_API_KEY=      # Additional lyrics source
STABILITY_API_KEY=       # Alternative image generation
COMFYUI_API_URL=         # Self-hosted AI image/video generation
```

See `.context/api-integrations.md` for the full list with auth details, rate limits, and costs.

## Coding Conventions

### TypeScript (Frontend)
- Strict mode enabled
- Functional components with hooks (no class components)
- Zustand for state (no Redux)
- TanStack Query for server state
- Path aliases: `@/components`, `@/hooks`, `@/stores`, `@/services`, `@/lib`, `@/types`
- File naming: `kebab-case.tsx` for components, `use-camel-case.ts` for hooks

### Python (Backend)
- Python 3.11+
- Type hints on all function signatures
- Pydantic models for all API request/response schemas
- Async handlers where I/O is involved
- Ruff for linting and formatting
- File naming: `snake_case.py`

### General
- No committed secrets — all API keys via environment variables
- All external API calls go through the server (never from client directly)
- Prefer editing existing files over creating new ones
- Keep implementations focused and minimal — no speculative features
