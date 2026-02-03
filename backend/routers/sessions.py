from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.services.session_storage import list_sessions, get_session, get_session_audio_path

router = APIRouter()


@router.get("/sessions")
async def get_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List saved recording sessions, newest first."""
    return {"sessions": list_sessions(limit=limit, offset=offset)}


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str):
    """Get full session metadata including transcript segments."""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/audio")
async def get_session_audio(session_id: str):
    """Download session audio as WAV file."""
    audio_path = get_session_audio_path(session_id)
    if audio_path is None:
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(
        audio_path,
        media_type="audio/wav",
        filename=f"{session_id}.wav",
    )
