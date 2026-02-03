"""In-process async job queue with semaphore-based concurrency.

No external dependencies (no Redis). Uses asyncio.Queue + asyncio.Semaphore.
Jobs flow: queued -> running -> completed/failed.
"""
import asyncio
import logging

from batch_worker.db import update_job
from batch_worker.pipeline.runner import run_pipeline

logger = logging.getLogger("batch-worker.queue")


class JobQueue:
    """Async job queue with bounded concurrency.

    Usage:
        q = JobQueue(max_concurrent=2)
        await q.start()         # call in lifespan startup
        await q.enqueue(...)    # non-blocking, returns immediately
        await q.shutdown()      # call in lifespan shutdown
    """

    def __init__(self, max_concurrent: int = 1):
        self._max = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def start(self):
        """Start worker loop."""
        self._running = True
        # Single dispatcher that respects semaphore
        self._workers.append(asyncio.create_task(self._dispatcher()))
        logger.info(f"Job queue started (max_concurrent={self._max})")

    async def shutdown(self):
        """Drain queue and cancel workers."""
        self._running = False
        # Signal dispatcher to exit
        await self._queue.put(None)
        for w in self._workers:
            w.cancel()
        self._workers.clear()
        logger.info("Job queue shut down")

    async def enqueue(self, job_id: str, input_data: dict, config):
        """Add a job to the queue. Updates status to 'queued'."""
        await update_job(job_id, status="queued", current_step="queued")
        await self._queue.put((job_id, input_data, config))
        qsize = self._queue.qsize()
        logger.info(f"Job {job_id} queued (queue depth: {qsize})")

    @property
    def queue_depth(self) -> int:
        return self._queue.qsize()

    async def _dispatcher(self):
        """Main loop: pull jobs from queue, run with semaphore limit."""
        while self._running:
            item = await self._queue.get()
            if item is None:
                break
            job_id, input_data, config = item
            # Acquire semaphore then run in background task
            asyncio.create_task(self._run_with_semaphore(job_id, input_data, config))

    async def _run_with_semaphore(self, job_id: str, input_data: dict, config):
        """Acquire semaphore, run pipeline, release."""
        async with self._semaphore:
            await update_job(job_id, status="running", current_step="starting")
            logger.info(f"Job {job_id} running")
            await run_pipeline(job_id, input_data, config)
