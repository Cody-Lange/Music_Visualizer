from typing import Literal

from pydantic import BaseModel, Field


LyricsSource = Literal["genius", "musixmatch", "whisper", "manual", "merged"]


class LyricsWord(BaseModel):
    text: str
    start_time: float
    end_time: float
    confidence: float = Field(ge=0, le=1, default=1.0)
    line_index: int = 0


class LyricsLine(BaseModel):
    text: str
    start_time: float
    end_time: float
    words: list[LyricsWord]


class LyricsMetadata(BaseModel):
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    genius_url: str | None = None
    has_sync: bool = False


class LyricsData(BaseModel):
    source: LyricsSource
    language: str = "en"
    confidence: float = Field(ge=0, le=1, default=1.0)
    lines: list[LyricsLine]
    words: list[LyricsWord]
    metadata: LyricsMetadata


class LyricsFetchRequest(BaseModel):
    title: str
    artist: str
    job_id: str | None = None
