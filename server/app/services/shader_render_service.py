"""Headless GLSL shader video renderer using ModernGL + Mesa.

Renders the same Shadertoy-compatible shaders used in the browser preview,
driving them with per-frame audio features extracted from the analysis data.
Output is piped as raw RGBA frames into FFmpeg for encoding.
"""

import asyncio
import logging
import math
import struct
import subprocess
import tempfile
from pathlib import Path

import numpy as np

try:
    import moderngl
except ImportError:
    moderngl = None  # type: ignore[assignment]

from app.config import settings
from app.models.render import RenderSpec

logger = logging.getLogger(__name__)

# The same vertex shader used in the browser ShaderScene
_VERTEX_SHADER = """\
#version 330
in vec2 in_position;
void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
}
"""

# Wrapper that turns Shadertoy-style mainImage into a proper fragment shader
_FRAGMENT_WRAPPER = """\
#version 330
precision highp float;

uniform float iTime;
uniform vec2 iResolution;
uniform float u_bass;
uniform float u_lowMid;
uniform float u_mid;
uniform float u_highMid;
uniform float u_treble;
uniform float u_energy;
uniform float u_beat;
uniform float u_spectralCentroid;

out vec4 fragColor;

{user_code}

void main() {{
    mainImage(fragColor, gl_FragCoord.xy);
}}
"""

# ── Curated fallback shaders ──────────────────────────────────────────
# Each is pre-tested to compile under #version 330 with the fragment
# wrapper.  ``pick_fallback_shader()`` selects based on description
# keywords so the user always gets visual variety.

_FALLBACK_PLASMA = """\
vec3 palette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return a + b * cos(6.28318 * (c * t + d));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);
    float t = iTime * 0.3;
    float d = length(uv);
    uv += sin(uv.yx * 3.0 + t + u_bass * 2.0) * (0.3 + u_energy * 0.5);
    d = length(uv);
    float rings = sin(d * 8.0 - t * 2.0 + u_bass * 6.0) * 0.5 + 0.5;
    vec3 col = palette(d + t * 0.2 + u_spectralCentroid,
        vec3(0.5), vec3(0.5), vec3(1.0, 0.7, 0.4), vec3(0.0, 0.15, 0.2));
    col *= rings;
    col += vec3(0.1, 0.05, 0.15) * u_treble * 3.0;
    col += vec3(0.3) * smoothstep(0.0, 1.0, u_beat);
    col *= 1.0 - smoothstep(0.5, 1.5, length(uv));
    fragColor = vec4(col, 1.0);
}
"""

_FALLBACK_KALEIDOSCOPE = """\
vec3 palette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return a + b * cos(6.28318 * (c * t + d));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);
    float t = iTime * 0.2;
    float a = atan(uv.y, uv.x);
    float r = length(uv);
    float segments = 6.0;
    a = mod(a, 6.28318 / segments);
    a = abs(a - 3.14159 / segments);
    uv = vec2(cos(a), sin(a)) * r;
    uv += sin(uv * 4.0 + t + u_mid * 3.0) * (0.15 + u_bass * 0.2);
    float d = length(uv);
    float pattern = sin(d * 12.0 - t * 3.0 + u_bass * 5.0) * 0.5 + 0.5;
    pattern *= sin(a * segments * 2.0 + t + u_treble * 4.0) * 0.5 + 0.5;
    vec3 col = palette(d * 0.5 + t * 0.3 + u_spectralCentroid * 0.5,
        vec3(0.5), vec3(0.5), vec3(1.0, 0.8, 0.6), vec3(0.2, 0.1, 0.0));
    col *= pattern * 1.5;
    col += vec3(0.2, 0.1, 0.3) * smoothstep(0.0, 1.0, u_beat);
    col += vec3(0.05) * u_treble;
    col *= 1.0 - smoothstep(0.6, 1.6, r);
    fragColor = vec4(col, 1.0);
}
"""

