#!/usr/bin/env python3
"""
Whisper Svenska REST API & WebSocket Server
Optimerad for Mac M4 Pro med dual-backend:
- faster-whisper (CTranslate2, CPU, int8) for accurate-profil
- mlx-whisper (Metal GPU, float16) for ultra_realtime/fast-profiler

Funktioner:
- REST API for filuppladdning och transkribering
- WebSocket API for realtidsstreaming
- Word-level timestamps och confidence heuristics
- Retry-endpoint for batch worker re-transkribering
- Stod for KBLab/kb-whisper modeller
- Tre transkriptionsprofiler: ultra_realtime, fast, accurate
"""
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import asyncio
import tempfile
import os
from pathlib import Path
import json
import base64
import time
import logging
from contextlib import asynccontextmanager

from faster_whisper import WhisperModel

# ============================================================================
# KONFIGURATION
# ============================================================================

API_VERSION = "4.0.0"
DEFAULT_MODEL = os.environ.get("WHISPER_MODEL", "KBLab/kb-whisper-medium")
DEFAULT_LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "sv")
BEAM_SIZE = int(os.environ.get("WHISPER_BEAM_SIZE", "5"))
VAD_FILTER = os.environ.get("WHISPER_VAD_FILTER", "true").lower() == "true"
DEVICE = os.environ.get("WHISPER_DEVICE", "auto")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

# Feature flags
ENABLE_MLX_REALTIME = os.environ.get("ENABLE_MLX_REALTIME", "false").lower() == "true"
ENABLE_GPU = os.environ.get("ENABLE_GPU", "false").lower() == "true"
MLX_MODEL_PATH = os.environ.get("MLX_MODEL_PATH", os.path.expanduser("~/whisper-models"))

logger = logging.getLogger("whisper-svenska")

# ============================================================================
# PROFIL-KONFIGURATION
# ============================================================================

PROFILE_CONFIG = {
    "ultra_realtime": {
        "model": "KBLab/kb-whisper-small",
        "backend": "mlx",
        "compute_type": "float16",
        "beam_size": 1,
        "chunk_ms": 1000,
        "description": "Lagsta latens (~1s), Metal GPU, beam=1",
    },
    "fast": {
        "model": "KBLab/kb-whisper-small",
        "backend": "mlx",
        "compute_type": "float16",
        "beam_size": 5,
        "chunk_ms": 1000,
        "description": "Lag latens, Metal GPU, beam=5",
    },
    "accurate": {
        "model": "KBLab/kb-whisper-medium",
        "backend": "faster_whisper",
        "compute_type": "int8",
        "beam_size": 5,
        "chunk_ms": 3000,
        "description": "Hog kvalitet, CPU int8, beam=5",
    },
    "highest_quality": {
        "model": "KBLab/kb-whisper-large",
        "backend": "faster_whisper",
        "compute_type": "int8",
        "beam_size": 5,
        "chunk_ms": 3000,
        "description": "Hogsta kvalitet, large-modell, CPU int8, beam=5",
    },
}

DEFAULT_PROFILE = "accurate"

# ============================================================================
# MODELL-CACHE (lazy loading, dual-backend)
# ============================================================================

_fw_cache: Dict[str, WhisperModel] = {}
_mlx_cache: Dict[str, Any] = {}  # mlx_whisper module loaded lazily
_mlx_module = None  # lazy import


def _get_mlx_module():
    """Lazy import av mlx_whisper — undviker ImportError om ej installerat."""
    global _mlx_module
    if _mlx_module is None:
        try:
            import mlx_whisper
            _mlx_module = mlx_whisper
            logger.info("mlx_whisper importerat OK")
        except ImportError:
            logger.warning("mlx_whisper ej installerat — MLX-backend otillgangligt")
            _mlx_module = False  # Mark as unavailable
    return _mlx_module if _mlx_module is not False else None


def _get_mlx_model_path(model_name: str) -> str:
    """Bygg lokal sokvag for MLX-konverterad modell.

    T.ex. KBLab/kb-whisper-small → ~/whisper-models/kb-whisper-small-mlx/
    """
    short_name = model_name.split("/")[-1]
    return os.path.join(MLX_MODEL_PATH, f"{short_name}-mlx")


