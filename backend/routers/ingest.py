"""Unified audio ingest endpoint.

En endpoint som alla klienter anvander: web, desktop, CLI, andra appar.
Tar emot en audiofil, transkriberar, sparar session, och startar pipeline.
"""
import logging

from fastapi import APIRouter, File, UploadFile, Query, HTTPException

from backend.services.ingest_service import ingest_audio_file

router = APIRouter()
logger = logging.getLogger("whisper-svenska.ingest")


@router.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    context: str = Query(default=None, description="Context-profil (meeting, brainstorm, journal, tech_notes, raw)"),
    profile: str = Query(default="accurate", description="Transkriberingsprofil (ultra_realtime, fast, accurate, highest_quality)"),
    source: str = Query(default="api", description="Kallsystem (web, cli, desktop, api)"),
):
    """Unified audio ingest — transkribera, spara och bearbeta i ett steg.

    Accepts multipart audio file upload. Returns session_id, job_id, and poll_url.
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Tom audiofil")

    filename = file.filename or "audio.wav"

    try:
        result = await ingest_audio_file(
            audio_bytes=audio_bytes,
            filename=filename,
            profile=profile,
            context_profile=context,
            source=source,
        )
        return result
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
