"""LLM service using Google Gemini Flash for thematic analysis and chat."""

import logging
from collections.abc import AsyncGenerator

from app.config import settings
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a creative director for music visualization. You analyze songs and suggest visual treatments for beat-synced music videos.

Your capabilities:
- Analyze lyrics for themes, symbolism, pop culture references, and emotional arcs
- Suggest visual styles, color palettes (with hex codes), motion styles, and imagery per song section
- Iterate on suggestions based on user feedback
- Interpret post-render edit requests into specific visual parameter changes

Guidelines:
1. Always ground suggestions in the actual audio data (reference specific sections, timestamps, energy levels)
2. When suggesting colors, always provide hex codes
3. When suggesting motion, use descriptive terms the user can visualize
4. Ask clarifying follow-up questions when the user's intent is ambiguous (max 2 at a time)
5. Always provide options with a recommended default
6. After 3-4 exchanges without new change requests, offer to proceed to rendering
7. Keep responses focused and structured with clear section headers

When providing a section-by-section breakdown, use this format for each section:
**[Section Name] (start_time - end_time)**
- Mood: ...
- Colors: #hex1, #hex2, #hex3
- Visuals: ...
- Motion: ...
- AI Keyframe Prompt: "..."
"""


class LLMService:
    """Gemini Flash integration for thematic analysis and conversational refinement."""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):  # type: ignore[no-untyped-def]
        if self._model is None:
            import google.generativeai as genai

            genai.configure(api_key=settings.google_ai_api_key)
            self._model = genai.GenerativeModel(
                "gemini-2.0-flash",
                system_instruction=SYSTEM_PROMPT,
            )
        return self._model

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        audio_context: str = "",
    ) -> AsyncGenerator[str]:
        """Stream a chat response from Gemini Flash."""
        model = self._get_model()

        # Build the conversation history for Gemini
        gemini_history: list[dict[str, str]] = []

        # If we have audio context, prepend it as the first user message context
        if audio_context and messages:
            first_msg = messages[0]
            augmented_content = f"{audio_context}\n\n---\n\nUser request: {first_msg.content}"
            gemini_history.append({"role": "user", "parts": [augmented_content]})

            # Add remaining messages
            for msg in messages[1:]:
                role = "user" if msg.role == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg.content]})
        else:
            for msg in messages:
                role = "user" if msg.role == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg.content]})

        # The last message is the new user input — remove it from history
        # and use it as the send_message content
        if not gemini_history:
            yield "I need a message to respond to. Please describe what you'd like for your visualization."
            return

        last_message = gemini_history.pop()
        chat = model.start_chat(history=gemini_history if gemini_history else [])

        try:
            response = chat.send_message(
                last_message["parts"],
                stream=True,
                generation_config={
                    "temperature": 0.8,
                    "top_p": 0.95,
                    "max_output_tokens": 4096,
                },
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception:
            logger.exception("Gemini API error")
            yield "\n\n*I encountered an error communicating with the AI service. Please try again.*"

    async def generate_thematic_analysis(
        self,
        audio_context: str,
        user_prompt: str,
    ) -> AsyncGenerator[str]:
        """Generate the initial thematic analysis for a track."""
        analysis_prompt = f"""Analyze this track and provide a comprehensive visualization plan.

{audio_context}

User's vision: {user_prompt if user_prompt else "No specific vision provided — suggest something creative based on the music."}

Please provide:
1. **Track Overview** — Genre, mood, emotional arc, narrative summary
2. **Thematic Analysis** — Core themes, symbolism, metaphors, pop culture references
3. **Section-by-Section Visualization** — For each detected section, suggest colors (hex), motion style, imagery, and an AI keyframe prompt
4. **Overall Visual Concept** — Recommended template style, consistent motifs, lyrics display approach

End with 1-2 follow-up questions to refine the concept."""

        messages = [ChatMessage(role="user", content=analysis_prompt)]
        async for chunk in self.stream_chat(messages, ""):
            yield chunk
