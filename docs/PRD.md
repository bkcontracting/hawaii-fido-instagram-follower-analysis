# PRD: AFK Pipeline — Project Refactoring & Automation

**Source:** `docs/AFK_PIPELINE_PLAN.md`
**Branch:** `claude/refactor-project-structure-YWohS`
**Status:** Ready for implementation

---

## 1. Problem Statement

The Hawaii Fi-Do Instagram Follower Analyzer has 12 standalone scripts with
no unified entry point. Running the full pipeline (CSV import → Instagram
scraping → AI analysis → reports) requires manually executing scripts in
sequence, monitoring each step, and handling errors by hand. This takes
~90 minutes of active developer attention.

**Goal:** A single `./scripts/run_afk_pipeline.sh` command that runs the
entire pipeline autonomously — the developer walks away, comes back to
completed reports.

---

## 2. Implementation Steps

Each numbered step is a discrete unit of work. Steps marked [PARALLEL]
can run concurrently. Each step has acceptance criteria that MUST pass
before the next step begins.

---

### STEP 1: Update `.gitignore`

**File:** `.gitignore`

**Action:** Add pipeline intermediary file patterns.

**Add these lines:**
```gitignore
# Pipeline intermediary files — never committed
data/candidates_raw.json
data/analysis_batches/
data/analysis_results/
data/followers.db.bak
```

**Acceptance criteria:**
- [ ] `.gitignore` contains all 4 patterns
- [ ] `git status` does not show any of these file patterns as untracked
- [ ] Existing tracked files (if any match) are untracked via `git rm --cached`

---

### STEP 2: Create `src/browser.py` [PARALLEL with 3-6]

**Source:** Extract from `scripts/enrich.py` (lines ~1-180)

**Action:** Move `BrowserConnectionManager` class and `make_fetcher()` function
into a standalone module.

**What to extract:**
- `BrowserConnectionManager` class (connects to Chrome CDP on port 9222)
- `make_fetcher()` factory function
- All supporting imports and constants

**What stays in `enrich.py`:** The enrichment loop, DB access, rate limiting.

**Files to create:**
1. `src/browser.py` (~180 lines)
2. `tests/unit/test_browser.py` (~150 lines)

**Acceptance criteria:**
- [ ] `python3 -c "from src.browser import BrowserConnectionManager"` — exits 0
- [ ] `python3 -c "from src.browser import make_fetcher"` — exits 0
- [ ] No non-stdlib imports (except `playwright`)
- [ ] `tests/unit/test_browser.py` exists with tests for each public function
- [ ] `pytest tests/unit/test_browser.py -v` — all pass

---

### STEP 3: Create `src/candidate_extractor.py` [PARALLEL with 2,4-6]

**Source:** Move from `scripts/extract_raw_candidates.py` (274 lines)

**Action:** Convert script into importable module with `extract_candidates()`
function.

**Files to create:**
1. `src/candidate_extractor.py` (~250 lines)
2. `tests/unit/test_candidate_extractor.py` (~200 lines)

**Acceptance criteria:**
- [ ] `python3 -c "from src.candidate_extractor import extract_candidates"` — exits 0
- [ ] No non-stdlib imports
- [ ] Test file exists with tests for each public function
- [ ] `pytest tests/unit/test_candidate_extractor.py -v` — all pass

---

### STEP 4: Create `src/analysis.py` [PARALLEL with 2-3,5-6]

**Source:** Merge `scripts/ai_analysis_orchestrator.py` (83 lines) +
`scripts/aggregate_and_rank.py` (129 lines)

**Action:** Create module with `split_batches()` and `aggregate_results()`.

**Files to create:**
1. `src/analysis.py` (~160 lines)
2. `tests/unit/test_analysis.py` (~150 lines)

**Acceptance criteria:**
- [ ] `python3 -c "from src.analysis import split_batches, aggregate_results"` — exits 0
- [ ] No non-stdlib imports
- [ ] Test file exists
- [ ] `pytest tests/unit/test_analysis.py -v` — all pass

---

### STEP 5: Create `src/db_reports.py` [PARALLEL with 2-4,6]

**Source:** Move from `scripts/generate_db_reports.py` (391 lines)

**Action:** Convert script into importable module. Preserve all existing
query logic exactly.

**Files to create:**
1. `src/db_reports.py` (~390 lines)

**Note:** Existing test `tests/unit/test_generate_db_reports.py` (1,354 lines)
covers this module. It will be renamed in Step 10.

**Acceptance criteria:**
- [ ] `python3 -c "from src.db_reports import generate_db_reports"` — exits 0
- [ ] No non-stdlib imports
- [ ] All existing report tests still pass after import path update

---

