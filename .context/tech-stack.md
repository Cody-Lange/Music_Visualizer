# Technology Stack

## Overview

This document defines the technology choices for the Music Visualizer application. The stack is split into a browser client (TypeScript/React) and a Python server backend, connected via REST/WebSocket APIs.

---

## Frontend

| Technology | Purpose | Version Target |
|-----------|---------|----------------|
| **React 18+** | UI framework | Latest stable |
| **TypeScript** | Type safety across the entire frontend | 5.x |
| **Vite** | Build tool and dev server | Latest stable |
| **Tailwind CSS** | Utility-first styling | 3.x |
| **Essentia.js** | Client-side audio analysis (BPM, beats, spectral features) via WebAssembly | Latest |
| **Meyda** | Lightweight timbral feature extraction (MFCC, spectral centroid/flux) | Latest |
| **Web Audio API** | Real-time audio playback and FFT via `AnalyserNode` | Browser native |
| **Three.js** | 3D procedural visualizations | Latest stable |
| **React Three Fiber** | React bindings for Three.js | Latest stable |
| **Remotion** | Programmatic video composition and rendering | 4.x |
| **@remotion/three** | Three.js integration within Remotion compositions | 4.x |
| **Zustand** | Lightweight state management | Latest stable |
| **React Query (TanStack Query)** | Server state management, caching, and data fetching | Latest stable |

### Frontend Dev Tooling

| Tool | Purpose |
|------|---------|
| **ESLint** | Linting |
| **Prettier** | Code formatting |
| **Vitest** | Unit testing |
| **Playwright** | E2E testing |

---

## Backend

| Technology | Purpose | Version Target |
|-----------|---------|----------------|
| **Python 3.11+** | Backend language | 3.11+ |
| **FastAPI** | REST API framework | Latest stable |
| **WebSockets (FastAPI)** | Real-time communication for chat/progress | Built-in |
| **Librosa** | Deep audio analysis (section segmentation, chromagram, onset detection) | Latest stable |
| **Essentia (Python)** | Additional MIR capabilities (rhythm extraction, mood/genre classification) | Latest stable |
| **Demucs** | Vocal/instrument source separation | Latest stable |
| **OpenAI Whisper** | Lyrics transcription with word-level timestamps | Latest stable |
| **FFmpeg** | Audio format conversion and final video encoding | 6.x |
| **Celery + Redis** | Background task queue for long-running renders | Latest stable |
| **SQLite → PostgreSQL** | Metadata storage (SQLite for dev, PostgreSQL for production) | Latest |
| **MinIO / S3** | Object storage for uploaded audio and rendered videos | Latest |

### Backend Dev Tooling

| Tool | Purpose |
|------|---------|
| **Ruff** | Linting and formatting |
| **pytest** | Testing |
| **mypy** | Static type checking |
| **Docker / Docker Compose** | Containerization for local dev and deployment |

---

## LLM Integration

| Service | Purpose | Notes |
|---------|---------|-------|
| **Google Gemini Flash** | Primary LLM for thematic analysis, visualization suggestions, conversational loop, and post-render edit interpretation | Free tier; model: `gemini-2.0-flash` |

### Gemini Flash Usage

- **Thematic analysis**: Receives lyrics + audio metadata (BPM, key, genre, mood, energy profile) and generates track description, themes, symbolism, pop culture references, and per-section visualization suggestions
- **Conversational refinement**: Powers the iterative chat where users refine visualization ideas
- **Edit interpretation**: Parses natural language edit requests ("make the chorus more intense", "change colors at 1:30 to blue") into structured parameter changes
- **API access**: Via Google AI Studio / Vertex AI free tier
- **Rate limits**: Free tier allows 15 RPM / 1M TPM for Flash — sufficient for single-user sessions

---

## AI Image Generation (Tier 2)

| Service | Purpose | Notes |
|---------|---------|-------|
| **Stable Diffusion (via ComfyUI API)** | Self-hosted keyframe image generation | Requires GPU; full control |
| **DALL-E 3 (OpenAI API)** | Cloud fallback for keyframe generation | $0.04-0.08/image |
| **Stability AI API** | Alternative cloud image generation | Per-image cost |

The system is designed to be provider-agnostic for image generation. The default for MVP is DALL-E 3 via API for simplicity; self-hosted ComfyUI is the long-term target for cost control.

---

## AI Video Generation (Tier 3 — Phase 2)

| Technology | Purpose | Notes |
|-----------|---------|-------|
| **Deforum** | Keyframe-based SD animation with camera motion controls | Beat-sync via audio feature mapping |
| **AnimateDiff** | Temporal consistency for SD video clips | 16-32 frame coherent clips |
| **ComfyUI** | Orchestration of AI video generation pipelines | Node-based workflow via API |

Tier 3 is reserved for Phase 2 after the core product is stable.

---

## Infrastructure

| Component | Technology | Notes |
|-----------|-----------|-------|
| **Containerization** | Docker + Docker Compose | All services containerized |
| **Reverse Proxy** | Nginx | Serves frontend, proxies API, handles WebSocket upgrades |
| **Task Queue** | Celery + Redis | Background render jobs |
| **Object Storage** | MinIO (dev) / S3 (prod) | Audio uploads and rendered videos |
| **Video Rendering** | Remotion Lambda (optional) | Parallel rendering for scale |
| **GPU Server** | RunPod / Baseten / self-hosted | Required only for Tier 2/3 AI visuals |

---

## Monorepo Structure

```
Music_Visualizer/
├── CLAUDE.md
├── .context/                    # Design documents (this directory)
├── client/                      # React frontend (Vite)
│   ├── src/
│   │   ├── components/          # React components
│   │   │   ├── ui/              # Shared UI primitives
│   │   │   ├── audio/           # Audio upload, waveform, player
│   │   │   ├── chat/            # Conversational interface
│   │   │   ├── visualizer/      # Real-time preview (Three.js/Canvas)
│   │   │   ├── timeline/        # Waveform timeline with beat/section markers
│   │   │   └── export/          # Export settings and progress
│   │   ├── hooks/               # Custom React hooks
│   │   ├── stores/              # Zustand stores
│   │   ├── services/            # API client, WebSocket handlers
│   │   ├── lib/                 # Audio analysis (Essentia.js, Meyda wrappers)
│   │   ├── types/               # TypeScript type definitions
│   │   └── remotion/            # Remotion compositions
│   │       ├── compositions/    # Video templates
│   │       ├── components/      # Remotion-specific visual components
│   │       └── utils/           # Frame/time/audio utilities
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── server/                      # Python backend (FastAPI)
│   ├── app/
│   │   ├── api/                 # Route handlers
│   │   │   ├── audio.py         # Audio upload and analysis endpoints
│   │   │   ├── lyrics.py        # Lyrics fetch/transcription endpoints
│   │   │   ├── chat.py          # LLM conversation endpoints (WebSocket)
│   │   │   ├── render.py        # Video render job endpoints
│   │   │   └── export.py        # Video download/export endpoints
│   │   ├── services/            # Business logic
│   │   │   ├── audio_analyzer.py
│   │   │   ├── lyrics_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── render_service.py
│   │   │   └── ai_image_service.py
│   │   ├── models/              # Pydantic models / DB schemas
│   │   ├── tasks/               # Celery background tasks
│   │   ├── config.py            # App configuration
│   │   └── main.py              # FastAPI app entry point
│   ├── tests/
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Key Dependency Versions (Pinning Strategy)

- Pin **major** versions in package.json / requirements.txt
- Use lockfiles (package-lock.json / pip-compile) for reproducible builds
- Renovate or Dependabot for automated dependency updates
