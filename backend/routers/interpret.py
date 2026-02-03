"""Omtolknings-API.

Laser ratt segment fran en befintlig session och skickar
ett nytt batch-jobb med vald context-profil.
Samma transkript — olika tolkningar. Ingen omtranskribering.
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from backend.services.session_storage import get_session, get_session_interpretations
from backend.services.batch_client import submit_post_processing

router = APIRouter()
logger = logging.getLogger("whisper-svenska.interpret")


@router.post("/interpret/{session_id}")
async def interpret_session(
    session_id: str,
    context: str = Query(..., description="Context-profil att tolka med (meeting, brainstorm, journal, tech_notes, raw)"),
):
    """Omtolka en befintlig session med ny context-profil.

    Laser ratt segment fran session.json, skickar nytt batch-jobb
    med vald context. Ingen omtranskribering behövs.
    """
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session hittades inte")

    # Use raw segments from session.json (not processed)
    segments = session.get("segments", [])
    if not segments:
        raise HTTPException(status_code=400, detail="Sessionen har inga segment")

    # Build audio path for diarization if needed
    audio_path = None
    if session.get("audio_file"):
        import os
        from backend.services.session_storage import SESSIONS_DIR
        audio_path = os.path.join(SESSIONS_DIR, session_id, session["audio_file"])

    job_id = await submit_post_processing(
        session_id=session_id,
        segments=segments,
        audio_path=audio_path,
        context_profile=context,
    )

    if not job_id:
        raise HTTPException(status_code=500, detail="Kunde inte skapa tolkningsjobb")

    return {
        "session_id": session_id,
        "context": context,
        "job_id": job_id,
        "poll_url": f"/api/jobs/{job_id}",
    }


@router.get("/sessions/{session_id}/interpretations")
async def list_interpretations(session_id: str):
    """Lista alla tolkningar for en session."""
    interpretations = get_session_interpretations(session_id)
    return {
        "session_id": session_id,
        "interpretations": {
            name: {
                "context_profile": data.get("context_profile", name),
                "summary": data.get("summary"),
                "segment_count": len(data.get("segments", [])),
            }
            for name, data in interpretations.items()
        },
    }
