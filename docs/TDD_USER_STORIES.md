# TDD User Stories: AFK Pipeline Refactoring

**Source PRD:** `docs/PRD.md`
**Source Plan:** `docs/AFK_PIPELINE_PLAN.md`
**Branch:** `claude/refactor-project-structure-YWohS`

Each story follows Red-Green-Refactor. Write the failing test first,
then the minimum code to pass, then clean up. Tests use `pytest` with
`tmp_path` fixtures and in-memory SQLite — never touch `data/followers.db`.

---

## Epic 1: Module Extraction (PRD Steps 1-7)

> Extract 5 standalone modules from scripts/ into src/, each with its own
> test suite. No behavior changes — pure structural moves.

---

### Story 1.0: Gitignore Pipeline Intermediary Files
**PRD Step:** 1

> As a developer, I want pipeline intermediary files gitignored so that
> transformation artifacts never pollute the git history.

**Acceptance tests:** None (config-only change).

**Verification:**
```bash
# These patterns exist in .gitignore:
grep -q "data/candidates_raw.json" .gitignore
grep -q "data/analysis_batches/" .gitignore
grep -q "data/analysis_results/" .gitignore
grep -q "data/followers.db.bak" .gitignore
```

**Notes:** `.gitignore` already contains `data/*.db.bak`, `data/analysis_batches`,
`data/analysis_results`, and `data/candidates_raw.json`. Verify these are
present and add any that are missing. Do NOT remove existing patterns.

---

### Story 1.1: Extract Browser Connection Module
**PRD Step:** 2

> As a developer, I want browser connection management in `src/browser.py`
> so that `scripts/enrich.py` doesn't inline Playwright setup code and
> the browser layer is independently testable.

**Source:** `scripts/enrich.py` — `BrowserConnectionManager` class + `make_fetcher()`

#### RED: Tests to write first (`tests/unit/test_browser.py`)

```python
"""Tests for src.browser — browser connection management."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestBrowserConnectionManager:
    """Test the CDP connection manager lifecycle."""

    def test_init_stores_port(self):
        """Manager stores the debugging port."""
        from src.browser import BrowserConnectionManager
        mgr = BrowserConnectionManager(port=9222)
        assert mgr.port == 9222

    def test_default_port_is_9222(self):
        """Default port is 9222 if not specified."""
        from src.browser import BrowserConnectionManager
        mgr = BrowserConnectionManager()
        assert mgr.port == 9222

    def test_connect_raises_without_chrome(self):
        """connect() raises ConnectionError when Chrome isn't running."""
        from src.browser import BrowserConnectionManager
        mgr = BrowserConnectionManager(port=19999)  # nothing on this port
        with pytest.raises((ConnectionError, OSError)):
            mgr.connect()

    def test_is_connected_false_before_connect(self):
        """is_connected returns False before connect() is called."""
        from src.browser import BrowserConnectionManager
        mgr = BrowserConnectionManager()
        assert mgr.is_connected is False


class TestMakeFetcher:
    """Test the fetcher factory function."""

    def test_returns_callable(self):
        """make_fetcher() returns a callable."""
        from src.browser import make_fetcher
        mock_mgr = MagicMock()
        fetcher = make_fetcher(mock_mgr)
        assert callable(fetcher)

    def test_fetcher_uses_manager(self):
        """Returned fetcher delegates to the browser manager."""
        from src.browser import make_fetcher
        mock_mgr = MagicMock()
        fetcher = make_fetcher(mock_mgr)
        # Fetcher should be usable (exact behavior depends on implementation)
        assert fetcher is not None


class TestModuleConstraints:
    """Verify module-level constraints."""

    def test_no_external_deps(self):
        """src/browser.py imports only stdlib + playwright."""
        import ast, pathlib
        source = pathlib.Path("src/browser.py").read_text()
        tree = ast.parse(source)
        allowed = {"playwright", "asyncio", "json", "urllib", "http",
                    "os", "sys", "time", "logging", "contextlib",
                    "typing", "dataclasses", "pathlib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top in allowed or top.startswith("src"), \
                        f"Disallowed import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top in allowed or top.startswith("src"), \
                        f"Disallowed import: {node.module}"
```

#### GREEN: Implementation (`src/browser.py`)

Extract from `scripts/enrich.py`:
- `BrowserConnectionManager` class (CDP connection, page creation, cleanup)
- `make_fetcher(manager)` factory that returns a fetcher callable
- Keep signatures identical to current usage in `enrich.py`

#### REFACTOR:
- Ensure `enrich.py` still works by importing from `src.browser`
- No behavior changes

---

### Story 1.2: Extract Candidate Extractor Module
**PRD Step:** 3

> As a developer, I want candidate extraction in `src/candidate_extractor.py`
> so that the logic for pulling scored profiles from the DB and fetching
> their websites is reusable and testable.

**Source:** `scripts/extract_raw_candidates.py` (274 lines)

#### RED: Tests to write first (`tests/unit/test_candidate_extractor.py`)

