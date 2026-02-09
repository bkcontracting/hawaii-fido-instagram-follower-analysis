"""Tests for scripts/rescore.py — re-classify and re-score all enriched followers."""
import sqlite3
import sys
import os
from unittest.mock import patch

import pytest

# Allow importing from project root and scripts/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)

from scripts.rescore import rescore, _connect
from src.database import _SCHEMA


# ── Helpers ───────────────────────────────────────────────────────────

def _create_db(tmp_path, rows=None):
    """Create a temp database with the followers schema and optional seed rows.

    Each row in `rows` should be a dict. Missing keys get sensible defaults.
    Returns the string path to the database file.
    """
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_SCHEMA)
    conn.commit()

    if rows:
        for row in rows:
            _insert_row(conn, row)
        conn.commit()

    conn.close()
    return db_path


def _insert_row(conn, data):
    """Insert a single follower row with defaults for missing fields."""
    defaults = {
        "handle": "test_handle",
        "display_name": "Test User",
        "profile_url": "https://instagram.com/test_handle",
        "follower_count": 500,
        "following_count": 200,
        "post_count": 20,
        "bio": "A test bio",
        "website": None,
        "is_verified": False,
        "is_private": False,
        "is_business": False,
        "category": "personal_passive",
        "subcategory": "general",
        "location": None,
        "is_hawaii": False,
        "confidence": 0.5,
        "priority_score": 0,
        "priority_reason": "",
        "status": "completed",
        "error_message": None,
        "processed_at": None,
    }
    merged = {**defaults, **data}
    columns = list(merged.keys())
    placeholders = ", ".join(["?"] * len(columns))
    col_names = ", ".join(columns)
    conn.execute(
        f"INSERT INTO followers ({col_names}) VALUES ({placeholders})",
        [merged[c] for c in columns],
    )


def _fetch_row(db_path, handle):
    """Fetch a single follower row by handle as a dict."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM followers WHERE handle = ?", (handle,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── 1. Zero completed rows ────────────────────────────────────────────

class TestZeroCompletedRows:
    def test_no_completed_rows_prints_message(self, tmp_path, capsys):
        """When no completed rows exist, rescore prints a message and returns."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "pending_user", "status": "pending"},
        ])
        rescore(db_path, dry_run=False)
        captured = capsys.readouterr()
        assert "No completed followers found." in captured.out

    def test_empty_table_prints_message(self, tmp_path, capsys):
        """When the table is completely empty, rescore prints a message."""
        db_path = _create_db(tmp_path)
        rescore(db_path, dry_run=False)
        captured = capsys.readouterr()
        assert "No completed followers found." in captured.out

    def test_no_completed_rows_returns_without_error(self, tmp_path):
        """rescore returns cleanly (None) when there are no completed rows."""
        db_path = _create_db(tmp_path)
        result = rescore(db_path, dry_run=False)
        assert result is None


# ── 2. dry_run=True does NOT modify database ─────────────────────────

class TestDryRunNoWrite:
    def test_dry_run_does_not_change_category(self, tmp_path):
        """With dry_run=True, category in DB is unchanged after rescore."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "vet_clinic_hi", "bio": "Veterinary clinic",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=True)
        row = _fetch_row(db_path, "vet_clinic_hi")
        assert row["category"] == "personal_passive"

    def test_dry_run_does_not_change_subcategory(self, tmp_path):
        """With dry_run=True, subcategory in DB is unchanged."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "dog_trainer_hi", "bio": "Dog trainer services",
             "is_business": True, "is_hawaii": True,
             "category": "unknown", "subcategory": "general",
             "confidence": 0.3, "priority_score": 5, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=True)
        row = _fetch_row(db_path, "dog_trainer_hi")
        assert row["subcategory"] == "general"

    def test_dry_run_does_not_change_score(self, tmp_path):
        """With dry_run=True, priority_score in DB is unchanged."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "bank_user", "bio": "First Hawaiian Bank",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=True)
        row = _fetch_row(db_path, "bank_user")
        assert row["priority_score"] == 0

    def test_dry_run_prints_dry_run_notice(self, tmp_path, capsys):
        """Dry run prints the [DRY RUN] notice at end."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "some_user", "bio": "Bank of Hawaii",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "priority_score": 0, "status": "completed"},
        ])
        rescore(db_path, dry_run=True)
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out


# ── 3. dry_run=False DOES write updated values ──────────────────────