_FALLBACK_TUNNEL = """\
vec3 palette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return a + b * cos(6.28318 * (c * t + d));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);
    float a = atan(uv.y, uv.x) / 6.28318;
    float r = length(uv);
    float tunnel = 0.5 / (r + 0.001);
    float speed = iTime * 0.5 + u_energy * 0.3;
    vec2 st = vec2(a + speed * 0.1, tunnel - speed);
    st += sin(st.yx * 3.0) * (0.1 + u_bass * 0.15);
    float p1 = sin(st.x * 12.0 + st.y * 6.0) * 0.5 + 0.5;
    float p2 = sin(st.x * 8.0 - st.y * 4.0 + u_mid * 4.0) * 0.5 + 0.5;
    float pattern = p1 * p2;
    vec3 col = palette(tunnel * 0.1 + iTime * 0.05 + u_spectralCentroid,
        vec3(0.5), vec3(0.5), vec3(0.8, 0.5, 1.0), vec3(0.1, 0.2, 0.3));
    col *= pattern;
    col *= tunnel * 0.4;
    col += vec3(0.2, 0.05, 0.1) * smoothstep(0.0, 1.0, u_beat);
    col += vec3(0.05) * u_treble / (r + 0.5);
    fragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
"""

_FALLBACK_WAVES = """\
float hashFn(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noiseFn(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hashFn(i);
    float b = hashFn(i + vec2(1.0, 0.0));
    float c = hashFn(i + vec2(0.0, 1.0));
    float d = hashFn(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
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
    vec2 p = uv * 4.0;
    float t = iTime * 0.3;
    p.x += t;
    p += fbm(p + t * 0.2) * (0.5 + u_bass * 0.5);
    float n = fbm(p);
    float wave = sin(uv.y * 10.0 + n * 6.0 + t * 2.0 + u_mid * 3.0);
    wave = smoothstep(0.0, 0.15, abs(wave - 0.3));
    float warm = 1.0 - u_spectralCentroid;
    vec3 c1 = vec3(0.1, 0.3, 0.6) * warm + vec3(0.5, 0.2, 0.7) * (1.0 - warm);
    vec3 c2 = vec3(0.8, 0.4, 0.2) * warm + vec3(0.2, 0.6, 0.9) * (1.0 - warm);
    vec3 col = mix(c1, c2, n);
    col *= wave;
    col += vec3(0.05, 0.02, 0.08) * u_energy * 2.0;
    col += vec3(0.2) * smoothstep(0.0, 1.0, u_beat);
    col += vec3(0.03) * u_treble;
    fragColor = vec4(col, 1.0);
}
"""

_FALLBACK_SPHERE = """\
vec3 palette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return a + b * cos(6.28318 * (c * t + d));
}

float sdSphere(vec3 p, float r) {
    return length(p) - r;
}

float scene(vec3 p) {
    float s = sdSphere(p, 1.0 + u_bass * 0.3);
    float ground = p.y + 1.5;
    return min(s, ground);
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
    float angle = iTime * 0.2;
    vec3 ro = vec3(sin(angle) * 3.5, 1.0, cos(angle) * 3.5);
    vec3 ta = vec3(0.0, 0.0, 0.0);
    vec3 fwd = normalize(ta - ro);
    vec3 right = normalize(cross(fwd, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(right, fwd);
    vec3 rd = normalize(fwd * 1.5 + right * uv.x + up * uv.y);
    float t = 0.0;
    for (int i = 0; i < 80; i++) {
        float d = scene(ro + rd * t);
        if (d < 0.001) break;
        t += d;
        if (t > 25.0) break;
    }
    vec3 col = vec3(0.02, 0.02, 0.05);
    if (t < 25.0) {
        vec3 p = ro + rd * t;
        vec3 n = getNormal(p);
        vec3 light = normalize(vec3(1.0, 2.0, -1.0));
        float diff = max(dot(n, light), 0.0);
        float spec = pow(max(dot(reflect(-light, n), -rd), 0.0), 32.0);
        col = palette(p.y * 0.3 + iTime * 0.1 + u_spectralCentroid,
            vec3(0.5), vec3(0.5), vec3(1.0, 0.7, 0.4), vec3(0.0, 0.15, 0.2));
        col *= diff * 0.8 + 0.2;
        col += vec3(0.8) * spec * u_treble;
        col += vec3(0.15) * smoothstep(0.0, 1.0, u_beat);
    }
    col += vec3(0.01) * u_energy;
    col *= 1.0 - 0.4 * length(uv);
    fragColor = vec4(col, 1.0);
}
"""

