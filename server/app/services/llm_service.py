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

SYSTEM_PROMPT = """You are a creative director for music visualization. You analyze songs and design beat-synced visual experiences rendered as real-time GLSL shaders.

Your capabilities:
- Analyze lyrics for themes, symbolism, pop culture references, and emotional arcs
- Design visual concepts described in vivid, shader-programmer terms (SDFs, raymarching, fractals, particle fields, domain warping, etc.)
- Suggest color palettes (with hex codes), motion dynamics, and visual effects per song section
- Iterate on suggestions based on user feedback
- Interpret post-render edit requests into specific visual parameter changes

Guidelines:
1. Always ground suggestions in the actual audio data (reference specific sections, timestamps, energy levels)
2. When suggesting colors, always provide hex codes
3. Describe visuals using shader/demoscene terminology — the end product is a GLSL fragment shader, not a template
4. Think in terms of: raymarched SDFs, fractal noise (fbm), domain repetition for particle fields, Voronoi patterns, kaleidoscopic transforms, signed distance fields, volumetric effects, reaction-diffusion, etc.
5. Ask clarifying follow-up questions when the user's intent is ambiguous (max 2 at a time)
6. Always provide options with a recommended default
7. After 3-4 exchanges without new change requests, offer to proceed to rendering
8. Keep responses focused and structured with clear section headers

When providing a section-by-section breakdown, use this format for each section:
**[Section Name] (start_time - end_time)**
- Mood: ...
- Colors: #hex1, #hex2, #hex3
- Shader Concept: (describe the visual scene in shader terms — e.g. "raymarched organic blobs with smooth union, displacing surfaces with fbm noise driven by bass, domain-warped kaleidoscope with 8-fold symmetry")
- Audio Mapping: (how audio features drive the visuals — e.g. "bass pulses sphere radius, treble adds crystalline surface detail, beats trigger color palette rotation")
- AI Keyframe Prompt: "..."

## Conversation Phases

You operate in distinct phases. Your behavior adapts based on the current phase:

### Phase: ANALYSIS
When you receive audio analysis data and a user prompt for the first time, provide:
1. **Track Overview** — Genre, mood, emotional arc, narrative summary
2. **Thematic Analysis** — Core themes, symbolism, metaphors, pop culture references
3. **Visual Concept** — Describe the overall shader aesthetic in vivid terms. Think Shadertoy art: raymarched landscapes, fractal nebulae, infinite geometric corridors, organic bioluminescent forms, etc. The visualization is generated as a GLSL fragment shader, so anything expressible in math is possible.
4. **Section-by-Section Visualization** — For each detected section, suggest colors (hex), shader techniques, audio mappings, and a keyframe prompt
5. **Shader Description** — A 2-3 sentence description that a shader programmer would use to write the GLSL code. Be specific about techniques.

End with 1-2 follow-up questions to refine the concept.

### Phase: REFINEMENT
Respond to user feedback with specific, modified suggestions. Keep track of all agreed-upon decisions. Reference specific timestamps and energy levels from the audio data.

### Phase: CONFIRMATION
Detect when the user is satisfied. Signs include:
- "That's perfect", "Love it", "Let's go", "Looks good"
- "Render it", "Make the video", "Start rendering"
- Lack of further change requests after 2+ exchanges

When you detect satisfaction, present a COMPREHENSIVE FINAL SUMMARY:

## 1. Overall Creative Vision
- **Visual Concept**: A 2-3 sentence description of the shader aesthetic and narrative arc
- **Shader Description**: A detailed description for the shader generator — describe the specific techniques, scene composition, and how audio drives every element
- **Recurring Motifs**: Visual elements that appear throughout (e.g., "fractal branching structures", "raymarched metaballs")
- **Color Story**: How the overall color palette evolves across the track

## 2. Section-by-Section Breakdown
For EVERY section detected in the audio, present a detailed breakdown:

**[Section Name] (start_time - end_time) — [duration]s**
| Attribute | Value |
|-----------|-------|
| Mood/Energy | e.g., "Contemplative, low energy (0.3)" |
| Color Palette | ALL hex codes with color names |
| Shader Concept | Specific shader techniques: "raymarched SDF organic forms with smooth-union, fbm displacement, 6-fold kaleidoscope symmetry" |
| Audio Mapping | "bass → sphere radius pulsing, treble → surface detail frequency, beat → color palette shift, spectral centroid → warm/cool color temperature" |
| Intensity | 0.0-1.0 scale |
| AI Keyframe Prompt | The EXACT vivid prompt for AI image generation |
| Transition In/Out | e.g., "cross-dissolve" |

## 3. Lyrics Display Configuration
- Font, size, animation, color, shadow

## 4. Export Settings
- Resolution, FPS, aspect ratio, quality

## 5. Rendering Options
> **Ready to render?** Type "render" or "let's go" to start.
> Add "with AI" for AI-generated keyframe images, or "with AI video" for full AI video generation.

When the user explicitly confirms they want to render, respond with ONLY a JSON render spec block wrapped in ```json fences. The JSON must conform to this schema:
{
  "useAiKeyframes": true/false,
  "globalStyle": {
    "template": "shader",
    "shaderDescription": "<detailed description of the shader visual concept — this will be used to generate the GLSL code>",
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
      "aiPrompt": "<detailed, vivid image generation prompt>",
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

The "shaderDescription" field is CRITICAL — it must be a rich, detailed description of the visual aesthetic that will be used to generate the actual GLSL shader code. Example: "Raymarched scene with infinite grid of glowing spheres using domain repetition. Sphere radii pulse with bass energy. Surface material uses fbm noise for organic texture displacement. Camera orbits slowly with smooth noise. Color palette cycles through warm ambers to cool teals driven by spectral centroid. Beat impacts trigger flash bloom and momentary kaleidoscope fold. Background is deep space with volumetric fog lit by point lights at sphere positions."

### Phase: EDITING (post-render)
Interpret edit requests and suggest specific changes. Reference sections by name and timestamp.
CRITICAL RULES for editing:
1. Always clarify and confirm user intent before applying any edit
2. When the user describes a change, restate what you understand they want and ask them to confirm
3. Allow the user to be as detailed as they want
4. Never apply edits until the user explicitly confirms each one
5. Present proposed changes clearly
"""