```python
"""Tests for src.candidate_extractor — DB to candidates JSON."""
import json
import sqlite3
import pytest


def _create_test_db(db_path, profiles):
    """Create a test DB with the followers schema and given profiles."""
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS followers (
        id INTEGER PRIMARY KEY, handle TEXT UNIQUE, display_name TEXT,
        profile_url TEXT, follower_count INTEGER, following_count INTEGER,
        post_count INTEGER, bio TEXT, website TEXT, is_verified INTEGER,
        is_private INTEGER, is_business INTEGER, category TEXT,
        subcategory TEXT, location TEXT, is_hawaii INTEGER,
        confidence REAL, priority_score INTEGER, priority_reason TEXT,
        status TEXT, error_message TEXT, processed_at TEXT, created_at TEXT
    )""")
    for i, p in enumerate(profiles, 1):
        defaults = dict(
            id=i, handle=f"user_{i}", display_name=f"User {i}",
            profile_url=f"https://instagram.com/user_{i}",
            follower_count=100, following_count=50, post_count=10,
            bio="Test bio", website="", is_verified=0, is_private=0,
            is_business=0, category="personal_engaged", subcategory="general",
            location="", is_hawaii=0, confidence=0.5, priority_score=50,
            priority_reason="test", status="completed", error_message=None,
            processed_at="2026-01-01", created_at="2026-01-01"
        )
        defaults.update(p)
        cols = ", ".join(defaults.keys())
        placeholders = ", ".join(["?"] * len(defaults))
        conn.execute(f"INSERT INTO followers ({cols}) VALUES ({placeholders})",
                     list(defaults.values()))
    conn.commit()
    conn.close()


class TestExtractCandidates:
    """Test the main extraction function."""

    def test_returns_list(self, tmp_path):
        """extract_candidates returns a list."""
        from src.candidate_extractor import extract_candidates
        db = str(tmp_path / "test.db")
        _create_test_db(db, [{"handle": "user1", "status": "completed"}])
        result = extract_candidates(db)
        assert isinstance(result, list)

    def test_excludes_pending_profiles(self, tmp_path):
        """Profiles with status='pending' are not extracted."""
        from src.candidate_extractor import extract_candidates
        db = str(tmp_path / "test.db")
        _create_test_db(db, [
            {"handle": "done_user", "status": "completed"},
            {"handle": "pending_user", "status": "pending"},
        ])
        result = extract_candidates(db)
        handles = [r["handle"] for r in result]
        assert "done_user" in handles
        assert "pending_user" not in handles

    def test_excludes_error_profiles(self, tmp_path):
        """Profiles with status='error' are not extracted."""
        from src.candidate_extractor import extract_candidates
        db = str(tmp_path / "test.db")
        _create_test_db(db, [
            {"handle": "good", "status": "completed"},
            {"handle": "bad", "status": "error"},
        ])
        result = extract_candidates(db)
        handles = [r["handle"] for r in result]
        assert "good" in handles
        assert "bad" not in handles

    def test_includes_private_profiles(self, tmp_path):
        """Private profiles ARE included (they have some data)."""
        from src.candidate_extractor import extract_candidates
        db = str(tmp_path / "test.db")
        _create_test_db(db, [
            {"handle": "priv", "status": "private", "is_private": 1},
        ])
        result = extract_candidates(db)
        handles = [r["handle"] for r in result]
        assert "priv" in handles

    def test_each_candidate_has_required_fields(self, tmp_path):
        """Each candidate dict has handle, bio, category, score fields."""
        from src.candidate_extractor import extract_candidates
        db = str(tmp_path / "test.db")
        _create_test_db(db, [{"handle": "u1", "status": "completed",
                               "bio": "Dog lover", "priority_score": 75}])
        result = extract_candidates(db)
        assert len(result) > 0
        candidate = result[0]
        for field in ("handle", "bio", "category", "priority_score"):
            assert field in candidate, f"Missing field: {field}"

    def test_writes_json_output_file(self, tmp_path):
        """extract_candidates can write results to a JSON file."""
        from src.candidate_extractor import extract_candidates
        db = str(tmp_path / "test.db")
        out = str(tmp_path / "candidates.json")
        _create_test_db(db, [{"handle": "u1", "status": "completed"}])
        result = extract_candidates(db, output_path=out)
        assert (tmp_path / "candidates.json").exists()
        data = json.loads((tmp_path / "candidates.json").read_text())
        assert isinstance(data, list)
        assert len(data) == len(result)

    def test_empty_db_returns_empty_list(self, tmp_path):
        """Empty database returns empty list, no error."""
        from src.candidate_extractor import extract_candidates
        db = str(tmp_path / "test.db")
        _create_test_db(db, [])
        result = extract_candidates(db)
        assert result == []
```

#### GREEN: Implementation (`src/candidate_extractor.py`)

Move from `scripts/extract_raw_candidates.py`:
- `extract_candidates(db_path, output_path=None) -> list[dict]`
- DB query for completed/private profiles
- Optional website content fetching
- JSON output writing

---

### Story 1.3: Extract Analysis Module
**PRD Step:** 4

> As a developer, I want batch splitting and result aggregation in
> `src/analysis.py` so that AI analysis preparation and post-processing
> are importable functions, not standalone scripts.

**Source:** `scripts/ai_analysis_orchestrator.py` (83 lines) +
`scripts/aggregate_and_rank.py` (129 lines)

#### RED: Tests to write first (`tests/unit/test_analysis.py`)