def _get_fw_model(model_name: str) -> WhisperModel:
    """Ladda faster-whisper modell fran cache eller skapa ny."""
    if model_name not in _fw_cache:
        logger.info(f"Laddar faster-whisper modell: {model_name} (device={DEVICE}, compute={COMPUTE_TYPE})")
        _fw_cache[model_name] = WhisperModel(
            model_name,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
        )
        logger.info(f"faster-whisper {model_name} laddad.")
    return _fw_cache[model_name]


def _mlx_available() -> bool:
    """Kolla om MLX-backend ar tillgangligt."""
    if not ENABLE_MLX_REALTIME:
        return False
    mlx = _get_mlx_module()
    return mlx is not None


# ============================================================================
# CONFIDENCE HEURISTICS
# ============================================================================

def _is_low_confidence(segment) -> bool:
    """Bedom om ett segment har lag kvalitet baserat pa Whisper-attribut.

    Troskelvarden fran original Whisper-pappret.
    Ren aritmetik pa redan beraknade attribut — noll extra latens.
    """
    if segment.avg_logprob < -1.0:
        return True  # modell osaker
    if segment.compression_ratio > 2.4:
        return True  # repetitivt/hallucinerat
    if segment.no_speech_prob > 0.6:
        return True  # tystnad tolkad som tal
    if segment.words:
        low = sum(1 for w in segment.words if w.probability < 0.3)
        if low / len(segment.words) > 0.3:
            return True  # >30% svaga ord
    return False


def _is_low_confidence_dict(seg: dict) -> bool:
    """Samma heuristik som _is_low_confidence men for dict-segment (MLX)."""
    avg_lp = seg.get("avg_logprob")
    if avg_lp is not None and avg_lp < -1.0:
        return True
    comp_r = seg.get("compression_ratio")
    if comp_r is not None and comp_r > 2.4:
        return True
    nsp = seg.get("no_speech_prob")
    if nsp is not None and nsp > 0.6:
        return True
    words = seg.get("words", [])
    if words:
        low = sum(1 for w in words if w.get("probability", 1.0) < 0.3)
        if low / len(words) > 0.3:
            return True
    return False


def _format_segment(segment) -> dict:
    """Formatera ett faster-whisper segment till JSON-response.

    Inkluderar word-level timestamps och confidence-metadata.
    Bakatkampatibelt — nya falt ar valfria tillagg.
    """
    words = []
    if segment.words:
        for w in segment.words:
            words.append({
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "word": w.word,
                "probability": round(w.probability, 4),
            })

    return {
        "start": round(segment.start, 3),
        "end": round(segment.end, 3),
        "text": segment.text.strip(),
        "words": words,
        "avg_logprob": round(segment.avg_logprob, 4),
        "compression_ratio": round(segment.compression_ratio, 4),
        "no_speech_prob": round(segment.no_speech_prob, 4),
        "low_confidence": _is_low_confidence(segment),
    }


def _format_mlx_segment(seg: dict) -> dict:
    """Formatera ett mlx-whisper segment till JSON-response.

    mlx_whisper returnerar dicts, inte objekt — anpassa faltnamn.
    """
    words = []
    for w in seg.get("words", []):
        words.append({
            "start": round(w.get("start", 0), 3),
            "end": round(w.get("end", 0), 3),
            "word": w.get("word", ""),
            "probability": round(w.get("probability", 0), 4),
        })

    avg_lp = seg.get("avg_logprob")
    comp_r = seg.get("compression_ratio")
    nsp = seg.get("no_speech_prob")

    return {
        "start": round(seg.get("start", 0), 3),
        "end": round(seg.get("end", 0), 3),
        "text": seg.get("text", "").strip(),
        "words": words,
        "avg_logprob": round(avg_lp, 4) if avg_lp is not None else None,
        "compression_ratio": round(comp_r, 4) if comp_r is not None else None,
        "no_speech_prob": round(nsp, 4) if nsp is not None else None,
        "low_confidence": _is_low_confidence_dict(seg),
    }


