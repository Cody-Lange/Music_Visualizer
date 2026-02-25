from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from the project root (one level above server/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required API keys
    google_ai_api_key: str = ""
    genius_api_token: str = ""

    # Optional API keys
    openai_api_key: str = ""
    musixmatch_api_key: str = ""
    stability_api_key: str = ""
    comfyui_api_url: str = ""

    # Infrastructure
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:///./data/music_visualizer.db"

    # Storage
    storage_backend: str = "local"
    storage_path: str = "./data/storage"
    minio_endpoint: str = ""
    minio_access_key: str = ""
    minio_secret_key: str = ""
    s3_bucket: str = ""

    # App settings
    cors_origins: str = "http://localhost:5173"
    max_upload_size_mb: int = 50
    gemini_model: str = "gemini-2.5-flash-lite"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_dir(self) -> Path:
        path = Path(self.storage_path) / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def render_dir(self) -> Path:
        path = Path(self.storage_path) / "renders"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def keyframe_dir(self) -> Path:
        path = Path(self.storage_path) / "keyframes"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def video_clip_dir(self) -> Path:
        path = Path(self.storage_path) / "video_clips"
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
