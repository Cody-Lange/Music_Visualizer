"""Video render service — orchestrates Remotion rendering pipeline.

For the MVP, this generates a placeholder video using FFmpeg directly.
The full Remotion integration is in Phase 9.
"""

import logging
import subprocess
from pathlib import Path

from app.config import settings
from app.models.render import RenderSpec

logger = logging.getLogger(__name__)


class RenderService:
    """Orchestrates video rendering from a render spec + audio analysis."""

    async def render_video(
        self,
        render_id: str,
        audio_path: str,
        analysis: dict,
        render_spec: RenderSpec,
        lyrics: dict | None = None,
    ) -> dict:
        """Render a visualization video.

        Current implementation: generates a video with audio using FFmpeg
        with a colored background that reacts to the render spec sections.
        Full Remotion pipeline to be implemented in Phase 9.
        """
        output_path = settings.render_dir / f"{render_id}.mp4"

        # For MVP: generate a simple visualization using FFmpeg filters
        # This proves the pipeline works end-to-end
        duration = analysis.get("metadata", {}).get("duration", 60)
        width, height = render_spec.export_settings.resolution
        fps = render_spec.export_settings.fps

        # Build FFmpeg filtergraph with section-based color changes
        filter_parts = self._build_section_filters(
            render_spec, duration, width, height
        )

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={width}x{height}:d={duration}:r={fps}",
            "-i", audio_path,
            "-filter_complex", filter_parts,
            "-map", "[out]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            str(output_path),
        ]

        logger.info("Starting FFmpeg render: %s", render_id)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
            if result.returncode != 0:
                logger.error("FFmpeg error: %s", result.stderr[-500:] if result.stderr else "unknown")
                raise RuntimeError(f"FFmpeg failed: {result.stderr[-200:] if result.stderr else 'unknown error'}")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Render timed out after 10 minutes") from e

        download_url = f"/storage/renders/{render_id}.mp4"
        logger.info("Render complete: %s -> %s", render_id, download_url)

        return {"download_url": download_url}

    def _build_section_filters(
        self,
        render_spec: RenderSpec,
        duration: float,
        width: int,
        height: int,
    ) -> str:
        """Build FFmpeg filter_complex string with section-colored overlays.

        Creates a simple but effective visualization: colored rectangles
        that change with each section, with a gradient effect.
        """
        if not render_spec.sections:
            # No sections — solid color based on template
            color = self._template_base_color(render_spec.global_style.template)
            return (
                f"[0:v]drawbox=x=0:y=0:w={width}:h={height}:color={color}@0.6"
                f":t=fill[out]"
            )

        # Build overlay chain for each section
        filters: list[str] = []
        prev_label = "0:v"

        for i, section in enumerate(render_spec.sections):
            color = section.color_palette[0] if section.color_palette else "#7C5CFC"
            # Remove '#' for FFmpeg
            color_hex = color.lstrip("#")
            start = section.start_time
            end = section.end_time

            label = f"s{i}"
            filters.append(
                f"[{prev_label}]drawbox=x=0:y=0:w={width}:h={height}"
                f":color=0x{color_hex}@0.5:t=fill"
                f":enable='between(t,{start},{end})'[{label}]"
            )
            prev_label = label

        # Final output label
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
        }
        return colors.get(template, "0x0A0A0F")
