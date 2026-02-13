"""Tests for the in-memory job store."""

import threading

from app.services.storage import JobStore


class TestJobStore:
    def setup_method(self):
        self.store = JobStore()

    def test_create_and_get(self):
        self.store.create_job("j1", {"status": "new"})
        job = self.store.get_job("j1")
        assert job is not None
        assert job["status"] == "new"

    def test_get_nonexistent_returns_none(self):
        assert self.store.get_job("nonexistent") is None

    def test_update_existing_job(self):
        self.store.create_job("j1", {"status": "new", "count": 0})
        self.store.update_job("j1", {"status": "updated", "extra": True})
        job = self.store.get_job("j1")
        assert job is not None
        assert job["status"] == "updated"
        assert job["extra"] is True
        assert job["count"] == 0  # Preserved from original

    def test_update_nonexistent_is_noop(self):
        # Should not raise
        self.store.update_job("missing", {"status": "updated"})
        assert self.store.get_job("missing") is None

    def test_delete_job(self):
        self.store.create_job("j1", {"data": 1})
        self.store.delete_job("j1")
        assert self.store.get_job("j1") is None

    def test_delete_nonexistent_is_noop(self):
        self.store.delete_job("missing")  # Should not raise

    def test_list_jobs(self):
        assert self.store.list_jobs() == []
        self.store.create_job("a", {})
        self.store.create_job("b", {})
        job_ids = self.store.list_jobs()
        assert set(job_ids) == {"a", "b"}

    def test_create_overwrites_existing(self):
        self.store.create_job("j1", {"version": 1})
        self.store.create_job("j1", {"version": 2})
        job = self.store.get_job("j1")
        assert job is not None
        assert job["version"] == 2

    def test_thread_safety(self):
        """Verify concurrent access doesn't corrupt state."""
        errors: list[Exception] = []

        def writer(job_id: str):
            try:
                for i in range(100):
                    self.store.create_job(f"{job_id}_{i}", {"val": i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(f"t{t}",)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(self.store.list_jobs()) == 400
