"""Whisper Batch Worker — FastAPI app, port 8400.

Separat process som kor post-processing pipeline pa transkriptioner.
"""
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from batch_worker.config import load_config
from batch_worker.db import init_db
from batch_worker.job_queue import JobQueue
from batch_worker.routers.jobs import router as jobs_router

logger = logging.getLogger("batch-worker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Init SQLite och ladda config vid start."""
    config = load_config()
    app.state.config = config
    await init_db()
    logger.info("Batch worker redo. Pipeline config:")
    logger.info(f"  retry={config.retry_enabled}, lang_detect={config.language_detect_enabled}")
    logger.info(f"  text_processing={config.text_processing_enabled}, pii={config.pii_flagging_enabled}")
    logger.info(f"  summary={config.summary_enabled}, diarization={config.diarization_enabled}")
    logger.info(f"  whisper_api_url={config.whisper_api_url}")
    logger.info(f"  max_concurrent_jobs={config.max_concurrent_jobs}")

    job_queue = JobQueue(max_concurrent=config.max_concurrent_jobs)
    app.state.job_queue = job_queue
    await job_queue.start()

    yield

    await job_queue.shutdown()


app = FastAPI(
    title="Whisper Batch Worker",
    description="Post-processing pipeline for Whisper transkriptioner",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "batch-worker", "version": "1.0.0"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Whisper Batch Worker v1.0.0")
    print("=" * 40)
    print("http://localhost:8400/docs")
    print("=" * 40)
    uvicorn.run(app, host="0.0.0.0", port=8400, log_level="info")
