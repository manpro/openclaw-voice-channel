"""Context-profiler for tolkningslagret.

Varje profil ar en konfiguration som styr vilka pipeline-steg som kors
och vilken LLM-prompt som anvands for sammanfattning.
"""

CONTEXT_PROFILES = {
    "raw": {
        "label": "Ratt transkript",
        "description": "Ingen efterbearbetning, ratt text fran ASR",
        "summary": False,
        "pii": False,
        "diarization": False,
        "text_processing": False,
    },
    "meeting": {
        "label": "Mote",
        "description": "Motesanteckningar med beslut och actions",
        "summary": True,
        "prompt": (
            "Du ar en assistent som sammanfattar motesanteckningar pa svenska.\n\n"
            "Identifiera:\n"
            "1. Viktiga beslut som fattades\n"
            "2. Action items (vem ska gora vad)\n"
            "3. Nasta steg\n\n"
            "Ge en kort sammanfattning (max 5 meningar) och lista alla action items.\n\n"
            "Transkription:\n{text}\n\n"
            'Svara i JSON-format: {{"summary": "...", "action_items": ["..."]}}'
        ),
        "pii": True,
        "diarization": True,
        "text_processing": True,
        "casing": "meeting_notes",
    },
    "brainstorm": {
        "label": "Brainstorm",
        "description": "Lista och gruppera ideer fran brainstorming",
        "summary": True,
        "prompt": (
            "Du ar en assistent som sammanfattar brainstorming-sessioner pa svenska.\n\n"
            "Identifiera alla ideer som diskuterats och gruppera dem i kategorier.\n"
            "Lista varje ide kort och koncist.\n\n"
            "Transkription:\n{text}\n\n"
            'Svara i JSON-format: {{"summary": "...", "action_items": ["ide 1", "ide 2", ...]}}'
        ),
        "pii": False,
        "diarization": False,
        "text_processing": True,
        "casing": "meeting_notes",
    },
    "journal": {
        "label": "Dagbok",
        "description": "Dagboksanteckningar och reflektioner",
        "summary": True,
        "prompt": (
            "Du ar en assistent som sammanfattar dagboksanteckningar pa svenska.\n\n"
            "Fanga:\n"
            "1. Huvudsakliga reflektioner och kanslor\n"
            "2. Viktiga handelser\n"
            "3. Insikter och lardomar\n\n"
            "Skriv sammanfattningen i forsta person.\n\n"
            "Transkription:\n{text}\n\n"
            'Svara i JSON-format: {{"summary": "...", "action_items": []}}'
        ),
        "pii": True,
        "diarization": False,
        "text_processing": True,
        "casing": "meeting_notes",
    },
    "tech_notes": {
        "label": "Tekniska anteckningar",
        "description": "Teknisk dokumentation, bevara facktermer",
        "summary": True,
        "prompt": (
            "Du ar en assistent som sammanfattar tekniska anteckningar pa svenska.\n\n"
            "Bevara alla tekniska termer, kodnamn och akronymer exakt som de namnts.\n"
            "Strukturera sammanfattningen med tydliga punkter.\n\n"
            "Transkription:\n{text}\n\n"
            'Svara i JSON-format: {{"summary": "...", "action_items": []}}'
        ),
        "pii": False,
        "diarization": False,
        "text_processing": False,
        "casing": "verbatim",
    },
}


def get_profile(name: str) -> dict | None:
    """Hamta en context-profil by namn."""
    return CONTEXT_PROFILES.get(name)


def list_profiles() -> list[dict]:
    """Lista alla tillgangliga context-profiler."""
    return [
        {"name": name, "label": p["label"], "description": p["description"]}
        for name, p in CONTEXT_PROFILES.items()
    ]