```python
"""Tests for src.analysis — batch splitting and result aggregation."""
import json
import sqlite3
import pytest


class TestSplitBatches:
    """Test the batch splitting function."""

    def test_splits_into_correct_count(self, tmp_path):
        """10 candidates with batch_size=3 produces 4 batches."""
        from src.analysis import split_batches
        candidates = [{"handle": f"u{i}"} for i in range(10)]
        result = split_batches(candidates, batch_size=3,
                               output_dir=str(tmp_path))
        assert result["batches"] == 4

    def test_batch_files_are_valid_json(self, tmp_path):
        """Each batch file is a valid JSON array."""
        from src.analysis import split_batches
        candidates = [{"handle": f"u{i}"} for i in range(5)]
        split_batches(candidates, batch_size=2, output_dir=str(tmp_path))
        for f in tmp_path.glob("batch_*.json"):
            data = json.loads(f.read_text())
            assert isinstance(data, list)

    def test_all_candidates_present_across_batches(self, tmp_path):
        """Sum of all batch sizes equals input size."""
        from src.analysis import split_batches
        candidates = [{"handle": f"u{i}"} for i in range(7)]
        split_batches(candidates, batch_size=3, output_dir=str(tmp_path))
        total = 0
        for f in tmp_path.glob("batch_*.json"):
            total += len(json.loads(f.read_text()))
        assert total == 7

    def test_empty_input_produces_no_batches(self, tmp_path):
        """Empty candidate list produces zero batch files."""
        from src.analysis import split_batches
        result = split_batches([], batch_size=5, output_dir=str(tmp_path))
        assert result["batches"] == 0
        assert list(tmp_path.glob("batch_*.json")) == []

    def test_batch_size_larger_than_input(self, tmp_path):
        """When batch_size > len(candidates), produces exactly 1 batch."""
        from src.analysis import split_batches
        candidates = [{"handle": "u1"}, {"handle": "u2"}]
        result = split_batches(candidates, batch_size=100,
                               output_dir=str(tmp_path))
        assert result["batches"] == 1

    def test_default_batch_size(self, tmp_path):
        """Default batch size is 30."""
        from src.analysis import split_batches
        candidates = [{"handle": f"u{i}"} for i in range(60)]
        result = split_batches(candidates, output_dir=str(tmp_path))
        assert result["batch_size"] == 30
        assert result["batches"] == 2


class TestAggregateResults:
    """Test the result aggregation function."""

    def _make_db(self, tmp_path, handles):
        db = str(tmp_path / "test.db")
        conn = sqlite3.connect(db)
        conn.execute("""CREATE TABLE followers (
            id INTEGER PRIMARY KEY, handle TEXT UNIQUE, display_name TEXT,
            profile_url TEXT, follower_count INTEGER, following_count INTEGER,
            post_count INTEGER, bio TEXT, website TEXT, is_verified INTEGER,
            is_private INTEGER, is_business INTEGER, category TEXT,
            subcategory TEXT, location TEXT, is_hawaii INTEGER,
            confidence REAL, priority_score INTEGER, priority_reason TEXT,
            status TEXT, error_message TEXT, processed_at TEXT,
            created_at TEXT, score INTEGER, entity_type TEXT,
            outreach_type TEXT)""")
        for i, h in enumerate(handles, 1):
            conn.execute(
                "INSERT INTO followers (id, handle, status) VALUES (?, ?, ?)",
                (i, h, "completed"))
        conn.commit()
        conn.close()
        return db

    def test_writes_scores_to_database(self, tmp_path):
        """aggregate_results writes score and entity_type to the DB."""
        from src.analysis import aggregate_results
        db = self._make_db(tmp_path, ["user1", "user2"])
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        (results_dir / "batch_1_results.json").write_text(json.dumps([
            {"username": "user1", "score": 85, "entity_type": "DONOR"},
            {"username": "user2", "score": 30, "entity_type": "EXCLUDE_spam"},
        ]))
        result = aggregate_results(db, str(results_dir))
        assert result["scored"] == 1  # user1 (not excluded)
        assert result["excluded"] == 1  # user2

    def test_returns_count_summary(self, tmp_path):
        """aggregate_results returns {scored, excluded, total}."""
        from src.analysis import aggregate_results
        db = self._make_db(tmp_path, ["u1"])
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        (results_dir / "batch_1_results.json").write_text(json.dumps([
            {"username": "u1", "score": 50, "entity_type": "PROSPECT"},
        ]))
        result = aggregate_results(db, str(results_dir))
        assert "scored" in result
        assert "excluded" in result
        assert "total" in result

    def test_empty_results_dir(self, tmp_path):
        """Empty results directory returns zero counts."""
        from src.analysis import aggregate_results
        db = self._make_db(tmp_path, [])
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        result = aggregate_results(db, str(results_dir))
        assert result["total"] == 0
```

---

### Story 1.4: Extract DB Reports Module
**PRD Step:** 5

> As a developer, I want database report generation in `src/db_reports.py`
> so that the report queries and formatting are importable from src/ and
> the existing 1,354-line test suite continues to pass.

**Source:** `scripts/generate_db_reports.py` (391 lines)

#### RED: Tests (existing `tests/unit/test_generate_db_reports.py` — 1,354 lines)

The existing test suite becomes the TDD spec. The key test is:

```python
# After moving to src/db_reports.py, update the import in the test file:
# OLD: from scripts.generate_db_reports import generate_reports, ...
# NEW: from src.db_reports import generate_reports, ...

# ALL 1,354 lines of tests must pass with the new import path.
# This is the "red" — change the import, watch tests fail,
# then create the module to make them pass.
```

**Critical:** The existing test imports these exact names:
- `_bio_text`, `_enrich`, `_is_excluded`, `_is_marketing_excluded`
- `_load_completed_profiles`, `_suggested_ask`
- `_write_fundraising_csv`, `_write_markdown`, `_write_marketing_csv`
- `generate_reports`
- `_CATEGORY_TO_ENTITY`, `_CATEGORY_TO_OUTREACH`
- `_EXCLUDED_CATEGORIES`, `_PET_MICRO_SUBCATEGORIES`

All must be present in `src/db_reports.py` with identical signatures.

#### GREEN: Implementation (`src/db_reports.py`)

Copy `scripts/generate_db_reports.py` → `src/db_reports.py` verbatim.
Update only: `if __name__ == "__main__"` block removed (or kept as no-op).

#### REFACTOR:
- Update test imports from `scripts.generate_db_reports` to `src.db_reports`
- Verify all 1,354 lines of tests pass

---

### Story 1.5: Extract AI Reports Module
**PRD Step:** 6

> As a developer, I want AI-driven report formatting in `src/ai_reports.py`
> so that converting AI analysis JSON into markdown and CSV deliverables
> is an importable function.

**Source:** `scripts/format_reports.py` (303 lines)

#### RED: Tests to write first (`tests/unit/test_ai_reports.py`)

```python
"""Tests for src.ai_reports — AI JSON to markdown/CSV formatting."""
import csv
import io
import json
import pytest


def _sample_profiles():
    """Return sample analyzed profiles for testing."""
    return [
        {
            "username": "maui_donor",
            "score": 92,
            "entity_type": "HIGH_VALUE_DONOR",
            "outreach_type": "DIRECT_ASK",
            "reasoning": "Major business owner, dog lover",
            "follower_count": 15000,
            "bio": "Maui business owner | Dog dad",
            "website": "https://mauibiz.com",
        },
        {
            "username": "spam_account",
            "score": 0,
            "entity_type": "EXCLUDE_spam",
            "outreach_type": "SKIP",
            "reasoning": "Bot account",
            "follower_count": 50000,
            "bio": "Follow for follow",
            "website": "",
        },
        {
            "username": "pet_shop_oahu",
            "score": 78,
            "entity_type": "MARKETING_PARTNER",
            "outreach_type": "PARTNERSHIP",
            "reasoning": "Pet supply store in Honolulu",
            "follower_count": 5000,
            "bio": "Oahu's best pet supplies",
            "website": "https://petshop.com",
        },
    ]


class TestFormatAiReports:
    """Test the main report formatting function."""

    def test_generates_markdown_file(self, tmp_path):
        """format_ai_reports creates a markdown output file."""
        from src.ai_reports import format_ai_reports
        profiles = _sample_profiles()
        md_path = str(tmp_path / "report.md")
        format_ai_reports(profiles, markdown_path=md_path)
        assert (tmp_path / "report.md").exists()
        content = (tmp_path / "report.md").read_text()
        assert len(content) > 0

    def test_generates_csv_file(self, tmp_path):
        """format_ai_reports creates a CSV output file."""
        from src.ai_reports import format_ai_reports
        profiles = _sample_profiles()
        csv_path = str(tmp_path / "report.csv")
        format_ai_reports(profiles, csv_path=csv_path)
        assert (tmp_path / "report.csv").exists()

    def test_csv_has_header_row(self, tmp_path):
        """CSV output starts with a header row."""
        from src.ai_reports import format_ai_reports
        profiles = _sample_profiles()
        csv_path = str(tmp_path / "report.csv")
        format_ai_reports(profiles, csv_path=csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            assert "username" in reader.fieldnames

    def test_excludes_skip_profiles_from_output(self, tmp_path):
        """Profiles with outreach_type=SKIP are excluded from reports."""
        from src.ai_reports import format_ai_reports
        profiles = _sample_profiles()
        csv_path = str(tmp_path / "report.csv")
        format_ai_reports(profiles, csv_path=csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            usernames = [row["username"] for row in reader]
        assert "spam_account" not in usernames

    def test_markdown_contains_top_prospects(self, tmp_path):
        """Markdown includes the scored (non-excluded) profiles."""
        from src.ai_reports import format_ai_reports
        profiles = _sample_profiles()
        md_path = str(tmp_path / "report.md")
        format_ai_reports(profiles, markdown_path=md_path)
        content = (tmp_path / "report.md").read_text()
        assert "maui_donor" in content
        assert "pet_shop_oahu" in content

    def test_empty_profiles_produces_empty_report(self, tmp_path):
        """Empty input produces a report file (possibly with just headers)."""
        from src.ai_reports import format_ai_reports
        csv_path = str(tmp_path / "report.csv")
        format_ai_reports([], csv_path=csv_path)
        assert (tmp_path / "report.csv").exists()

    def test_profiles_sorted_by_score_descending(self, tmp_path):
        """Output profiles are sorted by score, highest first."""
        from src.ai_reports import format_ai_reports
        profiles = _sample_profiles()
        csv_path = str(tmp_path / "report.csv")
        format_ai_reports(profiles, csv_path=csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            scores = [int(row["score"]) for row in reader if row.get("score")]
        assert scores == sorted(scores, reverse=True)
```

