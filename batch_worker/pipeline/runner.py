"""Pipeline-orkestrerare.

Kor pipeline-stegen sekventiellt, gated av feature flags.
Uppdaterar jobb-status i SQLite mellan varje steg.

Stodjer context_profile for att overrida vilka steg som kors
och vilken LLM-prompt som anvands.
"""
import json
import logging
import os
import traceback
from datetime import datetime, timezone

from batch_worker.db import update_job
from batch_worker.pipeline.confidence import evaluate_confidence
from batch_worker.pipeline.retry_transcribe import retry_low_confidence
from batch_worker.pipeline.language_detect import detect_segment_languages
from batch_worker.pipeline.text_processing import process_text
from batch_worker.pipeline.pii_flagging import flag_pii
from batch_worker.pipeline.summary import generate_summary
from batch_worker.context_profiles import get_profile

logger = logging.getLogger("batch-worker.pipeline")


async def run_pipeline(job_id: str, input_data: dict, config):
    """Kor hela pipeline for ett jobb.

    Varje steg gated av feature flag, med optional context_profile override.
    Status uppdateras i SQLite mellan steg.
    """
    try:
        await update_job(job_id, status="processing", current_step="init")

        segments = input_data.get("segments", [])
        language = input_data.get("language", "sv")
        context_profile_name = input_data.get("context_profile")
        result = {"language": language}

        # Load context profile overrides if specified
        profile = get_profile(context_profile_name) if context_profile_name else None
        if profile:
            result["context_profile"] = context_profile_name

        # Resolve effective flags: profile overrides config defaults
        def _flag(profile_key: str, config_attr: str) -> bool:
            if profile and profile_key in profile:
                return bool(profile[profile_key])
            return getattr(config, config_attr)

        summary_enabled = _flag("summary", "summary_enabled")
        pii_enabled = _flag("pii", "pii_flagging_enabled")
        diarization_enabled = _flag("diarization", "diarization_enabled")
        text_processing_enabled = _flag("text_processing", "text_processing_enabled")
        casing = profile.get("casing", config.casing_profile) if profile else config.casing_profile

        # Steg 0: Confidence-utvardering (alltid aktiv)
        await update_job(job_id, current_step="confidence")
        segments = evaluate_confidence(segments)

        # Steg 1: Retry low-confidence segments
        if config.retry_enabled:
            await update_job(job_id, current_step="retry")
            config._audio_base64 = input_data.get("audio_base64")
            segments = await retry_low_confidence(segments, config)
            config._audio_base64 = None

        # Steg 1.5: Speaker diarization
        if diarization_enabled:
            await update_job(job_id, current_step="diarization")
            from batch_worker.pipeline.diarization import diarize
            audio_path = input_data.get("audio_path")
            segments = diarize(segments, audio_path=audio_path)

        # Steg 2: Sprakdetektering
        if config.language_detect_enabled:
            await update_job(job_id, current_step="language_detect")
            segments = detect_segment_languages(segments, file_language=language)

        # Steg 3: Textbearbetning
        if text_processing_enabled:
            await update_job(job_id, current_step="text_processing")
            segments = process_text(segments, casing_profile=casing)

        # Steg 4: PII-flaggning
        if pii_enabled:
            await update_job(job_id, current_step="pii_flagging")
            segments = flag_pii(segments)

        # Steg 5: LLM-sammanfattning
        summary = None
        if summary_enabled:
            await update_job(job_id, current_step="summary")
            prompt_template = profile.get("prompt") if profile else None
            summary = await generate_summary(segments, config, prompt_template=prompt_template)

        # Fardigt
        result["segments"] = segments
        if summary:
            result["summary"] = summary

        await update_job(job_id, status="completed", current_step="done", result_data=result)
        logger.info(f"Job {job_id} klart: {len(segments)} segment bearbetade")

        # Write result to session directory if session_id is provided
        session_id = input_data.get("session_id")
        if session_id:
            _write_processed_result(session_id, job_id, result, context_profile_name)

    except Exception as e:
        logger.error(f"Job {job_id} misslyckades: {e}")
        logger.error(traceback.format_exc())
        await update_job(job_id, status="failed", error=str(e))
        session_id = input_data.get("session_id")
        if session_id:
            _update_session_status(session_id, "failed", job_id, error=str(e))


def _get_sessions_dir() -> str:
    return os.environ.get("SESSIONS_DIR", "/app/transcriptions/sessions")


def _write_processed_result(session_id: str, job_id: str, result: dict, context_profile: str | None = None):
    """Write result to session directory.

    If context_profile is set, writes to interpreted_{context}.json.
    Otherwise writes to processed.json (backward compatible).
    """
    sessions_dir = _get_sessions_dir()
    session_dir = os.path.join(sessions_dir, session_id)

    if not os.path.isdir(session_dir):
        logger.warning(f"Session directory not found: {session_dir}")
        return

    # Determine output filename
    if context_profile:
        filename = f"interpreted_{context_profile}.json"
    else:
        filename = "processed.json"

    output_path = os.path.join(session_dir, filename)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"Wrote {filename} for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to write {filename} for {session_id}: {e}")
        return

    # Update session.json with processing status
    _update_session_status(session_id, "completed", job_id)


def _update_session_status(session_id: str, status: str, job_id: str, error: str | None = None):
    """Update session.json with processing_status and processed_at."""
    sessions_dir = _get_sessions_dir()
    meta_path = os.path.join(sessions_dir, session_id, "session.json")

    if not os.path.exists(meta_path):
        return

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        meta["job_id"] = job_id
        meta["processing_status"] = status
        meta["processed_at"] = datetime.now(timezone.utc).isoformat()
        if error:
            meta["processing_error"] = error

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to update session.json for {session_id}: {e}")
