from fastapi import APIRouter, HTTPException

from app.models.lyrics import LyricsFetchRequest
from app.services.lyrics_service import LyricsService
from app.services.storage import job_store

router = APIRouter()


@router.post("/fetch")
async def fetch_lyrics(request: LyricsFetchRequest) -> dict:
    """Fetch lyrics from external services by title and artist."""
    service = LyricsService()
    result = await service.fetch_lyrics(request.title, request.artist)

    if not result:
        raise HTTPException(status_code=404, detail="Lyrics not found")

    # If a job_id was provided, attach lyrics to that job
    if request.job_id:
        job = job_store.get_job(request.job_id)
        if job:
            job_store.update_job(request.job_id, {"lyrics": result.model_dump()})

    return {"lyrics": result.model_dump()}


@router.get("/{job_id}")
async def get_lyrics(job_id: str) -> dict:
    """Get lyrics for a specific job."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    lyrics = job.get("lyrics")
    if not lyrics:
        raise HTTPException(status_code=404, detail="No lyrics available for this job")

    return {"job_id": job_id, "lyrics": lyrics}