### STEP 6: Create `src/ai_reports.py` [PARALLEL with 2-5]

**Source:** Move from `scripts/format_reports.py` (303 lines)

**Action:** Convert script into importable module with `format_ai_reports()`.

**Files to create:**
1. `src/ai_reports.py` (~300 lines)
2. `tests/unit/test_ai_reports.py` (~200 lines)

**Acceptance criteria:**
- [ ] `python3 -c "from src.ai_reports import format_ai_reports"` — exits 0
- [ ] No non-stdlib imports
- [ ] Test file exists
- [ ] `pytest tests/unit/test_ai_reports.py -v` — all pass

---

### STEP 7: Phase A Gate — Verify Steps 2-6

**Action:** Run full verification before proceeding.

**Gate checks:**
1. `pytest tests/ -v` — zero failures, zero errors
2. For each module (browser, candidate_extractor, analysis, db_reports, ai_reports):
   - `src/{module}.py` exists
   - `python3 -c "import src.{module}"` succeeds
   - No non-stdlib imports (except playwright)
   - Test file exists in `tests/unit/`
3. `pytest tests/ -v` again (regression check)

**On pass:** `git commit` all new `src/` modules and tests.

**On fail:** Write specific failures to `data/pipeline_state.md`, retry
the failing step(s).

**Acceptance criteria:**
- [ ] All 5 modules import cleanly
- [ ] All tests pass (zero failures)
- [ ] Git commit created: `"Phase A gate PASS — 5 modules moved to src/"`

---

### STEP 8: Expand `src/pipeline.py` [PARALLEL with 9]

**Source:** Existing `src/pipeline.py` (~30 lines)

**Action:** Add phase entry points that each return JSON-serializable dicts.

**Functions to add:**
```python
def phase_1_import(csv_path: str, db_path: str) -> dict:
    """Import CSV into database. Returns {inserted, skipped, total}."""

def phase_2_enrich(db_path: str) -> dict:
    """Run Playwright enrichment. Returns {completed, errors, private, pending}."""

def phase_3_extract(db_path: str) -> dict:
    """Extract candidates to JSON. Returns {candidates, with_website}."""

def phase_3_prepare(db_path: str) -> dict:
    """Split candidates into batches. Returns {batches, batch_size}."""

def phase_3_aggregate(db_path: str) -> dict:
    """Aggregate AI results into DB. Returns {scored, excluded, total}."""

def phase_4_reports(db_path: str) -> dict:
    """Generate all reports. Returns {files: [paths]}."""
```

**Acceptance criteria:**
- [ ] `python3 -c "from src.pipeline import phase_1_import, phase_2_enrich"` — exits 0
- [ ] Each function returns a dict (not None, not a string)

---

### STEP 9: Create `scripts/run_pipeline.py` [PARALLEL with 8]

**Action:** Create CLI entry point that calls `src/pipeline.py` functions
and prints JSON to stdout.

**Interface:**
```
python3 scripts/run_pipeline.py --phase 1 --csv data/followers_validated.csv --db data/followers.db
python3 scripts/run_pipeline.py --phase 2 --db data/followers.db
python3 scripts/run_pipeline.py --phase 3 --step extract --db data/followers.db
python3 scripts/run_pipeline.py --phase 3 --step prepare --db data/followers.db
python3 scripts/run_pipeline.py --phase 3 --step aggregate --db data/followers.db
python3 scripts/run_pipeline.py --phase 4 --db data/followers.db
python3 scripts/run_pipeline.py --status --db data/followers.db
python3 scripts/run_pipeline.py --help
```

**Acceptance criteria:**
- [ ] `python3 scripts/run_pipeline.py --help` — exits 0, shows usage
- [ ] `python3 scripts/run_pipeline.py --phase 1 --csv tests/fixtures/sample_followers.csv --db /tmp/test.db` — exits 0, prints valid JSON
- [ ] No non-stdlib imports (uses `argparse`, `json`, `sys`)

---

### STEP 10: Slim `scripts/enrich.py`

**Action:** Remove `BrowserConnectionManager` and `make_fetcher()` from
`scripts/enrich.py`. Replace with imports from `src.browser`.

**Before:** ~445 lines (inline browser code)
**After:** ~120 lines (imports browser code from src)

**Acceptance criteria:**
- [ ] `scripts/enrich.py` contains `from src.browser import`
- [ ] `scripts/enrich.py` does NOT contain `class BrowserConnectionManager`
- [ ] `pytest tests/ -v` — all pass (existing tests still work)

---

### STEP 11: Create `scripts/run_afk_pipeline.sh`

**Action:** Write the complete shell orchestrator from `docs/AFK_PIPELINE_PLAN.md`
(the "Complete Orchestrator" section).

