"""Feature 6: PII-flaggning via regex.

Flaggar enbart — maskerar aldrig.
"""
import re
from typing import List, Dict

# Regex-monster for svenska PII
_PATTERNS: Dict[str, re.Pattern] = {
    "personnummer": re.compile(r"\d{6,8}[-\s]?\d{4}"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "telefon": re.compile(r"(?:\+46|0)\s*[1-9]\d{0,2}[\s-]?\d{2,3}[\s-]?\d{2}[\s-]?\d{2}"),
}

# Svenska svordomar (vanliga)
_PROFANITY_WORDS = {
    "fan", "jävla", "jävlar", "helvete", "skit", "skita",
    "förbannad", "förbannade", "satan", "satans",
    "jävel", "jävligt", "faen", "fy fan",
}

_PROFANITY_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _PROFANITY_WORDS) + r")\b",
    re.IGNORECASE,
)


def flag_pii(segments: List[dict]) -> List[dict]:
    """Skanna segment for PII och svordomar. Flaggar utan att maskera."""
    for seg in segments:
        text = seg.get("text", "") or seg.get("processed_text", "")
        flags = []

        # Regex-baserade PII
        for pii_type, pattern in _PATTERNS.items():
            for match in pattern.finditer(text):
                flags.append({
                    "type": pii_type,
                    "start_char": match.start(),
                    "end_char": match.end(),
                    "text": match.group(),
                })

        # Svordomar
        for match in _PROFANITY_PATTERN.finditer(text):
            flags.append({
                "type": "profanity",
                "start_char": match.start(),
                "end_char": match.end(),
                "text": match.group(),
            })

        seg["pii_flags"] = flags
        seg["has_pii"] = len(flags) > 0

    return segments
