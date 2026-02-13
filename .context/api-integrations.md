# API Integrations & External Services

## Overview

This document details all third-party APIs and external services the application integrates with, including authentication, rate limits, costs, and fallback strategies.

---

## 1. Google Gemini Flash (Primary LLM)

### Purpose
- Thematic analysis of lyrics and audio
- Visualization suggestions and creative direction
- Conversational refinement loop
- Post-render edit interpretation (natural language → structured edits)

### Access
- **API**: Google AI Studio (Generative AI API)
- **Model**: `gemini-2.0-flash`
- **Authentication**: API key via `GOOGLE_AI_API_KEY` environment variable
- **SDK**: `google-generativeai` Python package

### Rate Limits (Free Tier)
| Metric | Limit |
|--------|-------|
| Requests per minute | 15 |
| Tokens per minute | 1,000,000 |
| Requests per day | 1,500 |

These limits are sufficient for single-user development and small-scale usage. For production, upgrade to the pay-as-you-go tier.

### Integration Pattern
```python
import google.generativeai as genai

genai.configure(api_key=os.environ["GOOGLE_AI_API_KEY"])

model = genai.GenerativeModel("gemini-2.0-flash")

# Streaming response for chat
async def stream_llm_response(messages: list[dict], system_prompt: str):
    chat = model.start_chat(history=messages)
    response = chat.send_message(
        messages[-1]["content"],
        stream=True,
        generation_config={
            "temperature": 0.8,       # creative but focused
            "top_p": 0.95,
            "max_output_tokens": 4096,
        },
        safety_settings={...},
    )
    for chunk in response:
        yield chunk.text
```

### Fallback
- If Gemini API is unreachable: retry 3 times with exponential backoff
- If rate limited: queue requests with delay
- If API key invalid: display error and instruct user to configure API key

---

## 2. Genius API (Lyrics Database)

### Purpose
- Fetch song lyrics by title and artist
- Retrieve song metadata (album, release date, annotations)

### Access
- **API**: REST API at `https://api.genius.com`
- **Authentication**: OAuth2 access token via `GENIUS_API_TOKEN` environment variable
- **SDK**: `lyricsgenius` Python package
- **Sign up**: https://genius.com/api-clients

### Rate Limits
| Metric | Limit |
|--------|-------|
| Requests per second | ~5 (unofficial) |
| Daily limit | No hard limit (reasonable use) |

### How Lyrics Are Fetched
The Genius API returns song metadata but not lyrics directly. The `lyricsgenius` library handles scraping:

```python
import lyricsgenius

genius = lyricsgenius.Genius(os.environ["GENIUS_API_TOKEN"])
genius.verbose = False
genius.remove_section_headers = False  # Keep [Verse], [Chorus] markers

song = genius.search_song(title="Bohemian Rhapsody", artist="Queen")
if song:
    lyrics_text = song.lyrics
    song_url = song.url
    # Section headers like [Verse 1], [Chorus] help with section alignment
```

### Limitations
- Lyrics require HTML scraping (may break if Genius changes their page structure)
- No word-level timestamps (only raw text)
- Non-English lyrics coverage is less comprehensive
- Some songs may have incorrect/incomplete lyrics

### Fallback
- If song not found: try with simplified title (remove parentheticals, "feat." etc.)
- If scraping fails: fall back to Musixmatch or Whisper transcription

---

## 3. Musixmatch API (Lyrics Database)

### Purpose
- Second source for lyrics (largest global database)
- Synced/timed lyrics when available (line-level timestamps)
- Better non-English coverage than Genius

### Access
- **API**: REST API at `https://api.musixmatch.com/ws/1.1/`
- **Authentication**: API key via `MUSIXMATCH_API_KEY` environment variable
- **Sign up**: https://developer.musixmatch.com/

### Rate Limits (Free Tier)
| Metric | Limit |
|--------|-------|
| Requests per day | 2,000 |
| Lyrics coverage | 30% of lyrics body |

### Limitations
- Free tier only returns 30% of lyrics — not usable as sole lyrics source
- Synced lyrics (timestamps) not available in free tier
- Commercial license required for full lyrics and synced data

### Usage Strategy
- Use primarily as a metadata source and to check for synced lyrics availability
- Cross-reference with Genius for lyrics text
- If synced lyrics are available (commercial tier), prefer those timestamps over Whisper

### Fallback
- If rate limited or unavailable: rely on Genius + Whisper

---

## 4. OpenAI Whisper API (Speech-to-Text)

### Purpose
- Transcribe lyrics from audio with word-level timestamps
- Forced alignment of known lyrics against audio for precise timing

### Access
- **API**: REST API at `https://api.openai.com/v1/audio/transcriptions`
- **Authentication**: API key via `OPENAI_API_KEY` environment variable
- **SDK**: `openai` Python package

### Cost
| Model | Cost |
|-------|------|
| whisper-1 | $0.006 / minute |

A 4-minute song costs ~$0.024.