**Key components:**
1. Config variables (paths, retry count, wave size)
2. `log()` and `log_section()` functions
3. `init_state()` — creates/resets `data/pipeline_state.md` (preserves learnings)
4. `run_station()` — runs a Claude session with retry logic
5. `run_gate()` — runs a verification gate
6. `run_phase_with_gate()` — combines station + gate with back pressure
7. `git_checkpoint()` — commits after passing gates (intermediary files excluded)
8. Gate functions: `gate_phase1` through `gate_phase4`
9. Pipeline execution: phases 1-4 with review stations
10. Cleanup section (prompt-gated via `CLEANUP_INTERMEDIARY`)

**Acceptance criteria:**
- [ ] `scripts/run_afk_pipeline.sh` exists
- [ ] File is executable (`chmod +x`)
- [ ] Starts with `#!/bin/bash`
- [ ] Contains `set -euo pipefail`
- [ ] `bash -n scripts/run_afk_pipeline.sh` — syntax check passes (exits 0)
- [ ] Contains all 6 gate functions
- [ ] Contains `git_checkpoint` function
- [ ] Contains `CLEANUP_INTERMEDIARY` handling
- [ ] Contains 2 review stations

---

### STEP 12: Phase B Gate — Verify Steps 8-11

**Gate checks:**
1. `pytest tests/ -v` — zero failures
2. `python3 scripts/run_pipeline.py --help` — exits 0
3. `scripts/run_afk_pipeline.sh` exists, executable, valid bash
4. `scripts/enrich.py` imports from `src.browser`
5. All 5 src modules import correctly:
   ```
   python3 -c "from src.browser import BrowserConnectionManager"
   python3 -c "from src.candidate_extractor import extract_candidates"
   python3 -c "from src.analysis import split_batches, aggregate_results"
   python3 -c "from src.db_reports import generate_db_reports"
   python3 -c "from src.ai_reports import format_ai_reports"
   ```
6. Integration test: `python3 scripts/run_pipeline.py --phase 1 --csv tests/fixtures/sample_followers.csv --db /tmp/test.db` — exits 0, valid JSON
7. `pytest tests/ -v` again (regression)

**On pass:** `git commit` pipeline.py, run_pipeline.py, run_afk_pipeline.sh, enrich.py.

**On fail:** Write failures to state file, retry.

**Acceptance criteria:**
- [ ] All 7 checks pass
- [ ] Git commit: `"Phase B gate PASS — pipeline CLI + shell orchestrator wired up"`

---

### STEP 13: Rename test file

**Action:** Rename `tests/unit/test_generate_db_reports.py` →
`tests/unit/test_report_generator.py`. Update all import paths inside.

**Acceptance criteria:**
- [ ] Old file does not exist
- [ ] New file exists with all test content preserved
- [ ] `pytest tests/unit/test_report_generator.py -v` — all pass

---

### STEP 14: Delete 7 old scripts

**Files to delete:**
1. `scripts/extract_raw_candidates.py`
2. `scripts/ai_analysis_orchestrator.py`
3. `scripts/aggregate_and_rank.py`
4. `scripts/format_reports.py`
5. `scripts/generate_db_reports.py`
6. `scripts/merge_top_followers.py`
7. `scripts/analyze_fundraising_candidates.py`

**Acceptance criteria:**
- [ ] All 7 files are gone
- [ ] `grep -r "extract_raw_candidates\|ai_analysis_orchestrator\|aggregate_and_rank\|format_reports\|generate_db_reports\|merge_top_followers\|analyze_fundraising" src/ scripts/ tests/` — zero matches

---

### STEP 15: Update `CLAUDE.md`

**Action:** Add pipeline documentation to CLAUDE.md.

**Add:**
- AFK pipeline usage: `./scripts/run_afk_pipeline.sh`
- Prerequisites (Chrome on 9222, CSV exists)
- Phase CLI: `python3 scripts/run_pipeline.py --phase N`
- Where to find logs: `data/pipeline_state.md`, `logs/`
- Cleanup: `CLEANUP_INTERMEDIARY=1`

**Acceptance criteria:**
- [ ] CLAUDE.md mentions `run_afk_pipeline.sh`
- [ ] CLAUDE.md mentions `run_pipeline.py`

---

### STEP 16: Phase C Gate — Final Verification

