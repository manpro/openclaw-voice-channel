import json
import re
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from backend.services.whisper_client import transcribe_audio
from backend.services.ingest_service import finalize_realtime_session

router = APIRouter()
logger = logging.getLogger("whisper-svenska.realtime")

_NOISE_RE = re.compile(r'^[\s\.\!\?\,\;\:\-\—\–\…\'\"\«\»\(\)\[\]]*$')


@router.websocket("/ws/transcribe")
async def websocket_transcribe(
    ws: WebSocket,
    profile: str = Query(default="accurate"),
):
    """Real-time transcription over WebSocket.

    Client sends binary audio chunks (WebM/Opus).
    Server responds with JSON: {"text": "...", "chunk": n, "profile": "..."}

    Profile is set via query param: /ws/transcribe?profile=fast

    All audio chunks and transcripts are saved to disk automatically
    when the session ends (WebSocket disconnects).
    """
    await ws.accept()
    chunk_index = 0

    # Session accumulation — does not affect realtime performance
    audio_chunks: list[bytes] = []
    transcripts: list[dict] = []
    started_at = datetime.now(timezone.utc).isoformat()

    try:
        while True:
            data = await ws.receive_bytes()
            if not data:
                continue

            # Skip very small blobs (< 500 bytes) that contain no useful audio
            if len(data) < 500:
                continue

            # Store raw chunk for session saving
            audio_chunks.append(data)

            try:
                result = await transcribe_audio(data, "chunk.webm", profile=profile)
                text = result.get("text", "").strip()
                # Skip empty or punctuation-only results (noise/hallucination)
                if not text or _NOISE_RE.match(text):
                    continue

                # Store transcript for session saving
                transcripts.append(result)

                await ws.send_text(
                    json.dumps({
                        "text": text,
                        "chunk": chunk_index,
                        "profile": profile,
                        "segments": result.get("segments"),
                    })
                )
                chunk_index += 1
            except Exception as e:
                await ws.send_text(json.dumps({"error": str(e)}))

    except WebSocketDisconnect:
        pass
    finally:
        # Save session and submit pipeline job via shared service
        ended_at = datetime.now(timezone.utc).isoformat()
        if audio_chunks:
            try:
                session_id = await finalize_realtime_session(
                    audio_chunks=audio_chunks,
                    transcripts=transcripts,
                    profile=profile,
                    started_at=started_at,
                    ended_at=ended_at,
                )
                if session_id:
                    logger.info(f"Session saved and submitted: {session_id}")
            except Exception as e:
                logger.error(f"Failed to save session: {e}")
