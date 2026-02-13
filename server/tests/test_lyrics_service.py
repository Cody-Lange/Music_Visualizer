"""Tests for the LyricsService."""

import pytest

from app.services.lyrics_service import LyricsService


@pytest.fixture
def service():
    return LyricsService()


class TestParseGeniusLyrics:
    def test_basic_lyrics(self, service: LyricsService):
        raw = "Song Title Lyrics\n[Verse 1]\nFirst line\nSecond line\n\n[Chorus]\nChorus line\n123Embed"
        lines = service._parse_genius_lyrics(raw)
        texts = [line.text for line in lines]

        assert "[Verse 1]" in texts
        assert "First line" in texts
        assert "Second line" in texts
        assert "[Chorus]" in texts
        assert "Chorus line" in texts
        # Header and Embed footer should be removed
        assert "Song Title Lyrics" not in texts
        assert "123Embed" not in texts

    def test_empty_lyrics(self, service: LyricsService):
        lines = service._parse_genius_lyrics("")
        assert lines == []

    def test_no_header_no_embed(self, service: LyricsService):
        raw = "Hello world\nSecond line"
        lines = service._parse_genius_lyrics(raw)
        assert len(lines) == 2
        assert lines[0].text == "Hello world"

    def test_contributors_header_removed(self, service: LyricsService):
        raw = "5 ContributorsSong Lyrics\nActual line"
        lines = service._parse_genius_lyrics(raw)
        texts = [line.text for line in lines]
        assert "Actual line" in texts
        assert len(lines) == 1

    def test_embed_footer_removed(self, service: LyricsService):
        raw = "Line one\nLine two\nEmbed"
        lines = service._parse_genius_lyrics(raw)
        texts = [line.text for line in lines]
        assert "Embed" not in texts

    def test_words_split_correctly(self, service: LyricsService):
        raw = "Hello beautiful world"
        lines = service._parse_genius_lyrics(raw)
        assert len(lines) == 1
        assert len(lines[0].words) == 3
        assert lines[0].words[0].text == "Hello"
        assert lines[0].words[2].text == "world"

    def test_timestamps_are_zero(self, service: LyricsService):
        raw = "Some lyrics here"
        lines = service._parse_genius_lyrics(raw)
        for line in lines:
            assert line.start_time == 0.0
            assert line.end_time == 0.0
            for word in line.words:
                assert word.start_time == 0.0
                assert word.end_time == 0.0

    def test_empty_lines_skipped(self, service: LyricsService):
        raw = "Line one\n\n\nLine two\n\n"
        lines = service._parse_genius_lyrics(raw)
        assert len(lines) == 2


class TestFetchLyrics:
    @pytest.mark.asyncio
    async def test_returns_none_without_token(self, service: LyricsService, monkeypatch):
        """Without GENIUS_API_TOKEN, should return None gracefully."""
        monkeypatch.setattr("app.config.settings.genius_api_token", "")
        result = await service.fetch_lyrics("Song", "Artist")
        assert result is None