_FALLBACK_FRACTAL = """\
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
    float angle = iTime * 0.15 + u_mid * 0.5;
    vec3 ro = vec3(2.5 * sin(angle), 1.5 + u_bass * 0.4, 2.5 * cos(angle));
    vec3 ta = vec3(0.0);
    vec3 fwd = normalize(ta - ro);
    vec3 right = normalize(cross(fwd, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(right, fwd);
    vec3 rd = normalize(fwd * 1.8 + right * uv.x + up * uv.y);
    float t = 0.0;
    vec3 col = vec3(0.02, 0.01, 0.04);
    for (int i = 0; i < 100; i++) {
        vec3 p = ro + rd * t;
        float d = mengerScene(p);
        if (d < 0.001) {
            vec3 n = getNormalM(p);
            vec3 light = normalize(vec3(0.8, 1.5, -0.6));
            float diff = max(dot(n, light), 0.0);
            float spec = pow(max(dot(reflect(-light, n), -rd), 0.0), 48.0);
            col = palette(length(p) * 0.2 + iTime * 0.05 + u_spectralCentroid,
                vec3(0.5), vec3(0.5), vec3(0.9, 0.6, 1.0), vec3(0.1, 0.2, 0.3));
            col *= diff * 0.6 + 0.4;
            col += spec * vec3(0.8, 0.7, 1.0) * u_treble;
            break;
        }
        t += d;
        if (t > 25.0) break;
    }
    col += vec3(0.2, 0.1, 0.3) * smoothstep(0.0, 1.0, u_beat) * 0.6;
    col *= 1.0 - 0.3 * length(uv);
    fragColor = vec4(col, 1.0);
}
"""

_FALLBACK_GRID = """\
vec3 palette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return a + b * cos(6.28318 * (c * t + d));
}

float hashFn(float n) {
    return fract(sin(n) * 43758.5453123);
}

float sdSphere(vec3 p, float r) {
    return length(p) - r;
}

float gridScene(vec3 p) {
    vec3 rep = vec3(3.0 + u_lowMid * 0.5);
    vec3 q = mod(p + rep * 0.5, rep) - rep * 0.5;
    float id = hashFn(dot(floor((p + rep * 0.5) / rep), vec3(1.0, 57.0, 113.0)));
    float r = (0.3 + u_bass * 0.2) * (0.5 + 0.5 * id);
    return sdSphere(q, r);
}

vec3 getGridNormal(vec3 p) {
    vec2 e = vec2(0.001, 0.0);
    return normalize(vec3(
        gridScene(p + e.xyy) - gridScene(p - e.xyy),
        gridScene(p + e.yxy) - gridScene(p - e.yxy),
        gridScene(p + e.yyx) - gridScene(p - e.yyx)));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord * 2.0 - iResolution.xy) / min(iResolution.x, iResolution.y);
    float camT = iTime * 0.3;
    vec3 ro = vec3(sin(camT) * 5.0, 2.0, cos(camT) * 5.0);
    vec3 ta = vec3(0.0);
    vec3 fwd = normalize(ta - ro);
    vec3 right = normalize(cross(fwd, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(right, fwd);
    vec3 rd = normalize(fwd * 2.0 + right * uv.x + up * uv.y);
    float t = 0.0;
    vec3 col = vec3(0.01, 0.01, 0.03);
    for (int i = 0; i < 100; i++) {
        vec3 p = ro + rd * t;
        float d = gridScene(p);
        if (d < 0.002) {
            vec3 n = getGridNormal(p);
            vec3 light = normalize(vec3(1.0, 2.0, -0.5));
            float diff = max(dot(n, light), 0.0);
            float spec = pow(max(dot(reflect(-light, n), -rd), 0.0), 64.0);
            float idVal = hashFn(dot(floor((p + 1.5) / 3.0), vec3(1.0, 57.0, 113.0)));
            col = palette(idVal + iTime * 0.1 + u_spectralCentroid,
                vec3(0.5), vec3(0.5), vec3(1.0, 0.8, 0.5), vec3(0.0, 0.1, 0.2));
            col *= diff * 0.7 + 0.3;
            col += spec * u_treble * 1.5;
            break;
        }
        float glow = 0.004 / (abs(d) + 0.05) * u_energy;
        col += vec3(glow * 0.2, glow * 0.05, glow * 0.3) * 0.3;
        t += d;
        if (t > 35.0) break;
    }
    col += vec3(0.25, 0.15, 0.35) * smoothstep(0.0, 1.0, u_beat) * 0.5;
    col *= 1.0 - 0.3 * length(uv);
    fragColor = vec4(col, 1.0);
}
"""

