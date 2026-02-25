import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.models.render import RenderEditRequest, RenderSpec
from app.services.ai_image_service import AIImageService
from app.services.render_service import RenderService
from app.services.storage import job_store

router = APIRouter()
logger = logging.getLogger(__name__)

# Valid values for Literal-typed fields — used to coerce LLM hallucinations
_VALID_TEMPLATES = {
    "nebula", "geometric", "waveform", "cinematic", "retro",
    "nature", "abstract", "urban", "glitchbreak", "90s-anime",
}
_VALID_MOTIONS = {
    "slow-drift", "pulse", "energetic", "chaotic",
    "breathing", "glitch", "smooth-flow", "staccato",
}
_VALID_TRANSITIONS = {
    "fade-from-black", "fade-to-black", "cross-dissolve", "hard-cut",
    "morph", "flash-white", "wipe", "zoom-in", "zoom-out",
}
_VALID_FPS = {24, 30, 60}


def _sanitize_render_spec(spec: dict) -> dict:
    """Coerce LLM-generated values to valid defaults when they don't match Literal types."""
    # Strip extra fields
    spec.pop("useAiKeyframes", None)

    # Sanitize globalStyle / global_style
    gs = spec.get("globalStyle") or spec.get("global_style") or {}
    if gs.get("template") not in _VALID_TEMPLATES:
        gs["template"] = "nebula"

    # Sanitize sections
    for sec in spec.get("sections", []):
        if sec.get("motionStyle", sec.get("motion_style")) not in _VALID_MOTIONS:
            sec["motionStyle"] = "slow-drift"
            sec.pop("motion_style", None)

        for key, camel in [("transitionIn", "transition_in"), ("transitionOut", "transition_out")]:
            val = sec.get(key, sec.get(camel, "cross-dissolve"))
            if val not in _VALID_TRANSITIONS:
                sec[key] = "cross-dissolve"
                sec.pop(camel, None)

        # Clamp intensity
        intensity = sec.get("intensity", 0.5)
        if isinstance(intensity, (int, float)):
            sec["intensity"] = max(0.0, min(1.0, float(intensity)))

    # Sanitize exportSettings / export_settings
    es = spec.get("exportSettings") or spec.get("export_settings") or {}
    if es.get("fps") not in _VALID_FPS:
        es["fps"] = 30

    return spec


@router.post("/start")
async def start_render(req: Request) -> dict:
    """Submit a render spec and start video generation.

    Accepts both camelCase and snake_case field names.
    AI keyframe images are generated when use_ai_keyframes is set on the job.
    """
    # Parse and validate manually for better error reporting
    try:
        body = await req.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}") from e

    # Extract job_id from either naming convention
    job_id = body.get("jobId") or body.get("job_id")
    if not job_id:
        raise HTTPException(status_code=422, detail="Missing jobId")

    raw_spec = body.get("renderSpec") or body.get("render_spec") or {}
    raw_spec = _sanitize_render_spec(raw_spec)

    try:
        render_spec = RenderSpec.model_validate(raw_spec)
    except ValidationError as e:
        logger.warning("Render spec validation failed: %s", e)
        raise HTTPException(status_code=422, detail=str(e)) from e

    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Audio job not found")

    analysis = job.get("analysis")
    if not analysis:
        raise HTTPException(status_code=400, detail="Audio analysis not complete")

    render_id = str(uuid.uuid4())
    job_store.create_job(render_id, {
        "type": "render",
        "audio_job_id": job_id,
        "render_spec": render_spec.model_dump(),
        "status": "queued",
        "percentage": 0,
    })

    # Check if AI keyframes were requested (stored separately by chat handler)
    use_ai = job.get("use_ai_keyframes", False)

    render_service = RenderService()
    keyframe_paths: dict[str, str] = {}

    try:
        # Step 1: Generate AI keyframes if requested
        if use_ai and render_spec.sections:
            job_store.update_job(render_id, {
                "status": "generating_keyframes",
                "percentage": 10,
            })
            logger.info("Generating AI keyframes for render %s", render_id)

            ai_service = AIImageService()
            try:
                aspect = render_spec.export_settings.aspect_ratio
                keyframe_paths = await ai_service.generate_keyframes(
                    sections=render_spec.sections,
                    global_style=render_spec.global_style,
                    aspect_ratio=aspect,
                )
            except Exception:
                logger.exception("AI keyframe generation failed, continuing with procedural")
            finally:
                await ai_service.close()

        # Step 2: Render the video
        job_store.update_job(render_id, {
            "status": "rendering",
            "percentage": 30 if use_ai else 10,
        })

        audio_path = job.get("path", "")
        result = await render_service.render_video(
            render_id=render_id,
            audio_path=audio_path,
            analysis=analysis,
            render_spec=render_spec,
            lyrics=job.get("lyrics"),
            keyframe_paths=keyframe_paths if keyframe_paths else None,
        )

        job_store.update_job(render_id, {
            "status": "complete",
            "percentage": 100,
            "download_url": result.get("download_url"),
        })

    except Exception as e:
        logger.exception("Render failed: %s", render_id)
        job_store.update_job(render_id, {"status": "error", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Render failed: {e}") from e

    return {
        "render_id": render_id,
        "status": "complete",
        "download_url": result.get("download_url"),
    }


@router.get("/{render_id}/status")
async def get_render_status(render_id: str) -> dict:
    """Get render job progress."""
    job = job_store.get_job(render_id)
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")

    return {
        "render_id": render_id,
        "status": job.get("status", "unknown"),
        "percentage": job.get("percentage", 0),
        "download_url": job.get("download_url"),
        "error": job.get("error"),
    }


@router.get("/{render_id}/download")
async def get_download_url(render_id: str) -> dict:
    """Get the download URL for a completed render."""
    job = job_store.get_job(render_id)
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")

    if job.get("status") != "complete":
        raise HTTPException(status_code=400, detail="Render not complete")

    url = job.get("download_url")
    if not url:
        raise HTTPException(status_code=404, detail="Download not available")

    return {"render_id": render_id, "download_url": url}


@router.post("/{render_id}/edit")
async def edit_render(render_id: str, request: RenderEditRequest) -> dict:
    """Submit an edit to an existing render."""
    job = job_store.get_job(render_id)
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")

    new_render_id = str(uuid.uuid4())
    job_store.create_job(new_render_id, {
        "type": "render_edit",
        "parent_render_id": render_id,
        "edit_description": request.edit_description,
        "render_spec": (request.render_spec.model_dump() if request.render_spec else job.get("render_spec")),
        "status": "queued",
        "percentage": 0,
    })

    return {"render_id": new_render_id, "status": "queued"}
