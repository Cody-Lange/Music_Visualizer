"""Tests for chat phase detection and render spec extraction."""

import json

import pytest

from app.api.chat import (
    _detect_phase_transition,
    _try_extract_render_spec,
    _build_analysis_context,
    _CONFIRM_PATTERNS,
    _LLM_ASKS_CONFIRM,
)
from app.services.storage import job_store


class TestConfirmPatterns:
    """Test user-side render confirmation regex."""

    @pytest.mark.parametrize(
        "text",
        [
            "Yes, render it",
            "render it",
            "Render the video",
            "Make the video",
            "Start render",
            "Let's go",
            "Let's render",
            "Looks good, render",
            "Looks perfect, let's go",
            "Go ahead",
            "Do it",
            "Yes, let's go",
            "yes please",
            "yes do it",
            "render now",
            "Render this",
        ],
    )
    def test_matches_confirm_phrases(self, text: str) -> None:
        assert _CONFIRM_PATTERNS.search(text), f"Should match: {text!r}"

    @pytest.mark.parametrize(
        "text",
        [
            "I want the colors to be warmer",
            "Change the intro section",
            "What about a different style?",
            "Can you make it more energetic?",
            "Tell me more about the sections",
        ],
    )
    def test_rejects_non_confirm(self, text: str) -> None:
        assert not _CONFIRM_PATTERNS.search(text), f"Should not match: {text!r}"


class TestLLMConfirmPatterns:
    """Test LLM-side render confirmation detection."""

    @pytest.mark.parametrize(
        "text",
        [
            "Are you ready to render?",
            "Ready to render?",
            "Shall I start rendering?",
            "Shall we begin rendering?",
            "Would you like to proceed with rendering?",
            "Want me to render this?",
        ],
    )
    def test_matches_llm_ask(self, text: str) -> None:
        assert _LLM_ASKS_CONFIRM.search(text), f"Should match: {text!r}"

    @pytest.mark.parametrize(
        "text",
        [
            "Here are the updated color suggestions",
            "I've modified the intro section",
            "Let me know if you'd like changes",
        ],
    )
    def test_rejects_non_ask(self, text: str) -> None:
        assert not _LLM_ASKS_CONFIRM.search(text), f"Should not match: {text!r}"


class TestPhaseTransition:
    """Test _detect_phase_transition logic."""

    def test_analysis_always_moves_to_refinement(self) -> None:
        assert _detect_phase_transition("analysis", "anything", "response", 1) == "refinement"

    def test_refinement_stays_on_regular_message(self) -> None:
        result = _detect_phase_transition(
            "refinement",
            "Make the colors warmer",
            "Sure, I've updated the color palette.",
            2,
        )
        assert result == "refinement"

    def test_refinement_to_confirmation_when_llm_asks(self) -> None:
        result = _detect_phase_transition(
            "refinement",
            "That looks great",
            "Wonderful! Here's the final plan. Ready to render?",
            4,
        )
        assert result == "confirmation"

    def test_refinement_to_confirmation_when_user_asks_render(self) -> None:
        result = _detect_phase_transition(
            "refinement",
            "Render it",
            "Here's the final summary...",
            3,
        )
        assert result == "confirmation"

    def test_confirmation_to_rendering_on_confirm(self) -> None:
        result = _detect_phase_transition(
            "confirmation",
            "Yes, render it",
            "",
            5,
        )
        assert result == "rendering"

    def test_confirmation_back_to_refinement_on_change(self) -> None:
        result = _detect_phase_transition(
            "confirmation",
            "Actually, change the intro colors to blue",
            "Updated the intro section.",
            5,
        )
        assert result == "refinement"

    def test_rendering_stays_rendering(self) -> None:
        result = _detect_phase_transition(
            "rendering",
            "anything",
            "response",
            6,
        )
        assert result == "rendering"

    def test_editing_stays_editing_on_normal_message(self) -> None:
        result = _detect_phase_transition(
            "editing",
            "Make the colors brighter in the chorus",
            "I've updated the chorus colors.",
            7,
        )
        assert result == "editing"

    def test_editing_to_rendering_on_render_request(self) -> None:
        result = _detect_phase_transition(
            "editing",
            "Render it",
            "",
            8,
        )
        assert result == "rendering"

    def test_editing_to_rendering_with_ai(self) -> None:
        result = _detect_phase_transition(
            "editing",
            "Render with AI",
            "",
            8,
        )
        assert result == "rendering"


class TestExtractRenderSpec:
    """Test _try_extract_render_spec from LLM text."""

    def test_extracts_json_block(self) -> None:
        text = """Here's the render spec:

```json
{"globalStyle": {"template": "nebula"}, "sections": [], "exportSettings": {}}
```

All done!"""
        result = _try_extract_render_spec(text)
        assert result is not None
        assert result["globalStyle"]["template"] == "nebula"

    def test_extracts_plain_json(self) -> None:
        text = '{"globalStyle": {"template": "cinematic"}, "sections": []}'
        result = _try_extract_render_spec(text)
        assert result is not None
        assert result["globalStyle"]["template"] == "cinematic"

    def test_returns_none_for_no_json(self) -> None:
        text = "Here are some suggestions for your visualization..."
        result = _try_extract_render_spec(text)
        assert result is None

    def test_returns_none_for_invalid_json(self) -> None:
        text = '{"globalStyle": {broken json'
        result = _try_extract_render_spec(text)
        assert result is None

    def test_extracts_code_block_without_json_tag(self) -> None:
        text = """```
{"globalStyle": {"template": "retro"}, "sections": []}
```"""
        result = _try_extract_render_spec(text)
        assert result is not None
        assert result["globalStyle"]["template"] == "retro"


class TestBuildAnalysisContext:
    """Test context building from job store data."""

    def setup_method(self) -> None:
        # Clear the job store between tests
        for jid in list(job_store._jobs.keys()):
            job_store.delete_job(jid)

    def test_empty_when_job_not_found(self) -> None:
        assert _build_analysis_context("nonexistent") == ""

    def test_includes_audio_analysis(self) -> None:
        job_store.create_job("test-job", {
            "analysis": {
                "metadata": {"filename": "test.mp3", "duration": 180.0},
                "rhythm": {"bpm": 120.0},
                "tonal": {"key": "C", "scale": "major"},
                "mood": {"valence": 0.7, "energy": 0.8, "tags": ["happy", "energetic"], "danceability": 0.9},
                "sections": {
                    "boundaries": [0.0, 60.0, 120.0],
                    "labels": ["intro", "verse", "chorus"],
                },
            },
        })
        context = _build_analysis_context("test-job")
        assert "BPM: 120.0" in context
        assert "Key: C major" in context
        assert "intro:" in context
        assert "verse:" in context
        assert "chorus:" in context

    def test_includes_lyrics(self) -> None:
        job_store.create_job("lyrics-job", {
            "lyrics": {
                "lines": [
                    {"text": "Hello world"},
                    {"text": "Second line"},
                    {"text": ""},  # empty line should be skipped
                ],
            },
        })
        context = _build_analysis_context("lyrics-job")
        assert "Hello world" in context
        assert "Second line" in context
        assert "=== LYRICS ===" in context
