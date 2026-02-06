# Hawaii Fi-Do: Full Build Plan

> **Instructions for Claude Code session:** Execute tasks in wave order below. Use TDD for all Python tasks (red→green→refactor). Commit after each task. Full spec in `PRD.md`. Use the `superpowers:executing-plans` or `superpowers:subagent-driven-development` skill to execute this plan.

## Context
Greenfield Python+SQLite Instagram follower analysis tool. PRD at `PRD.md` (v1.3). TDD workflow throughout. No code exists yet — only `PRD.md`, `README.md`, `data/followers_validated.csv` (830 records), `.gitignore`. Branch: `build-branch-1`.

---

## Execution Strategy

### Wave Sequence
```
Wave 0 (sequential):  0.1 → 0.2 → 8.1
Wave 1 (3 parallel):  Task 1 | Task 2 | Task 3
Wave 2 (sequential):  Task 4 → Task 5 → Task 6 → Task 7
Wave 3 (5 parallel):  9.1 | 9.2 | 9.3 | 9.4 | 9.5
```

### Dependency Graph
```
0.1 → 0.2 → 8.1 ─┬─→ Task 1 (csv_parser) ──────────────────┐
                   ├─→ Task 2 (database) ─────────┐           │
                   └─→ Task 3 (location_detector) ─┤           │
                                                    ↓           │
                                              Task 4 (classifier)
                                                    ↓           │
                                              Task 5 (scorer)   │
                                                    ↓           │
                                              Task 6 (batch_orch)│
                                                    ↓           ↓
                                              Task 7 (pipeline) ←┘
                                                    ↓
                                     Task 9 (5 skills — parallel)
```

---

## Task List