### Integration
```python
from openai import OpenAI

client = OpenAI()

def transcribe_audio(audio_path: str) -> dict:
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
        )
    return result
```

### Local Alternative
For self-hosted deployment (no per-minute cost):
- **faster-whisper**: CTranslate2-optimized Whisper implementation
- **Model**: `large-v3` for best accuracy
- **Requires**: GPU with 6+ GB VRAM (or CPU with ~16 GB RAM, much slower)

### Fallback
- If API unavailable: queue for retry
- If transcription quality is poor: flag to user, offer manual lyrics input

---

## 5. OpenAI DALL-E 3 API (AI Image Generation — Tier 2)

### Purpose
- Generate AI keyframe images for section backgrounds
- Default image generation provider for MVP

### Access
- **API**: REST API at `https://api.openai.com/v1/images/generations`
- **Authentication**: API key via `OPENAI_API_KEY` environment variable
- **SDK**: `openai` Python package

### Cost
| Size | Quality | Cost Per Image |
|------|---------|---------------|
| 1024x1024 | standard | $0.040 |
| 1024x1024 | hd | $0.080 |
| 1024x1792 / 1792x1024 | standard | $0.080 |
| 1024x1792 / 1792x1024 | hd | $0.120 |

Typical song (15 keyframes at 1792x1024 standard): ~$1.20

### Integration
```python
from openai import OpenAI

client = OpenAI()

def generate_keyframe(prompt: str, size: str = "1792x1024") -> str:
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="standard",
        n=1,
    )
    return response.data[0].url  # Download and store
```

### Rate Limits
| Tier | Images Per Minute |
|------|------------------|
| Tier 1 (new accounts) | 5 |
| Tier 2+ | 7-15 |

### Fallback
- If generation fails: retry once with simplified prompt
- If rate limited: queue with delay
- If API unavailable: fall back to Tier 1 procedural visuals

---

## 6. Stability AI API (Alternative Image Generation)

### Purpose
- Alternative to DALL-E 3 for keyframe generation
- Different artistic styles and capabilities

### Access
- **API**: REST API at `https://api.stability.ai/v2beta/`
- **Authentication**: API key via `STABILITY_API_KEY` environment variable
- **Models**: Stable Image Ultra, Stable Image Core, SD3.5

### Cost
| Model | Cost Per Image |
|-------|---------------|
| Stable Image Core | $0.03 |
| Stable Image Ultra | $0.08 |
| SD3.5 Large | $0.065 |

### When to Use
- When DALL-E 3 rate limits are hit
- When user prefers Stable Diffusion aesthetic
- When more control is needed (negative prompts, style parameters)

---

## 7. ComfyUI API (Self-Hosted Image/Video Generation)

### Purpose
- Self-hosted alternative for all AI image/video generation
- Required for Tier 3 (full AI video via Deforum/AnimateDiff)
- Maximum control and no per-image cost (aside from GPU)

### Access
- **API**: REST API on self-hosted instance (default port 8188)
- **Authentication**: None by default (configure reverse proxy + auth for production)
- **Configuration**: `COMFYUI_API_URL` environment variable

### Integration
```python
import aiohttp

async def queue_comfyui_workflow(workflow_json: dict) -> str:
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow_json}
        )
        data = await resp.json()
        return data["prompt_id"]

async def get_comfyui_result(prompt_id: str) -> bytes:
    # Poll /history/{prompt_id} until complete
    # Then fetch output image from /view endpoint
    ...
```

### Deployment Options
| Option | GPU | Cost | Latency |
|--------|-----|------|---------|
| RunPod serverless | A100/H100 | ~$0.0005/sec | Cold start: 30-60s |
| Baseten | A10G/A100 | ~$0.0006/sec | Cold start: 15-30s |
| Self-hosted (on-prem) | Your GPU | Electricity only | None |
| Local dev | Consumer GPU (8+ GB VRAM) | Free | None |

---

## Environment Variables Summary

```bash
# Required
GOOGLE_AI_API_KEY=           # Gemini Flash - thematic analysis & chat
GENIUS_API_TOKEN=            # Genius - lyrics fetching

# Optional (enhanced features)
OPENAI_API_KEY=              # Whisper API + DALL-E 3 keyframe generation
MUSIXMATCH_API_KEY=          # Musixmatch - additional lyrics source
STABILITY_API_KEY=           # Stability AI - alternative image generation
COMFYUI_API_URL=             # Self-hosted ComfyUI instance

# Infrastructure
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:///./data/music_visualizer.db
STORAGE_BACKEND=local        # "local", "minio", or "s3"
MINIO_ENDPOINT=              # If using MinIO
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
S3_BUCKET=                   # If using S3
```

---

## API Key Security

- All API keys stored in environment variables, never in code
- `.env` file for local development (gitignored)
- `.env.example` committed with placeholder values
- Production: secrets manager (AWS Secrets Manager, Vault, etc.)
- Client never has direct access to API keys — all external API calls go through the server
