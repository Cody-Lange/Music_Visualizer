"""Tests for LLM service — validates the google-genai SDK integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.chat import ChatMessage
from app.services.llm_service import LLMService, SYSTEM_PROMPT, RENDER_SPEC_EXTRACTION_PROMPT


class TestLLMServiceInit:
    """Test LLMService initialization."""

    def test_lazy_client(self) -> None:
        service = LLMService()
        assert service._client is None

    @patch("app.services.llm_service.settings")
    def test_raises_without_api_key(self, mock_settings: MagicMock) -> None:
        mock_settings.google_ai_api_key = ""
        service = LLMService()
        with pytest.raises(RuntimeError, match="GOOGLE_AI_API_KEY is not set"):
            service._get_client()

    @patch("app.services.llm_service.genai")
    @patch("app.services.llm_service.settings")
    def test_creates_client_with_api_key(
        self,
        mock_settings: MagicMock,
        mock_genai: MagicMock,
    ) -> None:
        mock_settings.google_ai_api_key = "test-key"
        mock_genai.Client.return_value = MagicMock()
        service = LLMService()
        client = service._get_client()
        mock_genai.Client.assert_called_once_with(api_key="test-key")
        assert client is not None

    @patch("app.services.llm_service.genai")
    @patch("app.services.llm_service.settings")
    def test_reuses_client(
        self,
        mock_settings: MagicMock,
        mock_genai: MagicMock,
    ) -> None:
        mock_settings.google_ai_api_key = "test-key"
        mock_genai.Client.return_value = MagicMock()
        service = LLMService()
        client1 = service._get_client()
        client2 = service._get_client()
        assert client1 is client2
        assert mock_genai.Client.call_count == 1


class TestStreamChat:
    """Test stream_chat method."""

    @pytest.mark.asyncio
    async def test_yields_fallback_when_no_messages(self) -> None:
        service = LLMService()
        chunks: list[str] = []
        async for chunk in service.stream_chat([], ""):
            chunks.append(chunk)
        assert any("need a message" in c for c in chunks)

    @pytest.mark.asyncio
    @patch("app.services.llm_service.genai")
    @patch("app.services.llm_service.settings")
    async def test_streams_response(
        self,
        mock_settings: MagicMock,
        mock_genai: MagicMock,
    ) -> None:
        mock_settings.google_ai_api_key = "test-key"

        # Set up the mock chain: client.aio.chats.create() -> chat -> send_message_stream()
        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Hello "
        mock_chunk2 = MagicMock()
        mock_chunk2.text = "world!"

        async def mock_async_iter():
            for chunk in [mock_chunk1, mock_chunk2]:
                yield chunk

        mock_chat = MagicMock()
        mock_chat.send_message_stream = AsyncMock(return_value=mock_async_iter())

        mock_chats = MagicMock()
        mock_chats.create.return_value = mock_chat

        mock_aio = MagicMock()
        mock_aio.chats = mock_chats

        mock_client = MagicMock()
        mock_client.aio = mock_aio
        mock_genai.Client.return_value = mock_client

        service = LLMService()
        messages = [ChatMessage(role="user", content="test message")]

        chunks: list[str] = []
        async for chunk in service.stream_chat(messages, ""):
            chunks.append(chunk)

        assert chunks == ["Hello ", "world!"]

    @pytest.mark.asyncio
    @patch("app.services.llm_service.genai")
    @patch("app.services.llm_service.settings")
    async def test_yields_error_on_exception(
        self,
        mock_settings: MagicMock,
        mock_genai: MagicMock,
    ) -> None:
        mock_settings.google_ai_api_key = "test-key"

        mock_chats = MagicMock()
        mock_chats.create.side_effect = Exception("API down")

        mock_aio = MagicMock()
        mock_aio.chats = mock_chats

        mock_client = MagicMock()
        mock_client.aio = mock_aio
        mock_genai.Client.return_value = mock_client

        service = LLMService()
        messages = [ChatMessage(role="user", content="test")]

        chunks: list[str] = []
        async for chunk in service.stream_chat(messages, ""):
            chunks.append(chunk)

        assert any("error" in c.lower() for c in chunks)

    @pytest.mark.asyncio
    @patch("app.services.llm_service.genai")
    @patch("app.services.llm_service.settings")
    async def test_audio_context_prepended(
        self,
        mock_settings: MagicMock,
        mock_genai: MagicMock,
    ) -> None:
        mock_settings.google_ai_api_key = "test-key"

        async def mock_async_iter():
            chunk = MagicMock()
            chunk.text = "response"
            yield chunk

        mock_chat = MagicMock()
        mock_chat.send_message_stream = AsyncMock(return_value=mock_async_iter())

        mock_chats = MagicMock()
        mock_chats.create.return_value = mock_chat

        mock_aio = MagicMock()
        mock_aio.chats = mock_chats

        mock_client = MagicMock()
        mock_client.aio = mock_aio
        mock_genai.Client.return_value = mock_client

        service = LLMService()
        messages = [
            ChatMessage(role="user", content="first message"),
            ChatMessage(role="assistant", content="reply"),
            ChatMessage(role="user", content="second message"),
        ]

        chunks: list[str] = []
        async for chunk in service.stream_chat(messages, "=== AUDIO ===\nBPM: 120"):
            chunks.append(chunk)

        # Verify history was created with audio context in first message
        create_call = mock_chats.create.call_args
        history = create_call.kwargs.get("history") or create_call.args[0] if create_call.args else None
        if history is None and "history" in (create_call.kwargs or {}):
            history = create_call.kwargs["history"]

        assert history is not None
        # First message in history should contain the audio context
        first_text = history[0].parts[0].text
        assert "=== AUDIO ===" in first_text
        assert "first message" in first_text


class TestExtractRenderSpec:
    """Test extract_render_spec method."""

    @pytest.mark.asyncio
    @patch("app.services.llm_service.genai")
    @patch("app.services.llm_service.settings")
    async def test_extracts_valid_json(
        self,
        mock_settings: MagicMock,
        mock_genai: MagicMock,
    ) -> None:
        mock_settings.google_ai_api_key = "test-key"

        spec_json = '{"globalStyle": {"template": "nebula"}, "sections": [], "exportSettings": {}}'
        mock_response = MagicMock()
        mock_response.text = spec_json

        mock_chat = MagicMock()
        mock_chat.send_message = AsyncMock(return_value=mock_response)

        mock_chats = MagicMock()
        mock_chats.create.return_value = mock_chat

        mock_aio = MagicMock()
        mock_aio.chats = mock_chats

        mock_client = MagicMock()
        mock_client.aio = mock_aio
        mock_genai.Client.return_value = mock_client

        service = LLMService()
        messages = [ChatMessage(role="user", content="test")]
        result = await service.extract_render_spec(messages, "")

        assert result is not None
        assert result["globalStyle"]["template"] == "nebula"

    @pytest.mark.asyncio
    @patch("app.services.llm_service.genai")
    @patch("app.services.llm_service.settings")
    async def test_strips_markdown_fences(
        self,
        mock_settings: MagicMock,
        mock_genai: MagicMock,
    ) -> None:
        mock_settings.google_ai_api_key = "test-key"

        spec_json = '```json\n{"globalStyle": {"template": "cinematic"}}\n```'
        mock_response = MagicMock()
        mock_response.text = spec_json

        mock_chat = MagicMock()
        mock_chat.send_message = AsyncMock(return_value=mock_response)

        mock_chats = MagicMock()
        mock_chats.create.return_value = mock_chat

        mock_aio = MagicMock()
        mock_aio.chats = mock_chats

        mock_client = MagicMock()
        mock_client.aio = mock_aio
        mock_genai.Client.return_value = mock_client

        service = LLMService()
        messages = [ChatMessage(role="user", content="test")]
        result = await service.extract_render_spec(messages, "")

        assert result is not None
        assert result["globalStyle"]["template"] == "cinematic"

    @pytest.mark.asyncio
    @patch("app.services.llm_service.genai")
    @patch("app.services.llm_service.settings")
    async def test_returns_none_on_invalid_json(
        self,
        mock_settings: MagicMock,
        mock_genai: MagicMock,
    ) -> None:
        mock_settings.google_ai_api_key = "test-key"

        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON at all"

        mock_chat = MagicMock()
        mock_chat.send_message = AsyncMock(return_value=mock_response)

        mock_chats = MagicMock()
        mock_chats.create.return_value = mock_chat

        mock_aio = MagicMock()
        mock_aio.chats = mock_chats

        mock_client = MagicMock()
        mock_client.aio = mock_aio
        mock_genai.Client.return_value = mock_client

        service = LLMService()
        messages = [ChatMessage(role="user", content="test")]
        result = await service.extract_render_spec(messages, "")

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.llm_service.genai")
    @patch("app.services.llm_service.settings")
    async def test_returns_none_on_api_error(
        self,
        mock_settings: MagicMock,
        mock_genai: MagicMock,
    ) -> None:
        mock_settings.google_ai_api_key = "test-key"

        mock_chats = MagicMock()
        mock_chats.create.side_effect = Exception("API error")

        mock_aio = MagicMock()
        mock_aio.chats = mock_chats

        mock_client = MagicMock()
        mock_client.aio = mock_aio
        mock_genai.Client.return_value = mock_client

        service = LLMService()
        messages = [ChatMessage(role="user", content="test")]
        result = await service.extract_render_spec(messages, "")

        assert result is None


class TestSystemPrompt:
    """Verify the system prompt contains all required phase instructions."""

    def test_contains_analysis_phase(self) -> None:
        assert "Phase: ANALYSIS" in SYSTEM_PROMPT

    def test_contains_refinement_phase(self) -> None:
        assert "Phase: REFINEMENT" in SYSTEM_PROMPT

    def test_contains_confirmation_phase(self) -> None:
        assert "Phase: CONFIRMATION" in SYSTEM_PROMPT

    def test_contains_editing_phase(self) -> None:
        assert "Phase: EDITING" in SYSTEM_PROMPT

    def test_contains_render_spec_schema(self) -> None:
        assert "globalStyle" in SYSTEM_PROMPT
        assert "sections" in SYSTEM_PROMPT
        assert "exportSettings" in SYSTEM_PROMPT

    def test_extraction_prompt_exists(self) -> None:
        assert "render spec" in RENDER_SPEC_EXTRACTION_PROMPT.lower()