---

### Story 1.6: Phase A Gate
**PRD Step:** 7

> As a developer, I want a verification gate after module extraction so
> that I can confirm all 5 modules are correct before wiring them up.

**This is not a code story — it's a verification checkpoint.**

**Gate test script (run manually or by Ralph loop):**
```bash
#!/bin/bash
# Phase A Gate
set -e

echo "=== Phase A Gate ==="

# 1. All tests pass
pytest tests/ -v || { echo "FAIL: tests"; exit 1; }

# 2. All 5 modules importable
python3 -c "from src.browser import BrowserConnectionManager, make_fetcher" || { echo "FAIL: browser"; exit 1; }
python3 -c "from src.candidate_extractor import extract_candidates" || { echo "FAIL: candidate_extractor"; exit 1; }
python3 -c "from src.analysis import split_batches, aggregate_results" || { echo "FAIL: analysis"; exit 1; }
python3 -c "from src.db_reports import generate_reports" || { echo "FAIL: db_reports"; exit 1; }
python3 -c "from src.ai_reports import format_ai_reports" || { echo "FAIL: ai_reports"; exit 1; }

# 3. Test files exist
test -f tests/unit/test_browser.py || { echo "FAIL: missing test_browser"; exit 1; }
test -f tests/unit/test_candidate_extractor.py || { echo "FAIL: missing test_candidate_extractor"; exit 1; }
test -f tests/unit/test_analysis.py || { echo "FAIL: missing test_analysis"; exit 1; }
test -f tests/unit/test_ai_reports.py || { echo "FAIL: missing test_ai_reports"; exit 1; }

# 4. Regression
pytest tests/ -v || { echo "FAIL: regression"; exit 1; }

echo "=== Phase A Gate PASSED ==="
```

**On pass:** `git commit` + checkpoint.

---

## Epic 2: Pipeline Wiring (PRD Steps 8-12)

> Wire the extracted modules into a unified pipeline with CLI entry point
> and shell orchestrator.

---

### Story 2.1: Expand Pipeline Entry Points
**PRD Step:** 8

> As a developer, I want `src/pipeline.py` to have entry point functions
> for all 4 phases so that `scripts/run_pipeline.py` can call them
> and get JSON-serializable results.

**Source:** Existing `src/pipeline.py` has `run_phase1()` and `run_phase2()`.

#### RED: Tests to add (`tests/unit/test_pipeline.py`)

Extend the existing 77-line test file:

```python
"""Additional tests for src.pipeline phase entry points."""
import json
import sqlite3
import pytest


class TestPhase1Import:
    """Test phase_1_import returns correct structure."""

    def test_returns_dict_with_inserted_count(self, tmp_path):
        from src.pipeline import phase_1_import
        csv_path = str(tmp_path / "test.csv")
        db_path = str(tmp_path / "test.db")
        with open(csv_path, "w") as f:
            f.write("handle,display_name,profile_url\n")
            f.write("user1,User One,https://instagram.com/user1\n")
            f.write("user2,User Two,https://instagram.com/user2\n")
        result = phase_1_import(csv_path, db_path)
        assert isinstance(result, dict)
        assert result["inserted"] >= 0
        assert "total" in result

    def test_result_is_json_serializable(self, tmp_path):
        from src.pipeline import phase_1_import
        csv_path = str(tmp_path / "test.csv")
        db_path = str(tmp_path / "test.db")
        with open(csv_path, "w") as f:
            f.write("handle,display_name,profile_url\n")
            f.write("u1,U1,https://instagram.com/u1\n")
        result = phase_1_import(csv_path, db_path)
        serialized = json.dumps(result)  # must not raise
        assert isinstance(json.loads(serialized), dict)


class TestPhase3Extract:
    """Test phase_3_extract returns correct structure."""

    def test_returns_dict_with_candidate_count(self, tmp_path):
        from src.pipeline import phase_3_extract
        # Need a DB with completed profiles
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""CREATE TABLE followers (
            id INTEGER PRIMARY KEY, handle TEXT UNIQUE, display_name TEXT,
            profile_url TEXT, follower_count INTEGER, following_count INTEGER,
            post_count INTEGER, bio TEXT, website TEXT, is_verified INTEGER,
            is_private INTEGER, is_business INTEGER, category TEXT,
            subcategory TEXT, location TEXT, is_hawaii INTEGER,
            confidence REAL, priority_score INTEGER, priority_reason TEXT,
            status TEXT, error_message TEXT, processed_at TEXT, created_at TEXT
        )""")
        conn.execute("""INSERT INTO followers
            (handle, status, bio, category, priority_score, display_name,
             profile_url, follower_count, following_count, post_count,
             is_verified, is_private, is_business, subcategory, location,
             is_hawaii, confidence, priority_reason, created_at)
            VALUES ('u1', 'completed', 'bio', 'business_local', 50,
                    'U1', 'url', 100, 50, 10, 0, 0, 0, 'general', '',
                    0, 0.5, 'test', '2026-01-01')""")
        conn.commit()
        conn.close()
        result = phase_3_extract(db_path)
        assert isinstance(result, dict)
        assert "candidates" in result


class TestPhase3Prepare:
    """Test phase_3_prepare returns correct structure."""

    def test_returns_dict_with_batch_count(self, tmp_path):
        from src.pipeline import phase_3_prepare
        # Create candidates JSON first
        cand_path = tmp_path / "candidates_raw.json"
        cand_path.write_text(json.dumps([
            {"handle": f"u{i}"} for i in range(10)
        ]))
        result = phase_3_prepare(str(tmp_path / "test.db"))
        assert isinstance(result, dict)
        assert "batches" in result


class TestPhase4Reports:
    """Test phase_4_reports returns correct structure."""

    def test_returns_dict_with_file_list(self, tmp_path):
        from src.pipeline import phase_4_reports
        result = phase_4_reports(str(tmp_path / "test.db"))
        assert isinstance(result, dict)
        assert "files" in result
        assert isinstance(result["files"], list)
```