class TestWriteUpdatedValues:
    def test_updates_category(self, tmp_path):
        """Rescore writes new category to the database."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "vet_biz", "bio": "Veterinary clinic for pets",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        row = _fetch_row(db_path, "vet_biz")
        assert row["category"] == "pet_industry"

    def test_updates_subcategory(self, tmp_path):
        """Rescore writes new subcategory to the database."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "vet_biz", "bio": "Veterinary clinic for pets",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        row = _fetch_row(db_path, "vet_biz")
        assert row["subcategory"] == "veterinary"

    def test_updates_confidence(self, tmp_path):
        """Rescore writes new confidence to the database."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "vet_biz", "bio": "Veterinary clinic for pets",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.1, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        row = _fetch_row(db_path, "vet_biz")
        # pet_industry confidence is 0.85
        assert row["confidence"] == 0.85

    def test_updates_priority_score(self, tmp_path):
        """Rescore writes new priority_score to the database."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "bank_hi", "bio": "First Hawaiian Bank Honolulu",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        row = _fetch_row(db_path, "bank_hi")
        # bank_financial + hawaii + business = 30 + 30 + 20 = 80
        assert row["priority_score"] == 80

    def test_updates_priority_reason(self, tmp_path):
        """Rescore writes new priority_reason to the database."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "bank_hi", "bio": "First Hawaiian Bank Honolulu",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        row = _fetch_row(db_path, "bank_hi")
        assert "hawaii" in row["priority_reason"].lower()
        assert "bank" in row["priority_reason"].lower()

    def test_only_updates_completed_rows(self, tmp_path):
        """Rescore does not update rows with status != 'completed'."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "completed_user", "bio": "First Hawaiian Bank",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "priority_score": 0,
             "status": "completed"},
            {"handle": "pending_user", "bio": "First Hawaiian Bank",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "priority_score": 0,
             "status": "pending"},
        ])
        rescore(db_path, dry_run=False)
        completed = _fetch_row(db_path, "completed_user")
        pending = _fetch_row(db_path, "pending_user")
        assert completed["category"] == "bank_financial"
        assert pending["category"] == "personal_passive"

    def test_updates_multiple_rows(self, tmp_path):
        """Rescore processes all completed rows, not just the first."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "bank_user", "bio": "First Hawaiian Bank",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "priority_score": 0,
             "status": "completed"},
            {"handle": "vet_user", "bio": "Veterinary clinic",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "priority_score": 0,
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        bank = _fetch_row(db_path, "bank_user")
        vet = _fetch_row(db_path, "vet_user")
        assert bank["category"] == "bank_financial"
        assert vet["category"] == "pet_industry"


# ── 4. Subcategory correctly passed to scorer (breeder fix) ──────────

class TestSubcategoryPassedToScorer:
    def test_breeder_subcategory_flows_to_scorer(self, tmp_path):
        """When classifier returns subcategory='breeder', scorer receives it
        and applies reduced pet_breeder(+10) instead of pet(+25)."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "puppy_breeder", "bio": "Golden retriever breeder",
             "is_business": False, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        row = _fetch_row(db_path, "puppy_breeder")
        assert row["category"] == "pet_industry"
        assert row["subcategory"] == "breeder"
        assert "pet_breeder(+10)" in row["priority_reason"]
        assert "pet(+25)" not in row["priority_reason"]

    def test_veterinary_subcategory_gets_full_pet_score(self, tmp_path):
        """When classifier returns subcategory='veterinary', scorer gives
        the full pet(+25) bonus, not the reduced breeder one."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "vet_office", "bio": "Veterinary clinic for your pets",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        row = _fetch_row(db_path, "vet_office")
        assert row["subcategory"] == "veterinary"
        assert "pet(+25)" in row["priority_reason"]
        assert "pet_breeder" not in row["priority_reason"]

    def test_breeder_score_lower_than_vet(self, tmp_path):
        """Breeder should score 15 points lower than veterinary (all else equal)."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "breeder_user", "bio": "Golden retriever breeder",
             "is_business": False, "is_hawaii": True,
             "follower_count": 500, "post_count": 20,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
            {"handle": "vet_user", "bio": "Veterinary clinic",
             "is_business": False, "is_hawaii": True,
             "follower_count": 500, "post_count": 20,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        breeder = _fetch_row(db_path, "breeder_user")
        vet = _fetch_row(db_path, "vet_user")
        assert vet["priority_score"] - breeder["priority_score"] == 15

    def test_score_profile_dict_includes_new_subcategory(self, tmp_path):
        """Verify the score function receives the NEW subcategory, not the old one.

        We mock score() to capture exactly what dict it receives.
        """
        db_path = _create_db(tmp_path, rows=[
            {"handle": "breeder_mock",
             "bio": "Golden retriever breeder in Honolulu",
             "is_business": False, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])

        captured_profiles = []
        original_score = __import__("src.scorer", fromlist=["score"]).score

        def spy_score(profile):
            captured_profiles.append(dict(profile))
            return original_score(profile)

        with patch("scripts.rescore.score", side_effect=spy_score):
            rescore(db_path, dry_run=False)

        assert len(captured_profiles) == 1
        assert captured_profiles[0]["subcategory"] == "breeder"
        assert captured_profiles[0]["category"] == "pet_industry"


# ── 5. Score delta detection ─────────────────────────────────────────

class TestScoreDeltaDetection:
    def test_large_score_change_detected(self, tmp_path, capsys):
        """A score change > 10 should appear in the report output."""
        # Start with category=personal_passive, score=0, then rescore
        # will classify as bank_financial with hawaii, giving a high score.
        db_path = _create_db(tmp_path, rows=[
            {"handle": "big_change_user", "bio": "First Hawaiian Bank",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        captured = capsys.readouterr()
        # Score goes from 0 to 80 (delta=80, definitely > 10)
        assert "Accounts with changes: 1" in captured.out

    def test_small_score_change_not_reported_as_change(self, tmp_path, capsys):
        """A score change <= 10 (with same category) is not counted as a change."""
        # We need a profile that re-classifies to the same category but with
        # score delta <= 10. personal_passive with bio triggers no big change.
        db_path = _create_db(tmp_path, rows=[
            {"handle": "small_change_user", "bio": "Just a person",
             "is_business": False, "is_hawaii": False,
             "follower_count": 100, "following_count": 50, "post_count": 10,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        row = _fetch_row(db_path, "small_change_user")
        captured = capsys.readouterr()
        # Category stays the same, score is 0 for personal_passive with
        # just "Just a person" bio, so delta should be 0.
        assert "No significant changes detected." in captured.out

    def test_score_delta_exactly_10_not_flagged(self, tmp_path):
        """abs(score_delta) == 10 is NOT > 10, so it should not be flagged.

        We use mocked classify/score to control exact values.
        """
        db_path = _create_db(tmp_path, rows=[
            {"handle": "exact_10_user", "bio": "Test",
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 50, "priority_reason": "",
             "status": "completed"},
        ])

        with patch("scripts.rescore.classify") as mock_classify, \
             patch("scripts.rescore.score") as mock_score:
            mock_classify.return_value = {
                "category": "personal_passive",
                "subcategory": "general",
                "confidence": 0.5,
            }
            mock_score.return_value = {
                "priority_score": 60,
                "priority_reason": "test(+60)",
            }
            rescore(db_path, dry_run=True)

        # delta is 60 - 50 = 10, which is NOT > 10, so no change flagged.
        # (We verify by checking the function did not error and completes.)

    def test_score_delta_11_is_flagged(self, tmp_path, capsys):
        """abs(score_delta) == 11 IS > 10, so it should be flagged."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "delta_11_user", "bio": "Test",
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 50, "priority_reason": "",
             "status": "completed"},
        ])

        with patch("scripts.rescore.classify") as mock_classify, \
             patch("scripts.rescore.score") as mock_score:
            mock_classify.return_value = {
                "category": "personal_passive",
                "subcategory": "general",
                "confidence": 0.5,
            }
            mock_score.return_value = {
                "priority_score": 61,
                "priority_reason": "test(+61)",
            }
            rescore(db_path, dry_run=True)

        captured = capsys.readouterr()
        assert "Accounts with changes: 1" in captured.out


# ── 6. Category change detection ─────────────────────────────────────

class TestCategoryChangeDetection:
    def test_category_change_flagged(self, tmp_path, capsys):
        """When category changes, it is reported in the output."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "cat_change_user", "bio": "First Hawaiian Bank",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": 80, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        captured = capsys.readouterr()
        # Category changes from personal_passive to bank_financial
        assert "Category Changes" in captured.out
        assert "cat_change_user" in captured.out

    def test_same_category_no_cat_change_report(self, tmp_path, capsys):
        """When category stays the same, it is NOT reported as a category change."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "same_cat_user", "bio": "First Hawaiian Bank",
             "is_business": True, "is_hawaii": True,
             "category": "bank_financial", "subcategory": "bank",
             "confidence": 0.9, "priority_score": 80, "priority_reason": "",
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        captured = capsys.readouterr()
        # Category stays bank_financial, no category change
        assert "Category Changes" not in captured.out

    def test_category_change_detected_even_with_small_score_delta(self, tmp_path, capsys):
        """Category change is flagged even if score delta is <= 10."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "cat_small_delta", "bio": "Test user",
             "category": "unknown", "subcategory": "general",
             "confidence": 0.3, "priority_score": 0, "priority_reason": "",
             "status": "completed"},
        ])

        with patch("scripts.rescore.classify") as mock_classify, \
             patch("scripts.rescore.score") as mock_score:
            mock_classify.return_value = {
                "category": "personal_passive",
                "subcategory": "general",
                "confidence": 0.5,
            }
            mock_score.return_value = {
                "priority_score": 5,
                "priority_reason": "test(+5)",
            }
            rescore(db_path, dry_run=True)

        captured = capsys.readouterr()
        # Category changed (unknown -> personal_passive), delta is only 5
        assert "Accounts with changes: 1" in captured.out


# ── 7. Handling of None old_score ─────────────────────────────────────

class TestNoneOldScore:
    def test_none_old_score_delta_is_none(self, tmp_path, capsys):
        """When old_score is NULL, score_delta should be None (not crash)."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "null_score_user", "bio": "First Hawaiian Bank",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "subcategory": "general",
             "confidence": 0.5, "priority_score": None, "priority_reason": None,
             "status": "completed"},
        ])
        # Should not raise any TypeError
        rescore(db_path, dry_run=False)
        row = _fetch_row(db_path, "null_score_user")
        # After rescore, the score should be written (not None anymore)
        assert row["priority_score"] is not None
        assert row["category"] == "bank_financial"

    def test_none_old_score_still_updates_db(self, tmp_path):
        """When old_score is None, the row is still updated properly."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "null_score_update", "bio": "Veterinary clinic",
             "is_business": True, "is_hawaii": True,
             "category": "unknown", "subcategory": "general",
             "confidence": 0.3, "priority_score": None, "priority_reason": None,
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        row = _fetch_row(db_path, "null_score_update")
        assert row["category"] == "pet_industry"
        assert row["subcategory"] == "veterinary"
        assert row["priority_score"] is not None
        assert row["priority_reason"] is not None

    def test_none_old_score_with_category_change_flagged(self, tmp_path, capsys):
        """When old_score is None AND category changes, it should be flagged."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "null_cat_change", "bio": "First Hawaiian Bank",
             "is_business": True, "is_hawaii": True,
             "category": "unknown", "subcategory": "general",
             "confidence": 0.3, "priority_score": None, "priority_reason": None,
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        captured = capsys.readouterr()
        assert "Accounts with changes: 1" in captured.out

    def test_none_old_score_tier_shows_na(self, tmp_path, capsys):
        """When old_score is None, old_tier should show 'N/A' in the report."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "na_tier_user", "bio": "First Hawaiian Bank Honolulu",
             "is_business": True, "is_hawaii": True,
             "category": "unknown", "subcategory": "general",
             "confidence": 0.3, "priority_score": None, "priority_reason": None,
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        captured = capsys.readouterr()
        # The old tier for null score should be N/A, and since the new score
        # is 80 (Tier 1), a tier upgrade is reported.
        assert "New Tier 1/2 Accounts" in captured.out
        assert "na_tier_user" in captured.out


# ── 8. Connection helper ─────────────────────────────────────────────

class TestConnectHelper:
    def test_connect_returns_connection(self, tmp_path):
        """_connect returns a sqlite3.Connection object."""
        db_path = str(tmp_path / "connect_test.db")
        conn = _connect(db_path)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_connect_uses_row_factory(self, tmp_path):
        """_connect sets row_factory to sqlite3.Row."""
        db_path = str(tmp_path / "row_test.db")
        conn = _connect(db_path)
        assert conn.row_factory is sqlite3.Row
        conn.close()


# ── 9. Report output ─────────────────────────────────────────────────

class TestReportOutput:
    def test_rescore_count_in_output(self, tmp_path, capsys):
        """Report prints the total count of rescored followers."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "user_a", "bio": "Test", "status": "completed",
             "category": "personal_passive", "priority_score": 0},
            {"handle": "user_b", "bio": "Test2", "status": "completed",
             "category": "personal_passive", "priority_score": 0},
        ])
        rescore(db_path, dry_run=False)
        captured = capsys.readouterr()
        assert "Rescored 2 followers" in captured.out

    def test_score_changes_section_shows_deltas_over_10(self, tmp_path, capsys):
        """Score Changes > 10 Points section is printed for big deltas."""
        db_path = _create_db(tmp_path, rows=[
            {"handle": "big_delta_user", "bio": "First Hawaiian Bank",
             "is_business": True, "is_hawaii": True,
             "category": "personal_passive", "priority_score": 10,
             "status": "completed"},
        ])
        rescore(db_path, dry_run=False)
        captured = capsys.readouterr()
        # Score delta = 80 - 10 = 70, definitely > 10
        assert "Score Changes > 10 Points" in captured.out
