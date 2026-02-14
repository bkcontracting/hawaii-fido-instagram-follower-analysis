"""Tests for src/batch_orchestrator.py — batch processing with retry logic."""
import os
import datetime
import sqlite3
from unittest.mock import patch, MagicMock
import pytest
from src.database import init_db, insert_followers, update_follower, get_status_counts, get_pending
from src.batch_orchestrator import create_batch, process_batch, run_with_retries, run_all, _connect


def _setup_db(tmp_path, count=5):
    """Create a DB with `count` pending followers."""
    db = str(tmp_path / "test.db")
    init_db(db)
    followers = [
        {"handle": f"user_{i}", "display_name": f"User {i}",
         "profile_url": f"https://instagram.com/user_{i}/"}
        for i in range(count)
    ]
    insert_followers(db, followers)
    return db


def _mock_fetcher(handle, profile_url):
    """Return a deterministic enriched profile dict."""
    return {
        "follower_count": 1000,
        "following_count": 200,
        "post_count": 60,
        "bio": f"Bio for {handle}",
        "website": None,
        "is_verified": False,
        "is_private": False,
        "is_business": False,
    }


def _failing_fetcher(handle, profile_url):
    """Always raises an exception."""
    raise Exception(f"Failed to fetch {handle}")


# ── 6.1 create_batch ──────────────────────────────────────────────
class TestCreateBatch:
    def test_claims_pending_records(self, tmp_path):
        db = _setup_db(tmp_path, count=5)
        batch = create_batch(db)
        assert len(batch) == 5
        counts = get_status_counts(db)
        assert counts.get("processing") == 5
        assert counts.get("pending", 0) == 0

    def test_respects_batch_size(self, tmp_path):
        db = _setup_db(tmp_path, count=30)
        os.environ["BATCH_SIZE"] = "10"
        try:
            import src.config
            import importlib
            importlib.reload(src.config)
            batch = create_batch(db)
            assert len(batch) == 10
        finally:
            del os.environ["BATCH_SIZE"]
            importlib.reload(src.config)

    def test_returns_empty_when_exhausted(self, tmp_path):
        db = _setup_db(tmp_path, count=0)
        batch = create_batch(db)
        assert batch == []

    def test_crash_recovery_resets_stale_processing(self, tmp_path):
        db = _setup_db(tmp_path, count=3)
        # Mark all as processing with old timestamp
        old_time = (datetime.datetime.now() - datetime.timedelta(minutes=10)).isoformat()
        for i in range(3):
            update_follower(db, f"user_{i}", {
                "status": "processing",
                "processed_at": old_time,
            })
        counts = get_status_counts(db)
        assert counts.get("processing") == 3

        batch = create_batch(db)
        # Should have reset stale records to pending, then claimed them
        assert len(batch) == 3

    def test_does_not_reset_recent_processing(self, tmp_path):
        db = _setup_db(tmp_path, count=3)
        # Mark all as processing with recent timestamp
        recent_time = datetime.datetime.now().isoformat()
        for i in range(3):
            update_follower(db, f"user_{i}", {
                "status": "processing",
                "processed_at": recent_time,
            })
        batch = create_batch(db)
        # No pending records, recent processing should NOT be reset
        assert batch == []

    def test_batch_returns_dicts(self, tmp_path):
        db = _setup_db(tmp_path, count=2)
        batch = create_batch(db)
        assert isinstance(batch[0], dict)
        assert "handle" in batch[0]


