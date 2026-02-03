"""Feature 7: LLM-sammanfattning.

Anropar valfri OpenAI-kompatibel endpoint (Ollama, vLLM, Claude API).
Disabled by default (FEATURE_SUMMARY=false).

Stodjer parameteriserad prompt via prompt_template fran context-profiler.
"""
import logging
from typing import List, Optional

import httpx

logger = logging.getLogger("batch-worker.summary")

SUMMARY_TIMEOUT = 30.0
MAX_TEXT_LENGTH = 8000

_DEFAULT_PROMPT = (
    "Du ar en assistent som sammanfattar transkriptioner pa svenska.\n\n"
    "Ge en kort sammanfattning (max 3 meningar) och lista eventuella action items.\n\n"
    "Transkription:\n{text}\n\n"
    'Svara i JSON-format: {{"summary": "...", "action_items": ["..."]}}'
)


async def generate_summary(
    segments: List[dict],
    config,
    prompt_template: Optional[str] = None,
) -> Optional[dict]:
    """Generera sammanfattning och action items fran transkription.

    Args:
        segments: Lista med transkriptionssegment.
        config: Pipeline-konfiguration med llm_url och llm_model.
        prompt_template: Optional prompt-mall med {text} placeholder.
            Om None anvands default-prompten.

    Returnerar {"summary": "...", "action_items": [...]} eller None vid fel.
    """
    if not config.llm_url:
        logger.warning("LLM_URL inte konfigurerad, hoppar over sammanfattning")
        return None

    full_text = " ".join(seg.get("text", "") for seg in segments)
    if not full_text.strip():
        return None

    # Trunkera vid behov
    truncated = full_text[:MAX_TEXT_LENGTH]

    template = prompt_template or _DEFAULT_PROMPT
    prompt = template.format(text=truncated)

    try:
        async with httpx.AsyncClient(timeout=SUMMARY_TIMEOUT) as client:
            response = await client.post(
                f"{config.llm_url}/v1/chat/completions",
                json={
                    "model": config.llm_model or "default",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]

            # Forsoker parsa JSON fran LLM-svaret
            import json
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # Om LLM inte returnerade valid JSON, wrappa texten
                return {"summary": content, "action_items": []}

    except Exception as e:
        logger.error(f"LLM-sammanfattning misslyckades: {e}")
        return None
