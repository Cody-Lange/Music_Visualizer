"""AI image and video generation service for keyframe creation.

Generates unique artwork for each section boundary using DALL-E 3
(via OpenAI API) or Stability AI as a fallback. Each image is tailored
to the section's mood, colors, and thematic content from the render spec.

Optionally converts keyframe images to short video clips via
Stability AI's image-to-video API for more dynamic visuals.
"""

import asyncio
import logging
from pathlib import Path

import httpx

from app.config import settings
from app.models.render import SectionSpec, GlobalStyle

logger = logging.getLogger(__name__)

# Negative prompt components to keep images clean
_NEGATIVE_SUFFIXES = (
    "Do not include any text, words, letters, watermarks, borders, frames, "
    "human faces, or photographic elements."
)

# Template to visual style mapping for prompt enrichment
_TEMPLATE_STYLES: dict[str, str] = {
    "nebula": "cosmic nebula art style, deep space, ethereal glow, astronomical imagery",
    "geometric": "geometric abstract art, sacred geometry, mathematical precision, clean lines",
    "waveform": "sound wave visualization, audio spectrum art, dark minimal aesthetic",
    "cinematic": "cinematic wide shot, dramatic lighting, film color grading, anamorphic",
    "retro": "retro 80s synthwave, neon colors, vintage CRT aesthetic, VHS grain",
    "nature": "organic nature art, bioluminescent, flowing natural forms, earth tones",
    "abstract": "abstract expressionist, bold brushstrokes, color field painting",
    "urban": "urban street art, graffiti aesthetic, concrete textures, gritty",
    "glitchbreak": "glitch art, data corruption, pixel sorting, digital distortion",
    "90s-anime": "90s anime cel art, bold outlines, vibrant flat colors, retro anime aesthetic",
}


def _build_prompt(section: SectionSpec, global_style: GlobalStyle) -> str:
    """Construct a detailed image generation prompt for a section."""
    base = section.ai_prompt or f"Abstract visualization for a {section.label} section"

    # Style from template
    template_style = _TEMPLATE_STYLES.get(global_style.template, "abstract digital art")

    # Color guidance
    color_str = ", ".join(section.color_palette[:4]) if section.color_palette else ""

    # Visual elements
    elements = ", ".join(section.visual_elements[:5]) if section.visual_elements else ""

    # Style modifiers from global
    modifiers = ", ".join(global_style.style_modifiers[:4]) if global_style.style_modifiers else ""

    parts = [base]
    if template_style:
        parts.append(template_style)
    if modifiers:
        parts.append(modifiers)
    if elements:
        parts.append(f"incorporating {elements}")
    if color_str:
        parts.append(f"dominant colors: {color_str}")
    parts.append("seamless background, high quality, 4K resolution")
    parts.append(_NEGATIVE_SUFFIXES)

    return ". ".join(parts)


def _size_for_aspect(aspect_ratio: str) -> str:
    """Map aspect ratio to DALL-E 3 supported size."""
    if aspect_ratio == "9:16":
        return "1024x1792"
    if aspect_ratio == "1:1":
        return "1024x1024"
    # Default 16:9
    return "1792x1024"