# ── 6.2 process_batch ─────────────────────────────────────────────
class TestProcessBatch:
    def test_completes_all_with_good_fetcher(self, tmp_path):
        db = _setup_db(tmp_path, count=3)
        batch = create_batch(db)
        result = process_batch(db, batch, _mock_fetcher)
        assert result["completed"] == 3
        assert result["errors"] == 0
        counts = get_status_counts(db)
        assert counts.get("completed") == 3

    def test_errors_dont_stop_batch(self, tmp_path):
        db = _setup_db(tmp_path, count=3)
        batch = create_batch(db)

        call_count = [0]
        def partial_fail(handle, url):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("fetch failed")
            return _mock_fetcher(handle, url)

        result = process_batch(db, batch, partial_fail)
        assert result["completed"] == 2
        assert result["errors"] == 1

    def test_all_fail(self, tmp_path):
        db = _setup_db(tmp_path, count=3)
        batch = create_batch(db)
        result = process_batch(db, batch, _failing_fetcher)
        assert result["completed"] == 0
        assert result["errors"] == 3
        counts = get_status_counts(db)
        assert counts.get("error") == 3

    def test_sets_classification_fields(self, tmp_path):
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)
        process_batch(db, batch, _mock_fetcher)
        # Verify enriched fields were stored
        from src.database import _connect
        conn = _connect(db)
        row = conn.execute("SELECT * FROM followers WHERE handle='user_0'").fetchone()
        conn.close()
        row_dict = dict(row)
        assert row_dict["category"] is not None
        assert row_dict["priority_score"] is not None
        assert row_dict["is_hawaii"] is not None
        assert row_dict["status"] == "completed"

    def test_stores_error_message(self, tmp_path):
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)
        process_batch(db, batch, _failing_fetcher)
        from src.database import _connect
        conn = _connect(db)
        row = conn.execute("SELECT * FROM followers WHERE handle='user_0'").fetchone()
        conn.close()
        assert dict(row)["error_message"] is not None
        assert "Failed to fetch" in dict(row)["error_message"]

    def test_private_account_gets_private_status(self, tmp_path):
        """Private accounts should get status='private' per PRD."""
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)

        def private_fetcher(handle, url):
            return {**_mock_fetcher(handle, url), "is_private": True}

        result = process_batch(db, batch, private_fetcher)
        assert result["completed"] == 1
        from src.database import _connect
        conn = _connect(db)
        row = conn.execute("SELECT * FROM followers WHERE handle='user_0'").fetchone()
        conn.close()
        assert dict(row)["status"] == "private"
        assert dict(row)["is_private"] == 1

    def test_not_found_page_state_marks_error(self, tmp_path):
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)

        def not_found_fetcher(handle, url):
            return {**_mock_fetcher(handle, url), "page_state": "not_found"}

        result = process_batch(db, batch, not_found_fetcher)
        assert result["completed"] == 0
        assert result["errors"] == 1

        from src.database import _connect
        conn = _connect(db)
        row = conn.execute("SELECT status, error_message FROM followers WHERE handle='user_0'").fetchone()
        conn.close()
        row_dict = dict(row)
        assert row_dict["status"] == "error"
        assert row_dict["error_message"] == "not_found"

    def test_suspended_page_state_marks_error(self, tmp_path):
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)

        def suspended_fetcher(handle, url):
            return {**_mock_fetcher(handle, url), "page_state": "suspended"}

        result = process_batch(db, batch, suspended_fetcher)
        assert result["completed"] == 0
        assert result["errors"] == 1

        from src.database import _connect
        conn = _connect(db)
        row = conn.execute("SELECT status, error_message FROM followers WHERE handle='user_0'").fetchone()
        conn.close()
        row_dict = dict(row)
        assert row_dict["status"] == "error"
        assert row_dict["error_message"] == "suspended"

    def test_rate_limited_page_state_not_completed(self, tmp_path):
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)

        def rate_limited_fetcher(handle, url):
            return {**_mock_fetcher(handle, url), "page_state": "rate_limited"}

        result = process_batch(db, batch, rate_limited_fetcher)
        assert result["completed"] == 0
        assert result["errors"] == 1

        from src.database import _connect
        conn = _connect(db)
        row = conn.execute("SELECT status, error_message FROM followers WHERE handle='user_0'").fetchone()
        conn.close()
        row_dict = dict(row)
        assert row_dict["status"] == "error"
        assert row_dict["error_message"] == "rate_limited"

    def test_login_required_page_state_not_completed(self, tmp_path):
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)

        def login_required_fetcher(handle, url):
            return {**_mock_fetcher(handle, url), "page_state": "login_required"}

        result = process_batch(db, batch, login_required_fetcher)
        assert result["completed"] == 0
        assert result["errors"] == 1

        from src.database import _connect
        conn = _connect(db)
        row = conn.execute("SELECT status, error_message FROM followers WHERE handle='user_0'").fetchone()
        conn.close()
        row_dict = dict(row)
        assert row_dict["status"] == "error"
        assert row_dict["error_message"] == "login_required"


# ── 6.3 run_with_retries ──────────────────────────────────────────
class TestRunWithRetries:
    def test_no_retries_needed(self, tmp_path):
        db = _setup_db(tmp_path, count=3)
        batch = create_batch(db)
        result = run_with_retries(db, batch, _mock_fetcher)
        assert result["completed"] == 3
        assert result["errors"] == 0
        assert result["retries_used"] == 0
        assert result["exhausted"] == False

    def test_retries_on_error(self, tmp_path):
        db = _setup_db(tmp_path, count=3)
        batch = create_batch(db)

        attempts = [0]
        def fail_then_succeed(handle, url):
            attempts[0] += 1
            if attempts[0] <= 3:  # First 3 calls fail (initial batch)
                raise Exception("transient error")
            return _mock_fetcher(handle, url)

        result = run_with_retries(db, batch, fail_then_succeed)
        assert result["completed"] == 3
        assert result["errors"] == 0
        assert result["retries_used"] >= 1

    def test_exhausts_retries(self, tmp_path):
        db = _setup_db(tmp_path, count=2)
        batch = create_batch(db)
        result = run_with_retries(db, batch, _failing_fetcher)
        assert result["completed"] == 0
        assert result["errors"] == 2
        assert result["exhausted"] == True

    def test_max_retries_respected(self, tmp_path):
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)
        os.environ["MAX_RETRIES"] = "2"
        try:
            import src.config
            import importlib
            importlib.reload(src.config)

            call_count = [0]
            def count_calls(handle, url):
                call_count[0] += 1
                raise Exception("always fail")

            run_with_retries(db, batch, count_calls)
            # MAX_RETRIES=2 means 2 total attempts (including initial)
            assert call_count[0] == 2
        finally:
            del os.environ["MAX_RETRIES"]
            importlib.reload(src.config)


