from typing import Literal

from pydantic import BaseModel


MessageRole = Literal["user", "assistant", "system"]

AnalysisStep = Literal[
    "uploading",
    "client_analysis",
    "server_analysis",
    "vocal_separation",
    "lyrics_transcription",
    "lyrics_fetch",
    "thematic_analysis",
    "complete",
]

RenderStatus = Literal[
    "idle", "queued", "generating_keyframes", "rendering", "encoding", "complete", "error"
]


class ChatMessage(BaseModel):
    role: MessageRole
    content: str


class AnalysisProgress(BaseModel):
    step: AnalysisStep
    progress: float
    message: str


class RenderProgress(BaseModel):
    status: RenderStatus
    current_frame: int | None = None
    total_frames: int | None = None
    percentage: float = 0
    message: str = ""
    download_url: str | None = None
    error: str | None = None
