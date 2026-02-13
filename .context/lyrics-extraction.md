# Lyrics Extraction & Analysis

## Overview

The lyrics pipeline fetches, transcribes, and analyzes song lyrics to drive both the LLM thematic analysis and timed text overlays in the rendered video. It uses a multi-source approach: fetch known lyrics from databases, transcribe from audio as fallback, and cross-reference for accuracy.

---

## Pipeline Architecture

```
Audio Upload
     │
     ├──→ Metadata Extraction (title, artist from ID3 tags / filename)
     │         │
     │         ├──→ Genius API lookup ──→ Lyrics text (no timestamps)
     │         │
     │         └──→ Musixmatch API lookup ──→ Lyrics text (+ synced lyrics if available)
     │
     ├──→ Demucs (vocal separation)
     │         │
     │         └──→ Isolated vocals WAV
     │                   │
     │                   └──→ Whisper (transcription)
     │                             │
     │                             └──→ Word-level timestamps + text
     │
     └──→ Cross-Reference & Merge
               │
               ├──→ If database lyrics found: Use Whisper timestamps aligned to known text
               ├──→ If only transcription: Use Whisper output directly (flag confidence)
               └──→ If nothing found: Allow manual lyrics input
               │
               └──→ Final Lyrics JSON (text + word-level timestamps + confidence)
                         │
                         └──→ Gemini Flash (thematic analysis)
```

---

## Source 1: Lyrics Database Lookup

### Genius API

- **Access**: REST API via `lyricsgenius` Python wrapper
- **Capabilities**: Song search by title + artist; returns full lyrics text, annotations, and metadata
- **Limitation**: API returns metadata only — lyrics require scraping the Genius HTML page. The `lyricsgenius` library handles this automatically
- **Rate limit**: Free tier available
- **When to use**: Always attempt first; most comprehensive English lyrics catalog

### Musixmatch API

- **Access**: REST API
- **Capabilities**: Largest lyrics database globally; some tracks have synced/timed lyrics (word or line-level timestamps)
- **Limitation**: Free tier limited to 30% of lyrics text; full lyrics require commercial license
- **When to use**: Check for synced lyrics availability (huge value if present); supplement Genius for non-English tracks

### Lookup Strategy

```python
async def fetch_lyrics(title: str, artist: str) -> LyricsResult:
    # 1. Try Genius first (full lyrics, free)
    genius_result = await genius_search(title, artist)

    # 2. Try Musixmatch for synced lyrics
    musixmatch_result = await musixmatch_search(title, artist)

    # 3. Prefer synced lyrics if available
    if musixmatch_result and musixmatch_result.has_sync:
        return merge(musixmatch_result, genius_result)

    # 4. Fall back to Genius text
    if genius_result:
        return genius_result

    # 5. Fall back to Musixmatch partial
    if musixmatch_result:
        return musixmatch_result

    return None  # Will rely on Whisper transcription
```

---

## Source 2: Audio Transcription

### Demucs (Vocal Separation)

Whisper accuracy improves dramatically when fed isolated vocals instead of the full mix.

- **Model**: `htdemucs` (hybrid transformer model)
- **Input**: Full audio mix
- **Output**: Separated stems — vocals, drums, bass, other
- **Processing time**: ~30-90 seconds for a 4-minute track (GPU); 2-5 minutes (CPU)
- **Quality**: State-of-the-art source separation; significantly reduces background instrumentation bleed

### OpenAI Whisper

- **Model**: `whisper-large-v3` (server-side) for highest accuracy
- **Input**: Isolated vocal track from Demucs
- **Output**: Word-level timestamps with confidence scores
- **API option**: OpenAI Whisper API ($0.006/min) — simpler, no local GPU needed
- **Local option**: `faster-whisper` (CTranslate2 optimized) for self-hosted deployment

**Whisper configuration for music:**
```python
result = whisper.transcribe(
    vocal_audio_path,
    language=detected_language,  # or None for auto-detect
    word_timestamps=True,
    condition_on_previous_text=True,
    temperature=0.0,            # deterministic for consistency
    compression_ratio_threshold=2.4,
    no_speech_threshold=0.6,
    initial_prompt="Song lyrics transcription:"  # hint that this is lyrics
)
```

**Known limitations for sung vocals:**
- Accuracy: ~70-85% for clean vocals; drops for:
  - Heavy autotune or vocal processing
  - Screaming / growling (metal, punk)
  - Rapid-fire delivery (fast rap)
  - Melismatic singing (R&B runs)
  - Heavy reverb / delay effects
  - Multiple overlapping voices
