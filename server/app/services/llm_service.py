"""LLM service using Google Gemini Flash for thematic analysis and chat."""

import asyncio
import json
import logging
import re as _re
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types
from google.genai.errors import ClientError

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

## Conversation Phases

You operate in distinct phases. Your behavior adapts based on the current phase:

### Phase: ANALYSIS
When you receive audio analysis data and a user prompt for the first time, provide:
1. **Track Overview** — Genre, mood, emotional arc, narrative summary
2. **Thematic Analysis** — Core themes, symbolism, metaphors, pop culture references
3. **Section-by-Section Visualization** — For each detected section, suggest colors (hex), motion style, imagery, and an AI keyframe prompt
4. **Overall Visual Concept** — Recommended template style, consistent motifs, lyrics display approach

End with 1-2 follow-up questions to refine the concept.

### Phase: REFINEMENT
Respond to user feedback with specific, modified suggestions. Keep track of all agreed-upon decisions. Reference specific timestamps and energy levels from the audio data.

### Phase: CONFIRMATION
Detect when the user is satisfied. Signs include:
- "That's perfect", "Love it", "Let's go", "Looks good"
- "Render it", "Make the video", "Start rendering"
- Lack of further change requests after 2+ exchanges
- User asking about export settings or timeline

When you detect satisfaction, present a COMPREHENSIVE FINAL SUMMARY of every agreed-upon decision. This is the last chance for the user to review before rendering, so be extremely thorough and specific. The summary MUST include ALL of the following:

## 1. Overall Creative Vision
- **Visual Concept**: A 2-3 sentence description of the overall artistic direction and narrative arc of the video
- **Template**: The chosen visual template (e.g., "nebula") and WHY it fits this track
- **Style Modifiers**: All active modifiers (e.g., "ethereal", "high-contrast") with brief explanations of their visual effect
- **Recurring Motifs**: Visual elements that appear throughout (e.g., "floating orbs", "fractal branches")
- **Color Story**: How the overall color palette evolves across the track

## 2. Section-by-Section Breakdown
For EVERY section detected in the audio, present a detailed breakdown:

**[Section Name] (start_time - end_time) — [duration]s**
| Attribute | Value |
|-----------|-------|
| Mood/Energy | e.g., "Contemplative, low energy (0.3)" |
| Color Palette | ALL hex codes with color names: #1B1464 (Deep Indigo), #7C5CFC (Electric Violet) |
| Motion Style | e.g., "slow-drift" — describe what the viewer will actually see |
| Intensity | 0.0-1.0 scale with human-readable description |
| Visual Elements | Specific objects/effects: "particle nebula with swirling dust lanes, distant stars pulsing on beats" |
| AI Keyframe Prompt | The EXACT vivid prompt for AI image generation |
| Transition In | e.g., "cross-dissolve from previous section over 0.5s" |
| Transition Out | e.g., "fade-to-black" |

## 3. Lyrics Display Configuration
- **Enabled**: Yes/No
- **Font**: sans/serif/mono (and why)
- **Size**: small/medium/large
- **Animation**: The specific animation style and what it looks like
- **Color**: Hex code with name
- **Shadow**: Yes/No

## 4. Export Settings
- **Resolution**: Width x Height
- **FPS**: Frame rate
- **Aspect Ratio**: 16:9, 9:16, or 1:1
- **Quality**: draft/standard/high

## 5. AI-Enhanced Rendering
Present this clearly:

> **Would you like to enhance this video with AI-generated artwork?**
>
> - **Procedural only** (default): Real-time geometric patterns, waveforms, and particle effects driven by the audio data. Free and renders quickly.
> - **AI-enhanced**: AI generates unique artwork for each section based on the keyframe prompts above, creating richer, more thematic visuals. Uses AI image generation.

Then end with a clear call to action:
> **Ready to render?** Type "render" or "let's go" to start. Add "with AI" if you want AI-generated keyframes.