#### GREEN: Expand `src/pipeline.py`

Add `phase_1_import`, `phase_3_extract`, `phase_3_prepare`,
`phase_3_aggregate`, `phase_4_reports` — each calling the
corresponding `src/` module and returning a dict.

---

### Story 2.2: Create Pipeline CLI
**PRD Step:** 9

> As a developer, I want a `scripts/run_pipeline.py` CLI so that the
> shell orchestrator can invoke each phase as a subprocess and get
> JSON results on stdout.

#### RED: Tests (integration-style, run via subprocess)

```python
"""Tests for scripts/run_pipeline.py CLI."""
import json
import subprocess
import pytest


class TestPipelineCLI:

    def test_help_exits_zero(self):
        """--help exits with code 0."""
        result = subprocess.run(
            ["python3", "scripts/run_pipeline.py", "--help"],
            capture_output=True, text=True)
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "phase" in result.stdout.lower()

    def test_phase1_produces_json(self, tmp_path):
        """--phase 1 with valid CSV produces JSON output."""
        csv_path = str(tmp_path / "test.csv")
        db_path = str(tmp_path / "test.db")
        with open(csv_path, "w") as f:
            f.write("handle,display_name,profile_url\n")
            f.write("u1,User 1,https://instagram.com/u1\n")
        result = subprocess.run(
            ["python3", "scripts/run_pipeline.py",
             "--phase", "1", "--csv", csv_path, "--db", db_path],
            capture_output=True, text=True)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_missing_phase_exits_nonzero(self):
        """Missing --phase argument exits with nonzero code."""
        result = subprocess.run(
            ["python3", "scripts/run_pipeline.py"],
            capture_output=True, text=True)
        assert result.returncode != 0
```

---

### Story 2.3: Slim Enrich Script
**PRD Step:** 10

> As a developer, I want `scripts/enrich.py` to import browser code
> from `src/browser` instead of defining it inline, reducing the script
> from ~445 lines to ~120 lines.

#### RED: Tests (verify the refactoring didn't break anything)

```python
"""Tests for scripts/enrich.py after slimming."""
import ast
import pathlib


class TestEnrichRefactored:

    def test_imports_from_src_browser(self):
        """enrich.py imports from src.browser."""
        source = pathlib.Path("scripts/enrich.py").read_text()
        assert "from src.browser import" in source or \
               "import src.browser" in source

    def test_no_inline_browser_class(self):
        """enrich.py does NOT define BrowserConnectionManager."""
        source = pathlib.Path("scripts/enrich.py").read_text()
        assert "class BrowserConnectionManager" not in source

    def test_line_count_reduced(self):
        """enrich.py is significantly shorter after extraction."""
        source = pathlib.Path("scripts/enrich.py").read_text()
        line_count = len(source.splitlines())
        assert line_count < 250, \
            f"enrich.py still has {line_count} lines (expected < 250)"
```

---

### Story 2.4: Create Shell Orchestrator
**PRD Step:** 11

> As a developer, I want a `scripts/run_afk_pipeline.sh` that orchestrates
> the full pipeline with context-isolated Claude sessions, back pressure
> gates, review stations, git checkpoints, and prompt-gated cleanup.

#### RED: Tests (structural validation)

```python
"""Tests for scripts/run_afk_pipeline.sh structure."""
import pathlib
import subprocess


class TestShellScript:

    def test_file_exists(self):
        assert pathlib.Path("scripts/run_afk_pipeline.sh").exists()

    def test_is_executable(self):
        p = pathlib.Path("scripts/run_afk_pipeline.sh")
        assert p.stat().st_mode & 0o111, "Script is not executable"

    def test_starts_with_shebang(self):
        content = pathlib.Path("scripts/run_afk_pipeline.sh").read_text()
        assert content.startswith("#!/bin/bash")

    def test_has_strict_mode(self):
        content = pathlib.Path("scripts/run_afk_pipeline.sh").read_text()
        assert "set -euo pipefail" in content

    def test_bash_syntax_valid(self):
        """bash -n checks syntax without executing."""
        result = subprocess.run(
            ["bash", "-n", "scripts/run_afk_pipeline.sh"],
            capture_output=True, text=True)
        assert result.returncode == 0, \
            f"Syntax error: {result.stderr}"

    def test_contains_gate_functions(self):
        content = pathlib.Path("scripts/run_afk_pipeline.sh").read_text()
        for gate in ["gate_phase1", "gate_phase2", "gate_phase3a",
                      "gate_phase3b", "gate_phase3c", "gate_phase4"]:
            assert gate in content, f"Missing gate function: {gate}"

    def test_contains_git_checkpoint(self):
        content = pathlib.Path("scripts/run_afk_pipeline.sh").read_text()
        assert "git_checkpoint" in content

    def test_contains_cleanup_flag(self):
        content = pathlib.Path("scripts/run_afk_pipeline.sh").read_text()
        assert "CLEANUP_INTERMEDIARY" in content

    def test_contains_review_stations(self):
        content = pathlib.Path("scripts/run_afk_pipeline.sh").read_text()
        assert "Review 1" in content
        assert "Review 2" in content

    def test_contains_ralph_wiggum_state_file(self):
        content = pathlib.Path("scripts/run_afk_pipeline.sh").read_text()
        assert "pipeline_state.md" in content
```

