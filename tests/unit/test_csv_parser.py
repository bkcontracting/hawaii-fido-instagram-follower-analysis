"""Tests for src/csv_parser.py — CSV parsing with dedup, fallback, and validation."""
import os
import pytest

from src.csv_parser import parse_followers, ParseError

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------
FIXTURES = os.path.join(os.path.dirname(__file__), os.pardir, "fixtures")
SAMPLE = os.path.join(FIXTURES, "sample_followers.csv")
EDGE = os.path.join(FIXTURES, "edge_cases.csv")
INVALID = os.path.join(FIXTURES, "invalid.csv")
EMPTY = os.path.join(FIXTURES, "empty.csv")


# ===================================================================
# 1.1 — Parse: basic happy-path
# ===================================================================
class TestParseFollowers:
    """parse_followers returns list[dict] with the 3 core keys."""

    def test_returns_list(self):
        result = parse_followers(SAMPLE)
        assert isinstance(result, list)

    def test_returns_dicts_with_correct_keys(self):
        result = parse_followers(SAMPLE)
        expected_keys = {"handle", "display_name", "profile_url"}
        for row in result:
            assert set(row.keys()) == expected_keys

    def test_sample_has_five_records(self):
        result = parse_followers(SAMPLE)
        assert len(result) == 5

    def test_extra_columns_ignored(self):
        """sample_followers.csv has 7 columns; only 3 should appear."""
        result = parse_followers(SAMPLE)
        for row in result:
            assert "completeness_score" not in row
            assert "is_edge_case" not in row
            assert "edge_case_types" not in row
            assert "validation_notes" not in row

    def test_first_record_values(self):
        result = parse_followers(SAMPLE)
        first = result[0]
        assert first["handle"] == "aloha_coffee_co"
        assert first["display_name"] == "Aloha Coffee Co"
        assert first["profile_url"] == "https://www.instagram.com/aloha_coffee_co/"

    def test_reads_by_header_not_position(self):
        """Edge-cases CSV has an extra_col; parser should still work by headers."""
        result = parse_followers(EDGE)
        assert isinstance(result, list)
        for row in result:
            assert "extra_col" not in row


# ===================================================================
# 1.2 — Edge cases
# ===================================================================
class TestEdgeCases:
    """Dedup, fallback, unicode, whitespace, quoted commas."""

    def test_dedup_by_handle_first_wins(self):
        result = parse_followers(EDGE)
        dup_rows = [r for r in result if r["handle"] == "dup_handle"]
        assert len(dup_rows) == 1
        assert dup_rows[0]["display_name"] == "First Entry"

    def test_empty_display_name_falls_back_to_handle(self):
        result = parse_followers(EDGE)
        row = next(r for r in result if r["handle"] == "empty_display")
        assert row["display_name"] == "empty_display"

    def test_unicode_preserved(self):
        result = parse_followers(EDGE)
        row = next(r for r in result if r["handle"] == "unicode_test")
        assert row["display_name"] == "Hale Ku\u02bbike"

    def test_whitespace_stripped_from_handle(self):
        result = parse_followers(EDGE)
        handles = [r["handle"] for r in result]
        assert "spaces_handle" in handles
        assert "  spaces_handle  " not in handles

    def test_whitespace_stripped_from_display_name(self):
        result = parse_followers(EDGE)
        row = next(r for r in result if r["handle"] == "spaces_handle")
        assert row["display_name"] == "Spaced Name"

    def test_commas_in_quoted_fields(self):
        result = parse_followers(EDGE)
        row = next(r for r in result if r["handle"] == "quoted_handle")
        assert row["display_name"] == "Name, With Comma"

    def test_edge_cases_total_unique_count(self):
        """6 rows, but dup_handle duplicated → 5 unique records."""
        result = parse_followers(EDGE)
        assert len(result) == 5


# ===================================================================
# 1.3 — Error handling
# ===================================================================
class TestErrors:
    """ParseError, FileNotFoundError, and empty CSV."""

    def test_parse_error_is_exception(self):
        assert issubclass(ParseError, Exception)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_followers("/nonexistent/path/followers.csv")

    def test_missing_handle_column_raises_parse_error(self):
        with pytest.raises(ParseError):
            parse_followers(INVALID)

    def test_empty_csv_returns_empty_list(self):
        result = parse_followers(EMPTY)
        assert result == []
