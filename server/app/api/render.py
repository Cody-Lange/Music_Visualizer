import uuid

from fastapi import APIRouter, HTTPException

from app.models.render import RenderRequest, RenderEditRequest
from app.services.render_service import RenderService
from app.services.storage import job_store

router = APIRouter()


@router.post("/start")
async def start_render(request: RenderRequest) -> dict:
    """Submit a render spec and start video generation."""
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

    # Start render (synchronous placeholder — will be Celery task)
    service = RenderService()
    try:
        audio_path = job.get("path", "")
        result = await service.render_video(
            render_id=render_id,
            audio_path=audio_path,
            analysis=analysis,
            render_spec=request.render_spec,
            lyrics=job.get("lyrics"),
        )
        job_store.update_job(render_id, {
            "status": "complete",
            "percentage": 100,
            "download_url": result.get("download_url"),
        })
    except Exception as e:
        job_store.update_job(render_id, {"status": "error", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Render failed: {e}") from e

    return {"render_id": render_id, "status": "complete"}


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
