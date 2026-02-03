"""Feature 4: Textbaserad sprakdetektering per segment."""
import logging
from typing import List

from langdetect import detect_langs, LangDetectException

logger = logging.getLogger("batch-worker.langdetect")

MIN_TEXT_LENGTH = 10


def detect_segment_languages(segments: List[dict], file_language: str = "sv") -> List[dict]:
    """Detektera sprak per segment med langdetect.

    - Text < 10 tecken: anvand fil-niva language
    - Text >= 10 tecken: textbaserad detektering
    - Flagga language_switch=True om segmentet avviker fran fil-spraket
    """
    for seg in segments:
        text = seg.get("text", "").strip()

        if len(text) < MIN_TEXT_LENGTH:
            seg["detected_language"] = file_language
            seg["language_confidence"] = 1.0
            seg["language_switch"] = False
            continue

        try:
            langs = detect_langs(text)
            if langs:
                best = langs[0]
                seg["detected_language"] = best.lang
                seg["language_confidence"] = round(best.prob, 4)
                seg["language_switch"] = best.lang != file_language
            else:
                seg["detected_language"] = file_language
                seg["language_confidence"] = 0.0
                seg["language_switch"] = False
        except LangDetectException:
            seg["detected_language"] = file_language
            seg["language_confidence"] = 0.0
            seg["language_switch"] = False

    language_switches = sum(1 for s in segments if s.get("language_switch"))
    if language_switches:
        logger.info(f"Sprakbyten detekterade: {language_switches}/{len(segments)} segment")

    return segments