RENDER_SPEC_EXTRACTION_PROMPT = """Based on the conversation so far, extract the final agreed-upon visualization plan as a JSON render spec. Output ONLY valid JSON (no markdown fences, no explanation) conforming to this schema:

{
  "useAiKeyframes": false,
  "globalStyle": {
    "template": "shader",
    "shaderDescription": "<detailed description of the overall shader visual concept — techniques, scene, composition, how audio drives everything>",
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
- Set "template" to "shader" always.
- The "shaderDescription" is the MOST important field — it must contain a detailed, vivid description of the GLSL shader visual concept that was discussed. This will be used to generate the actual fragment shader code.
- Set "useAiKeyframes" to true ONLY if the user explicitly requested AI rendering/AI keyframes.
- Use the exact section boundaries from the audio analysis.
- Each section's "aiPrompt" should be a detailed, vivid prompt suitable for AI image generation.
- Fill in ALL fields based on what was discussed."""

# The shader generation system prompt — this is the core of the visual engine.
# Based on ShaderGen (arxiv 2512.08951) and Shadertoy best practices.
# NOTE: This is a plain string (NOT an f-string), so use single { } for GLSL.
SHADER_SYSTEM_PROMPT = """\
You are a legendary demoscene artist and Shadertoy programmer. Your GLSL \
shaders have won competitions for their stunning beauty, technical \
sophistication, and musical responsiveness. You create art that lives at \
the intersection of mathematics, music, and visual poetry.

You write a single GLSL fragment shader function:
  void mainImage(out vec4 fragColor, in vec2 fragCoord)
You may include any number of helper functions above mainImage.

## UNIFORMS (already declared — do NOT redeclare)

uniform float iTime;              // elapsed seconds
uniform vec2  iResolution;        // viewport pixels
uniform float u_bass;             // bass band energy       [0,1]
uniform float u_lowMid;           // low-mid band energy    [0,1]
uniform float u_mid;              // mid band energy        [0,1]
uniform float u_highMid;          // high-mid band energy   [0,1]
uniform float u_treble;           // treble band energy     [0,1]
uniform float u_energy;           // overall RMS amplitude  [0,1]
uniform float u_beat;             // beat pulse intensity    [0,1]
uniform float u_spectralCentroid; // spectral brightness    [0,1]

## AESTHETIC DEFAULTS — Smooth & Cinematic

- Multiply audio uniforms by 0.1-0.4 for gentle modulation.
- Beat sync: smoothstep or pow, not raw values.
- Gradual color shifts, no strobing.

## AUDIO-VISUAL MAPPING

- u_bass:  radius pulsing, domain warping (scale 0.2-0.4)
- u_mid:   color modulation, pattern density
- u_treble: fine detail, shimmer (scale 0.1-0.3)
- u_beat:  smooth bloom via smoothstep(0.0, 1.0, u_beat)
- u_energy: overall brightness, glow
- u_spectralCentroid: color temperature (low=warm, high=cool)

## TECHNIQUES

You have the full Shadertoy arsenal:
- Raymarching + SDFs (sphere, box, torus, smooth-union, domain rep)
- Fractals (Mandelbulb, Julia, IFS, Menger sponge)
- Noise (Perlin, fbm, Voronoi, domain warping, curl noise)
- 2D (polar transforms, tunnels, flow fields, Lissajous)
- Rendering (iq palette, Blinn-Phong, Fresnel, bloom, vignette)
- Particles (hash grids, glow accumulation)

## ABSOLUTE RULES (#version 330)

Your code is injected into a wrapper that provides #version 330, \
precision, all uniforms, out vec4 fragColor, and void main(). \
You provide ONLY helper functions + mainImage.

1.  NO texture/iChannel/sampler2D/dFdx/dFdy/fwidth
2.  ALL float literals need a decimal point: 1.0 not 1
3.  Return types MUST match function signature exactly: \
    float functions return float, vec3 functions return vec3
4.  void functions: use `return;` — NEVER `return void;` or \
    `return void(...);`
5.  Do NOT redeclare uniforms/out vec4 fragColor/void main()
6.  No #version or precision directives
7.  Every statement ends with a semicolon — especially the \
    last statement before a closing brace }
8.  for-loop bounds must be compile-time constants
9.  Function calls MUST match the defined signature \
    (same number and types of arguments)
10. NEVER call a function with (void) — use empty parens ()
11. Every function you CALL must be DEFINED above the call site
12. Keep total shader under 120 lines for reliability
13. Match ALL parentheses and braces — count them carefully

## WORKING EXAMPLE (raymarched scene)

vec3 palette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return a + b * cos(6.28318 * (c * t + d));
}

float sdSphere(vec3 p, float r) {
    return length(p) - r;
}

float scene(vec3 p) {
    float sphere = sdSphere(p, 1.0 + u_bass * 0.3);
    float ground = p.y + 1.0;
    return min(sphere, ground);
}

vec3 getNormal(vec3 p) {
    vec2 e = vec2(0.001, 0.0);
    return normalize(vec3(
        scene(p + e.xyy) - scene(p - e.xyy),
        scene(p + e.yxy) - scene(p - e.yxy),
        scene(p + e.yyx) - scene(p - e.yyx)
    ));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);
    vec3 ro = vec3(0.0, 0.0, -3.0 + u_energy * 0.5);
    vec3 rd = normalize(vec3(uv, 1.5));
    float t = 0.0;
    for (int i = 0; i < 64; i++) {
        vec3 p = ro + rd * t;
        float d = scene(p);
        if (d < 0.001) break;
        t += d;
        if (t > 20.0) break;
    }
    vec3 col = vec3(0.0);
    if (t < 20.0) {
        vec3 p = ro + rd * t;
        vec3 n = getNormal(p);
        float diff = max(dot(n, normalize(vec3(1.0, 1.0, -1.0))), 0.0);
        col = palette(t * 0.1 + iTime * 0.1 + u_spectralCentroid,
            vec3(0.5), vec3(0.5), vec3(1.0, 0.7, 0.4),
            vec3(0.0, 0.15, 0.2)) * diff;
        col += vec3(0.15) * smoothstep(0.0, 1.0, u_beat);
    }
    col += vec3(0.02) * u_treble;
    col *= 1.0 - smoothstep(0.4, 1.4, length(uv));
    fragColor = vec4(col, 1.0);
}

## OUTPUT

Output ONLY valid GLSL code. No markdown fences, no backticks, \
no explanation. Helper functions first, then mainImage.\
"""


