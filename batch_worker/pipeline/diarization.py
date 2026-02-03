"""Speaker diarization — batch-only, feature-flagged (off by default).

FEATURE_DIARIZATION=false (default): steg hoppas over helt, ingen modell laddas.
FEATURE_DIARIZATION=true: kräver pyannote-audio eller liknande.

CPU-only antagande. Kan köras på annan hårdvara än api_server.

Output per segment:
    speaker_id:  str   ("SPEAKER_00", "SPEAKER_01", ...)
    speakers:    list   Tidsintervall per speaker i hela transkriptionen

Implementationsnoteringar:
    - Lazy model init: modellen laddas BARA om flaggan är true OCH
      diarize() anropas.
    - Segmenten enrichas in-place med speaker_id.
    - Ingen hårdkodad modellinitiering vid import.
"""
import logging
from typing import List, Optional

logger = logging.getLogger("batch-worker.diarization")

# Lazy-loaded model reference
_diarization_pipeline = None


def _get_pipeline():
    """Lazy-load diarization pipeline. Anropas bara om flaggan är true."""
    global _diarization_pipeline
    if _diarization_pipeline is None:
        try:
            from pyannote.audio import Pipeline
            _diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=True,
            )
            # Tvinga CPU
            import torch
            _diarization_pipeline.to(torch.device("cpu"))
            logger.info("Diarization pipeline laddad (CPU)")
        except ImportError:
            logger.error(
                "pyannote-audio inte installerat. "
                "Installera med: pip install pyannote-audio"
            )
            raise
    return _diarization_pipeline


def diarize(segments: List[dict], audio_path: Optional[str] = None) -> List[dict]:
    """Kör speaker diarization och enricha segment med speaker_id.

    Args:
        segments: Lista med segment-dicts (måste ha 'start' och 'end').
        audio_path: Sökväg till ljudfil för diarization.

    Returns:
        Segmenten enrichade med:
        - speaker_id: str  (t.ex. "SPEAKER_00")

    Raises:
        RuntimeError: Om audio_path saknas.

    Exempel på enrichat segment:
        {
            "start": 0.0,
            "end": 2.5,
            "text": "Hej alla",
            "speaker_id": "SPEAKER_00",
            ...
        }
    """
    if not audio_path:
        logger.warning("Ingen audio_path för diarization, hoppar över")
        for seg in segments:
            seg["speaker_id"] = "UNKNOWN"
        return segments

    pipeline = _get_pipeline()
    diarization_result = pipeline(audio_path)

    # Bygg tidsintervall-till-speaker mappning
    speaker_turns = []
    for turn, _, speaker in diarization_result.itertracks(yield_label=True):
        speaker_turns.append({
            "start": turn.start,
            "end": turn.end,
            "speaker": speaker,
        })

    # Matcha varje segment till den speaker som har störst överlapp
    for seg in segments:
        seg_start = seg["start"]
        seg_end = seg["end"]
        best_speaker = "UNKNOWN"
        best_overlap = 0.0

        for turn in speaker_turns:
            overlap_start = max(seg_start, turn["start"])
            overlap_end = min(seg_end, turn["end"])
            overlap = max(0.0, overlap_end - overlap_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn["speaker"]

        seg["speaker_id"] = best_speaker

    logger.info(
        f"Diarization klar: {len(set(s['speaker_id'] for s in segments))} "
        f"speakers i {len(segments)} segment"
    )
    return segments