---

### Story 2.5: Phase B Gate
**PRD Step:** 12

> As a developer, I want a verification gate after pipeline wiring so
> that CLI, shell script, and module imports are all confirmed before cleanup.

**Gate test script:**
```bash
#!/bin/bash
set -e

echo "=== Phase B Gate ==="

pytest tests/ -v
python3 scripts/run_pipeline.py --help
bash -n scripts/run_afk_pipeline.sh
test -x scripts/run_afk_pipeline.sh
grep -q "from src.browser import" scripts/enrich.py

python3 -c "from src.browser import BrowserConnectionManager"
python3 -c "from src.candidate_extractor import extract_candidates"
python3 -c "from src.analysis import split_batches, aggregate_results"
python3 -c "from src.db_reports import generate_reports"
python3 -c "from src.ai_reports import format_ai_reports"

# Integration test
python3 scripts/run_pipeline.py --phase 1 \
  --csv tests/fixtures/sample_followers.csv --db /tmp/phase_b_test.db

pytest tests/ -v  # regression

echo "=== Phase B Gate PASSED ==="
```

---

## Epic 3: Cleanup & Final Verification (PRD Steps 13-16)

> Rename test files, delete old scripts, update docs, run final gate.

---

### Story 3.1: Rename Test File
**PRD Step:** 13

> As a developer, I want the DB report test renamed from
> `test_generate_db_reports.py` to `test_report_generator.py` so that
> the test file name matches the new `src/db_reports.py` module.

#### RED: Test

```python
"""Verify test file rename."""
import pathlib

def test_old_name_gone():
    assert not pathlib.Path("tests/unit/test_generate_db_reports.py").exists()

def test_new_name_exists():
    assert pathlib.Path("tests/unit/test_report_generator.py").exists()
```

After rename: `pytest tests/unit/test_report_generator.py -v` — all 1,354 lines pass.

---

### Story 3.2: Delete Old Scripts
**PRD Step:** 14

> As a developer, I want the 7 replaced scripts deleted so that there
> is only one way to run each operation (through the new modules).

#### RED: Test

```python
"""Verify old scripts are deleted and no dangling references exist."""
import pathlib
import subprocess

OLD_SCRIPTS = [
    "scripts/extract_raw_candidates.py",
    "scripts/ai_analysis_orchestrator.py",
    "scripts/aggregate_and_rank.py",
    "scripts/format_reports.py",
    "scripts/generate_db_reports.py",
    "scripts/merge_top_followers.py",
    "scripts/analyze_fundraising_candidates.py",
]

class TestOldScriptsDeleted:

    def test_files_do_not_exist(self):
        for script in OLD_SCRIPTS:
            assert not pathlib.Path(script).exists(), \
                f"Old script still exists: {script}"

    def test_no_dangling_imports(self):
        """No src/, scripts/, or tests/ file imports the old scripts."""
        patterns = [
            "extract_raw_candidates",
            "ai_analysis_orchestrator",
            "aggregate_and_rank",
            "format_reports",
            "generate_db_reports",
            "merge_top_followers",
            "analyze_fundraising",
        ]
        for pattern in patterns:
            result = subprocess.run(
                ["grep", "-r", pattern, "src/", "scripts/", "tests/",
                 "--include=*.py", "-l"],
                capture_output=True, text=True)
            assert result.stdout.strip() == "", \
                f"Dangling reference to '{pattern}' in: {result.stdout.strip()}"
```

---

### Story 3.3: Update CLAUDE.md
**PRD Step:** 15

> As a developer, I want CLAUDE.md updated with pipeline documentation
> so that future sessions know how to run the AFK pipeline.

#### RED: Test

```python
"""Verify CLAUDE.md has pipeline documentation."""
import pathlib

def test_claude_md_mentions_afk_pipeline():
    content = pathlib.Path("CLAUDE.md").read_text()
    assert "run_afk_pipeline" in content

def test_claude_md_mentions_run_pipeline():
    content = pathlib.Path("CLAUDE.md").read_text()
    assert "run_pipeline" in content
```

---

### Story 3.4: Phase C Gate — Final Verification
**PRD Step:** 16

> As a developer, I want a comprehensive final gate that verifies every
> deliverable from the entire build before marking it complete.

**Gate test (the 13-item checklist as a pytest suite):**

