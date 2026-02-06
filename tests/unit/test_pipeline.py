"""Tests for src/pipeline.py — phase 1 and phase 2 runners."""
import os
import pytest
from src.pipeline import run_phase1, run_phase2
from src.database import init_db, get_status_counts, insert_followers


FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")
SAMPLE_CSV = os.path.join(FIXTURES, "sample_followers.csv")


def _mock_fetcher(handle, profile_url):
    return {
        "follower_count": 500,
        "following_count": 100,
        "post_count": 30,
        "bio": f"Bio for {handle}",
        "website": None,
        "is_verified": False,
        "is_private": False,
        "is_business": False,
    }


# ── 7.1 Phase 1 ───────────────────────────────────────────────────
class TestRunPhase1:
    def test_inserts_all_followers(self, tmp_path):
        db = str(tmp_path / "test.db")
        result = run_phase1(SAMPLE_CSV, db)
        assert result["inserted"] == 5

    def test_all_pending(self, tmp_path):
        db = str(tmp_path / "test.db")
        run_phase1(SAMPLE_CSV, db)
        counts = get_status_counts(db)
        assert counts.get("pending") == 5

    def test_idempotent(self, tmp_path):
        db = str(tmp_path / "test.db")
        r1 = run_phase1(SAMPLE_CSV, db)
        r2 = run_phase1(SAMPLE_CSV, db)
        assert r1["inserted"] == 5
        assert r2["inserted"] == 0

    def test_returns_dict(self, tmp_path):
        db = str(tmp_path / "test.db")
        result = run_phase1(SAMPLE_CSV, db)
        assert isinstance(result, dict)
        assert "inserted" in result


# ── 7.2 Phase 2 ───────────────────────────────────────────────────
class TestRunPhase2:
    def test_processes_all_pending(self, tmp_path):
        db = str(tmp_path / "test.db")
        run_phase1(SAMPLE_CSV, db)
        result = run_phase2(db, _mock_fetcher)
        assert result["total_completed"] == 5
        assert result["total_errors"] == 0
        counts = get_status_counts(db)
        assert counts.get("completed") == 5

    def test_no_pending_returns_zero(self, tmp_path):
        db = str(tmp_path / "test.db")
        init_db(db)
        result = run_phase2(db, _mock_fetcher)
        assert result["batches_run"] == 0

    def test_returns_dict_with_expected_keys(self, tmp_path):
        db = str(tmp_path / "test.db")
        run_phase1(SAMPLE_CSV, db)
        result = run_phase2(db, _mock_fetcher)
        assert "batches_run" in result
        assert "total_completed" in result
        assert "total_errors" in result
        assert "stopped" in result