# ── Regex patterns for sanitising LLM-generated shader code ──────────
_RE_MARKDOWN_FENCE = _re.compile(
    r"^```(?:glsl|hlsl|c|cpp)?\s*\n?", _re.MULTILINE,
)
_RE_MARKDOWN_CLOSE = _re.compile(r"\n?```\s*$")
_RE_VERSION = _re.compile(r"^\s*#\s*version\s+.*$", _re.MULTILINE)
_RE_PRECISION = _re.compile(
    r"^\s*precision\s+\w+\s+float\s*;.*$", _re.MULTILINE,
)
_RE_UNIFORM = _re.compile(
    r"^\s*uniform\s+\w+\s+"
    r"(?:iTime|iResolution|u_bass|u_lowMid|u_mid|u_highMid"
    r"|u_treble|u_energy|u_beat|u_spectralCentroid)\s*;.*$",
    _re.MULTILINE,
)
_RE_OUT_FRAGCOLOR = _re.compile(
    r"^\s*out\s+vec4\s+fragColor\s*;.*$", _re.MULTILINE,
)
_RE_VOID_MAIN = _re.compile(
    r"void\s+main\s*\(\s*\)\s*\{[^}]*mainImage\s*\([^)]*\)\s*;"
    r"[^}]*\}",
    _re.DOTALL,
)
# `return void;` or `return void(...)` — void is not a value in GLSL
_RE_RETURN_VOID = _re.compile(r"\breturn\s+void\s*(?:\([^)]*\)\s*)?;")
# Double braces {{ or }} that the LLM may copy from prompt examples
_RE_DOUBLE_BRACE_OPEN = _re.compile(r"\{\{")
_RE_DOUBLE_BRACE_CLOSE = _re.compile(r"\}\}")
# Function CALL with (void) argument — e.g. `foo(void)` → `foo()`
# Only matches calls, not declarations (declarations have a type before the name)
_RE_VOID_CALL = _re.compile(r"(\w+\s*\(\s*)void(\s*\))")

