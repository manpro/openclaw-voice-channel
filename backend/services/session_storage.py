"""Session storage — saves realtime recording sessions to disk.

Each session is stored as a directory containing:
  - audio.wav    (16kHz mono PCM)
  - session.json (metadata + full transcript with segments)
  - processed.json (default pipeline output, backward compatible)
  - interpreted_*.json (context-specific interpretations)

Sessions are saved to SESSIONS_DIR (default: /app/transcriptions/sessions/).
"""

import json
import os
import subprocess
import tempfile
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("whisper-svenska.sessions")

SESSIONS_DIR = os.environ.get(
    "SESSIONS_DIR",
    "/app/transcriptions/sessions",
)


def _ensure_sessions_dir():
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def save_session(
    audio_chunks: list[bytes],
    transcripts: list[dict[str, Any]],
    profile: str,
    started_at: str,
    ended_at: str,
) -> str | None:
    """Concatenate WebM audio chunks into a single WAV and save with metadata.

    Runs synchronously (intended to be called from a background task).
    Returns the session directory path, or None on failure.
    """
    if not audio_chunks:
        logger.info("No audio chunks to save — skipping session")
        return None

    _ensure_sessions_dir()

    # Build session directory name: 2026-02-01_12-30-00_accurate
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    session_id = f"{ts}_{profile}"
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    wav_path = os.path.join(session_dir, "audio.wav")
    meta_path = os.path.join(session_dir, "session.json")

    try:
        _concat_chunks_to_wav(audio_chunks, wav_path)
    except Exception as e:
        logger.error(f"Failed to save audio for session {session_id}: {e}")
        return None

    # Combine all transcript segments into one timeline
    all_segments = []
    full_text_parts = []
    for t in transcripts:
        text = t.get("text", "").strip()
        if text:
            full_text_parts.append(text)
        for seg in t.get("segments", []):
            all_segments.append(seg)

    # Get audio duration from WAV file
    duration = _get_wav_duration(wav_path)

    metadata = {
        "session_id": session_id,
        "profile": profile,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration": duration,
        "chunks": len(audio_chunks),
        "text": " ".join(full_text_parts),
        "segments": all_segments,
        "audio_file": "audio.wav",
        "audio_format": "wav",
        "sample_rate": 16000,
        "channels": 1,
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info(
        f"Session saved: {session_id} — "
        f"{len(audio_chunks)} chunks, "
        f"{duration:.1f}s audio, "
        f"{len(full_text_parts)} transcript parts"
    )
    return session_dir


def _concat_chunks_to_wav(chunks: list[bytes], output_path: str):
    """Concatenate multiple WebM/Opus chunks into a single 16kHz mono WAV."""
    tmp_dir = tempfile.mkdtemp(prefix="whisper_session_")
    chunk_files = []

    try:
        # Write each chunk to a temp file
        for i, chunk_data in enumerate(chunks):
            chunk_path = os.path.join(tmp_dir, f"chunk_{i:04d}.webm")
            with open(chunk_path, "wb") as f:
                f.write(chunk_data)
            chunk_files.append(chunk_path)

        # Build ffmpeg concat file
        concat_path = os.path.join(tmp_dir, "concat.txt")
        with open(concat_path, "w") as f:
            for cp in chunk_files:
                f.write(f"file '{cp}'\n")

        # Concatenate and convert to WAV in one step
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_path,
                "-ar", "16000",
                "-ac", "1",
                "-f", "wav",
                output_path,
            ],
            capture_output=True,
            check=True,
        )
    finally:
        # Cleanup temp files
        for cp in chunk_files:
            _safe_unlink(cp)
        _safe_unlink(os.path.join(tmp_dir, "concat.txt"))
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass


def _get_wav_duration(wav_path: str) -> float:
    """Get duration of a WAV file in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                wav_path,
            ],
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def list_sessions(limit: int = 50, offset: int = 0) -> list[dict]:
    """List saved sessions, newest first."""
    _ensure_sessions_dir()

    sessions = []
    session_dirs = sorted(Path(SESSIONS_DIR).iterdir(), reverse=True)

    for d in session_dirs[offset:offset + limit]:
        if not d.is_dir():
            continue
        meta_path = d / "session.json"
        if not meta_path.exists():
            continue
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            # Return summary (without full segments for listing)
            sessions.append({
                "session_id": meta.get("session_id", d.name),
                "profile": meta.get("profile"),
                "started_at": meta.get("started_at"),
                "duration": meta.get("duration"),
                "text": meta.get("text", "")[:200],
                "chunks": meta.get("chunks"),
                "job_id": meta.get("job_id"),
                "processing_status": meta.get("processing_status"),
            })
        except Exception:
            continue

    return sessions


def get_session(session_id: str) -> dict | None:
    """Get full session metadata including segments.

    Merges processed.json and all interpreted_*.json into the response.
    """
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    meta_path = os.path.join(session_dir, "session.json")

    if not os.path.exists(meta_path):
        return None

    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Merge processed.json if it exists (backward compatible)
    processed_path = os.path.join(session_dir, "processed.json")
    if os.path.exists(processed_path):
        try:
            with open(processed_path, "r", encoding="utf-8") as f:
                processed = json.load(f)
            data["processed"] = processed
        except Exception:
            pass

    # Discover and merge all interpreted_*.json files
    interpretations = get_session_interpretations(session_id)
    if interpretations:
        data["interpretations"] = interpretations

    return data


def get_session_interpretations(session_id: str) -> dict:
    """Discover all interpreted_*.json files for a session.

    Returns dict keyed by context name, e.g.:
    {"meeting": {...}, "brainstorm": {...}}
    """
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    if not os.path.isdir(session_dir):
        return {}

    interpretations = {}
    for f in os.listdir(session_dir):
        if f.startswith("interpreted_") and f.endswith(".json"):
            context_name = f[len("interpreted_"):-len(".json")]
            try:
                with open(os.path.join(session_dir, f), "r", encoding="utf-8") as fh:
                    interpretations[context_name] = json.load(fh)
            except Exception:
                continue

    return interpretations


def update_session_metadata(session_id: str, updates: dict):
    """Merge updates into an existing session.json."""
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    meta_path = os.path.join(session_dir, "session.json")

    if not os.path.exists(meta_path):
        logger.warning(f"Cannot update metadata — session not found: {session_id}")
        return

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        meta.update(updates)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to update session metadata for {session_id}: {e}")


def get_session_audio_path(session_id: str) -> str | None:
    """Get path to session audio file."""
    audio_path = os.path.join(SESSIONS_DIR, session_id, "audio.wav")
    return audio_path if os.path.exists(audio_path) else None


def _safe_unlink(path: str):
    try:
        os.unlink(path)
    except OSError:
        pass
