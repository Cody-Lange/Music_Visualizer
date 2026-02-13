"""In-memory job store. Replace with Redis/DB in production."""

import threading
from typing import Any


class JobStore:
    """Thread-safe in-memory job store.

    Production deployment should swap this for Redis-backed storage.
    The interface stays the same.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_job(self, job_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            self._jobs[job_id] = data

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(self, job_id: str, updates: dict[str, Any]) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(updates)

    def delete_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def list_jobs(self) -> list[str]:
        with self._lock:
            return list(self._jobs.keys())


# Singleton instance
job_store = JobStore()
