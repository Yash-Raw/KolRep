import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Coroutine, Optional
import uuid

logger = logging.getLogger("voicerep.desktop.job_manager")


@dataclass
class LocalJob:
    id: str
    job_type: str
    status: str = "queued"  # queued, processing, completed, failed, cancelled
    progress: float = 0.0  # 0.0 to 100.0
    stage: str = "Queued"
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    _task: Optional[asyncio.Task] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "job_type": self.job_type,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class LocalJobManager:
    """
    Redis-free in-process task execution engine.
    Ensures safe concurrency for Apple Silicon unified memory during local model synthesis.
    """

    def __init__(self, max_concurrent_jobs: int = 1) -> None:
        self.max_concurrent_jobs = max_concurrent_jobs
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._jobs: dict[str, LocalJob] = {}
        self._lock = asyncio.Lock()
        self._is_shutting_down = False

    def get_job(self, job_id: str) -> Optional[LocalJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        sorted_jobs = sorted(
            self._jobs.values(), key=lambda j: j.created_at, reverse=True
        )
        return [j.to_dict() for j in sorted_jobs[:limit]]

    def update_progress(self, job_id: str, progress: float, stage: str = "") -> None:
        job = self._jobs.get(job_id)
        if job and job.status == "processing":
            job.progress = max(0.0, min(100.0, progress))
            if stage:
                job.stage = stage

    async def cancel_job(self, job_id: str) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if job.status in ("completed", "failed", "cancelled"):
                return False

            job.status = "cancelled"
            job.completed_at = datetime.now(timezone.utc)
            job.stage = "Cancelled by user"

            if job._task and not job._task.done():
                job._task.cancel()
                try:
                    await asyncio.wait([job._task], timeout=2.0)
                except Exception:
                    pass
            logger.info(f"Job {job_id} cancelled.")
            return True

    def submit_job(
        self,
        job_id: str,
        job_type: str,
        coro_func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> LocalJob:
        if self._is_shutting_down:
            raise RuntimeError("Job manager is shutting down. Cannot accept new jobs.")

        job = LocalJob(id=job_id, job_type=job_type)
        self._jobs[job_id] = job

        async def _runner():
            async with self._semaphore:
                if job.status == "cancelled":
                    return

                job.status = "processing"
                job.started_at = datetime.now(timezone.utc)
                job.stage = "Starting synthesis..."
                logger.info(f"Starting job {job_id} ({job_type})")

                try:
                    res = await coro_func(job_id, *args, **kwargs)
                    if job.status != "cancelled":
                        job.status = "completed"
                        job.progress = 100.0
                        job.stage = "Complete"
                        job.result = res if isinstance(res, dict) else {"data": str(res)}
                        job.completed_at = datetime.now(timezone.utc)
                        logger.info(f"Job {job_id} completed successfully.")
                except asyncio.CancelledError:
                    job.status = "cancelled"
                    job.completed_at = datetime.now(timezone.utc)
                    job.stage = "Cancelled"
                    logger.info(f"Job {job_id} execution cancelled.")
                except Exception as e:
                    logger.error(f"Job {job_id} failed: {e}", exc_info=True)
                    job.status = "failed"
                    job.error = str(e)
                    job.completed_at = datetime.now(timezone.utc)
                    job.stage = f"Error: {str(e)[:100]}"

        loop = asyncio.get_running_loop()
        task = loop.create_task(_runner())
        job._task = task
        return job

    async def shutdown(self) -> None:
        """Gracefully cancels any active or pending background jobs."""
        logger.info("Shutting down LocalJobManager...")
        self._is_shutting_down = True
        active_tasks = []
        for job in self._jobs.values():
            if job.status in ("queued", "processing") and job._task and not job._task.done():
                job.status = "cancelled"
                job.completed_at = datetime.now(timezone.utc)
                job._task.cancel()
                active_tasks.append(job._task)

        if active_tasks:
            logger.info(f"Waiting for {len(active_tasks)} active jobs to cancel...")
            await asyncio.gather(*active_tasks, return_exceptions=True)
        logger.info("LocalJobManager shutdown complete.")


# Global singleton instance
local_job_manager = LocalJobManager(max_concurrent_jobs=1)