class AIImageService:
    """Generate AI keyframe images for visualization sections."""

    def __init__(self) -> None:
        self._http: httpx.AsyncClient | None = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=120)
        return self._http

    async def generate_keyframes(
        self,
        sections: list[SectionSpec],
        global_style: GlobalStyle,
        aspect_ratio: str = "16:9",
    ) -> dict[str, str]:
        """Generate one keyframe image per section.

        Returns a dict mapping section label -> local file path.
        Falls back to Stability AI if OpenAI is unavailable.
        """
        results: dict[str, str] = {}

        for section in sections:
            prompt = _build_prompt(section, global_style)
            logger.info(
                "Generating AI keyframe for section '%s': %.80s...",
                section.label, prompt,
            )

            path: str | None = None

            # Try DALL-E 3 first
            if settings.openai_api_key:
                path = await self._generate_dalle(
                    prompt, section.label, aspect_ratio,
                )

            # Fallback to Stability AI
            if not path and settings.stability_api_key:
                path = await self._generate_stability(
                    prompt, section.label, aspect_ratio,
                )

            if path:
                results[section.label] = path
                logger.info("Keyframe saved: %s -> %s", section.label, path)
            else:
                logger.warning(
                    "No AI image generated for section '%s' "
                    "(no API key configured or generation failed)",
                    section.label,
                )

        return results

    async def _generate_dalle(
        self, prompt: str, label: str, aspect_ratio: str,
    ) -> str | None:
        """Generate an image using DALL-E 3 via OpenAI API."""
        client = self._client()
        size = _size_for_aspect(aspect_ratio)

        try:
            resp = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": size,
                    "quality": "hd",
                    "response_format": "url",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            image_url = data["data"][0]["url"]

            # Download the image
            return await self._download_image(image_url, label)

        except Exception:
            logger.exception("DALL-E 3 generation failed for '%s'", label)
            return None

    async def _generate_stability(
        self, prompt: str, label: str, aspect_ratio: str,
    ) -> str | None:
        """Generate an image using Stability AI API."""
        client = self._client()

        # Map aspect ratio to Stability AI format
        ar_map = {"16:9": "16:9", "9:16": "9:16", "1:1": "1:1"}
        stability_ar = ar_map.get(aspect_ratio, "16:9")

        try:
            resp = await client.post(
                "https://api.stability.ai/v2beta/stable-image/generate/ultra",
                headers={
                    "Authorization": f"Bearer {settings.stability_api_key}",
                    "Accept": "image/*",
                },
                data={
                    "prompt": prompt,
                    "aspect_ratio": stability_ar,
                    "output_format": "png",
                },
            )
            resp.raise_for_status()

            # Save the image directly
            safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
            out_path = settings.keyframe_dir / f"{safe_label}.png"
            out_path.write_bytes(resp.content)
            return str(out_path)

        except Exception:
            logger.exception("Stability AI generation failed for '%s'", label)
            return None

    async def _download_image(self, url: str, label: str) -> str | None:
        """Download an image from a URL and save locally."""
        client = self._client()
        try:
            resp = await client.get(url)
            resp.raise_for_status()

            safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
            out_path = settings.keyframe_dir / f"{safe_label}.png"
            out_path.write_bytes(resp.content)
            return str(out_path)
        except Exception:
            logger.exception("Failed to download keyframe image for '%s'", label)
            return None

    # ── Video clip generation ────────────────────────────────────────────

    async def generate_video_clips(
        self,
        keyframe_paths: dict[str, str],
    ) -> dict[str, str]:
        """Convert keyframe images to video clips via Stability AI image-to-video.

        Returns a dict mapping section label -> local video file path.
        Requires STABILITY_API_KEY. Sections without a keyframe image are skipped.
        """
        if not settings.stability_api_key:
            logger.warning(
                "STABILITY_API_KEY not set — skipping video clip generation"
            )
            return {}

        results: dict[str, str] = {}
        tasks: dict[str, asyncio.Task[str | None]] = {}

        # Submit all sections in parallel
        for label, image_path in keyframe_paths.items():
            if not image_path or not Path(image_path).exists():
                continue
            tasks[label] = asyncio.create_task(
                self._image_to_video(image_path, label)
            )

        for label, task in tasks.items():
            try:
                video_path = await task
                if video_path:
                    results[label] = video_path
                    logger.info("Video clip saved: %s -> %s", label, video_path)
            except Exception:
                logger.exception(
                    "Video clip generation failed for section '%s'", label
                )

        return results

    async def _image_to_video(
        self, image_path: str, label: str,
    ) -> str | None:
        """Submit an image to Stability AI image-to-video and poll for result."""
        client = self._client()
        safe_label = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in label
        )

        try:
            # Step 1: Submit image-to-video request
            with open(image_path, "rb") as f:
                resp = await client.post(
                    "https://api.stability.ai/v2beta/image-to-video",
                    headers={
                        "Authorization": f"Bearer {settings.stability_api_key}",
                    },
                    files={"image": (Path(image_path).name, f, "image/png")},
                    data={
                        "cfg_scale": 2.5,
                        "motion_bucket_id": 180,
                    },
                )
                resp.raise_for_status()

            generation_id = resp.json()["id"]
            logger.info(
                "Video generation started for '%s': id=%s", label, generation_id
            )

            # Step 2: Poll for completion (up to 5 minutes)
            for attempt in range(60):
                await asyncio.sleep(5)
                result = await client.get(
                    f"https://api.stability.ai/v2beta/image-to-video/result/{generation_id}",
                    headers={
                        "Authorization": f"Bearer {settings.stability_api_key}",
                        "Accept": "video/*",
                    },
                )
                if result.status_code == 200:
                    out_path = settings.video_clip_dir / f"{safe_label}.mp4"
                    out_path.write_bytes(result.content)
                    return str(out_path)
                if result.status_code != 202:
                    logger.error(
                        "Unexpected status %d polling video for '%s'",
                        result.status_code, label,
                    )
                    return None

            logger.error("Video generation timed out for '%s'", label)
            return None

        except Exception:
            logger.exception("image-to-video failed for '%s'", label)
            return None

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None