```python
"""Phase C final gate — comprehensive build verification."""
import pathlib
import subprocess
import ast
import pytest


STDLIB_MODULES = {
    "abc", "argparse", "ast", "asyncio", "base64", "collections",
    "contextlib", "copy", "csv", "dataclasses", "datetime", "enum",
    "functools", "glob", "hashlib", "http", "io", "itertools", "json",
    "logging", "math", "os", "pathlib", "pprint", "re", "shutil",
    "sqlite3", "string", "subprocess", "sys", "tempfile", "textwrap",
    "threading", "time", "typing", "unittest", "urllib", "uuid",
    "warnings", "xml",
}
ALLOWED_EXTERNAL = {"playwright", "pytest", "src", "scripts"}


class TestPhaseCSrcModules:
    """Verify all src/ modules exist and import cleanly."""

    @pytest.mark.parametrize("module", [
        "browser", "candidate_extractor", "analysis",
        "db_reports", "ai_reports", "pipeline",
    ])
    def test_module_exists(self, module):
        assert pathlib.Path(f"src/{module}.py").exists()

    @pytest.mark.parametrize("module", [
        "browser", "candidate_extractor", "analysis",
        "db_reports", "ai_reports", "pipeline",
    ])
    def test_module_imports(self, module):
        result = subprocess.run(
            ["python3", "-c", f"import src.{module}"],
            capture_output=True, text=True)
        assert result.returncode == 0, \
            f"src.{module} failed to import: {result.stderr}"

    @pytest.mark.parametrize("module", [
        "browser", "candidate_extractor", "analysis",
        "db_reports", "ai_reports", "pipeline",
    ])
    def test_no_forbidden_imports(self, module):
        source = pathlib.Path(f"src/{module}.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                else:
                    names = [node.module.split(".")[0]] if node.module else []
                for name in names:
                    ok = (name in STDLIB_MODULES or
                          name in ALLOWED_EXTERNAL or
                          name.startswith("_"))
                    assert ok, \
                        f"src/{module}.py has disallowed import: {name}"


class TestPhaseCScripts:
    """Verify scripts are correct."""

    def test_run_pipeline_exists(self):
        assert pathlib.Path("scripts/run_pipeline.py").exists()

    def test_run_pipeline_help(self):
        result = subprocess.run(
            ["python3", "scripts/run_pipeline.py", "--help"],
            capture_output=True, text=True)
        assert result.returncode == 0

    def test_afk_pipeline_exists(self):
        assert pathlib.Path("scripts/run_afk_pipeline.sh").exists()

    def test_afk_pipeline_executable(self):
        p = pathlib.Path("scripts/run_afk_pipeline.sh")
        assert p.stat().st_mode & 0o111

    def test_enrich_imports_from_src(self):
        content = pathlib.Path("scripts/enrich.py").read_text()
        assert "from src.browser import" in content or \
               "import src.browser" in content


class TestPhaseCDeletions:
    """Verify old scripts are gone."""

    OLD_SCRIPTS = [
        "scripts/extract_raw_candidates.py",
        "scripts/ai_analysis_orchestrator.py",
        "scripts/aggregate_and_rank.py",
        "scripts/format_reports.py",
        "scripts/generate_db_reports.py",
        "scripts/merge_top_followers.py",
        "scripts/analyze_fundraising_candidates.py",
    ]

    @pytest.mark.parametrize("script", OLD_SCRIPTS)
    def test_old_script_deleted(self, script):
        assert not pathlib.Path(script).exists()


class TestPhaseCDocs:
    """Verify documentation updated."""

    def test_claude_md_updated(self):
        content = pathlib.Path("CLAUDE.md").read_text()
        assert "run_afk_pipeline" in content
        assert "run_pipeline" in content
```

---

## Test Execution Summary

### Test count by story

| Story | Tests | File |
|-------|-------|------|
| 1.1 Browser | 6 | `tests/unit/test_browser.py` |
| 1.2 Candidate Extractor | 7 | `tests/unit/test_candidate_extractor.py` |
| 1.3 Analysis | 9 | `tests/unit/test_analysis.py` |
| 1.4 DB Reports | 1,354 existing | `tests/unit/test_report_generator.py` |
| 1.5 AI Reports | 7 | `tests/unit/test_ai_reports.py` |
| 2.1 Pipeline | 4 | `tests/unit/test_pipeline.py` (extend) |
| 2.2 CLI | 3 | `tests/unit/test_pipeline_cli.py` |
| 2.3 Enrich | 3 | `tests/unit/test_enrich_refactored.py` |
| 2.4 Shell Script | 10 | `tests/unit/test_shell_script.py` |
| 3.1 Rename | 2 | inline |
| 3.2 Delete Scripts | 2 | `tests/unit/test_cleanup.py` |
| 3.3 CLAUDE.md | 2 | inline |
| 3.4 Phase C Gate | ~25 | `tests/unit/test_phase_c_gate.py` |
| **Total new** | **~80** | |
| **Total with existing** | **~1,434+** | |

### Run order

```bash
# After Epic 1:
pytest tests/unit/test_browser.py tests/unit/test_candidate_extractor.py \
       tests/unit/test_analysis.py tests/unit/test_ai_reports.py \
       tests/unit/test_report_generator.py -v

# After Epic 2:
pytest tests/ -v

# After Epic 3 (final):
pytest tests/ -v  # ALL tests, including Phase C gate suite
```
