from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api import audio, lyrics, chat, render, shader


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    # Ensure storage directories exist on startup
    for dir_path in [settings.upload_dir, settings.render_dir, settings.keyframe_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Music Visualizer API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(audio.router, prefix="/api/audio", tags=["audio"])
app.include_router(lyrics.router, prefix="/api/lyrics", tags=["lyrics"])
app.include_router(chat.router, prefix="/ws", tags=["chat"])
app.include_router(render.router, prefix="/api/render", tags=["render"])
app.include_router(shader.router, prefix="/api/shader", tags=["shader"])

# Serve rendered files
storage_path = Path(settings.storage_path)
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
