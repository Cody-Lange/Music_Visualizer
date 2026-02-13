"""Lyrics fetching service — Genius API with fallback strategies."""

import logging
import re

from app.config import settings
from app.models.lyrics import LyricsData, LyricsLine, LyricsMetadata, LyricsWord

logger = logging.getLogger(__name__)


class LyricsService:
    """Fetches lyrics from external databases."""

    async def fetch_lyrics(self, title: str, artist: str) -> LyricsData | None:
        """Try multiple sources to find lyrics."""
        # Source 1: Genius API
        result = await self._fetch_from_genius(title, artist)
        if result:
            return result

        logger.info("No lyrics found for '%s' by '%s'", title, artist)
        return None

    async def _fetch_from_genius(self, title: str, artist: str) -> LyricsData | None:
        """Fetch lyrics from Genius using lyricsgenius."""
        if not settings.genius_api_token:
            logger.warning("GENIUS_API_TOKEN not configured, skipping Genius lookup")
            return None

        try:
            import lyricsgenius

            genius = lyricsgenius.Genius(
                settings.genius_api_token,
                verbose=False,
                remove_section_headers=False,
                retries=2,
            )

            song = genius.search_song(title, artist)
            if not song or not song.lyrics:
                return None

            lyrics_text = song.lyrics
            lines = self._parse_genius_lyrics(lyrics_text)

            # Build flat word list
            words: list[LyricsWord] = []
            for line in lines:
                words.extend(line.words)

            return LyricsData(
                source="genius",
                language="en",
                confidence=0.9,
                lines=lines,
                words=words,
                metadata=LyricsMetadata(
                    title=song.title,
                    artist=song.artist,
                    genius_url=song.url if hasattr(song, "url") else None,
                    has_sync=False,  # Genius doesn't provide timestamps
                ),
            )
        except Exception:
            logger.exception("Genius API error for '%s' by '%s'", title, artist)
            return None

    def _parse_genius_lyrics(self, raw_text: str) -> list[LyricsLine]:
        """Parse raw Genius lyrics text into structured lines.

        Genius lyrics include section headers like [Verse 1], [Chorus], etc.
        We keep these as they help with section alignment.
        """
        # Remove the "X ContributorsTitle Lyrics" header that lyricsgenius includes
        lines_raw = raw_text.strip().split("\n")

        # Skip the first line if it looks like a header
        start_idx = 0
        if lines_raw and ("Lyrics" in lines_raw[0] or "Contributors" in lines_raw[0]):
            start_idx = 1

        # Remove trailing "Embed" or number
        if lines_raw and re.match(r"^\d*Embed$", lines_raw[-1].strip()):
            lines_raw = lines_raw[:-1]

        lines: list[LyricsLine] = []
        for i, raw_line in enumerate(lines_raw[start_idx:]):
            text = raw_line.strip()
            if not text:
                continue

            # Create words (without timestamps — Genius doesn't provide them)
            word_texts = text.split()
            words = [
                LyricsWord(
                    text=w,
                    start_time=0.0,
                    end_time=0.0,
                    confidence=0.9,
                    line_index=len(lines),
                )
                for w in word_texts
            ]

            lines.append(LyricsLine(
                text=text,
                start_time=0.0,
                end_time=0.0,
                words=words,
            ))

        return lines