# ============================================================================
# NOISE / HALLUCINATION FILTER
# ============================================================================

import re

_NOISE_RE = re.compile(r'^[\s\.\!\?\,\;\:\-\—\–\…\'\"\«\»\(\)\[\]]*$')


def _is_noise_text(text: str) -> bool:
    """Return True if text is only punctuation/whitespace — not real speech."""
    return bool(_NOISE_RE.match(text))


def _filter_noise_segments(segments: list) -> list:
    """Remove segments that are pure noise (punctuation-only, hallucinated)."""
    filtered = []
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        if _is_noise_text(text):
            continue
        # Skip segments where all words have very low probability
        words = seg.get("words", [])
        if words and all(w.get("probability", 0) < 0.01 for w in words):
            continue
        filtered.append(seg)
    return filtered


# ============================================================================
# TRANSKRIPTIONS-DISPATCHER
# ============================================================================

def _transcribe_faster_whisper(path: str, language: str, beam_size: int, model_name: str) -> dict:
    """Transkribera med faster-whisper backend (CPU int8)."""
    model = _get_fw_model(model_name)

    segments_iter, info = model.transcribe(
        path,
        language=language,
        beam_size=beam_size,
        vad_filter=VAD_FILTER,
        word_timestamps=True,
    )

    segments = []
    full_text_parts = []
    for segment in segments_iter:
        seg_dict = _format_segment(segment)
        segments.append(seg_dict)
        full_text_parts.append(seg_dict["text"])

    duration = segments[-1]["end"] if segments else None

    return {
        "text": " ".join(full_text_parts),
        "language": info.language,
        "segments": segments,
        "duration": duration,
        "language_probability": round(info.language_probability, 4) if info.language_probability else None,
        "backend": "faster_whisper",
    }


def _transcribe_mlx(path: str, language: str, beam_size: int, model_name: str) -> dict:
    """Transkribera med mlx-whisper backend (Metal GPU float16)."""
    mlx = _get_mlx_module()
    if mlx is None:
        raise RuntimeError("mlx-whisper ej tillgangligt")

    mlx_path = _get_mlx_model_path(model_name)

    # Kolla om lokal MLX-modell finns, annars prova HF-repo direkt
    if os.path.isdir(mlx_path):
        model_ref = mlx_path
    else:
        logger.warning(f"Lokal MLX-modell saknas: {mlx_path}, provar HF-repo: {model_name}")
        model_ref = model_name

    # mlx_whisper does not support beam search yet — use greedy (temperature=0)
    result = mlx.transcribe(
        path,
        path_or_hf_repo=model_ref,
        language=language,
        word_timestamps=True,
        fp16=True,
        temperature=0.0,
    )

    raw_segments = []
    for seg in result.get("segments", []):
        raw_segments.append(_format_mlx_segment(seg))

    # mlx_whisper has no VAD — filter noise/hallucinated segments
    segments = _filter_noise_segments(raw_segments)

    full_text_parts = [s["text"] for s in segments]
    duration = segments[-1]["end"] if segments else None

    return {
        "text": " ".join(full_text_parts),
        "language": result.get("language", language),
        "segments": segments,
        "duration": duration,
        "language_probability": None,
        "backend": "mlx",
    }


def _transcribe_with_profile(path: str, profile: str, language: str) -> dict:
    """Dispatcha transkribering till ratt backend baserat pa profil.

    Om MLX ar otillgangligt faller ultra_realtime/fast tillbaka pa faster-whisper.
    """
    if profile not in PROFILE_CONFIG:
        logger.warning(f"Okand profil '{profile}', faller tillbaka pa '{DEFAULT_PROFILE}'")
        profile = DEFAULT_PROFILE

    config = PROFILE_CONFIG[profile]
    model_name = config["model"]
    beam_size = config["beam_size"]
    backend = config["backend"]

    t0 = time.perf_counter()

    # Dispatcha till ratt backend
    if backend == "mlx" and _mlx_available():
        result = _transcribe_mlx(path, language, beam_size, model_name)
    else:
        if backend == "mlx":
            logger.info(f"MLX ej tillgangligt for profil '{profile}', faller tillbaka pa faster-whisper")
        result = _transcribe_faster_whisper(path, language, beam_size, model_name)

    elapsed = time.perf_counter() - t0
    result["profile"] = profile
    result["inference_time"] = round(elapsed, 3)
    logger.info(f"Profil={profile} backend={result['backend']} tid={elapsed:.3f}s")

    return result