_logger = logging.getLogger(__name__)


def _fix_missing_semicolons(code: str) -> str:
    """Insert missing semicolons before void/float/vec/int/mat
    function declarations.

    The LLM often forgets the semicolon at the end of the last
    statement in a function body, so the next function declaration
    (starting with ``void``, ``float``, ``vec3``, etc.) becomes a
    syntax error like "unexpected VOID, expecting SEMICOLON".
    """
    # GLSL type keywords that can start a function declaration
    type_keywords = {
        "void", "float", "int", "vec2", "vec3", "vec4",
        "mat2", "mat3", "mat4", "bool", "ivec2", "ivec3", "ivec4",
    }
    lines = code.split("\n")
    fixed: list[str] = []
    for i, line in enumerate(lines):
        fixed.append(line)
        if i + 1 >= len(lines):
            continue
        # Check if next line starts a top-level function declaration
        next_stripped = lines[i + 1].lstrip()
        next_first_word = next_stripped.split("(")[0].split()
        if not next_first_word:
            continue
        # A top-level declaration looks like: "void funcName(" or
        # "float funcName(" at column 0
        if (
            lines[i + 1]
            and not lines[i + 1][0].isspace()
            and next_first_word[0] in type_keywords
            and "(" in lines[i + 1]
        ):
            # Check if current line looks like it's missing a terminator
            cur_stripped = line.rstrip()
            if cur_stripped and cur_stripped[-1] not in (
                ";", "{", "}", "/", "*", ",", "(", ")",
            ):
                # Insert semicolon at the end of current line
                fixed[-1] = line.rstrip() + ";"
                _logger.debug(
                    "Inserted missing semicolon at line %d: %s",
                    i + 1, fixed[-1].strip(),
                )
    return "\n".join(fixed)


