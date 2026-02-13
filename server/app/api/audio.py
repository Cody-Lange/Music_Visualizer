import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile

from app.config import settings
from app.services.audio_analyzer import AudioAnalyzerService
from app.services.storage import job_store

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}


def _validate_audio_file(filename: str, size: int) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    if size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb} MB",
        )


@router.post("/upload")
async def upload_audio(file: UploadFile) -> dict[str, str]:
    """Upload an audio file and start analysis. Returns a job ID."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    _validate_audio_file(file.filename, len(content))

    job_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix.lower()
    audio_path = settings.upload_dir / f"{job_id}{ext}"

    async with aiofiles.open(audio_path, "wb") as f:
        await f.write(content)

    # Store job metadata
    job_store.create_job(job_id, {
        "filename": file.filename,
        "path": str(audio_path),
        "status": "analyzing",
    })

    # Run analysis (synchronous for now, will be Celery task in production)
    try:
        analyzer = AudioAnalyzerService()
        analysis = analyzer.analyze(str(audio_path), file.filename)
        job_store.update_job(job_id, {
            "status": "complete",
            "analysis": analysis.model_dump(),
        })
    except Exception as e:
        job_store.update_job(job_id, {"status": "error", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}") from e

    return {"job_id": job_id, "status": "complete"}


@router.get("/{job_id}/analysis")
async def get_analysis(job_id: str) -> dict:
    """Get analysis results for a job."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") == "error":
        raise HTTPException(status_code=500, detail=job.get("error", "Analysis failed"))

    analysis = job.get("analysis")
    if not analysis:
        raise HTTPException(status_code=202, detail="Analysis still in progress")

    return {"job_id": job_id, "status": job["status"], "analysis": analysis}


@router.get("/{job_id}/waveform")
async def get_waveform(job_id: str) -> dict:
    """Get simplified waveform data for timeline display."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    analysis = job.get("analysis")
    if not analysis:
        raise HTTPException(status_code=202, detail="Analysis still in progress")

    # Return a subset of spectral data optimized for waveform rendering
    spectral = analysis.get("spectral", {})
    return {
        "job_id": job_id,
        "times": spectral.get("times", []),
        "rms": spectral.get("rms", []),
    }