# Ordered list: (keywords, shader_code)
_FALLBACK_LIBRARY: list[tuple[list[str], str]] = [
    (["sphere", "3d", "ray", "orb", "planet", "ball"],
     _FALLBACK_SPHERE),
    (["tunnel", "warp", "speed", "hyper", "vortex", "portal"],
     _FALLBACK_TUNNEL),
    (["kaleidoscope", "geometric", "crystal", "mirror",
      "symmetry", "mandala"],
     _FALLBACK_KALEIDOSCOPE),
    (["fractal", "menger", "sierpinski", "infinite", "recursive",
      "abstract", "mathematical"],
     _FALLBACK_FRACTAL),
    (["grid", "particle", "galaxy", "star", "space", "cosmos",
      "constellation", "nebula", "field"],
     _FALLBACK_GRID),
    (["ocean", "wave", "water", "flow", "fluid", "organic", "nature"],
     _FALLBACK_WAVES),
    ([], _FALLBACK_PLASMA),  # default
]

# Keep a simple default alias for the client-side fallback import
_FALLBACK_SHADER = _FALLBACK_PLASMA


def pick_fallback_shader(description: str = "") -> str:
    """Pick a curated fallback shader based on description keywords."""
    desc_lower = description.lower()
    for keywords, shader in _FALLBACK_LIBRARY:
        if not keywords:
            continue
        if any(kw in desc_lower for kw in keywords):
            return shader
    # Rotate through fallbacks based on hash of description
    # so different descriptions get different visuals
    idx = hash(description) % len(_FALLBACK_LIBRARY)
    return _FALLBACK_LIBRARY[idx][1]


def _interpolate(times: list[float], values: list[float], t: float) -> float:
    """Linear interpolation of a value at time t from arrays of timestamps and values."""
    if not times or not values:
        return 0.0
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]

    # Binary search for the bracket
    lo, hi = 0, len(times) - 1
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if times[mid] <= t:
            lo = mid
        else:
            hi = mid

    span = times[hi] - times[lo]
    if span <= 0:
        return values[lo]
    frac = (t - times[lo]) / span
    return values[lo] + frac * (values[hi] - values[lo])


def _compute_beat_intensity(beat_times: list[float], t: float, decay: float = 0.15) -> float:
    """Compute beat intensity at time t: 1.0 on beat, exponential decay after."""
    if not beat_times:
        return 0.0

    # Find closest beat at or before t
    best_dt = float("inf")
    for bt in beat_times:
        dt = t - bt
        if 0 <= dt < best_dt:
            best_dt = dt

    if best_dt == float("inf"):
        return 0.0

    return math.exp(-best_dt / decay)


