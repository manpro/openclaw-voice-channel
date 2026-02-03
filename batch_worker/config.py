"""Pipeline configuration via environment variables."""
import os
from dataclasses import dataclass, field


@dataclass
class PipelineConfig:
    """Feature flags och konfiguration for batch worker pipeline.

    Alla varden kan overridas via environment variables.
    """
    # Feature 3: Retry low-confidence segments
    retry_enabled: bool = True
    retry_beam_size: int = 10
    retry_with_large: bool = False

    # Feature 4: Language detection
    language_detect_enabled: bool = True

    # Feature 5: Text processing
    text_processing_enabled: bool = True
    casing_profile: str = "verbatim"  # verbatim | meeting_notes | subtitle_friendly
    normalize_punctuation: bool = True

    # Feature 6: PII flagging
    pii_flagging_enabled: bool = True

    # Feature 7: LLM summary
    summary_enabled: bool = False  # Disabled by default, kräver LLM

    # URLs
    whisper_api_url: str = "http://localhost:8123"
    llm_url: str = ""
    llm_model: str = ""

    # HTTP client settings
    http_timeout: float = 60.0
    http_retries: int = 3
    http_retry_backoff: float = 1.0

    # Concurrency
    max_concurrent_jobs: int = 1

    # Diarization (batch-only, off by default)
    diarization_enabled: bool = False


def load_config() -> PipelineConfig:
    """Ladda konfiguration fran environment variables."""

    def _bool(key: str, default: bool) -> bool:
        val = os.environ.get(key, "")
        if not val:
            return default
        return val.lower() in ("true", "1", "yes")

    return PipelineConfig(
        retry_enabled=_bool("FEATURE_RETRY", True),
        retry_beam_size=int(os.environ.get("RETRY_BEAM_SIZE", "10")),
        retry_with_large=_bool("FEATURE_RETRY_LARGE", False),
        language_detect_enabled=_bool("FEATURE_LANG_DETECT", True),
        text_processing_enabled=_bool("FEATURE_TEXT_PROCESSING", True),
        casing_profile=os.environ.get("CASING_PROFILE", "verbatim"),
        normalize_punctuation=_bool("NORMALIZE_PUNCTUATION", True),
        pii_flagging_enabled=_bool("FEATURE_PII", True),
        summary_enabled=_bool("FEATURE_SUMMARY", False),
        whisper_api_url=os.environ.get("WHISPER_API_URL", "http://localhost:8123"),
        llm_url=os.environ.get("LLM_URL", ""),
        llm_model=os.environ.get("LLM_MODEL", ""),
        http_timeout=float(os.environ.get("HTTP_TIMEOUT", "60.0")),
        http_retries=int(os.environ.get("HTTP_RETRIES", "3")),
        http_retry_backoff=float(os.environ.get("HTTP_RETRY_BACKOFF", "1.0")),
        max_concurrent_jobs=int(os.environ.get("MAX_CONCURRENT_JOBS", "1")),
        diarization_enabled=_bool("FEATURE_DIARIZATION", False),
    )