### TASK 0.1 — Project Bootstrap
**Create directory structure and package files**
- Create: `src/__init__.py`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/fixtures/` (dir), `output/` (dir), `.claude/skills/` (dir)
- Verify: `pytest --collect-only` runs clean
- **Deps:** none | **Parallel:** no | **Size:** S
- **Commit:** "Bootstrap project structure"

### TASK 0.2 — Config Module (TDD)
**`src/config.py` — pipeline settings with env overrides**
- Constants: `BATCH_SIZE=20`, `MAX_SUBAGENTS=2`, `MAX_RETRIES=3`
- Each overridable via same-name env var (int conversion)
- No external deps beyond stdlib
- Tests: `tests/unit/test_config.py` — verify defaults + env overrides
- **Deps:** 0.1 | **Parallel:** no | **Size:** S
- **Commit:** "Add config module with env overrides"

### TASK 8.1 — Test Fixtures
**Create all fixture files in `tests/fixtures/`**
- `sample_followers.csv` — 5 records: business, org, personal, unicode (Kuʻike), website. Must include the 7 CSV columns from the validated format (handle, display_name, profile_url, completeness_score, is_edge_case, edge_case_types, validation_notes)
- `edge_cases.csv` — duplicate handles, empty display_name, unicode, commas in quoted fields, extra whitespace, extra columns
- `invalid.csv` — missing `handle` column header
- `empty.csv` — header row only, zero data rows
- `mock_profiles.json` — 5 enriched profile dicts matching sample_followers handles. Categories: business_local, organization, influencer, personal_engaged, spam_bot. Values must be deterministic for scorer tests (see PRD §Test Fixture Specifications)
- **Deps:** 0.1 | **Parallel:** no | **Size:** M
- **Commit:** "Add test fixtures"

---

### TASK 1 — CSV Parser (TDD) ⚡ PARALLEL
**`src/csv_parser.py` + `tests/unit/test_csv_parser.py`**

Stories (sequential within task):
1. **1.1 Parse:** `parse_followers(filepath) -> list[dict]` — reads by column headers (not positional), returns `{handle, display_name, profile_url}`, ignores extra columns
2. **1.2 Edge cases:** dedup by handle (first wins), fallback display_name→handle if empty, preserve Unicode, strip whitespace
3. **1.3 Errors:** `class ParseError(Exception)`, raise `FileNotFoundError` for missing file, raise `ParseError` for missing `handle` column, empty CSV returns `[]`

- **Deps:** 8.1 | **Parallel:** YES — with Tasks 2, 3 | **Size:** M
- **Import rules:** no imports from other `src/` modules
- **Commit:** "Add CSV parser with edge cases and errors"

### TASK 2 — Database (TDD) ⚡ PARALLEL
**`src/database.py` + `tests/unit/test_database.py`**

Stories (sequential within task):
1. **2.1 Schema:** `init_db(db_path)` — creates SQLite file + followers table (22 columns per PRD §Data Model). Idempotent.
2. **2.2 Insert:** `insert_followers(db_path, followers) -> int` — returns count inserted, skips duplicates by handle (INSERT OR IGNORE), sets `status='pending'`
3. **2.3 Queries:** `get_pending(db_path, limit) -> list[dict]`, `update_follower(db_path, handle, data)`, `get_status_counts(db_path) -> dict`

- **Deps:** 8.1 | **Parallel:** YES — with Tasks 1, 3 | **Size:** M
- **Import rules:** no imports from other `src/` modules
- **Commit:** "Add database module with CRUD operations"

### TASK 3 — Location Detector (TDD) ⚡ PARALLEL
**`src/location_detector.py` + `tests/unit/test_location_detector.py`**

Stories (sequential within task):
1. **3.1 Confidence:** `hawaii_confidence(text) -> float` — weighted signal matching:
   - Strong (+0.4): city names (Honolulu, Kailua, Kapolei, Aiea, Pearl City, Kaneohe, Waipahu, Mililani, Waikiki, Hilo, Lahaina, Kona), state (Hawaii, HI, Hawai'i, Hawaiʻi), area code 808
   - Medium (+0.3): island names (Oahu, Maui, Kauai, Big Island, Molokai, Lanai), airport HNL, zip prefix 967/968
   - Weak (+0.15): cultural ("Aloha", "Hawaiian")
   - Signals compound, capped at 1.0. None/empty → 0.0
2. **3.2 Threshold:** `is_hawaii(text) -> bool` — returns `hawaii_confidence(text) >= 0.4`. Safe on None/empty.

- **Deps:** 8.1 | **Parallel:** YES — with Tasks 1, 2 | **Size:** M
- **Import rules:** no imports from other `src/` modules
- **Commit:** "Add location detector with confidence scoring"

---

### TASK 4 — Classifier (TDD)
**`src/classifier.py` + `tests/unit/test_classifier.py`**

`classify(profile) -> {category, subcategory, confidence}`

13 rules in priority order — first match wins. All keyword checks scan **handle + display_name + bio**:
1. bank/financial/credit union → `bank_financial`
2. pet keywords¹ AND (is_business OR commercial signal²) → `pet_industry`
3. church/school/rotary/club/golf AND NOT charity keywords → `organization`
4. rescue/humane/nonprofit/501c/shelter/charity → `charity`
5. council/mayor/senator/representative/governor AND is_hawaii → `elected_official`
6. event/tournament/festival/magazine/news/photographer/media/press → `media_event`
7. is_business AND is_hawaii → `business_local`
8. is_business AND NOT is_hawaii → `business_national`
9. follower_count >= 10000 AND NOT is_business → `influencer`
10. following > 10× followers AND posts < 5 → `spam_bot`
11. posts > 50 AND NOT is_business → `personal_engaged`
12. posts <= 50 AND NOT is_business → `personal_passive`
13. fallback → `unknown` (confidence < 0.5)

¹ Pet keywords: "veterinar", "vet clinic", "pet ", "dog trainer", "groomer", "kennel", "animal hospital", "canine", "paws", "pet food", "pet supply", "dog gym"
² Commercial signals: "shop", "store", "service", "clinic", "supply", "co", "inc"

Subcategories per PRD §Subcategory Values. Imports `location_detector` only.

- **Deps:** Task 3 | **Parallel:** no | **Size:** L
- **Commit:** "Add classifier with 13 decision rules"

### TASK 5 — Scorer (TDD)
**`src/scorer.py` + `tests/unit/test_scorer.py`**

Stories (sequential within task):
1. **5.1 Score:** `score(profile) -> {priority_score, priority_reason}` — base components (hawaii +30, bank +30, pet +25, org +25, elected +25, business +20, media +15, influencer +20, verified +10)
2. **5.2 Factors:** reach score (5 follower tiers: 50k+ → +20, 10k-50k → +15, 5k-10k → +10, 1k-5k → +5, <1k → +0), engagement (+5 website, +5 posts>100, +10 dogs/pets bio, +5 community/giving bio), penalties (-50 charity, -20 private, -100 spam, -10 no bio). **No-stack rule:** pet_industry excludes dogs/pets bio bonus. Clamp 0–100.
3. **5.3 Tiers:** `get_tier(score) -> str` — 80–100→"Tier 1 - High Priority", 60–79→"Tier 2 - Medium Priority", 40–59→"Tier 3 - Low Priority", 0–39→"Tier 4 - Skip"

Verify against PRD §Reference Scoring Examples. No imports from other `src/` modules.

- **Deps:** Task 3 (test data needs hawaii checks), Task 4 (test data uses categories) | **Parallel:** no | **Size:** L
- **Commit:** "Add scorer with priority algorithm and tiers"

### TASK 6 — Batch Orchestrator (TDD)
**`src/batch_orchestrator.py` + `tests/unit/test_batch_orchestrator.py`**

Stories (sequential within task):
1. **6.1 Batch:** `create_batch(db_path) -> list[dict]` — crash recovery (reset stale `processing` records >5 min to `pending`), then atomically claim up to `BATCH_SIZE` pending records as `processing`. Empty list when exhausted.
2. **6.2 Process:** `process_batch(db_path, batch, fetcher_fn) -> {completed, errors}` — per follower: `fetcher_fn(handle, profile_url)` → build `combined_text = f"{handle} {display_name} {bio or ''}"` → `is_hawaii(combined_text)` + `hawaii_confidence(combined_text)` → `classify(profile)` → `score(profile)` → `update_follower()`. Error on single follower doesn't stop batch.
3. **6.3 Retry:** `run_with_retries(db_path, batch, fetcher_fn) -> {completed, errors, retries_used, exhausted}` — up to `MAX_RETRIES` total attempts. Filter to error records between retries, reset to pending, re-process. Final errors permanent.
4. **6.4 Loop:** `run_all(db_path, fetcher_fn) -> {batches_run, total_completed, total_errors, stopped, reason}` — loop create_batch→run_with_retries until no pending. Stop on `{stopped: True, reason: "batch_exhausted"}`.

Imports: `database`, `location_detector`, `classifier`, `scorer`, `config`

- **Deps:** Tasks 2, 3, 4, 5, 0.2 | **Parallel:** no | **Size:** L
- **Commit:** "Add batch orchestrator with retry logic"

### TASK 7 — Pipeline (TDD)
**`src/pipeline.py` + `tests/unit/test_pipeline.py`**

1. **7.1 Phase 1:** `run_phase1(csv_path, db_path) -> {inserted}` — calls `parse_followers()` → `init_db()` → `insert_followers()`. Idempotent.
2. **7.2 Phase 2:** `run_phase2(db_path, fetcher_fn) -> {batches_run, total_completed, total_errors, stopped}` — calls `run_all()`. Returns `{batches_run: 0}` if no pending.

Imports: all above modules.

- **Deps:** Tasks 1, 6 | **Parallel:** no | **Size:** M
- **Commit:** "Add pipeline runners for phase 1 and 2"

---

### TASK 9 — Slash Command Skills ⚡ PARALLEL
**5 markdown files in `.claude/skills/`** — prompt-driven, no Python. Each instructs Claude to query `data/followers.db` directly and format as markdown tables.

All 5 can be built in parallel (separate files):

1. **9.1 `/prospects`** → `.claude/skills/prospects.md` — default: score>=60, limit 25, sorted by priority_score desc. Filters: `--category`, `--min-score`, `--hawaii`, `--limit`. Columns: handle, display_name, category, priority_score, tier (derived via CASE WHEN), priority_reason, follower_count, is_hawaii

2. **9.2 `/summary`** → `.claude/skills/summary.md` — full dashboard: total count + status breakdown, Hawaii vs non-Hawaii (count + avg score), category breakdown, tier distribution, top 10 overall, top 10 per category, "Needs Review" list (unknown + error)

3. **9.3 `/donors`** → `.claude/skills/donors.md` — default: bank_financial + business_local + organization, score>=50, sorted desc. Filters: `--hawaii`, `--min-score`. Columns: handle, display_name, category, subcategory, priority_score, bio (truncated 80 chars), website

4. **9.4 `/outreach`** → `.claude/skills/outreach.md` — default: score>=40, grouped by tier, limit 20. Filters: `--category`, `--tier`. Columns: handle, display_name, category, priority_score, bio (truncated), website, profile_url

5. **9.5 `/export`** → `.claude/skills/export.md` — writes to `output/`: `top_prospects.csv` (score>=60), `full_export.csv` (all), `analysis_summary.md`. Flags: `--prospects`, `--full`, `--summary`. Column lists per PRD §/export. Handle no-data case (headers only).

- **Deps:** Tasks 5, 7 | **Parallel:** YES — all 5 with each other | **Size:** M total
- **Commit:** "Add slash command skills for analysis"

---

## Verification (after all tasks)
1. `pytest tests/ -v` — full suite green
2. `python -c "from src.pipeline import run_phase1; print(run_phase1('data/followers_validated.csv', '/tmp/test.db'))"` — parses all 830 records
3. Verify all 5 `.claude/skills/*.md` files exist and are well-formed
4. Run `/export` skill against a test DB to verify output file generation

## Key References
- Full spec: `PRD.md` (read this for any ambiguity)
- Source data: `data/followers_validated.csv` (7 columns, 830 records)
- DB schema: PRD §Data Model (22 columns, `tier` derived at query time)
- Classification rules: PRD §Classification Decision Rules (13 rules, priority order)
- Scoring algorithm: PRD §Scoring Algorithm (base + reach + engagement - penalties)
- Module import rules: PRD §Module Boundaries
