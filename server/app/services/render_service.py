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


_TRANS_DUR = 0.5  # Default crossfade transition duration (seconds)

# Map render spec transition types to FFmpeg xfade transition names
_XFADE_MAP: dict[str, str] = {
    "fade-from-black": "fadeblack",
    "fade-to-black": "fadeblack",
    "cross-dissolve": "dissolve",
    "hard-cut": "fade",
    "morph": "smoothleft",
    "flash-white": "fadewhite",
    "wipe": "wiperight",
    "zoom-in": "zoomin",
    "zoom-out": "circleclose",
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

        # Count additional inputs (AI keyframe images) and map section → input index
        extra_inputs: list[str] = []
        num_keyframe_inputs = 0
        keyframe_input_map: dict[str, int] = {}  # section_label → FFmpeg input index
        if keyframe_paths:
            for section in render_spec.sections:
                kf = keyframe_paths.get(section.label, "")
                if kf and Path(kf).exists():
                    input_idx = 1 + num_keyframe_inputs  # [0] is color source
                    keyframe_input_map[section.label] = input_idx
                    extra_inputs.extend(["-loop", "1", "-t", str(duration), "-i", kf])
                    num_keyframe_inputs += 1

        # Input layout: [0]=color source, [1..N]=keyframes, [N+1]=audio
        audio_input_index = 1 + num_keyframe_inputs

        logger.info(
            "Starting FFmpeg render: %s (template=%s, sections=%d)",
            render_id, template, len(render_spec.sections),
        )

        # Graceful degradation: full → no-beats → no-transitions → simple → minimal
        for attempt_label, use_beats, use_xfade in [
            ("full", True, True),
            ("full-no-beats", False, True),
            ("full-no-transitions", False, False),
        ]:
            filter_complex = self._build_full_filter_graph(
                render_spec, template, duration, width, height, fps,
                beats if use_beats else [],
                keyframe_input_map,
                use_xfade=use_xfade,
            )

            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=black:s={width}x{height}:d={duration}:r={fps}",
                *extra_inputs,
                "-i", audio_path,
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-map", f"{audio_input_index}:a",
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

            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=600, check=False,
                )
                if result.returncode == 0:
                    if attempt_label != "full":
                        logger.info("Render succeeded with %s strategy", attempt_label)
                    download_url = f"/storage/renders/{render_id}.mp4"
                    logger.info("Render complete: %s -> %s", render_id, download_url)
                    return {"download_url": download_url}

                logger.warning(
                    "Render attempt '%s' failed:\n%s",
                    attempt_label,
                    result.stderr[-2000:] if result.stderr else "unknown",
                )
            except subprocess.TimeoutExpired as e:
                raise RuntimeError("Render timed out after 10 minutes") from e

        # Both full attempts failed — use simple section-color fallback
        logger.warning("Full render strategies exhausted, using simple fallback")
        return await self._fallback_render(
            render_id, audio_path, analysis, render_spec, output_path,
        )

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
        keyframe_input_map: dict[str, int],
        use_xfade: bool = True,
    ) -> str:
        """Build a comprehensive FFmpeg filter_complex.

        Per-section pipeline:
        1. Gradient background
        2. AI keyframe overlay (if available) OR procedural effect blend
        3. Dynamic color effects (hue cycling, vignette) for keyframe sections
        4. Zoompan motion with per-section variation
        5. Smooth xfade transitions between sections (or concat fallback)
        6. Beat-synced flash overlay
        """
        filters: list[str] = []
        section_out_labels: list[str] = []
        section_durations: list[float] = []

        if not render_spec.sections:
            color = self._template_base_color(template)
            return (
                f"[0:v]drawbox=x=0:y=0:w={width}:h={height}:color={color}@0.8"
                f":t=fill[vout]"
            )

        n_sections = len(render_spec.sections)
        trans_dur = _TRANS_DUR if use_xfade and n_sections > 1 else 0

        for i, section in enumerate(render_spec.sections):
            s = f"s{i}"
            colors = section.color_palette or ["#7C5CFC", "#1A1A28"]
            c0 = colors[0].lstrip("#")
            c1 = (colors[1] if len(colors) > 1 else colors[0]).lstrip("#")
            c2 = (colors[2] if len(colors) > 2 else colors[0]).lstrip("#")
            sec_dur = max(section.end_time - section.start_time, 0.1)
            intensity = section.intensity
            kf_idx = keyframe_input_map.get(section.label)

            # Extend section duration for transition overlap
            actual_dur = sec_dur
            if trans_dur > 0:
                if i > 0:
                    actual_dur += trans_dur / 2
                if i < n_sections - 1:
                    actual_dur += trans_dur / 2

            # ── Layer 1: section-unique gradient background ──
            top_h = height // 2 + int(height * 0.1 * math.sin(i * 1.7))
            bot_h = height - top_h
            filters.append(
                f"color=c=#{c0}:s={width}x{height}:d={actual_dur}:r={fps},"
                f"drawbox=x=0:y=0:w={width}:h={top_h}:color=0x{c1}@0.45:t=fill,"
                f"drawbox=x=0:y={top_h}:w={width}:h={bot_h}:color=0x{c2}@0.35:t=fill"
                f"[{s}_bg]"
            )

            if kf_idx is not None:
                # ── AI keyframe: scale to fit, overlay on gradient ──
                filters.append(
                    f"[{kf_idx}:v]scale={width}:{height}"
                    f":force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
                    f"setsar=1,trim=duration={actual_dur},setpts=PTS-STARTPTS,"
                    f"format=yuva420p[{s}_kf]"
                )
                filters.append(
                    f"[{s}_bg]format=yuva420p[{s}_bgf];"
                    f"[{s}_bgf][{s}_kf]overlay=0:0:format=auto[{s}_comp]"
                )

                # ── Dynamic color effects for keyframe sections ──
                hue_period = max(actual_dur, 2.0)
                hue_amp = 5 + intensity * 20
                sat = 1 + intensity * 0.15
                filters.append(
                    f"[{s}_comp]"
                    f"hue=H=sin(2*PI*t/{hue_period:.2f})*{hue_amp:.1f}"
                    f":s={sat:.2f}+0.1*sin(2*PI*t/{hue_period:.2f}+1.5),"
                    f"vignette=angle=PI/4"
                    f"[{s}_fx]"
                )
                motion_in = f"{s}_fx"
            else:
                # ── No keyframe: procedural effect layer ──
                proc = self._procedural_effect(
                    template, s, width, height, actual_dur, fps, intensity,
                )
                if proc:
                    filters.append(proc)
                    blend_strength = 0.25 + intensity * 0.35
                    filters.append(
                        f"[{s}_bg][{s}_fx]blend=all_mode=screen"
                        f":all_opacity={blend_strength:.2f}[{s}_comp]"
                    )
                else:
                    filters.append(f"[{s}_bg]null[{s}_comp]")
                motion_in = f"{s}_comp"

            # ── Motion (zoompan) with per-section phase variation ──
            motion = _MOTION_PARAMS.get(
                section.motion_style, _MOTION_PARAMS["slow-drift"]
            )
            phase = i * 37 % 100
            x_expr = motion["x"].replace("on/", f"(on+{phase})/")
            y_expr = motion["y"].replace("on/", f"(on+{phase})/")

            pad_w, pad_h = int(width * 1.25), int(height * 1.25)
            total_frames = max(int(actual_dur * fps), 1)
            filters.append(
                f"[{motion_in}]scale={pad_w}:{pad_h},"
                f"zoompan=z='{motion['z']}':"
                f"x='{x_expr}':y='{y_expr}':"
                f"d={total_frames}:s={width}x{height}:fps={fps},"
                f"format=yuv420p"
                f"[{s}_out]"
            )

            section_out_labels.append(f"{s}_out")
            section_durations.append(actual_dur)

        # ── Join sections: xfade transitions or concat ──
        if n_sections == 1:
            filters.append(f"[{section_out_labels[0]}]null[vmain]")
        elif use_xfade:
            current = section_out_labels[0]
            running_dur = section_durations[0]
            for i in range(1, n_sections):
                next_lbl = section_out_labels[i]
                t = min(
                    trans_dur,
                    section_durations[i - 1] / 3,
                    section_durations[i] / 3,
                )
                offset = max(running_dur - t, 0)
                trans_name = _XFADE_MAP.get(
                    render_spec.sections[i].transition_in, "dissolve"
                )
                out_lbl = "vmain" if i == n_sections - 1 else f"x{i}"
                filters.append(
                    f"[{current}][{next_lbl}]xfade=transition={trans_name}"
                    f":duration={t:.3f}:offset={offset:.3f}[{out_lbl}]"
                )
                current = out_lbl
                running_dur += section_durations[i] - t
        else:
            concat_in = "".join(f"[{lbl}]" for lbl in section_out_labels)
            filters.append(
                f"{concat_in}concat=n={n_sections}:v=1:a=0[vmain]"
            )

        # ── Beat-synced flash overlay ──
        beat_flash = self._beat_flash_filter(beats, width, height, fps)
        if beat_flash:
            filters.append(f"[vmain]{beat_flash}[vout]")
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

    @staticmethod
    def _beat_flash_filter(
        beats: list[float],
        width: int,
        height: int,
        fps: int,
    ) -> str | None:
        """Return a drawbox filter that flashes white on beat hits.

        Uses enable='between(t,a,b)+...' which is the same proven
        approach as _simple_section_filters.  Applies directly to the
        main video stream — no separate source, no blend, no format
        mismatch risk.
        """
        if not beats:
            return None

        flash_dur = 2.0 / fps
        # Limit beats to keep the enable expression within FFmpeg limits.
        parts = [
            f"between(t,{b:.3f},{b + flash_dur:.3f})"
            for b in beats[:50]
        ]
        if not parts:
            return None

        expr = "+".join(parts)
        return (
            f"drawbox=x=0:y=0:w={width}:h={height}"
            f":color=white@0.12:t=fill:enable='{expr}'"
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
