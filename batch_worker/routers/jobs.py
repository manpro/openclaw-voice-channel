"""Job submission och polling endpoints."""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from batch_worker.db import create_job, get_job

logger = logging.getLogger("batch-worker.jobs")

router = APIRouter()


class JobSubmitRequest(BaseModel):
    """Input for att skapa ett nytt pipeline-jobb."""
    segments: List[dict]
    language: str = "sv"
    audio_base64: Optional[str] = None  # Behövs för retry-steget
    audio_path: Optional[str] = None    # Sökväg till WAV för diarization
    session_id: Optional[str] = None    # För resultat-writeback till session
    context_profile: Optional[str] = None  # Context-profil för tolkningslagret


class JobSubmitResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    id: str
    status: str
    current_step: str
    created_at: str
    updated_at: str
    error: str


@router.post("/jobs", response_model=JobSubmitResponse)
async def submit_job(request: Request, body: JobSubmitRequest):
    """Skapa ett nytt pipeline-jobb.

    Jobbet laggs i kön och körs med begränsad concurrency.
    Returnerar job_id for polling.
    """
    input_data = body.model_dump()
    job_id = await create_job(input_data)

    config = request.app.state.config
    job_queue = request.app.state.job_queue
    await job_queue.enqueue(job_id, input_data, config)

    logger.info(f"Job {job_id} skapad med {len(body.segments)} segment")
    return JobSubmitResponse(job_id=job_id, status="queued")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Poll status for ett jobb."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Jobb hittades inte")
    return JobStatusResponse(
        id=job["id"],
        status=job["status"],
        current_step=job["current_step"] or "",
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        error=job["error"] or "",
    )


@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    """Hamta fardigt resultat for ett jobb."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Jobb hittades inte")
    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Jobb inte klart. Status: {job['status']}, steg: {job['current_step']}",
        )
    return {
        "id": job["id"],
        "status": job["status"],
        "result": job["result_data"],
    }
