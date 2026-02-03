"""Feature 5: Textnormalisering och casing."""
import re
import unicodedata
from typing import List


def process_text(segments: List[dict], casing_profile: str = "verbatim") -> List[dict]:
    """Applicera textbearbetning baserat pa profil.

    Profiler:
    - verbatim: ingen andring
    - meeting_notes: capitalize meningar, normalisera unicode-punkt
    - subtitle_friendly: max 42 tecken/rad, max 2 rader/segment
    """
    if casing_profile == "verbatim":
        return segments

    for seg in segments:
        text = seg.get("text", "")

        # Gemensam: normalisera unicode-punktering
        text = _normalize_punctuation(text)

        if casing_profile == "meeting_notes":
            text = _capitalize_sentences(text)
        elif casing_profile == "subtitle_friendly":
            text = _capitalize_sentences(text)
            seg["subtitle_lines"] = _split_subtitle_lines(text)

        seg["processed_text"] = text

    return segments


def _normalize_punctuation(text: str) -> str:
    """Normalisera unicode-punktering till ASCII-ekvivalenter."""
    replacements = {
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2026": "...",  # ellipsis
        "\u00a0": " ",  # non-breaking space
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _capitalize_sentences(text: str) -> str:
    """Capitalize forsta bokstaven i varje mening."""
    # Matcha efter meningsslut (. ! ?) foljt av mellanslag
    result = re.sub(
        r'(^|[.!?]\s+)(\w)',
        lambda m: m.group(1) + m.group(2).upper(),
        text,
    )
    # Saker att forsta tecknet ar versalt
    if result and result[0].isalpha():
        result = result[0].upper() + result[1:]
    return result


def _split_subtitle_lines(text: str, max_chars: int = 42, max_lines: int = 2) -> List[str]:
    """Dela upp text i undertextrader med max tecken och rader."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        if len(test_line) <= max_chars:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
            if len(lines) >= max_lines:
                # Lagg resten pa sista raden
                lines[-1] = f"{lines[-1]} {current_line}"
                current_line = ""
                remaining = " ".join(words[words.index(word) + 1:])
                if remaining:
                    lines[-1] = f"{lines[-1]} {remaining}"
                break

    if current_line:
        if len(lines) >= max_lines:
            lines[-1] = f"{lines[-1]} {current_line}"
        else:
            lines.append(current_line)

    return lines[:max_lines]