# ============================================================================
# FASTAPI APP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ladda standardmodell vid serverstart."""
    logger.info(f"Laddar standardmodell (faster-whisper): {DEFAULT_MODEL}")
    _get_fw_model(DEFAULT_MODEL)
    if ENABLE_MLX_REALTIME:
        logger.info(f"MLX realtime aktiverat — modeller laddas vid forsta request (lazy)")
    logger.info("Whisper Svenska API redo!")
    yield
    _fw_cache.clear()
    _mlx_cache.clear()


app = FastAPI(
    title="Whisper Svenska API",
    description="REST och WebSocket API for svensk transkribering med dual-backend (faster-whisper + mlx-whisper)",
    version=API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST/RESPONSE MODELLER
# ============================================================================

class TranscribeResponse(BaseModel):
    text: str
    language: str
    segments: Optional[List[dict]] = None
    duration: Optional[float] = None
    language_probability: Optional[float] = None
    backend: Optional[str] = None
    profile: Optional[str] = None
    inference_time: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    model: str
    mlx_enabled: bool = False
    gpu_enabled: bool = False
    loaded_models: Dict[str, List[str]] = {}
    memory_info: Optional[Dict[str, Any]] = None


class RetryRequest(BaseModel):
    """Request for re-transkribering av specifikt tidsintervall."""
    audio_url: Optional[str] = None
    audio_base64: Optional[str] = None
    start: float
    end: float
    beam_size: int = 10
    model: str = "KBLab/kb-whisper-medium"
    language: str = "sv"


# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {"status": "ok", "version": API_VERSION, "model": DEFAULT_MODEL}


@app.get("/health", response_model=HealthResponse)
async def health():
    memory_info = None
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        memory_info = {"rss_mb": round(usage.ru_maxrss / 1024, 1)}
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        version=API_VERSION,
        model=DEFAULT_MODEL,
        mlx_enabled=ENABLE_MLX_REALTIME,
        gpu_enabled=ENABLE_GPU,
        loaded_models={
            "faster_whisper": list(_fw_cache.keys()),
            "mlx": list(_mlx_cache.keys()),
        },
        memory_info=memory_info,
    )


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_file(
    file: UploadFile = File(...),
    language: str = DEFAULT_LANGUAGE,
    include_timestamps: bool = True,
    profile: str = Query(default=DEFAULT_PROFILE),
):
    """Transkribera en ljudfil till text.

    Returnerar text, segments med word-level timestamps och confidence-metadata.
    Profil valjer backend och parametrar (ultra_realtime, fast, accurate).
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or "audio.wav").suffix) as tmp:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Tom fil")
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = _transcribe_with_profile(tmp_path, profile, language)

        return TranscribeResponse(
            text=result["text"],
            language=result["language"],
            segments=result["segments"] if include_timestamps else None,
            duration=result["duration"],
            language_probability=result["language_probability"],
            backend=result["backend"],
            profile=result["profile"],
            inference_time=result["inference_time"],
        )
    finally:
        os.unlink(tmp_path)


@app.post("/transcribe/batch")
async def transcribe_batch(files: List[UploadFile] = File(...)):
    """Transkribera flera filer samtidigt."""
    results = []
    for file in files:
        try:
            result = await transcribe_file(file, language=DEFAULT_LANGUAGE)
            results.append({
                "filename": file.filename,
                "success": True,
                "data": result.model_dump(),
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e),
            })
    return {"results": results}


@app.post("/transcribe/retry")
async def transcribe_retry(request: RetryRequest):
    """Re-transkribera ett tidsintervall med hogre kvalitet.

    Anropas av batch worker for att forbattra svaga segment.
    Stodjer hogre beam_size och alternativ modell (t.ex. large).
    Alltid faster-whisper — retry ar batch-kontext, inte realtime.
    """
    if not request.audio_base64:
        raise HTTPException(status_code=400, detail="audio_base64 kravs")

    model = _get_fw_model(request.model)

    audio_bytes = base64.b64decode(request.audio_base64)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments_iter, info = model.transcribe(
            tmp_path,
            language=request.language,
            beam_size=request.beam_size,
            vad_filter=VAD_FILTER,
            word_timestamps=True,
        )

        segments = []
        for segment in segments_iter:
            if segment.end < request.start:
                continue
            if segment.start > request.end:
                break
            segments.append(_format_segment(segment))

        return {
            "segments": segments,
            "language": info.language,
            "language_probability": round(info.language_probability, 4) if info.language_probability else None,
            "model": request.model,
            "beam_size": request.beam_size,
        }
    finally:
        os.unlink(tmp_path)


@app.post("/warmup")
async def warmup_model(
    profile: str = Query(default=DEFAULT_PROFILE),
):
    """Pre-load the model for a given profile.

    Returns status indicating whether the model is ready.
    Useful for frontend to trigger model loading before recording starts.
    """
    if profile not in PROFILE_CONFIG:
        raise HTTPException(status_code=400, detail=f"Okand profil: {profile}")

    config = PROFILE_CONFIG[profile]
    model_name = config["model"]
    backend = config["backend"]

    t0 = time.perf_counter()

    try:
        if backend == "mlx" and _mlx_available():
            mlx_path = _get_mlx_model_path(model_name)
            if not os.path.isdir(mlx_path):
                return {"status": "error", "profile": profile, "detail": f"MLX-modell saknas: {mlx_path}"}
            mlx = _get_mlx_module()
            if mlx is None:
                return {"status": "error", "profile": profile, "detail": "mlx-whisper ej tillgangligt"}
            # Actually load the model by running a silent dummy transcription
            if model_name not in _mlx_cache:
                logger.info(f"Warmup: laddar MLX-modell '{model_name}' for profil '{profile}'...")
                silence = os.path.join(tempfile.gettempdir(), "_warmup_silence.wav")
                if not os.path.exists(silence):
                    import struct
                    # Generate 0.1s of silence as minimal WAV (16-bit PCM, 16kHz mono)
                    sr, dur = 16000, 0.1
                    n_samples = int(sr * dur)
                    raw = struct.pack(f"<{n_samples}h", *([0] * n_samples))
                    with open(silence, "wb") as f:
                        f.write(b"RIFF")
                        f.write(struct.pack("<I", 36 + len(raw)))
                        f.write(b"WAVEfmt ")
                        f.write(struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16))
                        f.write(b"data")
                        f.write(struct.pack("<I", len(raw)))
                        f.write(raw)
                mlx.transcribe(silence, path_or_hf_repo=mlx_path, language="sv", fp16=True, temperature=0.0)
                _mlx_cache[model_name] = True
                logger.info(f"Warmup: MLX-modell '{model_name}' laddad for profil '{profile}'")
            else:
                logger.info(f"Warmup: MLX-modell '{model_name}' redan laddad (cache hit)")
        else:
            # faster-whisper: eagerly load into cache
            _get_fw_model(model_name)
            logger.info(f"Warmup: faster-whisper modell '{model_name}' laddad for profil '{profile}'")

        elapsed = time.perf_counter() - t0
        return {
            "status": "ready",
            "profile": profile,
            "model": model_name,
            "backend": backend if (backend != "mlx" or _mlx_available()) else "faster_whisper",
            "load_time": round(elapsed, 3),
        }
    except Exception as e:
        logger.error(f"Warmup misslyckades for profil '{profile}': {e}")
        raise HTTPException(status_code=500, detail=f"Warmup misslyckades: {e}")


# ============================================================================
# WEBSOCKET API
# ============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_json(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)


manager = ConnectionManager()


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """WebSocket endpoint for realtidsstreaming.

    Protokoll:
    1. Client skickar: {"action": "start", "language": "sv", "profile": "fast"}
    2. Client streamar audio: {"action": "audio", "data": "<base64>"}
    3. Server svarar: {"type": "transcript", "text": "...", "is_final": true/false, "profile": "fast"}
    4. Client stanger: {"action": "stop"}
    """
    await manager.connect(websocket)

    import numpy as np

    audio_buffer = []
    is_streaming = False
    language = DEFAULT_LANGUAGE
    profile = DEFAULT_PROFILE

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "start":
                language = data.get("language", DEFAULT_LANGUAGE)
                profile = data.get("profile", DEFAULT_PROFILE)
                is_streaming = True
                audio_buffer = []
                await manager.send_json({
                    "type": "status",
                    "message": "Streaming startad",
                    "profile": profile,
                }, websocket)

            elif action == "audio" and is_streaming:
                audio_base64 = data.get("data")
                audio_bytes = base64.b64decode(audio_base64)
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_buffer.append(audio_array.astype(np.float32) / 32768.0)

            elif action == "process":
                if audio_buffer:
                    audio_data = np.concatenate(audio_buffer)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                        import soundfile as sf
                        sf.write(tmp.name, audio_data, 16000)
                        tmp_path = tmp.name

                    try:
                        result = _transcribe_with_profile(tmp_path, profile, language)
                        await manager.send_json({
                            "type": "transcript",
                            "text": result["text"],
                            "is_final": True,
                            "segments": result["segments"],
                            "profile": result["profile"],
                            "backend": result["backend"],
                            "inference_time": result["inference_time"],
                        }, websocket)
                    finally:
                        os.unlink(tmp_path)

                    audio_buffer = []

            elif action == "stop":
                is_streaming = False
                audio_buffer = []
                await manager.send_json({"type": "status", "message": "Streaming stoppad"}, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.get("/models")
async def list_models():
    profiles = {}
    for name, cfg in PROFILE_CONFIG.items():
        profiles[name] = {
            "model": cfg["model"],
            "backend": cfg["backend"],
            "compute_type": cfg["compute_type"],
            "beam_size": cfg["beam_size"],
            "chunk_ms": cfg["chunk_ms"],
            "description": cfg["description"],
            "available": cfg["backend"] != "mlx" or _mlx_available(),
        }

    return {
        "profiles": profiles,
        "default_profile": DEFAULT_PROFILE,
        "models": [
            {"name": "KBLab/kb-whisper-small", "description": "Snabbast, lagst kvalitet"},
            {"name": "KBLab/kb-whisper-medium", "description": "Balanserad (rekommenderad)"},
            {"name": "KBLab/kb-whisper-large", "description": "Hogsta kvalitet, langsammare"},
        ],
        "current": DEFAULT_MODEL,
        "loaded": {
            "faster_whisper": list(_fw_cache.keys()),
            "mlx": list(_mlx_cache.keys()),
        },
        "mlx_enabled": ENABLE_MLX_REALTIME,
        "gpu_enabled": ENABLE_GPU,
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Whisper Svenska API Server v" + API_VERSION)
    print("=" * 60)
    print(f"Modell:    {DEFAULT_MODEL}")
    print(f"Beam size: {BEAM_SIZE}")
    print(f"VAD:       {VAD_FILTER}")
    print(f"Device:    {DEVICE}")
    print(f"Compute:   {COMPUTE_TYPE}")
    print(f"MLX:       {ENABLE_MLX_REALTIME}")
    print(f"GPU:       {ENABLE_GPU}")
    print(f"MLX path:  {MLX_MODEL_PATH}")
    print("=" * 60)
    print("Profiler:")
    for name, cfg in PROFILE_CONFIG.items():
        avail = "OK" if cfg["backend"] != "mlx" or ENABLE_MLX_REALTIME else "FALLBACK→CPU"
        print(f"  {name:20s} {cfg['backend']:15s} beam={cfg['beam_size']} chunk={cfg['chunk_ms']}ms [{avail}]")
    print("=" * 60)
    print(f"REST API:   http://localhost:8123/docs")
    print(f"WebSocket:  ws://localhost:8123/ws/transcribe")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8123, log_level="info")
