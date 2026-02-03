import httpx
import subprocess
import tempfile
import os

WHISPER_URL = "http://mini.local:8123/transcribe"
TIMEOUT = 120.0


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    profile: str = "accurate",
) -> dict:
    """Send audio to Whisper API and return full response dict.

    Args:
        audio_bytes: Raw audio data.
        filename: Original filename (used to detect format).
        profile: Transcription profile (ultra_realtime, fast, accurate).

    Returns:
        Dict with text, language, segments, backend, profile, etc.
    """
    # If the audio is WebM/Opus (from browser recording), convert to WAV
    if filename.endswith(".webm") or filename.endswith(".ogg"):
        audio_bytes = await convert_to_wav(audio_bytes)
        filename = "audio.wav"

    url = f"{WHISPER_URL}?profile={profile}"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        files = {"file": (filename, audio_bytes, "audio/wav")}
        response = await client.post(url, files=files)
        response.raise_for_status()
        return response.json()


WHISPER_WARMUP_URL = "http://mini.local:8123/warmup"


async def warmup_profile(profile: str = "accurate") -> dict:
    """Ask Whisper server to pre-load the model for a given profile.

    Returns dict with status, profile, model, backend, load_time.
    """
    url = f"{WHISPER_WARMUP_URL}?profile={profile}"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(url)
        response.raise_for_status()
        return response.json()


async def convert_to_wav(audio_bytes: bytes) -> bytes:
    """Convert audio bytes to WAV using ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as infile:
        infile.write(audio_bytes)
        infile_path = infile.name

    outfile_path = infile_path.replace(".webm", ".wav")

    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", infile_path,
                "-ar", "16000", "-ac", "1", "-f", "wav",
                outfile_path,
            ],
            capture_output=True,
            check=True,
        )
        with open(outfile_path, "rb") as f:
            return f.read()
    finally:
        for p in (infile_path, outfile_path):
            if os.path.exists(p):
                os.unlink(p)
