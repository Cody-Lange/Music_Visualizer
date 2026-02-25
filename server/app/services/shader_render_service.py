"""Headless GLSL shader video renderer using ModernGL + Mesa.

Renders the same Shadertoy-compatible shaders used in the browser preview,
driving them with per-frame audio features extracted from the analysis data.
Output is piped as raw RGBA frames into FFmpeg for encoding.
"""

import logging
import math
import struct
import subprocess
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

# Fallback shader if the user's shader fails to compile
_FALLBACK_SHADER = """\
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
    vec3 col = palette(
        d + t * 0.2 + u_spectralCentroid,
        vec3(0.5), vec3(0.5), vec3(1.0, 0.7, 0.4), vec3(0.0, 0.15, 0.2)
    );
    col *= rings;
    col += vec3(0.1, 0.05, 0.15) * u_treble * 3.0;
    col += vec3(0.3) * u_beat;
    float vig = 1.0 - smoothstep(0.4, 1.4, length((fragCoord / iResolution.xy - 0.5) * 2.0));
    col *= vig;
    fragColor = vec4(col, 1.0);
}
"""


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

    async def render_shader_video(
        self,
        render_id: str,
        audio_path: str,
        analysis: dict,
        render_spec: RenderSpec,
        shader_code: str,
    ) -> dict:
        """Render a complete video from a GLSL shader + audio analysis.

        Produces an MP4 with the shader visuals driven by per-frame audio features.
        """
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

        # Try to compile user's shader, fall back if it fails
        frag_src = _FRAGMENT_WRAPPER.format(user_code=shader_code)
        try:
            prog = ctx.program(
                vertex_shader=_VERTEX_SHADER,
                fragment_shader=frag_src,
            )
        except Exception as e:
            logger.warning("User shader failed to compile, using fallback: %s", e)
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

        proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        total_frames = int(duration * fps)

        try:
            fbo.use()

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
            proc.stdin.close()
            proc.wait(timeout=60)

            if proc.returncode != 0:
                stderr = proc.stderr.read().decode(errors="replace")
                logger.error("FFmpeg failed: %s", stderr[-500:])
                raise RuntimeError(f"FFmpeg encoding failed (rc={proc.returncode})")

            # Cleanup GL resources
            vao.release()
            vbo.release()
            prog.release()
            fbo.release()
            ctx.release()

        download_url = f"/storage/renders/{render_id}.mp4"
        logger.info("Shader render complete: %s → %s", render_id, download_url)

        return {"download_url": download_url, "output_path": str(output_path)}
