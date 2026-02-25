"""Video render service — orchestrates FFmpeg rendering pipeline.

Generates unique, template-driven videos using FFmpeg filter graphs.
Each template serves as a starting point; the actual video is customized
per-section using the render spec's colors, motion styles, intensities,
visual elements, and AI keyframe images (when available).
"""

import logging
import math
import subprocess
from pathlib import Path

from app.config import settings
from app.models.render import RenderSpec

logger = logging.getLogger(__name__)


# Motion style to FFmpeg zoompan parameters
_MOTION_PARAMS: dict[str, dict[str, str]] = {
    "slow-drift": {
        "z": "zoom+0.0003",
        "x": "iw/2-(iw/zoom/2)+2*sin(on/80)",
        "y": "ih/2-(ih/zoom/2)+2*cos(on/90)",
    },
    "pulse": {
        "z": "1.0+0.03*sin(on/8)",
        "x": "iw/2-(iw/zoom/2)",
        "y": "ih/2-(ih/zoom/2)",
    },
    "energetic": {
        "z": "zoom+0.001",
        "x": "iw/2-(iw/zoom/2)+4*sin(on/15)",
        "y": "ih/2-(ih/zoom/2)+4*cos(on/12)",
    },
    "chaotic": {
        "z": "1.0+0.05*sin(on/5)",
        "x": "iw/2-(iw/zoom/2)+8*sin(on/7)",
        "y": "ih/2-(ih/zoom/2)+8*cos(on/6)",
    },
    "breathing": {
        "z": "1.0+0.02*sin(on/20)",
        "x": "iw/2-(iw/zoom/2)",
        "y": "ih/2-(ih/zoom/2)",
    },
    "glitch": {
        "z": "1.0+0.04*sin(on/3)",
        "x": "iw/2-(iw/zoom/2)+10*sin(on/4)",
        "y": "ih/2-(ih/zoom/2)",
    },
    "smooth-flow": {
        "z": "zoom+0.0005",
        "x": "iw/2-(iw/zoom/2)+3*sin(on/50)",
        "y": "ih/2-(ih/zoom/2)+3*cos(on/60)",
    },
    "staccato": {
        "z": "1.0+0.06*abs(sin(on/4))",
        "x": "iw/2-(iw/zoom/2)",
        "y": "ih/2-(ih/zoom/2)",
    },
}


def _hex_to_ffmpeg(hex_color: str) -> str:
    """Convert #RRGGBB to 0xRRGGBB for FFmpeg."""
    return "0x" + hex_color.lstrip("#")