# ── 6.4 run_all ───────────────────────────────────────────────────
class TestRunAll:
    def test_processes_all_pending(self, tmp_path):
        db = _setup_db(tmp_path, count=5)
        result = run_all(db, _mock_fetcher)
        assert result["total_completed"] == 5
        assert result["total_errors"] == 0
        assert result["batches_run"] >= 1
        counts = get_status_counts(db)
        assert counts.get("completed") == 5

    def test_stops_on_exhausted_batch(self, tmp_path):
        db = _setup_db(tmp_path, count=3)
        result = run_all(db, _failing_fetcher)
        assert result["stopped"] == True
        assert result["reason"] == "batch_exhausted"

    def test_no_pending_returns_zero_batches(self, tmp_path):
        db = _setup_db(tmp_path, count=0)
        result = run_all(db, _mock_fetcher)
        assert result["batches_run"] == 0
        assert result["total_completed"] == 0

    def test_multiple_batches(self, tmp_path):
        db = _setup_db(tmp_path, count=25)
        os.environ["BATCH_SIZE"] = "10"
        try:
            import src.config
            import importlib
            importlib.reload(src.config)
            result = run_all(db, _mock_fetcher)
            assert result["batches_run"] == 3
            assert result["total_completed"] == 25
        finally:
            del os.environ["BATCH_SIZE"]
            importlib.reload(src.config)

    def test_completed_records_untouched(self, tmp_path):
        db = _setup_db(tmp_path, count=5)
        # Complete 3 manually
        for i in range(3):
            update_follower(db, f"user_{i}", {"status": "completed"})
        result = run_all(db, _mock_fetcher)
        assert result["total_completed"] == 2
        counts = get_status_counts(db)
        assert counts.get("completed") == 5


# ── Direct _connect test ─────────────────────────────────────────

class TestConnectHelper:
    def test_connect_returns_connection(self, tmp_path):
        db = str(tmp_path / "connect.db")
        conn = _connect(db)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_connect_uses_row_factory(self, tmp_path):
        db = str(tmp_path / "factory.db")
        conn = _connect(db)
        assert conn.row_factory is sqlite3.Row
        conn.close()


# ── Additional process_batch page_state coverage ─────────────────

class TestProcessBatchPageStates:
    def test_unknown_page_state_raises_error(self, tmp_path):
        """Unknown page_state (not normal/not_found/suspended/rate_limited/login_required)
        should raise RuntimeError caught by the except block."""
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)

        def unknown_state_fetcher(handle, url):
            return {**_mock_fetcher(handle, url), "page_state": "weird_state"}

        result = process_batch(db, batch, unknown_state_fetcher)
        assert result["errors"] == 1
        from src.database import _connect as db_connect
        conn = db_connect(db)
        row = conn.execute("SELECT error_message FROM followers WHERE handle='user_0'").fetchone()
        conn.close()
        assert "unknown_page_state" in dict(row)["error_message"]

    def test_page_state_none_defaults_to_normal(self, tmp_path):
        """page_state=None should default to 'normal' via `or 'normal'`."""
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)

        def none_state_fetcher(handle, url):
            return {**_mock_fetcher(handle, url), "page_state": None}

        result = process_batch(db, batch, none_state_fetcher)
        assert result["completed"] == 1
        assert result["errors"] == 0

    def test_rate_limited_error_message_in_db(self, tmp_path):
        """rate_limited page_state should store 'rate_limited' as error_message."""
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)

        def rate_limited_fetcher(handle, url):
            return {**_mock_fetcher(handle, url), "page_state": "rate_limited"}

        process_batch(db, batch, rate_limited_fetcher)
        from src.database import _connect as db_connect
        conn = db_connect(db)
        row = conn.execute("SELECT error_message FROM followers WHERE handle='user_0'").fetchone()
        conn.close()
        assert dict(row)["error_message"] == "rate_limited"

    def test_login_required_error_message_in_db(self, tmp_path):
        """login_required page_state should store 'login_required' as error_message."""
        db = _setup_db(tmp_path, count=1)
        batch = create_batch(db)

        def login_required_fetcher(handle, url):
            return {**_mock_fetcher(handle, url), "page_state": "login_required"}

        process_batch(db, batch, login_required_fetcher)
        from src.database import _connect as db_connect
        conn = db_connect(db)
        row = conn.execute("SELECT error_message FROM followers WHERE handle='user_0'").fetchone()
        conn.close()
        assert dict(row)["error_message"] == "login_required"