When the user explicitly confirms they want to render, respond with ONLY a JSON render spec block wrapped in ```json fences. The JSON must conform to this schema:
{
  "useAiKeyframes": true/false,
  "globalStyle": {
    "template": "<one of: nebula, geometric, waveform, cinematic, retro, nature, abstract, urban, glitchbreak, 90s-anime>",
    "styleModifiers": ["<modifier>", ...],
    "recurringMotifs": ["<motif>", ...],
    "lyricsDisplay": {
      "enabled": true/false,
      "font": "<sans|serif|mono>",
      "size": "<small|medium|large>",
      "animation": "<fade-word|typewriter|karaoke|float-up|none>",
      "color": "#hex",
      "shadow": true/false
    }
  },
  "sections": [
    {
      "label": "<section label>",
      "startTime": <float>,
      "endTime": <float>,
      "colorPalette": ["#hex", ...],
      "motionStyle": "<slow-drift|pulse|energetic|chaotic|breathing|glitch|smooth-flow|staccato>",
      "intensity": <0.0-1.0>,
      "aiPrompt": "<detailed, vivid image generation prompt specific to this section's mood, themes, and agreed visual concept>",
      "transitionIn": "<transition type>",
      "transitionOut": "<transition type>",
      "visualElements": ["<element>", ...]
    }
  ],
  "exportSettings": {
    "resolution": [1920, 1080],
    "fps": 30,
    "aspectRatio": "16:9",
    "format": "mp4",
    "quality": "high"
  }
}

Set "useAiKeyframes" to true ONLY if the user explicitly asks for AI-generated keyframes / AI rendering. Default is false.

### Phase: EDITING (post-render)
Interpret edit requests and suggest specific changes. Reference sections by name and timestamp.
CRITICAL RULES for editing:
1. Always clarify and confirm user intent before applying any edit
2. When the user describes a change, restate what you understand they want and ask them to confirm before proceeding
3. Allow the user to be as detailed as they want — they may specify exact timestamps, individual sections, or broad stylistic changes
4. Never apply edits until the user explicitly confirms each one
5. Present proposed changes clearly (what will change, which sections/timestamps are affected) so the user can approve or modify
"""

RENDER_SPEC_EXTRACTION_PROMPT = """Based on the conversation so far, extract the final agreed-upon visualization plan as a JSON render spec. Output ONLY valid JSON (no markdown fences, no explanation) conforming to this schema:

{
  "useAiKeyframes": false,
  "globalStyle": {
    "template": "<one of: nebula, geometric, waveform, cinematic, retro, nature, abstract, urban, glitchbreak, 90s-anime>",
    "styleModifiers": ["<modifier>"],
    "recurringMotifs": ["<motif>"],
    "lyricsDisplay": {
      "enabled": true,
      "font": "sans",
      "size": "medium",
      "animation": "fade-word",
      "color": "#F0F0F5",
      "shadow": true
    }
  },
  "sections": [
    {
      "label": "<section label>",
      "startTime": 0.0,
      "endTime": 10.0,
      "colorPalette": ["#hex1", "#hex2", "#hex3"],
      "motionStyle": "slow-drift",
      "intensity": 0.5,
      "aiPrompt": "<detailed, vivid image generation prompt specific to this section>",
      "transitionIn": "cross-dissolve",
      "transitionOut": "cross-dissolve",
      "visualElements": ["element1", "element2"]
    }
  ],
  "exportSettings": {
    "resolution": [1920, 1080],
    "fps": 30,
    "aspectRatio": "16:9",
    "format": "mp4",
    "quality": "high"
  }
}

IMPORTANT:
- Set "useAiKeyframes" to true ONLY if the user explicitly requested AI rendering/AI keyframes.
- Use the exact section boundaries from the audio analysis.
- Each section's "aiPrompt" should be a detailed, vivid prompt suitable for AI image generation — not generic. Tailor it to the specific mood, themes, and visual concept discussed for that section.
- Each section's "visualElements" should list specific procedural effects (particles, geometric shapes, waveforms, etc.) tailored to the section.
- Fill in ALL fields based on what was discussed."""


class LLMService:
    """Gemini Flash integration for thematic analysis and conversational refinement."""

    def __init__(self) -> None:
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            api_key = settings.google_ai_api_key
            if not api_key:
                raise RuntimeError(
                    "GOOGLE_AI_API_KEY is not set. Please set it in your .env file or environment."
                )
            self._client = genai.Client(api_key=api_key)
        return self._client

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        audio_context: str = "",
    ) -> AsyncGenerator[str]:
        """Stream a chat response from Gemini Flash.

        Retries up to 3 times on rate-limit (429) errors with backoff.
        """
        if not messages:
            yield "I need a message to respond to. Please describe what you'd like for your visualization."
            return

        client = self._get_client()

        # Build the conversation history as Content objects
        history: list[types.Content] = []

        if audio_context and messages:
            first_msg = messages[0]
            augmented_content = f"{audio_context}\n\n---\n\nUser request: {first_msg.content}"
            history.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=augmented_content)],
                )
            )
            for msg in messages[1:]:
                role = "user" if msg.role == "user" else "model"
                history.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg.content)],
                    )
                )
        else:
            for msg in messages:
                role = "user" if msg.role == "user" else "model"
                history.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg.content)],
                    )
                )

        # The last message is the new user input — remove from history for send_message
        last_content = history.pop()

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.8,
            top_p=0.95,
            max_output_tokens=8192,
        )

        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                chat = client.aio.chats.create(
                    model=settings.gemini_model,
                    history=history if history else None,
                    config=config,
                )

                response = await chat.send_message_stream(
                    last_content.parts[0].text if last_content.parts else "",
                )

                async for chunk in response:
                    if chunk.text:
                        yield chunk.text

                return  # Success — stop retrying

            except ClientError as e:
                if e.code == 429 and attempt < max_retries:
                    delay = 15.0
                    match = _re.search(
                        r"retry in ([\d.]+)s", str(e), _re.IGNORECASE,
                    )
                    if match:
                        delay = float(match.group(1)) + 1.0
                    logger.warning(
                        "Rate limited on stream_chat (attempt %d/%d), "
                        "retrying in %.1fs",
                        attempt + 1, max_retries, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.exception("Gemini API error")
                yield (
                    "\n\n*I encountered an error communicating with "
                    "the AI service. Please try again.*"
                )
                return

            except Exception:
                logger.exception("Gemini API error")
                yield (
                    "\n\n*I encountered an error communicating with "
                    "the AI service. Please try again.*"
                )
                return

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

    async def extract_render_spec(
        self,
        messages: list[ChatMessage],
        audio_context: str,
    ) -> dict | None:
        """Extract a structured render spec from the conversation.

        Retries up to 3 times on rate-limit (429) errors with backoff.
        Returns the parsed JSON dict or None if extraction fails.
        """
        client = self._get_client()

        # Build history with audio context
        history: list[types.Content] = []
        if audio_context and messages:
            first_msg = messages[0]
            augmented = f"{audio_context}\n\n---\n\nUser request: {first_msg.content}"
            history.append(
                types.Content(role="user", parts=[types.Part.from_text(text=augmented)])
            )
            for msg in messages[1:]:
                role = "user" if msg.role == "user" else "model"
                history.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=msg.content)])
                )
        else:
            for msg in messages:
                role = "user" if msg.role == "user" else "model"
                history.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=msg.content)])
                )

        # Add the extraction prompt as a final user message
        history.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=RENDER_SPEC_EXTRACTION_PROMPT)],
            )
        )
        last_content = history.pop()

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=4096,
        )

        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                chat = client.aio.chats.create(
                    model=settings.gemini_model,
                    history=history if history else None,
                    config=config,
                )

                response = await chat.send_message(
                    last_content.parts[0].text if last_content.parts else "",
                )

                raw = response.text.strip()
                # Strip markdown fences if present
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[: raw.rfind("```")]
                raw = raw.strip()

                return json.loads(raw)

            except ClientError as e:
                if e.code == 429 and attempt < max_retries:
                    # Parse retry delay from error message if available
                    delay = 15.0  # default
                    match = _re.search(r"retry in ([\d.]+)s", str(e), _re.IGNORECASE)
                    if match:
                        delay = float(match.group(1)) + 1.0
                    logger.warning(
                        "Rate limited on render spec extraction (attempt %d/%d), "
                        "retrying in %.1fs",
                        attempt + 1, max_retries, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.exception("Gemini API error extracting render spec")
                return None
            except json.JSONDecodeError:
                logger.warning("Failed to parse render spec JSON from LLM response")
                return None
            except Exception:
                logger.exception("Error extracting render spec")
                return None

        return None
