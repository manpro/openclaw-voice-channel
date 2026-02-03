"""Lightweight HTTP client for submitting jobs to batch_worker."""
import logging
from typing import Optional

import httpx

logger = logging.getLogger("whisper-svenska.batch-client")

BATCH_WORKER_URL = "http://127.0.0.1:8400"


async def submit_post_processing(
    session_id: str,
    segments: list[dict],
    audio_path: Optional[str] = None,
    language: str = "sv",
    context_profile: Optional[str] = None,
) -> Optional[str]:
    """Submit a post-processing job to batch_worker.

    Returns job_id on success, None on failure.
    """
    payload = {
        "segments": segments,
        "language": language,
        "session_id": session_id,
        "audio_path": audio_path,
    }
    if context_profile:
        payload["context_profile"] = context_profile

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{BATCH_WORKER_URL}/jobs",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            job_id = data.get("job_id")
            logger.info(f"Submitted post-processing job {job_id} for session {session_id}")
            return job_id
    except Exception as e:
        logger.error(f"Failed to submit post-processing for session {session_id}: {e}")
        return None