- Timestamps can drift ±200ms, especially during held notes
- May hallucinate words during instrumental sections (mitigated by Demucs separation)

---

## Cross-Referencing & Alignment

When both database lyrics and Whisper transcription are available:

```
1. Normalize both texts (lowercase, strip punctuation, collapse whitespace)
2. Use dynamic time warping (DTW) or sequence alignment to match Whisper words
   to database lyrics words
3. For each matched word pair:
   - Use the DATABASE text (more accurate spelling/formatting)
   - Use the WHISPER timestamp (provides timing information)
4. For unmatched segments:
   - If Whisper has extra words → likely hallucination → discard
   - If database has extra words → likely missed by Whisper → interpolate timestamps
5. Output: Merged lyrics with accurate text AND accurate timestamps
```

This cross-referencing approach is inspired by `python-lyrics-transcriber`, which achieves significantly better results than either source alone.

---

## Manual Lyrics Input

Always available as a fallback or override:

- User can paste lyrics directly into a text area
- If pasted without timestamps, system uses Whisper forced alignment to generate timestamps against the known text (much more accurate than free transcription)
- User can manually adjust word timestamps in the timeline UI

---

## Lyrics Output Schema

```typescript
interface LyricsData {
  source: "genius" | "musixmatch" | "whisper" | "manual" | "merged";
  language: string;  // ISO 639-1 code
  confidence: number; // 0-1 overall confidence

  lines: LyricsLine[];
  words: LyricsWord[];  // flat array for timeline rendering

  metadata: {
    title?: string;
    artist?: string;
    album?: string;
    geniusUrl?: string;
    hasSync: boolean;    // whether word-level timestamps are available
  };
}

interface LyricsLine {
  text: string;
  startTime: number;   // seconds
  endTime: number;      // seconds
  words: LyricsWord[];
}

interface LyricsWord {
  text: string;
  startTime: number;     // seconds
  endTime: number;        // seconds
  confidence: number;     // 0-1 for this specific word
  lineIndex: number;      // which line this word belongs to
}
```

---

## Thematic Analysis (via Gemini Flash)

Once lyrics are extracted, they're sent to Gemini Flash along with audio analysis metadata for deep thematic analysis.

### LLM Prompt Structure

```
You are analyzing a music track for visual storytelling. Given the following
audio analysis and lyrics, provide a detailed breakdown.

AUDIO METADATA:
- BPM: {bpm}, Key: {key} {scale}
- Mood tags: {mood_tags}
- Energy profile: {energy_description}
- Duration: {duration}
- Sections: {section_list_with_timestamps}

LYRICS:
{full_lyrics_text}

Provide the following analysis:

1. TRACK OVERVIEW
   - Genre and subgenre classification
   - Overall mood and emotional arc
   - One-paragraph description of the song's narrative/message

2. THEMATIC ANALYSIS
   - Core themes (2-4 main themes with supporting lyric excerpts)
   - Symbolism and metaphors (explain what they represent)
   - Pop culture references (movies, books, historical events, other songs)
   - Emotional journey (how does the emotional tone shift throughout?)

3. SECTION-BY-SECTION BREAKDOWN
   For each section ({section_labels}):
   - Lyrical content summary
   - Emotional tone
   - Key imagery evoked by the lyrics
   - Suggested visual approach:
     - Color palette (3-5 colors with hex codes)
     - Motion style (calm/flowing, energetic/pulsing, chaotic, etc.)
     - Visual metaphors and imagery
     - Suggested AI image prompt for keyframe generation
     - Transition suggestion to/from adjacent sections

4. VISUALIZATION CONCEPT
   - Overall visual style recommendation (abstract, cinematic, nature, urban, etc.)
   - Consistent visual motifs that should appear throughout
   - How to visually represent the song's emotional arc
   - Lyrics display style recommendation
```

### LLM Response Handling

- Response is streamed to the chat UI via WebSocket
- Structured sections are parsed and stored in the render spec
- Section-specific suggestions are linked to the corresponding timeline sections
- User can accept, modify, or reject each suggestion individually in the chat

---

## Privacy Considerations

- Audio files are only sent to external services when necessary:
  - Whisper API (if using cloud transcription)
  - Genius/Musixmatch (metadata only, not audio)
- Lyrics text is sent to Gemini Flash for analysis
- Users are informed which services will receive their data before processing begins
- Option for fully local processing: local Whisper + manual lyrics + local LLM (future)
