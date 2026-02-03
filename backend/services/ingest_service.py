"""Shared ingest service — common logic for session creation and processing.

Used by both the REST ingest endpoint and the WebSocket realtime flow.
"""
import logging
from typing import Optional

from backend.services.session_storage import save_session, update_session_metadata
from backend.services.whisper_client import transcribe_audio
from backend.services.batch_client import submit_post_processing

logger = logging.getLogger("whisper-svenska.ingest")


async def ingest_audio_file(
    audio_bytes: bytes,
    filename: str,
    profile: str = "accurate",
    context_profile: Optional[str] = None,
    source: str = "api",
) -> dict:
    """Ingest a single audio file: transcribe, save session, submit pipeline job.

    Returns dict with session_id, job_id, and poll_url.
    """
    # Step 1: Transcribe via Whisper API
    result = await transcribe_audio(audio_bytes, filename, profile=profile)

    segments = result.get("segments", [])
    text = result.get("text", "")
    language = result.get("language", "sv")

    # Step 2: Save session to disk
    from datetime import datetime, timezone
    started_at = datetime.now(timezone.utc).isoformat()
    ended_at = started_at  # Single file, no duration span

    # For file uploads we save the raw bytes as a single "chunk"
    path = save_session(
        audio_chunks=[audio_bytes],
        transcripts=[result],
        profile=profile,
        started_at=started_at,
        ended_at=ended_at,
    )

    if not path:
        raise RuntimeError("Failed to save session")

    session_id = path.rstrip("/").split("/")[-1]
    audio_path = f"{path}/audio.wav"

    # Step 3: Submit pipeline job
    job_id = await submit_post_processing(
        session_id=session_id,
        segments=segments,
        audio_path=audio_path,
        language=language,
        context_profile=context_profile,
    )

    if job_id:
        update_session_metadata(session_id, {
            "job_id": job_id,
            "processing_status": "submitted",
            "source": source,
        })

    return {
        "session_id": session_id,
        "job_id": job_id,
        "poll_url": f"/api/jobs/{job_id}" if job_id else None,
        "text": text,
        "language": language,
        "segment_count": len(segments),
    }


async def finalize_realtime_session(
    audio_chunks: list[bytes],
    transcripts: list[dict],
    profile: str,
    started_at: str,
    ended_at: str,
    context_profile: Optional[str] = None,
) -> Optional[str]:
    """Finalize a realtime recording session: save to disk and submit pipeline job.

    Returns session_id or None on failure.
    """
    path = save_session(
        audio_chunks=audio_chunks,
        transcripts=transcripts,
        profile=profile,
        started_at=started_at,
        ended_at=ended_at,
    )

    if not path:
        return None

    session_id = path.rstrip("/").split("/")[-1]
    all_segments = []
    for t in transcripts:
        all_segments.extend(t.get("segments", []))

    audio_path = f"{path}/audio.wav"

    try:
        job_id = await submit_post_processing(
            session_id=session_id,
            segments=all_segments,
            audio_path=audio_path,
            context_profile=context_profile,
        )
        if job_id:
            update_session_metadata(session_id, {
                "job_id": job_id,
                "processing_status": "submitted",
            })
            logger.info(f"Post-processing job {job_id} submitted for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to submit post-processing: {e}")

    return session_id