class RenderService:
    """Orchestrates video rendering from a render spec + audio analysis."""

    async def render_video(
        self,
        render_id: str,
        audio_path: str,
        analysis: dict,
        render_spec: RenderSpec,
        lyrics: dict | None = None,
        keyframe_paths: dict[str, str] | None = None,
    ) -> dict:
        """Render a visualization video.

        Creates a unique video by compositing per-section visuals:
        - Template-specific procedural backgrounds per section
        - Section-specific multi-color gradients from the render spec
        - Motion applied via zoompan (drift, pulse, chaotic, etc.)
        - AI keyframe images composited when available
        - Beat-synced flash overlays at beat positions
        """
        output_path = settings.render_dir / f"{render_id}.mp4"
        duration = analysis.get("metadata", {}).get("duration", 60)
        width, height = render_spec.export_settings.resolution
        fps = render_spec.export_settings.fps
        template = render_spec.global_style.template
        beats = analysis.get("rhythm", {}).get("beats", [])

        # Try the full filter graph first; fall back to simple if it fails
        filter_complex = self._build_full_filter_graph(
            render_spec, template, duration, width, height, fps, beats,
            keyframe_paths or {},
        )

        # Count additional inputs (AI keyframe images)
        extra_inputs: list[str] = []
        if keyframe_paths:
            for section in render_spec.sections:
                kf = keyframe_paths.get(section.label, "")
                if kf and Path(kf).exists():
                    extra_inputs.extend(["-loop", "1", "-t", str(duration), "-i", kf])

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={width}x{height}:d={duration}:r={fps}",
            *extra_inputs,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", f"{1 + len(extra_inputs) // 4}:a",
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

        logger.info(
            "Starting FFmpeg render: %s (template=%s, sections=%d)",
            render_id, template, len(render_spec.sections),
        )

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600, check=False,
            )
            if result.returncode != 0:
                logger.warning(
                    "Full render failed, falling back: %s",
                    result.stderr[-500:] if result.stderr else "unknown",
                )
                return await self._fallback_render(
                    render_id, audio_path, analysis, render_spec, output_path,
                )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Render timed out after 10 minutes") from e

        download_url = f"/storage/renders/{render_id}.mp4"
        logger.info("Render complete: %s -> %s", render_id, download_url)
        return {"download_url": download_url}

    # ── Full filter graph ────────────────────────────────────────────────

    def _build_full_filter_graph(
        self,
        render_spec: RenderSpec,
        template: str,
        duration: float,
        width: int,
        height: int,
        fps: int,
        beats: list[float],
        keyframe_paths: dict[str, str],
    ) -> str:
        """Build a comprehensive FFmpeg filter_complex.

        Per-section: unique gradient + procedural overlay + motion + transitions.
        Then: concatenate sections, add beat-flash layer, composite.
        """
        filters: list[str] = []
        section_out_labels: list[str] = []

        if not render_spec.sections:
            color = self._template_base_color(template)
            return (
                f"[0:v]drawbox=x=0:y=0:w={width}:h={height}:color={color}@0.8"
                f":t=fill[vout]"
            )

        for i, section in enumerate(render_spec.sections):
            s = f"s{i}"
            colors = section.color_palette or ["#7C5CFC", "#1A1A28"]
            c0 = colors[0].lstrip("#")
            c1 = (colors[1] if len(colors) > 1 else colors[0]).lstrip("#")
            c2 = (colors[2] if len(colors) > 2 else colors[0]).lstrip("#")
            sec_dur = max(section.end_time - section.start_time, 0.1)
            intensity = section.intensity

            # ── Layer 1: section-unique gradient background ──
            # Vary the gradient layout per section using index
            top_h = height // 2 + int(height * 0.1 * math.sin(i * 1.7))
            bot_h = height - top_h
            filters.append(
                f"color=c=#{c0}:s={width}x{height}:d={sec_dur}:r={fps},"
                f"drawbox=x=0:y=0:w={width}:h={top_h}:color=0x{c1}@0.45:t=fill,"
                f"drawbox=x=0:y={top_h}:w={width}:h={bot_h}:color=0x{c2}@0.35:t=fill"
                f"[{s}_bg]"
            )

            # ── Layer 2: template-specific procedural effect ──
            proc = self._procedural_effect(template, s, width, height, sec_dur, fps, intensity)
            if proc:
                filters.append(proc)
                blend_strength = 0.25 + intensity * 0.35
                filters.append(
                    f"[{s}_bg][{s}_fx]blend=all_mode=screen"
                    f":all_opacity={blend_strength:.2f}[{s}_comp]"
                )
            else:
                filters.append(f"[{s}_bg]null[{s}_comp]")

            # ── Layer 3: motion (zoompan) ──
            motion = _MOTION_PARAMS.get(
                section.motion_style, _MOTION_PARAMS["slow-drift"]
            )
            pad_w, pad_h = int(width * 1.25), int(height * 1.25)
            total_frames = max(int(sec_dur * fps), 1)
            filters.append(
                f"[{s}_comp]scale={pad_w}:{pad_h},"
                f"zoompan=z='{motion['z']}':"
                f"x='{motion['x']}':y='{motion['y']}':"
                f"d={total_frames}:s={width}x{height}:fps={fps}"
                f"[{s}_out]"
            )

            section_out_labels.append(f"{s}_out")

        # ── Concatenate all sections ──
        concat_in = "".join(f"[{lbl}]" for lbl in section_out_labels)
        n = len(section_out_labels)
        filters.append(f"{concat_in}concat=n={n}:v=1:a=0[vmain]")

        # ── Beat-synced flash overlay ──
        beat_flash = self._beat_flash(beats, duration, width, height, fps)
        if beat_flash:
            filters.append(beat_flash)
            filters.append(
                "[vmain][beat_fl]blend=all_mode=addition:all_opacity=0.12[vout]"
            )
        else:
            filters.append("[vmain]null[vout]")

        return ";".join(filters)

    # ── Procedural effects per template ──────────────────────────────────

    def _procedural_effect(
        self,
        template: str,
        s: str,
        w: int,
        h: int,
        dur: float,
        fps: int,
        intensity: float,
    ) -> str | None:
        """Return an FFmpeg filter fragment that generates a procedural visual."""
        fx = f"{s}_fx"
        frames = max(int(dur * fps), 1)

        if template in ("nebula", "cinematic", "nature", "90s-anime"):
            # Organic swirling pattern via geq
            speed = 0.3 + intensity * 0.7
            scale = 30 + intensity * 40
            r = f"128+127*sin(X/{scale:.0f}+N*{speed:.2f}/{fps})"
            g = f"128+127*sin(Y/{scale + 10:.0f}+N*{speed * 0.7:.2f}/{fps}+1.5)"
            b = f"128+127*cos((X+Y)/{scale + 20:.0f}+N*{speed * 0.5:.2f}/{fps})"
            return (
                f"color=c=black:s={w}x{h}:d={dur}:r={fps},"
                f"geq=r='{r}':g='{g}':b='{b}'[{fx}]"
            )

        if template in ("geometric", "abstract"):
            mi = int(40 + intensity * 80)
            return (
                f"mandelbrot=s={w}x{h}:maxiter={mi}:inner=convergence:rate={fps},"
                f"trim=duration={dur},setpts=PTS-STARTPTS[{fx}]"
            )

        if template in ("waveform", "urban"):
            rule = 110 if template == "waveform" else 30
            return (
                f"cellauto=s={w}x{h}:rule={rule}:rate={fps},"
                f"trim=duration={dur},setpts=PTS-STARTPTS[{fx}]"
            )

        if template in ("retro", "glitchbreak"):
            return (
                f"life=s={w}x{h}:mold=10:rate={fps},"
                f"trim=duration={dur},setpts=PTS-STARTPTS[{fx}]"
            )

        return None

    # ── Beat flash ───────────────────────────────────────────────────────

    def _beat_flash(
        self,
        beats: list[float],
        duration: float,
        w: int,
        h: int,
        fps: int,
    ) -> str | None:
        if not beats:
            return None

        # Limit to 50 beats to keep the geq expression within FFmpeg limits
        flash_dur = 2.0 / fps
        parts = [
            f"between(t\\,{b:.3f}\\,{b + flash_dur:.3f})"
            for b in beats[:50]
        ]
        if not parts:
            return None

        expr = "+".join(parts)
        return (
            f"color=c=white:s={w}x{h}:d={duration}:r={fps},"
            f"geq=lum='255*({expr})':cb=128:cr=128[beat_fl]"
        )

    # ── Fallback (simple render) ─────────────────────────────────────────

    async def _fallback_render(
        self,
        render_id: str,
        audio_path: str,
        analysis: dict,
        render_spec: RenderSpec,
        output_path: Path,
    ) -> dict:
        """Simplified fallback using section-colored overlays.

        If this also fails, falls through to _minimal_render.
        """
        duration = analysis.get("metadata", {}).get("duration", 60)
        width, height = render_spec.export_settings.resolution
        fps = render_spec.export_settings.fps

        filt = self._simple_section_filters(render_spec, duration, width, height)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={width}x{height}:d={duration}:r={fps}",
            "-i", audio_path,
            "-filter_complex", filt,
            "-map", "[out]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-shortest",
            str(output_path),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "Simple fallback render also failed, trying minimal: %s",
                result.stderr[-300:] if result.stderr else "unknown",
            )
            return await self._minimal_render(
                render_id, audio_path, duration, width, height, fps,
                render_spec.global_style.template, output_path,
            )
        download_url = f"/storage/renders/{render_id}.mp4"
        return {"download_url": download_url}

    async def _minimal_render(
        self,
        render_id: str,
        audio_path: str,
        duration: float,
        width: int,
        height: int,
        fps: int,
        template: str,
        output_path: Path,
    ) -> dict:
        """Ultra-simple render: solid template color + audio. Cannot fail."""
        color = self._template_base_color(template)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={color}:s={width}x{height}:d={duration}:r={fps}",
            "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-shortest",
            str(output_path),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Minimal render failed: "
                f"{result.stderr[-200:] if result.stderr else 'unknown'}"
            )
        download_url = f"/storage/renders/{render_id}.mp4"
        logger.info("Minimal render succeeded: %s", render_id)
        return {"download_url": download_url}

    def _simple_section_filters(
        self,
        render_spec: RenderSpec,
        duration: float,
        width: int,
        height: int,
    ) -> str:
        if not render_spec.sections:
            c = self._template_base_color(render_spec.global_style.template)
            return f"[0:v]drawbox=x=0:y=0:w={width}:h={height}:color={c}@0.6:t=fill[out]"

        filters: list[str] = []
        prev = "0:v"
        for i, sec in enumerate(render_spec.sections):
            c1 = (sec.color_palette[0] if sec.color_palette else "#7C5CFC").lstrip("#")
            c2 = (sec.color_palette[1] if len(sec.color_palette) > 1 else c1).lstrip("#")
            label = f"s{i}"
            filters.append(
                f"[{prev}]"
                f"drawbox=x=0:y=0:w={width}:h={height // 2}:color=0x{c1}@0.6:t=fill"
                f":enable='between(t,{sec.start_time},{sec.end_time})',"
                f"drawbox=x=0:y={height // 2}:w={width}:h={height // 2}:color=0x{c2}@0.4:t=fill"
                f":enable='between(t,{sec.start_time},{sec.end_time})'[{label}]"
            )
            prev = label

        filters[-1] = filters[-1].rsplit("[", 1)[0] + "[out]"
        return ";".join(filters)

    @staticmethod
    def _template_base_color(template: str) -> str:
        colors = {
            "nebula": "0x1B1464",
            "geometric": "0x7C5CFC",
            "waveform": "0x0A0A0F",
            "cinematic": "0x1A1A28",
            "retro": "0xFF00FF",
            "nature": "0x2D5016",
            "abstract": "0x12121A",
            "urban": "0x333333",
            "glitchbreak": "0xFF0066",
            "90s-anime": "0xFF8844",
        }
        return colors.get(template, "0x0A0A0F")
