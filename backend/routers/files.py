import os
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

TRANSCRIPTIONS_DIR = "/app/transcriptions"


class SaveRequest(BaseModel):
    text: str
    filename: str | None = None


@router.get("/files")
async def list_files():
    """List saved transcription files."""
    os.makedirs(TRANSCRIPTIONS_DIR, exist_ok=True)
    files = []
    for name in sorted(os.listdir(TRANSCRIPTIONS_DIR), reverse=True):
        if name.endswith(".txt"):
            path = os.path.join(TRANSCRIPTIONS_DIR, name)
            stat = os.stat(path)
            files.append({
                "name": name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    return {"files": files}


@router.post("/files")
async def save_file(req: SaveRequest):
    """Save a transcription to a text file."""
    os.makedirs(TRANSCRIPTIONS_DIR, exist_ok=True)

    if req.filename:
        name = req.filename if req.filename.endswith(".txt") else req.filename + ".txt"
    else:
        name = datetime.now().strftime("transkription_%Y%m%d_%H%M%S.txt")

    # Sanitize filename
    name = os.path.basename(name)
    path = os.path.join(TRANSCRIPTIONS_DIR, name)

    with open(path, "w", encoding="utf-8") as f:
        f.write(req.text)

    return {"name": name, "path": path}


@router.get("/files/{filename}")
async def get_file(filename: str):
    """Get contents of a saved transcription."""
    path = os.path.join(TRANSCRIPTIONS_DIR, os.path.basename(filename))
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Filen hittades inte")
    with open(path, "r", encoding="utf-8") as f:
        return {"name": filename, "text": f.read()}


@router.delete("/files/{filename}")
async def delete_file(filename: str):
    """Delete a saved transcription."""
    path = os.path.join(TRANSCRIPTIONS_DIR, os.path.basename(filename))
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Filen hittades inte")
    os.unlink(path)
    return {"deleted": filename}
