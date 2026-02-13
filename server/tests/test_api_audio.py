"""Tests for audio API endpoints."""

import io
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.storage import job_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_job_store():
    """Clear job store between tests."""
    job_store._jobs.clear()
    yield
    job_store._jobs.clear()


class TestUploadEndpoint:
    def test_upload_rejects_missing_filename(self):
        response = client.post("/api/audio/upload", files={"file": ("", b"data")})
        # FastAPI will handle this
        assert response.status_code in (400, 422)

    def test_upload_rejects_unsupported_format(self):
        response = client.post(
            "/api/audio/upload",
            files={"file": ("song.txt", b"not audio", "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported format" in response.json()["detail"]

    def test_upload_rejects_oversized_file(self):
        # Create a file larger than 50MB
        huge = b"x" * (51 * 1024 * 1024)
        response = client.post(
            "/api/audio/upload",
            files={"file": ("song.mp3", huge, "audio/mpeg")},
        )
        assert response.status_code == 400
        assert "too large" in response.json()["detail"]

    @patch("app.api.audio.AudioAnalyzerService")
    def test_upload_success(self, mock_cls):
        """Mock the analyzer to test the upload flow without actual audio."""
        mock_analyzer = MagicMock()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"metadata": {"filename": "test.mp3"}}
        mock_analyzer.analyze.return_value = mock_result
        mock_cls.return_value = mock_analyzer

        audio_bytes = b"\xff\xfb\x90\x00" + b"\x00" * 1000  # Fake MP3 header
        response = client.post(
            "/api/audio/upload",
            files={"file": ("test.mp3", audio_bytes, "audio/mpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "complete"

    @patch("app.api.audio.AudioAnalyzerService")
    def test_upload_analysis_failure(self, mock_cls):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.side_effect = RuntimeError("bad audio")
        mock_cls.return_value = mock_analyzer

        response = client.post(
            "/api/audio/upload",
            files={"file": ("test.mp3", b"\xff\xfb" + b"\x00" * 500, "audio/mpeg")},
        )
        assert response.status_code == 500
        assert "Analysis failed" in response.json()["detail"]


class TestAnalysisEndpoint:
    def test_get_analysis_not_found(self):
        response = client.get("/api/audio/nonexistent/analysis")
        assert response.status_code == 404

    def test_get_analysis_in_progress(self):
        job_store.create_job("j1", {"status": "analyzing"})
        response = client.get("/api/audio/j1/analysis")
        assert response.status_code == 202

    def test_get_analysis_error(self):
        job_store.create_job("j1", {"status": "error", "error": "something broke"})
        response = client.get("/api/audio/j1/analysis")
        assert response.status_code == 500

    def test_get_analysis_complete(self):
        job_store.create_job("j1", {
            "status": "complete",
            "analysis": {"metadata": {"filename": "test.mp3"}},
        })
        response = client.get("/api/audio/j1/analysis")
        assert response.status_code == 200
        data = response.json()
        assert data["analysis"]["metadata"]["filename"] == "test.mp3"


class TestWaveformEndpoint:
    def test_waveform_not_found(self):
        response = client.get("/api/audio/missing/waveform")
        assert response.status_code == 404

    def test_waveform_in_progress(self):
        job_store.create_job("j1", {"status": "analyzing"})
        response = client.get("/api/audio/j1/waveform")
        assert response.status_code == 202

    def test_waveform_complete(self):
        job_store.create_job("j1", {
            "status": "complete",
            "analysis": {"spectral": {"times": [0.0, 0.5], "rms": [0.3, 0.7]}},
        })
        response = client.get("/api/audio/j1/waveform")
        assert response.status_code == 200
        data = response.json()
        assert data["times"] == [0.0, 0.5]
        assert data["rms"] == [0.3, 0.7]
