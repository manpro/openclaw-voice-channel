"""Feature 3: Retry low-confidence segments via Whisper API.

All communication goes through config.whisper_api_url (remote-ready).
Includes configurable timeout and retry with exponential backoff.
"""
import asyncio
import logging
from typing import List

import httpx

logger = logging.getLogger("batch-worker.retry")


async def _post_with_retries(client: httpx.AsyncClient, url: str, json: dict, config) -> httpx.Response:
    """POST with configurable retries and exponential backoff."""
    last_exc = None
    for attempt in range(config.http_retries):
        try:
            resp = await client.post(url, json=json)
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.TransportError) as e:
            last_exc = e
            if attempt < config.http_retries - 1:
                wait = config.http_retry_backoff * (2 ** attempt)
                logger.warning(f"Retry attempt {attempt + 1} failed: {e}, waiting {wait}s")
                await asyncio.sleep(wait)
    raise last_exc


async def retry_low_confidence(segments: List[dict], config) -> List[dict]:
    """Re-transkribera segment med lag confidence via /transcribe/retry.

    Strategi 1: Samma modell med hogre beam_size.
    Strategi 2: Om fortfarande svagt och retry_with_large=True, anvand large-modellen.
    """
    audio_base64 = config._audio_base64  # Satt av runner fran job input

    if not audio_base64:
        logger.warning("Ingen audio_base64 tillganglig, hoppar over retry")
        return segments

    low_segments = [(i, seg) for i, seg in enumerate(segments) if seg.get("low_confidence")]

    if not low_segments:
        logger.info("Inga low-confidence segment, hoppar over retry")
        return segments

    logger.info(f"Retry: {len(low_segments)} low-confidence segment via {config.whisper_api_url}")
    retry_url = f"{config.whisper_api_url}/transcribe/retry"

    timeout = httpx.Timeout(config.http_timeout)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for idx, seg in low_segments:
            # Strategi 1: samma modell, hogre beam_size
            try:
                result = await _post_with_retries(client, retry_url, {
                    "audio_base64": audio_base64,
                    "start": seg["start"],
                    "end": seg["end"],
                    "beam_size": config.retry_beam_size,
                    "model": "KBLab/kb-whisper-medium",
                    "language": seg.get("language", "sv"),
                }, config)
                retry_data = result.json()
                retry_segments = retry_data.get("segments", [])

                if retry_segments:
                    best = retry_segments[0]
                    if not best.get("low_confidence", True):
                        segments[idx] = {**seg, **best, "retried": True, "retry_model": "medium"}
                        logger.info(f"Segment {idx} forbattrat med medium beam={config.retry_beam_size}")
                        continue

            except Exception as e:
                logger.error(f"Retry strategi 1 misslyckades for segment {idx}: {e}")

            # Strategi 2: large-modell om aktiverat
            if config.retry_with_large:
                try:
                    result = await _post_with_retries(client, retry_url, {
                        "audio_base64": audio_base64,
                        "start": seg["start"],
                        "end": seg["end"],
                        "beam_size": config.retry_beam_size,
                        "model": "KBLab/kb-whisper-large",
                        "language": seg.get("language", "sv"),
                    }, config)
                    retry_data = result.json()
                    retry_segments = retry_data.get("segments", [])

                    if retry_segments:
                        best = retry_segments[0]
                        segments[idx] = {**seg, **best, "retried": True, "retry_model": "large"}
                        logger.info(f"Segment {idx} re-transkriberat med large")

                except Exception as e:
                    logger.error(f"Retry strategi 2 (large) misslyckades for segment {idx}: {e}")

    return segments