**Gate checks:**
1. All 7 old scripts deleted (verified by file absence)
2. No dangling imports (grep returns zero)
3. `pytest tests/ -v` — zero failures, zero errors
4. Full checklist (13 items from plan):
   - [ ] `src/browser.py` exists, imports clean
   - [ ] `src/candidate_extractor.py` exists, imports clean
   - [ ] `src/analysis.py` exists, imports clean
   - [ ] `src/db_reports.py` exists, imports clean
   - [ ] `src/ai_reports.py` exists, imports clean
   - [ ] `src/pipeline.py` exists, has phase functions
   - [ ] `scripts/run_pipeline.py` exists, --help works
   - [ ] `scripts/run_afk_pipeline.sh` exists, executable
   - [ ] `scripts/enrich.py` imports from src.browser
   - [ ] 7 old scripts deleted
   - [ ] All tests pass
   - [ ] CLAUDE.md updated
   - [ ] No stdlib violations in src/

**On pass:** `git commit -A` — deletions, new files, CLAUDE.md.

**Acceptance criteria:**
- [ ] 13/13 checklist items verified
- [ ] Git commit: `"Phase C gate PASS — 7 old scripts deleted, CLAUDE.md updated"`

---

## 3. File Inventory

### Created (new files)

| # | File | ~Lines | Step |
|---|------|--------|------|
| 1 | `src/browser.py` | 180 | 2 |
| 2 | `src/candidate_extractor.py` | 250 | 3 |
| 3 | `src/analysis.py` | 160 | 4 |
| 4 | `src/db_reports.py` | 390 | 5 |
| 5 | `src/ai_reports.py` | 300 | 6 |
| 6 | `scripts/run_pipeline.py` | 100 | 9 |
| 7 | `scripts/run_afk_pipeline.sh` | 350 | 11 |
| 8 | `tests/unit/test_browser.py` | 150 | 2 |
| 9 | `tests/unit/test_candidate_extractor.py` | 200 | 3 |
| 10 | `tests/unit/test_analysis.py` | 150 | 4 |
| 11 | `tests/unit/test_ai_reports.py` | 200 | 6 |

### Modified

| File | Step | Change |
|------|------|--------|
| `src/pipeline.py` | 8 | Expand from ~30 to ~100 lines |
| `scripts/enrich.py` | 10 | Slim from ~445 to ~120 lines |
| `.gitignore` | 1 | Add 4 intermediary patterns |
| `CLAUDE.md` | 15 | Add pipeline docs |
| `tests/unit/test_generate_db_reports.py` | 13 | Renamed to `test_report_generator.py` |

### Deleted

| File | Step |
|------|------|
| `scripts/extract_raw_candidates.py` | 14 |
| `scripts/ai_analysis_orchestrator.py` | 14 |
| `scripts/aggregate_and_rank.py` | 14 |
| `scripts/format_reports.py` | 14 |
| `scripts/generate_db_reports.py` | 14 |
| `scripts/merge_top_followers.py` | 14 |
| `scripts/analyze_fundraising_candidates.py` | 14 |

---

## 4. Execution Order

```
Step 1:  .gitignore update
   |
   ├── Step 2:  src/browser.py + test          ─┐
   ├── Step 3:  src/candidate_extractor.py + test │
   ├── Step 4:  src/analysis.py + test            ├── PARALLEL
   ├── Step 5:  src/db_reports.py                 │
   └── Step 6:  src/ai_reports.py + test         ─┘
         |
   Step 7:  PHASE A GATE (pytest + code review + git commit)
         |
   ├── Step 8:  Expand src/pipeline.py   ─┐
   ├── Step 9:  scripts/run_pipeline.py    ├── PARALLEL
   ├── Step 10: Slim scripts/enrich.py     │
   └── Step 11: scripts/run_afk_pipeline.sh┘
         |
   Step 12: PHASE B GATE (pytest + integration test + git commit)
         |
   Step 13: Rename test file
         |
   Step 14: Delete 7 old scripts
         |
   Step 15: Update CLAUDE.md
         |
   Step 16: PHASE C GATE (full checklist + git commit)
         |
      BUILD COMPLETE
```

---

## 5. Constraints

- `data/followers.db` is git-tracked and irreplaceable — NEVER delete/drop, back up before bulk writes
- All `src/` is stdlib only — no pip installs except `pytest`/`playwright`
- `classifier.py` rules are priority-ordered — NEVER reorder
- All 1,354 lines of existing report tests must be preserved
- Intermediary pipeline files (`data/candidates_raw.json`, `data/analysis_batches/`, `data/analysis_results/`, `data/followers.db.bak`) are gitignored — never committed

---

## 6. Verification (after all steps complete)

1. `pytest tests/ -v` — all green
2. `python3 scripts/run_pipeline.py --phase 1 --csv tests/fixtures/sample_followers.csv --db /tmp/test.db` — exits 0, valid JSON
3. `bash -n scripts/run_afk_pipeline.sh` — syntax valid
4. `git log --oneline` — shows 3 phase gate commits
5. `.gitignore` blocks intermediary files
6. No old scripts remain
7. All src modules importable
