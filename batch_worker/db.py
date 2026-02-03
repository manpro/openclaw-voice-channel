"""SQLite job store via aiosqlite."""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

DB_PATH = os.environ.get("JOBS_DB_PATH", "jobs.db")


async def init_db():
    """Skapa jobs-tabellen om den inte finns."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                input_data TEXT,
                result_data TEXT,
                current_step TEXT DEFAULT '',
                error TEXT DEFAULT ''
            )
        """)
        await db.commit()


async def create_job(input_data: dict) -> str:
    """Skapa ett nytt jobb och returnera dess id."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO jobs (id, status, created_at, updated_at, input_data) VALUES (?, ?, ?, ?, ?)",
            (job_id, "pending", now, now, json.dumps(input_data)),
        )
        await db.commit()
    return job_id


async def get_job(job_id: str) -> Optional[dict]:
    """Hamta ett jobb via id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "input_data": json.loads(row["input_data"]) if row["input_data"] else None,
            "result_data": json.loads(row["result_data"]) if row["result_data"] else None,
            "current_step": row["current_step"],
            "error": row["error"],
        }


async def update_job(
    job_id: str,
    *,
    status: Optional[str] = None,
    current_step: Optional[str] = None,
    result_data: Optional[dict] = None,
    error: Optional[str] = None,
):
    """Uppdatera ett jobb."""
    now = datetime.now(timezone.utc).isoformat()
    sets = ["updated_at = ?"]
    params = [now]

    if status is not None:
        sets.append("status = ?")
        params.append(status)
    if current_step is not None:
        sets.append("current_step = ?")
        params.append(current_step)
    if result_data is not None:
        sets.append("result_data = ?")
        params.append(json.dumps(result_data))
    if error is not None:
        sets.append("error = ?")
        params.append(error)

    params.append(job_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        await db.commit()
