"""Feature 2 utokad: Confidence-utvardering for pipeline.

Samma heuristik som api_server.py men applicerad pa redan serialiserade segment-dicts.
"""
from typing import List


def evaluate_confidence(segments: List[dict]) -> List[dict]:
    """Bedom confidence for varje segment och berika med metadata.

    Returnerar segmenten med uppdaterade confidence-falt.
    """
    for seg in segments:
        seg["low_confidence"] = _is_low_confidence_dict(seg)

        # Berakna overall word confidence
        words = seg.get("words", [])
        if words:
            probs = [w.get("probability", 1.0) for w in words]
            seg["word_confidence_avg"] = round(sum(probs) / len(probs), 4)
            seg["word_confidence_min"] = round(min(probs), 4)
            seg["low_confidence_words"] = [
                w for w in words if w.get("probability", 1.0) < 0.3
            ]
        else:
            seg["word_confidence_avg"] = None
            seg["word_confidence_min"] = None
            seg["low_confidence_words"] = []

    return segments


def _is_low_confidence_dict(seg: dict) -> bool:
    """Bedom om ett segment-dict har lag kvalitet."""
    if seg.get("avg_logprob", 0) < -1.0:
        return True
    if seg.get("compression_ratio", 0) > 2.4:
        return True
    if seg.get("no_speech_prob", 0) > 0.6:
        return True

    words = seg.get("words", [])
    if words:
        low = sum(1 for w in words if w.get("probability", 1.0) < 0.3)
        if low / len(words) > 0.3:
            return True

    return False
