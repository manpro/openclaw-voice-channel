from fastapi import APIRouter, UploadFile, File, HTTPException, Query

from backend.services.whisper_client import transcribe_audio, warmup_profile

router = APIRouter()


@router.post("/transcribe")
async def batch_transcribe(
    file: UploadFile = File(...),
    profile: str = Query(default="accurate"),
):
    """Transcribe an uploaded audio file.

    Profile selects backend and parameters on the Whisper server.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Tom fil")

    try:
        result = await transcribe_audio(
            contents,
            file.filename or "audio.wav",
            profile=profile,
        )
        return {
            "text": result.get("text", ""),
            "filename": file.filename,
            "profile": profile,
            "segments": result.get("segments"),
            "backend": result.get("backend"),
            "inference_time": result.get("inference_time"),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Whisper API-fel: {e}")


@router.post("/warmup")
async def warmup(
    profile: str = Query(default="accurate"),
):
    """Pre-load the model for a given profile on the Whisper server."""
    try:
        result = await warmup_profile(profile=profile)
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Warmup-fel: {e}")
