"""Tests for lyrics API endpoints."""

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


class TestFetchLyricsEndpoint:
    @patch("app.api.lyrics.LyricsService")
    def test_lyrics_not_found(self, mock_cls):
        mock_service = AsyncMock()
        mock_service.fetch_lyrics.return_value = None
        mock_cls.return_value = mock_service

        response = client.post(
            "/api/lyrics/fetch",
            json={"title": "Unknown Song", "artist": "Nobody"},
        )
        assert response.status_code == 404

    @patch("app.api.lyrics.LyricsService")
    def test_lyrics_found(self, mock_cls):
        from app.models.lyrics import LyricsData, LyricsMetadata

        mock_data = LyricsData(
            source="genius",
            lines=[],
            words=[],
            metadata=LyricsMetadata(title="Test", artist="Test", has_sync=False),
        )
        mock_service = AsyncMock()
        mock_service.fetch_lyrics.return_value = mock_data
        mock_cls.return_value = mock_service

        response = client.post(
            "/api/lyrics/fetch",
            json={"title": "Test", "artist": "Test"},
        )
        assert response.status_code == 200
        assert response.json()["lyrics"]["source"] == "genius"

    @patch("app.api.lyrics.LyricsService")
    def test_lyrics_attached_to_job(self, mock_cls):
        from app.models.lyrics import LyricsData, LyricsMetadata

        mock_data = LyricsData(
            source="genius", lines=[], words=[],
            metadata=LyricsMetadata(has_sync=False),
        )
        mock_service = AsyncMock()
        mock_service.fetch_lyrics.return_value = mock_data
        mock_cls.return_value = mock_service

        job_store.create_job("j1", {"status": "complete"})

        response = client.post(
            "/api/lyrics/fetch",
            json={"title": "Song", "artist": "Artist", "job_id": "j1"},
        )
        assert response.status_code == 200

        job = job_store.get_job("j1")
        assert job is not None
        assert "lyrics" in job


class TestGetLyricsEndpoint:
    def test_job_not_found(self):
        response = client.get("/api/lyrics/missing")
        assert response.status_code == 404

    def test_no_lyrics_on_job(self):
        job_store.create_job("j1", {"status": "complete"})
        response = client.get("/api/lyrics/j1")
        assert response.status_code == 404

    def test_lyrics_present(self):
        job_store.create_job("j1", {
            "status": "complete",
            "lyrics": {"source": "genius", "lines": []},
        })
        response = client.get("/api/lyrics/j1")
        assert response.status_code == 200
        assert response.json()["lyrics"]["source"] == "genius"
