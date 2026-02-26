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
# NOTE: This is a plain string (NOT an f-string), so use single { } for GLSL.
SHADER_SYSTEM_PROMPT = """\
You are a legendary demoscene artist and Shadertoy programmer. You create \
stunning, COMPLEX audio-reactive GLSL shaders — raymarched worlds, fractal \
nebulae, infinite geometric corridors, bioluminescent forms, particle \
galaxies, flowing noise fields, Mandelbulb zooms, IFS fractals, domain-\
warped alien landscapes, volumetric god rays, kaleidoscopic crystal \
caverns, and infinite mirror halls. Your work is pure visual poetry driven \
by mathematics and music.

You are NOT constrained to simple effects. You should create shaders \
with the complexity and artistry seen on Shadertoy's front page: \
hundreds of raymarching steps, intricate fractal formulae, multi-layered \
noise compositions, thousands of particle-like elements via domain \
repetition, sophisticated lighting models with ambient occlusion, \
and cinematic camera paths.

## SETUP

Your code is inserted into a #version 330 wrapper that already declares \
all uniforms, `out vec4 fragColor`, and `void main()`. You output ONLY \
helper functions + `void mainImage(out vec4 fragColor, in vec2 fragCoord)`.

Available uniforms (do not redeclare):
  iTime, iResolution, u_bass, u_lowMid, u_mid, u_highMid,
  u_treble, u_energy, u_beat, u_spectralCentroid
All audio uniforms are in [0,1]. NO textures or samplers are available.
NEVER use texture(), sampler2D, sampler1D, or any texture sampling — \
there are NO texture inputs. Generate all visuals procedurally.

You MUST define `void mainImage(out vec4 fragColor, in vec2 fragCoord)` \
— this is the REQUIRED entry point. The wrapper calls it from main().

## AUDIO MAPPING — SMOOTH AND MUSICAL

Map EVERY audio uniform to something visible, but keep motion SMOOTH \
and cinematic. Avoid jerky, hyperactive, or seizure-inducing visuals.

- u_bass → gentle macro motion: radius pulsing, domain warping amplitude, \
  large-scale deformation. Keep scale SMALL: multiply by 0.1-0.3 max. \
  Example: `1.0 + u_bass * 0.2` NOT `1.0 + u_bass * 2.0`
- u_lowMid → medium-scale features: fog density, wave amplitude modulation \
  (scale 0.1-0.3)
- u_mid → color cycling, pattern frequency modulation, rotation speed \
  (scale 0.05-0.2)
- u_highMid → detail variation: noise octave weighting, surface roughness \
  (scale 0.1-0.3)
- u_treble → fine detail: shimmer, crystalline edges, sparkle effects \
  (scale 0.05-0.15)
- u_beat → VERY SUBTLE impact: gentle glow only. Maximum additive: \
  `col += vec3(0.08) * smoothstep(0.0, 1.0, u_beat)`. NEVER go above 0.1. \
  NEVER flash to white or black. NEVER zoom the camera on beats. \
  NEVER multiply color by u_beat — only ADD a tiny amount.
- u_energy → overall intensity: slight brightness boost, glow radius \
  (scale 0.1-0.3, added to a base of 0.7-0.8)
- u_spectralCentroid → tonal quality: warm/cool color temperature blend \
  (low=warm ambers, high=cool blues, scale 0.1-0.3)

## VISUAL QUALITY RULES — CRITICAL

These rules prevent ugly, unwatchable output. Follow them strictly:

1. CAMERA SPEED: Camera orbit/movement must be SLOW. Use `iTime * 0.05` \
   to `iTime * 0.15` for camera angles. NEVER use `iTime * 0.4` or higher. \
   The viewer should feel like they're drifting, not spinning.
2. NO CAMERA SHAKE: NEVER add random noise to camera position. Keep camera \
   movement on smooth curves (sin/cos with slow time).
3. NO EXCESSIVE ZOOM: Set a WIDE field of view. For simple cameras use \
   `normalize(vec3(uv, 2.0))` or wider. For lookat cameras use \
   `normalize(fwd * 2.0 + right * uv.x + up * uv.y)`. NEVER use focal \
   length below 1.8 — values like 0.5, 1.0, or 1.5 are TOO ZOOMED IN. \
   NEVER let audio uniforms multiply the FOV or camera distance — the \
   scene must stay at a stable, comfortable viewing distance. Camera \
   orbit radius should be 3.0-6.0 (not 1.0-2.0).
4. NO FULL-SCREEN FLASH: Beat impacts should add a TINY glow (0.05-0.08 max), \
   not a blinding white flash. `col += vec3(0.08) * smoothstep(...)` is the \
   MAXIMUM. `col += vec3(0.1) * u_beat` is already TOO BRIGHT. \
   `col += vec3(1.0) * u_beat` is absolutely FORBIDDEN. NEVER multiply the \
   entire color by u_beat — only ADD a small constant.
5. SMOOTH MOTION: All motion driven by audio should be smooth. Use \
   `mix()` or `smoothstep()` to interpolate, never raw uniform multiplication \
   that creates jitter.
6. STABLE COMPOSITION: The main subject should stay roughly centered and \
   at a consistent scale. Avoid audio-driven scaling that makes objects \
   balloon or shrink dramatically.
7. GENTLE COLOR TRANSITIONS: Color palette changes from audio should be \
   gradual (scale 0.1-0.3). Avoid abrupt color pops.

## TECHNIQUES — USE THESE FREELY, COMBINE THEM

Raymarching (128+ steps for complex scenes), SDFs (sphere, box, torus, \
cylinder, cone, capsule, smooth union/subtraction/intersection, domain \
repetition for infinite grids, twist/bend/displacement), fractals \
(Mandelbulb, Mandelbox, Julia sets, IFS/Iterated Function Systems, \
Sierpinski, Menger sponge), noise (fbm with 5-8 octaves, Voronoi, \
curl noise, domain warping chains, ridged noise, turbulence), polar \
transforms, tunnels, flow fields, particle hash grids (1000s of points \
via floor/fract), Phong/Blinn-Phong/PBR lighting, ambient occlusion, \
soft shadows, Fresnel, fog/volumetrics, glow/bloom, vignette, \
chromatic aberration, film grain, reaction-diffusion, Truchet tiles, \
kaleidoscope via angle modulo, parametric surfaces.

## EXAMPLE 1 — Raymarched Sphere (basic)

vec3 palette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return a + b * cos(6.28318 * (c * t + d));
}

float sdSphere(vec3 p, float r) {
    return length(p) - r;
}

float scene(vec3 p) {
    return sdSphere(p, 1.0 + u_bass * 0.3);
}

vec3 getNormal(vec3 p) {
    vec2 e = vec2(0.001, 0.0);
    return normalize(vec3(
        scene(p + e.xyy) - scene(p - e.xyy),
        scene(p + e.yxy) - scene(p - e.yxy),
        scene(p + e.yyx) - scene(p - e.yyx)));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);
    vec3 ro = vec3(0.0, 0.0, -3.0);
    vec3 rd = normalize(vec3(uv, 2.0));
    float t = 0.0;
    for (int i = 0; i < 64; i++) {
        float d = scene(ro + rd * t);
        if (d < 0.001) break;
        t += d;
        if (t > 20.0) break;
    }
    vec3 col = vec3(0.02);
    if (t < 20.0) {
        vec3 p = ro + rd * t;
        vec3 n = getNormal(p);
        float diff = max(dot(n, normalize(vec3(1.0, 1.0, -1.0))), 0.0);
        col = palette(t * 0.1 + iTime * 0.1 + u_spectralCentroid,
            vec3(0.5), vec3(0.5), vec3(1.0, 0.7, 0.4),
            vec3(0.0, 0.15, 0.2)) * diff;
        col += vec3(0.08) * smoothstep(0.0, 1.0, u_beat);
    }
    col *= 1.0 - 0.4 * length(uv);
    fragColor = vec4(col, 1.0);
}

## EXAMPLE 2 — fbm Noise Landscape

float hashFn(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noiseFn(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(
        mix(hashFn(i), hashFn(i + vec2(1.0, 0.0)), f.x),
        mix(hashFn(i + vec2(0.0, 1.0)), hashFn(i + vec2(1.0, 1.0)), f.x),
        f.y);
}

float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 5; i++) {
        v += a * noiseFn(p);
        p *= 2.0;
        a *= 0.5;
    }
    return v;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec2 p = uv * 6.0;
    p.x += iTime * 0.08;
    p += fbm(p * 0.8 + iTime * 0.05) * (0.3 + u_bass * 0.2);
    float n = fbm(p + u_mid * 0.3);
    float n2 = fbm(p * 2.0 - iTime * 0.1);
    vec3 col = mix(
        vec3(0.1, 0.2, 0.5),
        vec3(0.9, 0.4, 0.1),
        n + u_spectralCentroid * 0.2);
    col += vec3(0.6, 0.3, 0.8) * n2 * u_treble * 0.5;
    col += vec3(0.1) * smoothstep(0.0, 1.0, u_beat);
    col *= 0.8 + 0.2 * u_energy;
    fragColor = vec4(col, 1.0);
}

## EXAMPLE 3 — Domain-Rep Infinite Grid of Glowing Orbs (1000s of objects)

vec3 palette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return a + b * cos(6.28318 * (c * t + d));
}

float hashFn(float n) {
    return fract(sin(n) * 43758.5453123);
}

float sdSphere(vec3 p, float r) {
    return length(p) - r;
}

float scene(vec3 p) {
    vec3 rep = vec3(3.0 + u_lowMid * 0.5);
    vec3 q = mod(p + rep * 0.5, rep) - rep * 0.5;
    float baseR = 0.3 + u_bass * 0.25;
    float id = hashFn(dot(floor((p + rep * 0.5) / rep), vec3(1.0, 57.0, 113.0)));
    float r = baseR * (0.5 + 0.5 * id);
    return sdSphere(q, r);
}

vec3 getNormal(vec3 p) {
    vec2 e = vec2(0.001, 0.0);
    return normalize(vec3(
        scene(p + e.xyy) - scene(p - e.xyy),
        scene(p + e.yxy) - scene(p - e.yxy),
        scene(p + e.yyx) - scene(p - e.yyx)));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);
    float camT = iTime * 0.1;
    vec3 ro = vec3(sin(camT) * 6.0, 2.0 + sin(camT * 0.3) * 0.5, cos(camT) * 6.0);
    vec3 ta = vec3(0.0, 0.0, 0.0);
    vec3 fwd = normalize(ta - ro);
    vec3 right = normalize(cross(fwd, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(right, fwd);
    vec3 rd = normalize(fwd * 2.0 + right * uv.x + up * uv.y);
    float t = 0.0;
    vec3 col = vec3(0.01, 0.01, 0.03);
    for (int i = 0; i < 128; i++) {
        vec3 p = ro + rd * t;
        float d = scene(p);
        if (d < 0.002) {
            vec3 n = getNormal(p);
            vec3 light = normalize(vec3(1.0, 2.0, -0.5));
            float diff = max(dot(n, light), 0.0);
            float spec = pow(max(dot(reflect(-light, n), -rd), 0.0), 64.0);
            float idVal = hashFn(dot(floor((p + 1.5) / 3.0), vec3(1.0, 57.0, 113.0)));
            col = palette(idVal + iTime * 0.05 + u_spectralCentroid * 0.2,
                vec3(0.5), vec3(0.5), vec3(1.0, 0.8, 0.5), vec3(0.0, 0.1, 0.2));
            col *= diff * 0.7 + 0.3;
            col += spec * u_treble * 0.5;
            float glow = 0.03 / (d + 0.01) * (0.5 + u_energy * 0.3);
            col += vec3(glow * 0.3, glow * 0.1, glow * 0.4);
            break;
        }
        float glow = 0.005 / (abs(d) + 0.05) * (0.5 + u_energy * 0.3);
        col += vec3(glow * 0.2, glow * 0.05, glow * 0.3) * 0.3;
        t += d;
        if (t > 40.0) break;
    }
    col += vec3(0.1, 0.07, 0.12) * smoothstep(0.0, 1.0, u_beat);
    col *= 1.0 - 0.35 * length(uv);
    fragColor = vec4(col, 1.0);
}

## EXAMPLE 4 — IFS Fractal (Menger-like)

float sdBox(vec3 p, vec3 b) {
    vec3 d = abs(p) - b;
    return min(max(d.x, max(d.y, d.z)), 0.0) + length(max(d, 0.0));
}

float mengerScene(vec3 p) {
    float d = sdBox(p, vec3(1.0));
    float s = 1.0;
    for (int m = 0; m < 4; m++) {
        vec3 a = mod(p * s, 2.0) - 1.0;
        s *= 3.0;
        vec3 r = abs(1.0 - 3.0 * abs(a));
        float da = max(r.x, r.y);
        float db = max(r.y, r.z);
        float dc = max(r.z, r.x);
        float c = (min(da, min(db, dc)) - 1.0) / s;
        d = max(d, c);
    }
    return d;
}

vec3 getNormalM(vec3 p) {
    vec2 e = vec2(0.0005, 0.0);
    return normalize(vec3(
        mengerScene(p + e.xyy) - mengerScene(p - e.xyy),
        mengerScene(p + e.yxy) - mengerScene(p - e.yxy),
        mengerScene(p + e.yyx) - mengerScene(p - e.yyx)));
}

vec3 palette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return a + b * cos(6.28318 * (c * t + d));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);
    float angle = iTime * 0.08 + u_mid * 0.1;
    vec3 ro = vec3(4.0 * sin(angle), 1.5 + u_bass * 0.15, 4.0 * cos(angle));
    vec3 ta = vec3(0.0);
    vec3 fwd = normalize(ta - ro);
    vec3 right = normalize(cross(fwd, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(right, fwd);
    vec3 rd = normalize(fwd * 2.0 + right * uv.x + up * uv.y);
    float t = 0.0;
    float ao = 0.0;
    vec3 col = vec3(0.02, 0.01, 0.04);
    for (int i = 0; i < 128; i++) {
        vec3 p = ro + rd * t;
        float d = mengerScene(p);
        if (d < 0.001) {
            vec3 n = getNormalM(p);
            vec3 light = normalize(vec3(0.8, 1.5, -0.6));
            float diff = max(dot(n, light), 0.0);
            float spec = pow(max(dot(reflect(-light, n), -rd), 0.0), 48.0);
            float fresnel = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);
            col = palette(length(p) * 0.2 + iTime * 0.03 + u_spectralCentroid * 0.2,
                vec3(0.5), vec3(0.5), vec3(0.9, 0.6, 1.0), vec3(0.1, 0.2, 0.3));
            col *= diff * 0.6 + 0.4;
            col += spec * vec3(0.8, 0.7, 1.0) * u_treble * 0.3;
            col += fresnel * vec3(0.2, 0.1, 0.4) * u_highMid * 0.3;
            col *= 1.0 - ao * 0.4;
            break;
        }
        ao += 0.02;
        t += d;
        if (t > 30.0) break;
    }
    col += vec3(0.08, 0.05, 0.1) * smoothstep(0.0, 1.0, u_beat);
    col *= 1.0 - 0.35 * length(uv);
    col = pow(col, vec3(0.9));
    fragColor = vec4(col, 1.0);
}

## RULES

1. Use float literals with decimals: 1.0, 0.5, 3.14159 (NEVER bare integers \
   in vec/mat constructors — vec3(1, 0, 0) is INVALID, use vec3(1.0, 0.0, 0.0))
2. Define helper functions ABOVE where they are called
3. Every statement ends with a semicolon
4. for-loop bounds must be compile-time constants
5. float functions return float, vec3 functions return vec3
6. Use mod(a, b) for float modulo — NEVER use the % operator on floats
7. Do NOT limit yourself to simple effects. Use 100+ line shaders with \
   multiple techniques if the concept calls for it.

## NVIDIA COMPATIBILITY — CRITICAL

NVIDIA's GLSL compiler is STRICT. These patterns compile on Mesa \
but CRASH on NVIDIA. NEVER use them:

- NEVER write `void(expr);` or `void();` — void is NOT a \
  constructor. To discard a return value, just call the function: \
  `myFunc();` not `void(myFunc());`
- NEVER write `return void;` or `return void(expr);` — in void \
  functions just write `return;`
- NEVER name a function `hash` — it collides with an NVIDIA \
  built-in. Use `hashFn` or `hash21` or `hash13` instead.
- NEVER name a function `noise` — it collides on some NVIDIA \
  drivers. Use `noiseFn` or `noiseVal` instead.
- NEVER pass `void` as an argument: `foo(void)` is only valid \
  in declarations, not calls.
- NEVER use bare integer literals in vec/mat constructors: \
  `vec3(1, 2, 3)` FAILS — must be `vec3(1.0, 2.0, 3.0)`.
- NEVER use `%` on float values — use `mod(a, b)` instead.
- NEVER use `#define` for function-like macros with complex \
  expressions — inline them as functions instead.
- NEVER use texture(), sampler2D(), or any texture/sampler types. \
  There are NO texture inputs — all visuals must be procedural.
- You MUST define `void mainImage(out vec4 fragColor, in vec2 fragCoord)` \
  — this is the entry point called by the wrapper.

## OUTPUT

Output ONLY valid GLSL code. No markdown fences, no backticks, \
no explanation. Helper functions first, then mainImage. Be ambitious.\
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
# Double braces {{ or }} that the LLM may copy from prompt examples
_RE_DOUBLE_BRACE_OPEN = _re.compile(r"\{\{")
_RE_DOUBLE_BRACE_CLOSE = _re.compile(r"\}\}")

_logger = logging.getLogger(__name__)


def _find_matching_paren(s: str, start: int) -> int:
    """Return index of the closing ')' matching the '(' at *start*.

    Handles nested parentheses.  Returns -1 when unmatched.
    """
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _strip_void_expressions(code: str) -> str:
    """Remove all void-as-expression patterns from GLSL code.

    NVIDIA GLSL compilers reject ``void(expr)``, ``void()``,
    ``return void;``, and ``func(void)`` with "cannot construct
    this type" — even though Mesa accepts them.  This function
    aggressively strips ALL such patterns line-by-line so the shader
    is cross-driver compatible.

    Uses balanced-paren matching to handle nested calls like
    ``void(sin(x * 2.0))`` correctly.
    """
    lines = code.split("\n")
    fixed: list[str] = []
    for line in lines:
        stripped = line.strip()

        # ── Keep function declarations: `void funcName(...)` ─────
        # These are the ONLY valid use of `void` at line-start
        # followed by an identifier + paren.
        if _re.match(r"^void\s+\w+\s*\(", stripped):
            fixed.append(line)
            continue

        # ── Remove standalone void(...) expression statements ────
        # Match `void(` then find its balanced `)`, check if that's
        # the whole statement (possibly with trailing `;`).
        m_void_stmt = _re.match(r"^(\s*)void\s*\(", line)
        if m_void_stmt:
            paren_start = line.index("(", m_void_stmt.start())
            paren_end = _find_matching_paren(line, paren_start)
            if paren_end != -1:
                after = line[paren_end + 1:].strip()
                if after in ("", ";"):
                    _logger.debug(
                        "Stripped void expression: %s", stripped,
                    )
                    continue

        # ── Fix `return void;` and `return void(...)` → `return;`
        m_ret = _re.search(r"\breturn\s+void\b", line)
        if m_ret:
            # Check for `return void(...)` with balanced parens
            after_void = line[m_ret.end():]
            m_paren = _re.match(r"\s*\(", after_void)
            if m_paren:
                paren_idx = m_ret.end() + after_void.index("(")
                paren_close = _find_matching_paren(line, paren_idx)
                if paren_close != -1:
                    line = (
                        line[:m_ret.start()]
                        + "return"
                        + line[paren_close + 1:]
                    )
            else:
                line = _re.sub(
                    r"\breturn\s+void\s*;", "return;", line,
                )

        # ── Fix `func(void)` calls → `func()` ──────────────────
        # In GLSL, void as a function argument is invalid in calls.
        line = _re.sub(r"(\w+\s*\(\s*)void(\s*\))", r"\1\2", line)

        # ── Fix void cast in expression: `void(expr)` → `expr` ──
        # Use balanced-paren matching for nested calls.
        while True:
            m_cast = _re.search(r"\bvoid\s*\(", line)
            if not m_cast:
                break
            # Skip if this is a function declaration
            before = line[:m_cast.start()].rstrip()
            if not before or _re.match(
                r"^void\s+\w+\s*$", line[:m_cast.end()],
            ):
                break
            paren_start = m_cast.end() - 1
            paren_end = _find_matching_paren(line, paren_start)
            if paren_end == -1:
                break
            inner = line[paren_start + 1:paren_end]
            line = line[:m_cast.start()] + inner + line[paren_end + 1:]

        fixed.append(line)
    return "\n".join(fixed)


def _rename_nvidia_reserved(code: str) -> str:
    """Rename user-defined functions that collide with NVIDIA built-ins.

    NVIDIA's GLSL compiler exposes ``hash``, ``noise``, ``input``,
    ``output`` in some extension contexts, causing 'no matching
    overloaded function found' or redefinition errors. We rename
    all occurrences to safe alternatives.
    """
    # Map of reserved names → safe replacements
    _RESERVED_MAP = {
        "hash": "hashFn",
        "noise": "noiseFn",
        "input": "inputVal",
        "output": "outputVal",
    }
    for reserved, replacement in _RESERVED_MAP.items():
        # Only rename if the user actually defines it as a function
        if _re.search(
            rf"\b(?:float|vec[234]|int|void|mat[234])\s+{reserved}\s*\(",
            code,
        ):
            code = _re.sub(rf"\b{reserved}\b", replacement, code)
    return code


def _fix_int_literals_in_constructors(code: str) -> str:
    """Fix bare integer literals in vec/mat constructors for NVIDIA.

    NVIDIA rejects ``vec3(1, 0, 0)`` — requires ``vec3(1.0, 0.0, 0.0)``.
    Mesa/Intel accept both. This converts integer literals inside
    vec/mat constructors to float literals.
    """
    def _fix_args(match: _re.Match) -> str:
        prefix = match.group(1)  # e.g. "vec3("
        args = match.group(2)
        suffix = match.group(3)  # ")"

        # Process each token — convert bare integers to floats
        def _int_to_float(arg_match: _re.Match) -> str:
            token = arg_match.group(0)
            # Don't convert if it's already a float or part of one
            return token + ".0"

        # Match standalone integer literals (not part of identifiers or floats)
        fixed_args = _re.sub(
            r"(?<![.\w])(-?\d+)(?![\w.])",
            _int_to_float,
            args,
        )
        return prefix + fixed_args + suffix

    # Match vec2/3/4 and mat2/3/4 constructors
    code = _re.sub(
        r"(\b(?:vec[234]|mat[234])\s*\()([^)]+)(\))",
        _fix_args,
        code,
    )
    return code


def _fix_modulo_on_floats(code: str) -> str:
    """Replace ``%`` operator with ``mod()`` in float contexts.

    NVIDIA rejects ``%`` for float operands; only ``mod()`` is valid.
    We leave integer ``%`` alone (inside int/ivec declarations or
    for-loop bodies with obvious int variables).
    """
    lines = code.split("\n")
    fixed: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Skip comments
        if stripped.startswith("//"):
            fixed.append(line)
            continue
        # Skip lines that are clearly int context
        if _re.match(r"^\s*(?:int|ivec|uint|uvec)\s", stripped):
            fixed.append(line)
            continue
        # Skip for-loop headers with int iterators
        if _re.match(r"^\s*for\s*\(\s*int\s", stripped):
            fixed.append(line)
            continue
        # Replace  `expr % expr` with `mod(expr, expr)`
        # This is a conservative regex: matches `a % b` patterns
        line = _re.sub(
            r"(\b[\w.]+(?:\([^)]*\))?)\s*%\s*([\w.]+(?:\([^)]*\))?)",
            r"mod(\1, \2)",
            line,
        )
        fixed.append(line)
    return "\n".join(fixed)


def _strip_texture_sampler_calls(code: str) -> str:
    """Remove texture()/sampler2D() calls that the LLM hallucinates.

    No textures or samplers are available in the shader environment, but
    the LLM sometimes generates ``texture(sampler2D(...), uv)`` patterns.
    These cause 'cannot construct opaque type sampler2D' errors.

    Strategy: replace entire ``texture(sampler2D(...), uv)`` expressions
    with ``vec4(0.5)`` so the shader still compiles; also remove any
    standalone ``sampler2D(...)`` constructions.
    """
    # Replace  texture(sampler2D(...), ...) → vec4(0.5)
    # We need balanced-paren matching for the nested sampler2D call.
    max_passes = 20
    for _ in range(max_passes):
        m = _re.search(r"\btexture\s*\(\s*sampler2D\s*\(", code)
        if not m:
            break
        # Find the outer texture( opening paren
        outer_start = code.index("(", m.start())
        outer_end = _find_matching_paren(code, outer_start)
        if outer_end == -1:
            break
        code = code[:m.start()] + "vec4(0.5)" + code[outer_end + 1:]

    # Remove any remaining standalone sampler2D(...) constructions
    for _ in range(max_passes):
        m = _re.search(r"\bsampler2D\s*\(", code)
        if not m:
            break
        paren_start = code.index("(", m.start())
        paren_end = _find_matching_paren(code, paren_start)
        if paren_end == -1:
            break
        # Replace with the inner expression (it's likely a channel/unit number)
        inner = code[paren_start + 1:paren_end].strip()
        code = code[:m.start()] + inner + code[paren_end + 1:]

    # Remove any remaining bare texture() calls (no samplers available)
    # Replace  texture(expr, uv)  →  vec4(0.5)
    for _ in range(max_passes):
        m = _re.search(r"\btexture\s*\(", code)
        if not m:
            break
        paren_start = code.index("(", m.start())
        paren_end = _find_matching_paren(code, paren_start)
        if paren_end == -1:
            break
        code = code[:m.start()] + "vec4(0.5)" + code[paren_end + 1:]

    return code


def _fix_narrow_fov(code: str) -> str:
    """Widen narrow field-of-view values in raymarching cameras.

    LLM-generated shaders often use tight FOV (small focal length)
    which makes scenes look extremely zoomed in.  We detect the two
    common raymarching camera patterns and enforce a minimum FOV:

    Pattern A (simple):  ``normalize(vec3(uv, X))``
    Pattern B (lookat):  ``normalize(fwd * X + right * uv.x + up * uv.y)``

    Minimum focal length is 1.8 (comfortable wide-angle).
    """
    min_fov = 1.8

    # Pattern A: normalize(vec3(uv, FLOAT))
    def _fix_simple_fov(m: _re.Match) -> str:
        prefix = m.group(1)  # "normalize(vec3(uv, "  or similar
        val_str = m.group(2)
        suffix = m.group(3)
        try:
            val = float(val_str)
            if val < min_fov:
                _logger.debug("Widening simple FOV from %s to %s", val_str, min_fov)
                return f"{prefix}{min_fov}{suffix}"
        except ValueError:
            pass
        return m.group(0)

    code = _re.sub(
        r"(normalize\s*\(\s*vec3\s*\(\s*uv\s*,\s*)"
        r"(\d+\.?\d*)"
        r"(\s*\))",
        _fix_simple_fov,
        code,
    )

    # Pattern B: normalize(fwd * FLOAT + right * uv.x + up * uv.y)
    def _fix_lookat_fov(m: _re.Match) -> str:
        prefix = m.group(1)
        val_str = m.group(2)
        suffix = m.group(3)
        try:
            val = float(val_str)
            if val < min_fov:
                _logger.debug("Widening lookat FOV from %s to %s", val_str, min_fov)
                return f"{prefix}{min_fov}{suffix}"
        except ValueError:
            pass
        return m.group(0)

    code = _re.sub(
        r"(normalize\s*\(\s*fwd\s*\*\s*)"
        r"(\d+\.?\d*)"
        r"(\s*\+\s*right\s*\*)",
        _fix_lookat_fov,
        code,
    )

    return code


def _fix_missing_semicolons(code: str) -> str:
    """Insert missing semicolons before function declarations.

    The LLM often omits the semicolon on the last statement before a
    new top-level function, causing "unexpected VOID/FLOAT" errors.
    """
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
        next_stripped = lines[i + 1].lstrip()
        next_first_word = next_stripped.split("(")[0].split()
        if not next_first_word:
            continue
        if (
            lines[i + 1]
            and not lines[i + 1][0].isspace()
            and next_first_word[0] in type_keywords
            and "(" in lines[i + 1]
        ):
            cur_stripped = line.rstrip()
            if cur_stripped and cur_stripped[-1] not in (
                ";", "{", "}", "/", "*", ",", "(", ")",
            ):
                fixed[-1] = line.rstrip() + ";"
    return "\n".join(fixed)


def sanitize_shader_code(raw: str) -> str:
    """Clean up common LLM mistakes in generated GLSL code.

    Handles:
    - Markdown fences
    - Duplicate uniform / out / #version / precision declarations
    - Wrapper void main() that the host already provides
    - ALL void-as-expression patterns (NVIDIA compat)
    - NVIDIA reserved name collisions (``hash`` → ``hashFn``, etc.)
    - Integer literals in vec/mat constructors (NVIDIA compat)
    - Float modulo ``%`` → ``mod()`` (NVIDIA compat)
    - texture() / sampler2D calls (no textures available)
    - Double braces ``{{`` / ``}}``
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

    # ── Convert void main() → void mainImage() if needed ──
    # When the LLM puts all code inside void main() without a
    # separate mainImage, the wrapper regex above doesn't match.
    # Rename main() to mainImage(out vec4 fragColor, in vec2 fragCoord)
    # so the host wrapper can call it.
    if not _re.search(r"\bvoid\s+mainImage\s*\(", code):
        # Handle both void main() and void main(void)
        code = _re.sub(
            r"\bvoid\s+main\s*\(\s*(?:void\s*)?\)",
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)",
            code,
            count=1,
        )
        # Replace any gl_FragColor writes with fragColor (the out param)
        code = _re.sub(r"\bgl_FragColor\b", "fragColor", code)

    # ── Rename near-miss mainImage signatures ────────────────
    # LLM sometimes writes mainImage with wrong params, e.g.
    # void mainImage(vec4 fragColor, vec2 fragCoord) (missing out/in)
    # or void mainImage(out vec4 color, in vec2 coord) (wrong names)
    if not _re.search(r"\bvoid\s+mainImage\s*\(\s*out\s+vec4\s+fragColor\s*,\s*in\s+vec2\s+fragCoord\s*\)", code):
        # Fix signatures that have mainImage but wrong parameter qualifiers/names
        code = _re.sub(
            r"\bvoid\s+mainImage\s*\([^)]*vec4[^)]*vec2[^)]*\)",
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)",
            code,
            count=1,
        )

    # ── Last resort: synthesize mainImage if completely missing ──
    # When the LLM outputs code with no entry point at all, look
    # for patterns that indicate rendering code (fragColor assignment,
    # gl_FragColor, etc.) and wrap appropriately.
    if not _re.search(r"\bvoid\s+mainImage\s*\(", code):
        # Check if there's a function that writes fragColor or gl_FragColor
        # (a rendering function with the wrong name)
        m_render_fn = _re.search(
            r"\bvoid\s+(\w+)\s*\(\s*(?:out\s+)?vec4\s+\w+\s*,"
            r"\s*(?:in\s+)?vec2\s+\w+\s*\)",
            code,
        )
        if m_render_fn:
            # Rename this function to mainImage with correct signature
            old_name = m_render_fn.group(1)
            _logger.debug(
                "Renaming '%s' to mainImage as entry point", old_name,
            )
            code = _re.sub(
                r"\bvoid\s+" + _re.escape(old_name) + r"\s*\([^)]*\)",
                "void mainImage(out vec4 fragColor, in vec2 fragCoord)",
                code,
                count=1,
            )
            # Also rename all calls to this function
            code = _re.sub(
                r"\b" + _re.escape(old_name) + r"\s*\(",
                "mainImage(",
                code,
            )
        elif _re.search(r"\bfragColor\b|\bgl_FragColor\b", code):
            # Code has fragColor writes but no function wrapping them.
            # Find the split point: keep top-level functions above,
            # wrap remaining statements in mainImage.
            _logger.debug(
                "No entry point found but fragColor writes detected "
                "— synthesizing mainImage wrapper",
            )
            # Simple heuristic: find the last closing brace of a
            # function definition, everything after it is "main" code
            lines = code.split("\n")
            last_func_end = -1
            brace_depth = 0
            in_func = False
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Detect function definition start
                if _re.match(
                    r"^(?:float|vec[234]|mat[234]|int|void|bool)"
                    r"\s+\w+\s*\(",
                    stripped,
                ) and not stripped.startswith("void mainImage"):
                    in_func = True
                if in_func:
                    brace_depth += stripped.count("{") - stripped.count("}")
                    if brace_depth <= 0 and in_func and "{" in code[:sum(len(l)+1 for l in lines[:i+1])]:
                        last_func_end = i
                        in_func = False
                        brace_depth = 0

            if last_func_end >= 0:
                # Split: functions stay above, remaining code goes into mainImage
                pre = "\n".join(lines[:last_func_end + 1])
                post = "\n".join(lines[last_func_end + 1:])
                if post.strip():
                    code = (
                        pre + "\n\n"
                        "void mainImage(out vec4 fragColor, in vec2 fragCoord) {\n"
                        "    vec2 uv = (fragCoord * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);\n"
                        + post + "\n"
                        "}\n"
                    )
            else:
                # No function definitions at all — wrap everything
                code = (
                    "void mainImage(out vec4 fragColor, in vec2 fragCoord) {\n"
                    "    vec2 uv = (fragCoord * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);\n"
                    + code + "\n"
                    "}\n"
                )
            code = _re.sub(r"\bgl_FragColor\b", "fragColor", code)

    # ── Fix ALL void-as-expression patterns ──────────────────
    # This is the big one: NVIDIA rejects void(expr), void(),
    # return void;, func(void) — even though Mesa accepts them.
    code = _strip_void_expressions(code)

    # ── Rename NVIDIA reserved names ─────────────────────────
    # NVIDIA exposes `hash`, `noise`, etc. as built-ins.
    code = _rename_nvidia_reserved(code)

    # ── Fix integer literals in vec/mat constructors ─────────
    # NVIDIA rejects vec3(1, 0, 0) — needs vec3(1.0, 0.0, 0.0)
    code = _fix_int_literals_in_constructors(code)

    # ── Fix float modulo operator ────────────────────────────
    # NVIDIA rejects `%` on floats — must use mod()
    code = _fix_modulo_on_floats(code)

    # ── Strip texture/sampler2D calls (no textures available) ─
    # LLM hallucinates texture(sampler2D(...), uv) patterns.
    code = _strip_texture_sampler_calls(code)

    # ── Fix double braces {{ → { and }} → } ─────────────────
    code = _RE_DOUBLE_BRACE_OPEN.sub("{", code)
    code = _RE_DOUBLE_BRACE_CLOSE.sub("}", code)

    # ── Strip stray backslash line continuations ─────────────
    code = _re.sub(r"\\\n", "\n", code)

    # ── Fix missing semicolons before function declarations ──
    code = _fix_missing_semicolons(code)

    # ── Widen narrow FOV values ─────────────────────────────
    # Prevents "too zoomed in" output by enforcing minimum focal length
    code = _fix_narrow_fov(code)

    # ── Log missing mainImage (no injection) ──────────────
    # Previously we injected a simple gradient here, but that
    # caused the shader to "compile" as amorphous color blobs
    # and prevented the curated fallback shaders from being used.
    # Now we let the code fail naturally so the retry pipeline
    # can attempt LLM fixes and ultimately fall back to the
    # sophisticated curated shaders (raymarching, fractals, etc.).
    if not _re.search(r"\bvoid\s+mainImage\s*\(", code):
        _logger.warning(
            "No mainImage found after all sanitization tiers — "
            "code will fail compile and trigger curated fallback"
        )

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
                raw = (response.text or "").strip()
                if not raw:
                    logger.warning(
                        "Gemini returned empty response for shader gen "
                        "(attempt %d/%d)",
                        attempt + 1, max_retries + 1,
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(2.0)
                        continue
                    return None
                sanitized = sanitize_shader_code(raw)
                # Log first 40 lines at INFO so compilation failures
                # can be diagnosed from server output.
                preview = "\n".join(
                    sanitized.splitlines()[:40],
                )
                logger.info(
                    "Generated shader (%d lines, %d chars):\n%s%s",
                    len(sanitized.splitlines()),
                    len(sanitized),
                    preview,
                    "\n..." if len(sanitized.splitlines()) > 40
                    else "",
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
            "Create a visually STUNNING, complex, music-reactive GLSL "
            "fragment shader.\n\n"
            f"Visual concept: {description}\n"
            f"Mood: {mood_str}{color_hint}\n\n"
            "IMPORTANT: Do NOT create a simple or minimal shader. "
            "Create something worthy of the Shadertoy front page. "
            "Use advanced techniques appropriate to the concept:\n"
            "- Raymarching with 100+ steps for detailed scenes\n"
            "- SDFs with smooth boolean operations for organic forms\n"
            "- Domain repetition for infinite grids (1000s of objects)\n"
            "- Fractal formulae (Mandelbulb, IFS, Menger sponge)\n"
            "- Multi-octave fbm noise with domain warping chains\n"
            "- Voronoi patterns for cellular/crystal effects\n"
            "- Sophisticated lighting (diffuse + specular + AO + Fresnel)\n"
            "- Cinematic camera orbits with smooth noise\n"
            "- Volumetric glow and fog for depth atmosphere\n"
            "Combine multiple techniques. Use 80-200 lines.\n\n"
            "EVERY audio uniform must drive a visible parameter, but keep "
            "motion SMOOTH and cinematic — no jerky camera, no excessive "
            "zoom, no blinding flashes. Use small multipliers (0.1-0.3) "
            "on audio uniforms. Camera speed: iTime * 0.05 to 0.15.\n"
            "u_bass → gentle macro deformation (scale 0.1-0.2), "
            "u_mid → color/pattern (scale 0.1-0.2), "
            "u_treble → fine detail (scale 0.05-0.15), "
            "u_beat → very subtle glow ONLY (scale 0.05-0.08, NEVER above 0.1), "
            "u_energy → brightness (scale 0.1-0.3), "
            "u_spectralCentroid → warm/cool color temp.\n\n"
            "NVIDIA RULES (CRITICAL):\n"
            "- Use float literals: 1.0 not 1 in vec/mat constructors\n"
            "- Name hash functions 'hashFn', noise functions 'noiseFn'\n"
            "- Never use void() as constructor/expression\n"
            "- Never write 'return void;'\n"
            "- Use mod(a, b) not % for floats\n"
            "- NEVER use texture(), sampler2D, or any sampler types — "
            "no textures are available. All visuals must be procedural.\n"
            "- You MUST define void mainImage(out vec4 fragColor, "
            "in vec2 fragCoord) — this is the required entry point.\n\n"
            "Output ONLY GLSL code."
        )
        return await self._call_shader_llm(prompt, temperature=0.85)

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
                "NVIDIA ERROR: You used `void` as a constructor or "
                "expression. Common causes:\n"
                "- `void(expr);` — just call the function directly\n"
                "- `return void;` or `return void(expr);` — use "
                "`return;` with no value\n"
                "- `void();` — remove the line entirely\n"
                "Find EVERY `void(` that is NOT a function "
                "declaration and remove/fix it.\n\n"
            )
        elif "no matching overloaded function" in error_lower:
            fn_match = _re.search(
                r"'(\w+)'\s*:\s*no matching overloaded",
                compile_error,
            )
            fn_name = fn_match.group(1) if fn_match else "unknown"
            specific_advice = (
                f"NVIDIA ERROR: '{fn_name}' collides with an NVIDIA "
                f"built-in function. Rename your function to "
                f"'{fn_name}Fn' everywhere (definition + all calls)."
                f"\n\n"
            )
        elif "cannot convert return value" in error_lower:
            specific_advice = (
                "A function's return statement has the wrong "
                "type. Check that float functions return float, "
                "vec3 functions return vec3, etc. Use explicit "
                "constructors like float(...) or vec3(...).\n\n"
            )
        elif "opaque type" in error_lower or "sampler2d" in error_lower:
            specific_advice = (
                "ERROR: You used texture() or sampler2D but NO textures "
                "or samplers are available in this environment. You MUST "
                "remove ALL texture(), sampler2D, sampler1D, and any "
                "texture sampling code. Generate all visuals procedurally "
                "using math — noise functions, SDFs, fractals, etc.\n\n"
            )
        elif "no function with name" in error_lower:
            fn_match = _re.search(
                r"no function with name '(\w+)'", compile_error,
            )
            fn_name = fn_match.group(1) if fn_match else "mainImage"
            specific_advice = (
                f"ERROR: The function '{fn_name}' is missing. "
                f"You MUST define `void mainImage(out vec4 fragColor, "
                f"in vec2 fragCoord)` — this is the required entry "
                f"point. The wrapper calls it from main().\n\n"
            )

        prompt = (
            f"This shader was meant to depict: {description}\n\n"
            f"It FAILED to compile with this error:\n"
            f"{compile_error}\n"
            f"{line_hint}\n"
            f"{specific_advice}"
            f"Broken shader:\n{previous_code}\n\n"
            "Fix ONLY the compilation error(s). Do NOT "
            "simplify, remove features, reduce complexity, "
            "or dumb down the shader. Preserve ALL the "
            "visual quality, effects, audio reactivity, "
            "and artistic complexity of the original.\n\n"
            "REMEMBER: The wrapper provides #version 330, "
            "all uniforms, out vec4 fragColor, and void "
            "main(). Do NOT redeclare those.\n\n"
            "NVIDIA COMPATIBILITY RULES:\n"
            "- Never use void() as constructor/expression\n"
            "- Never write 'return void;' — use 'return;'\n"
            "- Name hash functions 'hashFn', noise 'noiseFn'\n"
            "- Use float literals: 1.0 not 1 in constructors\n"
            "- Use mod(a, b) not % for float operands\n"
            "- Define functions ABOVE their first use\n"
            "- NEVER use texture(), sampler2D, or any sampler types "
            "— no textures are available\n"
            "- You MUST define void mainImage(out vec4 fragColor, "
            "in vec2 fragCoord) as the entry point\n\n"
            "Output ONLY the complete corrected GLSL code. "
            "No markdown fences, no explanation."
        )
        return await self._call_shader_llm(prompt, temperature=0.4)

    async def generate_shader_simple(
        self,
        description: str,
        mood_tags: list[str] | None = None,
    ) -> str | None:
        """Generate a fresh shader after previous attempts failed.

        Still aims for visual beauty and complexity — uses the full
        description and mood. Emphasizes NVIDIA-safe patterns by
        referencing the examples from the system prompt more directly.
        """
        mood_str = (
            ", ".join(mood_tags) if mood_tags else "energetic, dynamic"
        )
        prompt = (
            "A previous shader attempt failed to compile. Generate "
            "a FRESH, visually impressive audio-reactive GLSL shader "
            "from scratch. Do NOT simplify — be ambitious.\n\n"
            f"Visual concept: {description}\n"
            f"Mood: {mood_str}\n\n"
            "Use a DIFFERENT approach than typical simple shaders. "
            "Choose from these proven-to-compile techniques:\n"
            "- Raymarching with SDFs (like Example 1 or 3 in system prompt)\n"
            "- IFS fractals (like Example 4 in system prompt)\n"
            "- Multi-layered fbm with domain warping (like Example 2)\n"
            "- Domain repetition for infinite geometry grids\n"
            "- Voronoi + kaleidoscope combinations\n"
            "- Tunnel effects with complex texturing\n\n"
            "EVERY audio uniform must visibly affect the output, but keep "
            "motion SMOOTH and cinematic. Use small multipliers (0.1-0.3) "
            "on audio uniforms. Camera: iTime * 0.05 to 0.15. "
            "No camera shake, no excessive zoom, no blinding beat flashes.\n\n"
            "NVIDIA COMPATIBILITY IS MANDATORY:\n"
            "- ALL float literals must have decimals: 1.0 not 1\n"
            "- Name hash functions 'hashFn', noise functions 'noiseFn'\n"
            "- NEVER use void() as expression/constructor\n"
            "- NEVER write 'return void;' — use 'return;'\n"
            "- Use mod(a, b) not % for float modulo\n"
            "- Define all helper functions ABOVE their first use\n"
            "- NEVER use texture(), sampler2D, or any sampler/texture types "
            "— all visuals must be procedural\n"
            "- You MUST define void mainImage(out vec4 fragColor, "
            "in vec2 fragCoord) as the entry point\n\n"
            "Output ONLY GLSL code. No markdown fences. No explanation."
        )
        return await self._call_shader_llm(prompt, temperature=0.7)
