import logging
import uuid

from fastapi import APIRouter, HTTPException

from app.models.render import RenderRequest, RenderEditRequest
from app.services.ai_image_service import AIImageService
from app.services.render_service import RenderService
from app.services.storage import job_store

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/start")
async def start_render(request: RenderRequest) -> dict:
    """Submit a render spec and start video generation.

    If the render spec includes useAiKeyframes=true (set via the raw JSON
    from the chat), AI keyframe images are generated for each section before
    the video is rendered.
    """
    job = job_store.get_job(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Audio job not found")

    analysis = job.get("analysis")
    if not analysis:
        raise HTTPException(status_code=400, detail="Audio analysis not complete")

    render_id = str(uuid.uuid4())
    job_store.create_job(render_id, {
        "type": "render",
        "audio_job_id": request.job_id,
        "render_spec": request.render_spec.model_dump(),
        "status": "queued",
        "percentage": 0,
    })

    # Check if AI keyframes were requested (passed as extra field in raw JSON)
    raw_spec = job.get("render_spec", {})
    use_ai = raw_spec.get("useAiKeyframes", False)

    render_service = RenderService()
    keyframe_paths: dict[str, str] = {}

    try:
        # Step 1: Generate AI keyframes if requested
        if use_ai and request.render_spec.sections:
            job_store.update_job(render_id, {
                "status": "generating_keyframes",
                "percentage": 10,
            })
            logger.info("Generating AI keyframes for render %s", render_id)

            ai_service = AIImageService()
            try:
                aspect = request.render_spec.export_settings.aspect_ratio
                keyframe_paths = await ai_service.generate_keyframes(
                    sections=request.render_spec.sections,
                    global_style=request.render_spec.global_style,
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
            render_spec=request.render_spec,
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
