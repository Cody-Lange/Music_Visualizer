"""Tests for the Settings configuration."""

from app.config import Settings


class TestSettings:
    def test_cors_origin_list_single(self):
        s = Settings(cors_origins="http://localhost:5173")
        assert s.cors_origin_list == ["http://localhost:5173"]

    def test_cors_origin_list_multiple(self):
        s = Settings(cors_origins="http://localhost:5173, http://example.com , https://app.test")
        assert s.cors_origin_list == [
            "http://localhost:5173",
            "http://example.com",
            "https://app.test",
        ]

    def test_max_upload_bytes(self):
        s = Settings(max_upload_size_mb=50)
        assert s.max_upload_bytes == 50 * 1024 * 1024

    def test_max_upload_bytes_custom(self):
        s = Settings(max_upload_size_mb=100)
        assert s.max_upload_bytes == 100 * 1024 * 1024

    def test_directory_properties_create_dirs(self, tmp_path):
        s = Settings(storage_path=str(tmp_path / "storage"))
        upload_dir = s.upload_dir
        render_dir = s.render_dir
        keyframe_dir = s.keyframe_dir

        assert upload_dir.exists()
        assert render_dir.exists()
        assert keyframe_dir.exists()
        assert upload_dir.name == "uploads"
        assert render_dir.name == "renders"
        assert keyframe_dir.name == "keyframes"

    def test_defaults(self):
        s = Settings(
            _env_file=None,
            google_ai_api_key="",
            genius_api_token="",
        )
        assert s.redis_url == "redis://localhost:6379/0"
        assert s.storage_backend == "local"
        assert s.max_upload_size_mb == 50
        assert s.google_ai_api_key == ""
        assert s.genius_api_token == ""