class ShaderRenderService:
    """Renders GLSL shader video server-side using ModernGL headless context."""

    def __init__(self) -> None:
        if moderngl is None:
            raise RuntimeError("moderngl is not installed")

    @staticmethod
    def _nvidia_static_check(shader_code: str) -> str | None:
        """Catch GLSL patterns that NVIDIA rejects but Mesa accepts.

        Returns ``None`` if the code looks clean, or an error string
        describing the issue.  This runs *before* the real GL compile
        so we can sanitize proactively on Mesa/EGL servers whose
        compiler is too lenient.
        """
        import re as _re

        lines = shader_code.split("\n")
        in_block_comment = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track block comments
            if "/*" in stripped:
                in_block_comment = True
            if "*/" in stripped:
                in_block_comment = False
                continue
            if in_block_comment:
                continue

            # Skip single-line comments
            if stripped.startswith("//"):
                continue

            # Strip inline comments for analysis
            code_part = stripped.split("//")[0].rstrip()
            if not code_part:
                continue

            # ── void(...) as expression (not a declaration) ──────
            # Valid declaration: `void funcName(...)`
            # Invalid expression: `void(...)` or `void();`
            if _re.search(r"\bvoid\s*\(", code_part):
                if not _re.match(r"^void\s+\w+\s*\(", code_part):
                    return (
                        f"NVIDIA compat: line {i}: "
                        f"void() expression is invalid — {stripped}"
                    )

            # ── return void ─────────────────────────────────────
            if _re.search(r"\breturn\s+void\b", code_part):
                return (
                    f"NVIDIA compat: line {i}: "
                    f"return void is invalid — {stripped}"
                )

            # ── func(void) in a call ────────────────────────────
            # Valid declaration: `float foo(void) {`
            # Invalid call: `x = foo(void);`
            if _re.search(r"\w+\s*\(\s*void\s*\)", code_part):
                # Check if it's a declaration (has a type before the name)
                if not _re.match(
                    r"^(?:void|float|int|vec[234]|mat[234]|bool|"
                    r"ivec[234]|uvec[234]|sampler\w+)\s+\w+\s*\(\s*void\s*\)",
                    code_part,
                ):
                    return (
                        f"NVIDIA compat: line {i}: "
                        f"func(void) call syntax is invalid "
                        f"— {stripped}"
                    )

            # ── Modulo on floats using % instead of mod() ────────
            # NVIDIA rejects `float_expr % float_expr`; must use mod()
            if _re.search(r"[a-zA-Z_]\w*\s*%\s*[a-zA-Z0-9_.]", code_part):
                # Only flag if it looks like float context (not int loop vars)
                if not _re.match(r"^\s*(?:int|ivec|uint|uvec)", code_part):
                    return (
                        f"NVIDIA compat: line {i}: "
                        f"use mod() instead of % for float types — {stripped}"
                    )

            # ── Implicit int-to-float in vec/mat constructors ────
            # NVIDIA rejects vec3(1, 0, 0); must be vec3(1.0, 0.0, 0.0)
            m_vec = _re.finditer(
                r"\b(vec[234]|mat[234])\s*\(([^)]+)\)", code_part,
            )
            for mv in m_vec:
                args = mv.group(2)
                # Check for bare integer literals (not part of a float)
                tokens = [t.strip() for t in args.split(",")]
                for tok in tokens:
                    tok = tok.strip()
                    # Pure integer literal (not 0.0, not a variable)
                    if _re.match(r"^-?\d+$", tok) and tok not in ("0", "1"):
                        return (
                            f"NVIDIA compat: line {i}: "
                            f"use float literals (e.g. {tok}.0) in "
                            f"{mv.group(1)} constructor — {stripped}"
                        )

        # ── Reserved function names on NVIDIA ────────────────
        if _re.search(
            r"\b(?:float|vec[234]|int)\s+hash\s*\(", shader_code,
        ):
            return (
                "NVIDIA compat: function 'hash' collides with "
                "NVIDIA built-in — rename to 'hashFn'"
            )

        # ── Other NVIDIA reserved names ──────────────────────
        nvidia_reserved = ["noise", "input", "output"]
        for name in nvidia_reserved:
            if _re.search(
                rf"\b(?:float|vec[234]|int|void)\s+{name}\s*\(",
                shader_code,
            ):
                return (
                    f"NVIDIA compat: function '{name}' collides with "
                    f"NVIDIA built-in/keyword — rename to '{name}Fn'"
                )

        return None

    @staticmethod
    def _try_compile(shader_code: str) -> str | None:
        """Try compiling shader_code in a temporary GL context.

        Runs NVIDIA static analysis first (catches patterns Mesa
        accepts but NVIDIA rejects), then compiles with ModernGL.
        Returns None on success, or the error message string on
        failure.
        """
        # Run the sanitizer one more time as a safety net — the LLM
        # service sanitizes output, but fix_shader and retry paths
        # may introduce new patterns.
        from app.services.llm_service import sanitize_shader_code

        shader_code = sanitize_shader_code(shader_code)

        # Static check for NVIDIA-incompatible patterns
        nvidia_err = ShaderRenderService._nvidia_static_check(
            shader_code,
        )
        if nvidia_err:
            return nvidia_err

        import sys
        _kw: dict = {}
        if sys.platform.startswith("linux"):
            _kw["backend"] = "egl"
        ctx = moderngl.create_standalone_context(**_kw)
        try:
            frag_src = _FRAGMENT_WRAPPER.format(
                user_code=shader_code,
            )
            ctx.program(
                vertex_shader=_VERTEX_SHADER,
                fragment_shader=frag_src,
            )
            return None
        except Exception as e:
            return str(e)
        finally:
            ctx.release()

    async def render_shader_video(
        self,
        render_id: str,
        audio_path: str,
        analysis: dict,
        render_spec: RenderSpec,
        shader_code: str,
    ) -> dict:
        """Render a complete video from a GLSL shader + audio analysis.

        Validates the shader first.  If compilation fails, asks the LLM
        to fix it (up to 3 retries).  Falls back to a curated shader on
        total failure.  The heavy GL + FFmpeg work runs in a thread.
        """
        compile_err = await asyncio.to_thread(
            self._try_compile, shader_code,
        )
        if compile_err:
            logger.warning(
                "Shader failed to compile, requesting LLM fix: %s",
                compile_err,
            )
            from app.services.llm_service import LLMService

            llm = LLMService()
            desc = (
                render_spec.global_style.shader_description
                or "audio-reactive visualization"
            )
            broken_code = shader_code
            for retry in range(3):
                fixed = await llm.fix_shader(
                    previous_code=broken_code,
                    compile_error=compile_err,
                    description=desc,
                )
                if not fixed:
                    break
                retry_err = await asyncio.to_thread(
                    self._try_compile, fixed,
                )
                if retry_err is None:
                    logger.info(
                        "LLM-fixed shader compiled on retry %d",
                        retry + 1,
                    )
                    shader_code = fixed
                    compile_err = None
                    break
                logger.warning(
                    "LLM retry %d still fails: %s",
                    retry + 1, retry_err,
                )
                broken_code = fixed
                compile_err = retry_err

            if compile_err:
                logger.warning(
                    "All retries failed, using fallback shader",
                )
                shader_code = pick_fallback_shader(desc)

        return await asyncio.to_thread(
            self._render_blocking,
            render_id, audio_path, analysis, render_spec, shader_code,
        )

    def _render_blocking(
        self,
        render_id: str,
        audio_path: str,
        analysis: dict,
        render_spec: RenderSpec,
        shader_code: str,
    ) -> dict:
        """Synchronous render implementation (called from a thread)."""
        width, height = render_spec.export_settings.resolution
        fps = render_spec.export_settings.fps
        duration = analysis.get("metadata", {}).get("duration", 60.0)

        output_dir = Path(settings.storage_path) / "renders"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{render_id}.mp4"

        logger.info(
            "Starting shader render: %s (%dx%d @ %dfps, %.1fs)",
            render_id, width, height, fps, duration,
        )

        # Extract audio feature timeseries from analysis
        beat_times = analysis.get("rhythm", {}).get("beats", [])
        spectral = analysis.get("spectral", {})
        spec_times = spectral.get("times", [])
        rms_values = spectral.get("rms", [])
        centroid_values = spectral.get("spectral_centroid", [])

        # Energy bands (if available from analysis, otherwise derive from RMS)
        band_data = spectral.get("energy_bands", {})
        bass_values = band_data.get("bass", [])
        low_mid_values = band_data.get("low_mid", [])
        mid_values = band_data.get("mid", [])
        high_mid_values = band_data.get("high_mid", [])
        treble_values = band_data.get("treble", [])

        # Create OpenGL context and compile shader.
        # EGL is Linux-only; on Windows WGL is used automatically; on macOS CGL.
        import sys
        _backend_kwargs: dict = {}
        if sys.platform.startswith("linux"):
            _backend_kwargs["backend"] = "egl"
        ctx = moderngl.create_standalone_context(**_backend_kwargs)
        fbo = ctx.framebuffer(
            color_attachments=[ctx.texture((width, height), 4)],
        )

        # Compile shader (already validated+retried in render_shader_video,
        # but keep fallback as a safety net for context-specific failures)
        frag_src = _FRAGMENT_WRAPPER.format(user_code=shader_code)
        try:
            prog = ctx.program(
                vertex_shader=_VERTEX_SHADER,
                fragment_shader=frag_src,
            )
        except Exception as e:
            logger.warning("Shader failed in render context, using fallback: %s", e)
            frag_src = _FRAGMENT_WRAPPER.format(user_code=_FALLBACK_SHADER)
            prog = ctx.program(
                vertex_shader=_VERTEX_SHADER,
                fragment_shader=frag_src,
            )

        # Fullscreen quad (two triangles)
        vertices = np.array([
            -1.0, -1.0,
             1.0, -1.0,
            -1.0,  1.0,
             1.0,  1.0,
        ], dtype="f4")
        vbo = ctx.buffer(vertices)
        vao = ctx.vertex_array(prog, [(vbo, "2f", "in_position")])

        # Set up FFmpeg to receive raw RGBA frames
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgba",
            "-r", str(fps),
            "-i", "pipe:0",
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "21",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            str(output_path),
        ]

        # Write FFmpeg stderr to a temp file instead of a pipe to avoid the
        # classic subprocess deadlock: if the 64KB pipe buffer fills (FFmpeg
        # writes lots of progress/stats), FFmpeg blocks on stderr writes and
        # can never finish reading stdin → everything hangs.
        stderr_file = tempfile.NamedTemporaryFile(
            mode="w+b", suffix=".log", delete=False,
        )
        stderr_path = Path(stderr_file.name)

        proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
        )

        total_frames = int(duration * fps)

        # Scale FFmpeg finalization timeout: encoding overhead after all frames
        # are piped depends on duration, resolution, and the faststart muxer pass.
        ffmpeg_timeout = max(180, int(duration * 3) + 60)

        try:
            fbo.use()
            ctx.viewport = (0, 0, width, height)

            for frame_idx in range(total_frames):
                t = frame_idx / fps

                # Compute audio features at this time
                rms = _interpolate(spec_times, rms_values, t) if rms_values else 0.3
                centroid = _interpolate(spec_times, centroid_values, t) if centroid_values else 0.5
                beat = _compute_beat_intensity(beat_times, t)

                # Energy bands
                bass = _interpolate(spec_times, bass_values, t) if bass_values else rms * 0.8
                low_mid = _interpolate(spec_times, low_mid_values, t) if low_mid_values else rms * 0.6
                mid = _interpolate(spec_times, mid_values, t) if mid_values else rms * 0.5
                high_mid = _interpolate(spec_times, high_mid_values, t) if high_mid_values else rms * 0.4
                treble = _interpolate(spec_times, treble_values, t) if treble_values else rms * 0.3

                # Set uniforms (only set if they exist in the shader)
                for name, value in [
                    ("iTime", t),
                    ("iResolution", (float(width), float(height))),
                    ("u_bass", bass),
                    ("u_lowMid", low_mid),
                    ("u_mid", mid),
                    ("u_highMid", high_mid),
                    ("u_treble", treble),
                    ("u_energy", rms),
                    ("u_beat", beat),
                    ("u_spectralCentroid", centroid),
                ]:
                    if name in prog:
                        if isinstance(value, tuple):
                            prog[name].value = value
                        else:
                            prog[name].value = value

                # Render
                ctx.clear(0.0, 0.0, 0.0, 1.0)
                vao.render(moderngl.TRIANGLE_STRIP)

                # Read pixels (bottom-to-top in OpenGL, need to flip)
                raw = fbo.color_attachments[0].read()
                # Flip vertically: OpenGL has origin at bottom-left
                frame = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 4)
                frame = np.flipud(frame)
                proc.stdin.write(frame.tobytes())

                # Log progress periodically
                if frame_idx % (fps * 10) == 0 and frame_idx > 0:
                    pct = int(frame_idx / total_frames * 100)
                    logger.info("Shader render %s: %d%% (%d/%d frames)", render_id, pct, frame_idx, total_frames)

        finally:
            # Always release GL resources first (independent of FFmpeg)
            vao.release()
            vbo.release()
            prog.release()
            fbo.release()
            ctx.release()

            # Close FFmpeg stdin to signal end-of-stream, then wait
            proc.stdin.close()
            try:
                proc.wait(timeout=ffmpeg_timeout)
            except subprocess.TimeoutExpired:
                logger.error(
                    "FFmpeg timed out after %ds for render %s, killing",
                    ffmpeg_timeout, render_id,
                )
                proc.kill()
                proc.wait(timeout=10)
                raise RuntimeError(
                    f"FFmpeg encoding timed out after {ffmpeg_timeout}s"
                )
            finally:
                stderr_file.close()

            if proc.returncode != 0:
                stderr_tail = stderr_path.read_text(errors="replace")[-500:]
                logger.error("FFmpeg failed: %s", stderr_tail)
                stderr_path.unlink(missing_ok=True)
                raise RuntimeError(f"FFmpeg encoding failed (rc={proc.returncode})")

            stderr_path.unlink(missing_ok=True)

        download_url = f"/storage/renders/{render_id}.mp4"
        logger.info("Shader render complete: %s → %s", render_id, download_url)

        return {"download_url": download_url, "output_path": str(output_path)}
