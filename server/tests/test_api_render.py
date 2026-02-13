"""Tests for render API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.storage import job_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_job_store():
    job_store._jobs.clear()
    yield
    job_store._jobs.clear()


class TestStartRenderEndpoint:
    def test_missing_audio_job(self):
        response = client.post(
            "/api/render/start",
            json={
                "job_id": "nonexistent",
                "render_spec": {},
            },
        )
        assert response.status_code == 404

    def test_analysis_not_complete(self):
        job_store.create_job("j1", {"status": "analyzing"})
        response = client.post(
            "/api/render/start",
            json={"job_id": "j1", "render_spec": {}},
        )
        assert response.status_code == 400
        assert "not complete" in response.json()["detail"]

    @patch("app.api.render.RenderService")
    def test_render_success(self, mock_cls):
        mock_service = AsyncMock()
        mock_service.render_video.return_value = {"download_url": "/storage/renders/r1.mp4"}
        mock_cls.return_value = mock_service

        job_store.create_job("j1", {
            "status": "complete",
            "path": "/tmp/audio.mp3",
            "analysis": {"metadata": {"duration": 180}},
        })

        response = client.post(
            "/api/render/start",
            json={"job_id": "j1", "render_spec": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert "render_id" in data

    @patch("app.api.render.RenderService")
    def test_render_failure(self, mock_cls):
        mock_service = AsyncMock()
        mock_service.render_video.side_effect = RuntimeError("FFmpeg crashed")
        mock_cls.return_value = mock_service

        job_store.create_job("j1", {
            "status": "complete",
            "path": "/tmp/audio.mp3",
            "analysis": {"metadata": {"duration": 60}},
        })

        response = client.post(
            "/api/render/start",
            json={"job_id": "j1", "render_spec": {}},
        )
        assert response.status_code == 500
        assert "Render failed" in response.json()["detail"]


class TestRenderStatusEndpoint:
    def test_not_found(self):
        response = client.get("/api/render/missing/status")
        assert response.status_code == 404

    def test_returns_status(self):
        job_store.create_job("r1", {
            "status": "rendering",
            "percentage": 50,
            "download_url": None,
            "error": None,
        })
        response = client.get("/api/render/r1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rendering"
        assert data["percentage"] == 50


class TestDownloadEndpoint:
    def test_not_found(self):
        response = client.get("/api/render/missing/download")
        assert response.status_code == 404

    def test_not_complete(self):
        job_store.create_job("r1", {"status": "rendering"})
        response = client.get("/api/render/r1/download")
        assert response.status_code == 400

    def test_no_url(self):
        job_store.create_job("r1", {"status": "complete"})
        response = client.get("/api/render/r1/download")
        assert response.status_code == 404

    def test_success(self):
        job_store.create_job("r1", {
            "status": "complete",
            "download_url": "/storage/renders/r1.mp4",
        })
        response = client.get("/api/render/r1/download")
        assert response.status_code == 200
        assert response.json()["download_url"] == "/storage/renders/r1.mp4"


class TestEditEndpoint:
    def test_not_found(self):
        response = client.post(
            "/api/render/missing/edit",
            json={"edit_description": "make it blue"},
        )
        assert response.status_code == 404

    def test_creates_new_render_job(self):
        job_store.create_job("r1", {
            "status": "complete",
            "render_spec": {"global_style": {"template": "nebula"}},
        })
        response = client.post(
            "/api/render/r1/edit",
            json={"edit_description": "add more particles"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["render_id"] != "r1"  # New ID created