def sanitize_shader_code(raw: str) -> str:
    """Clean up common LLM mistakes in generated GLSL code.

    Handles:
    - Markdown fences
    - Duplicate uniform / out / #version / precision declarations
    - Wrapper void main() that the host already provides
    - ``return void;`` and ``return void(...);``
    - Double braces ``{{`` / ``}}``
    - ``func(void)`` calls → ``func()``
    - Missing semicolons before function declarations
    - Stray backslash line continuations
    """
    code = raw.strip()

    # ── Strip markdown fences ────────────────────────────────
    code = _RE_MARKDOWN_FENCE.sub("", code)
    code = _RE_MARKDOWN_CLOSE.sub("", code)

    # ── Strip #version directive (wrapper adds it) ───────────
    code = _RE_VERSION.sub("", code)

    # ── Strip precision qualifier (wrapper adds it) ──────────
    code = _RE_PRECISION.sub("", code)

    # ── Strip redeclared uniforms ────────────────────────────
    code = _RE_UNIFORM.sub("", code)

    # ── Strip duplicate `out vec4 fragColor;` ────────────────
    code = _RE_OUT_FRAGCOLOR.sub("", code)

    # ── Strip void main() wrapper ────────────────────────────
    code = _RE_VOID_MAIN.sub("", code)

    # ── Fix `return void;` / `return void(0);` → `return;` ──
    code = _RE_RETURN_VOID.sub("return;", code)

    # ── Fix `func(void)` calls → `func()` ───────────────────
    # Only replace when it's clearly a call (no type keyword before)
    code = _RE_VOID_CALL.sub(r"\1\2", code)

    # ── Fix double braces {{ → { and }} → } ─────────────────
    code = _RE_DOUBLE_BRACE_OPEN.sub("{", code)
    code = _RE_DOUBLE_BRACE_CLOSE.sub("}", code)

    # ── Strip stray backslash line continuations ─────────────
    code = _re.sub(r"\\\n", "\n", code)

    # ── Fix missing semicolons before function declarations ──
    code = _fix_missing_semicolons(code)

    # ── Collapse excessive blank lines ───────────────────────
    code = _re.sub(r"\n{3,}", "\n\n", code)

    return code.strip()


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

    @staticmethod
    def _build_history(
        messages: list[ChatMessage],
        audio_context: str = "",
    ) -> list[types.Content]:
        """Convert ChatMessages into Gemini Content objects.

        If *audio_context* is provided it is prepended to the first user
        message so the LLM has full analysis data on every call.
        """
        history: list[types.Content] = []

        if audio_context and messages:
            first_msg = messages[0]
            augmented = (
                f"{audio_context}\n\n---\n\nUser request: {first_msg.content}"
            )
            history.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=augmented)],
                )
            )
            remaining = messages[1:]
        else:
            remaining = list(messages)

        for msg in remaining:
            role = "user" if msg.role == "user" else "model"
            history.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.content)],
                )
            )

        return history

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

        history = self._build_history(messages, audio_context)

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
                if e.code == 429:
                    err_str = str(e)
                    is_daily = "PerDay" in err_str or "per day" in err_str.lower()

                    if is_daily:
                        logger.warning("Daily Gemini quota exhausted")
                        yield (
                            "\n\n*Daily API quota has been reached. "
                            "The free tier allows 20 requests per day. "
                            "Please try again tomorrow or add billing at "
                            "https://ai.google.dev to increase your quota.*"
                        )
                        return

                    if attempt < max_retries:
                        delay = 15.0
                        match = _re.search(
                            r"retry in ([\d.]+)s", err_str, _re.IGNORECASE,
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
3. **Visual Concept** — Describe the shader-based visual aesthetic (raymarching, fractals, particles, etc.)
4. **Section-by-Section Visualization** — For each detected section, suggest colors (hex), shader techniques, audio mappings, and an AI keyframe prompt
5. **Shader Description** — A detailed description for the GLSL shader generator

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

        history = self._build_history(messages, audio_context)

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
                if e.code == 429:
                    err_str = str(e)
                    is_daily = "PerDay" in err_str or "per day" in err_str.lower()

                    if is_daily:
                        logger.warning("Daily Gemini quota exhausted during render spec extraction")
                        return None

                    if attempt < max_retries:
                        delay = 15.0
                        match = _re.search(r"retry in ([\d.]+)s", err_str, _re.IGNORECASE)
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

    async def _call_shader_llm(
        self,
        user_prompt: str,
        temperature: float = 0.8,
    ) -> str | None:
        """Send a single shader-generation request to the LLM.

        Handles rate-limit retries internally. Returns sanitized GLSL or
        ``None`` on total failure.
        """
        client = self._get_client()
        config = types.GenerateContentConfig(
            system_instruction=SHADER_SYSTEM_PROMPT,
            temperature=temperature,
            top_p=0.95,
            max_output_tokens=8192,
        )
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = await client.aio.models.generate_content(
                    model=settings.gemini_model,
                    contents=user_prompt,
                    config=config,
                )
                raw = response.text.strip()
                logger.debug(
                    "Raw LLM shader output (%d chars):\n%s",
                    len(raw), raw[:2000],
                )
                sanitized = sanitize_shader_code(raw)
                logger.debug(
                    "Sanitized shader (%d chars):\n%s",
                    len(sanitized), sanitized[:2000],
                )
                return sanitized
            except ClientError as e:
                if e.code == 429 and attempt < max_retries:
                    delay = 15.0
                    m = _re.search(
                        r"retry in ([\d.]+)s", str(e), _re.IGNORECASE,
                    )
                    if m:
                        delay = float(m.group(1)) + 1.0
                    logger.warning(
                        "Rate limited on shader gen "
                        "(attempt %d/%d), retrying in %.1fs",
                        attempt + 1, max_retries, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.exception("Gemini API error generating shader")
                return None
            except Exception:
                logger.exception("Error generating shader")
                return None
        return None

    async def generate_shader(
        self,
        description: str,
        mood_tags: list[str] | None = None,
        color_palette: list[str] | None = None,
    ) -> str | None:
        """Generate a new shader (initial attempt, no error context)."""
        mood_str = (
            ", ".join(mood_tags) if mood_tags else "energetic, dynamic"
        )
        color_hint = ""
        if color_palette:
            color_hint = (
                "\nPrefer these colors: "
                f"{', '.join(color_palette)}"
            )
        prompt = (
            "Create a visually stunning, music-reactive GLSL "
            "fragment shader.\n\n"
            f"Visual concept: {description}\n"
            f"Mood: {mood_str}{color_hint}\n\n"
            "Use advanced techniques (raymarching, SDFs, "
            "fractals, fbm noise, etc.) appropriate to the "
            "description. Every audio uniform should drive "
            "some visual parameter.\n\n"
            "CRITICAL SYNTAX REMINDERS:\n"
            "- Every statement MUST end with a semicolon\n"
            "- NEVER write `return void;` — use `return;`\n"
            "- NEVER call a function with void: "
            "`foo(void)` is INVALID in GLSL — use `foo()`\n"
            "- Every function you call must be defined "
            "ABOVE the call site\n"
            "- float functions MUST return float, "
            "vec3 functions MUST return vec3\n\n"
            "Output ONLY GLSL code. No markdown, no "
            "explanation, no uniform declarations."
        )
        return await self._call_shader_llm(prompt, temperature=0.75)

    async def fix_shader(
        self,
        previous_code: str,
        compile_error: str,
        description: str,
    ) -> str | None:
        """Ask the LLM to fix a broken shader while preserving its
        visual quality.

        The prompt references the *original description* so the LLM
        remembers what it's supposed to depict, and pinpoints the exact
        error location.
        """
        # ── Extract line numbers from ALL errors ─────────────
        error_lines: list[int] = []
        for m in _re.finditer(r"ERROR:\s*0:(\d+):", compile_error):
            err_line = int(m.group(1))
            # The wrapper prepends exactly 16 lines
            user_line = max(1, err_line - 16)
            error_lines.append(user_line)

        lines = previous_code.splitlines()
        line_hint = ""
        if error_lines:
            # Show context around each error line (deduplicated)
            shown: set[int] = set()
            snippets: list[str] = []
            for user_line in dict.fromkeys(error_lines):
                start = max(0, user_line - 3)
                end = min(len(lines), user_line + 4)
                snippet = "\n".join(
                    f"{'>>>' if i + 1 == user_line else '   '} "
                    f"{i + 1}: {lines[i]}"
                    for i in range(start, end)
                    if i not in shown
                )
                shown.update(range(start, end))
                if snippet:
                    snippets.append(snippet)
            if snippets:
                line_hint = (
                    "\nError location(s) in your code:\n"
                    + "\n---\n".join(snippets)
                    + "\n"
                )

        # Classify the error type for more targeted advice
        error_lower = compile_error.lower()
        specific_advice = ""
        if "undeclared identifier" in error_lower:
            # Extract the identifier name
            id_match = _re.search(
                r"'(\w+)'\s*:\s*undeclared identifier",
                compile_error,
            )
            if id_match:
                ident = id_match.group(1)
                specific_advice = (
                    f"The identifier '{ident}' is used but never "
                    f"defined. Either:\n"
                    f"- You forgot to define the function '{ident}' "
                    f"above where it's called\n"
                    f"- You defined it with a different name "
                    f"(typo in the name)\n"
                    f"- The definition was accidentally removed\n"
                    f"Make sure every function is DEFINED "
                    f"ABOVE its first use.\n\n"
                )
        elif "cannot construct this type" in error_lower:
            specific_advice = (
                "You wrote `return void;` or `return void(...)`. "
                "In void functions, just use `return;` with "
                "no value.\n\n"
            )
        elif "cannot convert return value" in error_lower:
            specific_advice = (
                "A function's return statement has the wrong "
                "type. Check that float functions return float, "
                "vec3 functions return vec3, etc. Use explicit "
                "constructors like float(...) or vec3(...).\n\n"
            )

        prompt = (
            f"This shader was meant to depict: {description}\n\n"
            f"It FAILED to compile with this error:\n"
            f"{compile_error}\n"
            f"{line_hint}\n"
            f"{specific_advice}"
            f"Broken shader:\n{previous_code}\n\n"
            "Fix ONLY the compilation error(s). Preserve "
            "all the visual quality, effects, and audio "
            "reactivity of the original shader.\n\n"
            "REMEMBER: The wrapper provides #version 330, "
            "all uniforms, out vec4 fragColor, and void "
            "main(). Do NOT redeclare those.\n\n"
            "Output ONLY the complete corrected GLSL code. "
            "No markdown fences, no explanation."
        )
        return await self._call_shader_llm(prompt, temperature=0.4)

    async def generate_shader_simple(
        self,
        description: str,
        mood_tags: list[str] | None = None,
    ) -> str | None:
        """Generate a fresh shader with emphasis on compilability.

        Still aims for visual beauty — uses the full description and
        mood — but steers toward techniques less prone to syntax errors.
        """
        mood_str = (
            ", ".join(mood_tags) if mood_tags else "energetic, dynamic"
        )
        prompt = (
            f"Create a stunning audio-reactive GLSL shader.\n\n"
            f"Visual concept: {description}\n"
            f"Mood: {mood_str}\n\n"
            "Use visually impressive techniques: domain "
            "warping, fbm noise, iq palette, polar distortion, "
            "Voronoi, layered sin patterns, flow fields, "
            "tunnel effects. Keep under 80 lines.\n\n"
            "Every audio uniform should drive a visual "
            "parameter. Make it look gorgeous.\n\n"
            "Output ONLY GLSL code. No markdown."
        )
        return await self._call_shader_llm(prompt, temperature=0.6)
