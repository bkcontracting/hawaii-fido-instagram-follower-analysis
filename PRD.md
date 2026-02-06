# Product Requirements Document: Instagram Follower Analysis Tool

## Project Overview

**Project Name:** Hawaii Fi-Do Instagram Follower Analyzer
**Version:** 1.3
**Date:** February 4th, 2026
**Owner:** Hawaii Fi-Do

### Purpose

Build an automated tool to analyze Hawaii Fi-Do's Instagram followers (~830) to identify high-value engagement candidates for fundraising, partnerships, and community outreach. The tool will extract follower data, classify each account, and produce a prioritized list of prospects.

### Background

Hawaii Fi-Do is a service dog nonprofit organization. To grow community support and fundraising efforts, they need to understand their Instagram follower base and identify:
- Local Hawaii businesses that could sponsor or partner
- Organizations (churches, schools, community groups) for outreach
- Influential accounts that could amplify their message
- Individuals with high engagement potential

---

## Goals & Success Criteria

### Primary Goals

1. **Extract** all follower data from saved Instagram CSV into a structured database
2. **Enrich** each follower profile with additional data (follower count, bio, classification)
3. **Classify** followers into actionable categories (business, organization, personal, etc.)
4. **Prioritize** followers based on fundraising/partnership potential
5. **Output** a ranked list of top engagement candidates

### Success Criteria

- [ ] Successfully parse 100% of followers from source CSV
- [ ] Visit and analyze 95%+ of follower profiles (some may be private/deleted)
- [ ] Classify each follower with 80%+ accuracy
- [ ] Produce final ranked list with clear reasoning for each recommendation
- [ ] Complete full analysis without Instagram rate-limiting/blocking

---

## System Architecture

### Phase 1: CSV Parsing

**Input:** `data/followers_validated.csv` (saved followers page)

> **Note:** The source CSV contains 7 columns: `handle`, `display_name`, `profile_url`, `completeness_score`, `is_edge_case`, `edge_case_types`, `validation_notes`. The extra columns are validation metadata from a preprocessing step. The parser must select only the 3 core fields (`handle`, `display_name`, `profile_url`) and ignore any additional columns.

**Process:**
1. Parse CSV to extract follower entries
2. For each follower, capture:
   - Display name
   - Instagram handle (@username)
   - Profile URL
3. Store in SQLite database with status "pending"

**Output:** SQLite database with ~830 follower records

### Phase 2: Profile Enrichment

**Input:** SQLite database of followers

**Process:**
1. Launch 2 parallel browser subagents
2. Each agent:
   - Claims a "pending" follower from the database
   - Navigates to their Instagram profile
   - Extracts profile data (see Data Model below)
   - Updates database record with enriched data
   - Marks record as "completed"
3. Implement delays (3-5 seconds) between requests to avoid detection

**Output:** Enriched database with full profile data and classifications

### Phase 3: Interactive Analysis (Slash Commands)

**Input:** Completed SQLite database at `data/followers.db`

Phase 3 replaces static file generation with **5 Claude Code slash commands** that query the database live. Each command has smart defaults (useful with zero arguments) and optional filters for drilling down.

**Architecture:** All 5 commands are prompt-driven Claude Code skills (`.claude/skills/` markdown files). They instruct Claude to query SQLite directly and format results as markdown tables in the terminal. No new Python source modules are needed for Phase 3. The DB path `data/followers.db` is auto-detected relative to project root.

#### `/prospects` — Top Engagement Candidates
- **Default:** score >= 60, sorted by priority_score desc, limit 25
- **Filters:** `--category`, `--min-score`, `--hawaii`, `--limit`
- **Columns:** handle, display_name, category, priority_score, tier, priority_reason, follower_count, is_hawaii

#### `/summary` — Analysis Dashboard
- **Default:** Full statistical overview:
  - Total follower count + status breakdown
  - Hawaii vs. non-Hawaii (count + avg score)
  - Category breakdown (count + avg score per category)
  - Tier distribution
  - Top 10 overall
  - Top 10 per category
  - "Needs Review" list (unknown + error accounts)

#### `/donors` — Financial Resource Targets
- **Default:** bank_financial + business_local + organization with score >= 50, sorted by priority_score desc
- **Filters:** `--hawaii`, `--min-score`
- **Columns:** handle, display_name, category, subcategory, priority_score, bio (truncated 80 chars), website

#### `/outreach` — Actionable Contact List
- **Default:** score >= 40, sorted by priority_score desc, grouped by tier, limit 20
- **Filters:** `--category`, `--tier`
- **Columns:** handle, display_name, category, priority_score, bio (truncated), website, profile_url

#### `/export` — File Export (preserves original static export behavior)
- **Default:** Writes all 3 files to `output/`:
  - `top_prospects.csv` — score >= 60, sorted by priority_score desc
  - `full_export.csv` — all followers
  - `analysis_summary.md` — full statistical breakdown
- **Flags:** `--prospects`, `--full`, `--summary` to export just one
- **`top_prospects.csv` columns:** handle, display_name, category, priority_score, tier, priority_reason, follower_count, bio, website, is_hawaii, profile_url
- **`full_export.csv` columns:** handle, display_name, category, subcategory, priority_score, tier, priority_reason, follower_count, following_count, post_count, bio, website, is_verified, is_private, is_business, is_hawaii, location, confidence, status, profile_url
- **`analysis_summary.md` contents:** Total follower count, Hawaii vs. non-Hawaii breakdown (count + avg score), category breakdown (count + avg score per category), tier distribution, top 10 overall, top 10 per category, "Needs Review" section (unknown + error accounts)
- If no enriched data exists, exports are created with headers only and summary notes "No enriched data available".

---

## Data Model

### Follower Record Schema

```
followers (
  id              INTEGER PRIMARY KEY,
  handle          TEXT UNIQUE,        -- @username
  display_name    TEXT,               -- Full display name
  profile_url     TEXT,               -- Instagram profile link

  -- Enriched data (Phase 2)
  follower_count  INTEGER,            -- Number of followers
  following_count INTEGER,            -- Number following
  post_count      INTEGER,            -- Total posts
  bio             TEXT,               -- Profile bio text
  website         TEXT,               -- External link if present
  is_verified     BOOLEAN,            -- Blue checkmark
  is_private      BOOLEAN,            -- Private account
  is_business     BOOLEAN,            -- Business/creator account

  -- Classification (Phase 2)
  category        TEXT,               -- See categories below
  subcategory     TEXT,               -- See subcategory values below
  location        TEXT,               -- Detected location
  is_hawaii       BOOLEAN,            -- Hawaii-based indicator
  confidence      REAL,               -- Classification confidence 0-1

  -- Scoring (Phase 2)
  priority_score  INTEGER,            -- Final ranking score
  priority_reason TEXT,               -- Why this score

  -- Metadata
  status          TEXT,               -- pending, processing, completed, error, private
  error_message   TEXT,               -- If status=error
  processed_at    DATETIME,           -- When enriched
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

> **Note:** `tier` is not stored in the database. Slash commands and exports derive it from `priority_score` using `get_tier()` logic or equivalent SQL CASE WHEN expressions.

### Classification Categories

| Category | Description | Priority |
|----------|-------------|----------|
| `business_local` | Hawaii-based business | HIGH |
| `organization` | rotary club, member club (golf, elks, etc), church, school, community group | HIGH |
| `bank_financial` | Banks, financial services | HIGH |
| `pet_industry` | Pet/animal businesses: vets, trainers, pet stores, groomers, pet food, dog services. Commercial only — nonprofits stay as `charity`. | HIGH |
| `influencer` | High follower count (10k+) | HIGH |
| `elected_official` | Hawaii-based government elected official such as councilman | HIGH |
| `media_event` | Local media, events, photographers, press outlets | MEDIUM |
| `business_national` | Non-Hawaii business | MEDIUM |
| `personal_engaged` | Active personal account | LOW |
| `personal_passive` | Low activity personal | SKIP |
| `charity` | Other nonprofits/charities | SKIP |
| `spam_bot` | Fake/bot accounts | SKIP |
| `unknown` | Could not classify | REVIEW |

### Subcategory Values

Subcategories are best-effort from bio keywords and are **not used in scoring**:

| Category | Subcategory values |
|----------|-------------------|
| `pet_industry` | `veterinary`, `trainer`, `pet_store`, `groomer`, `pet_food`, `general` |
| `business_local` | `restaurant`, `retail`, `service`, `real_estate`, `general` |
| `organization` | `church`, `school`, `club`, `community_group`, `general` |
| `bank_financial` | `bank`, `credit_union`, `financial_advisor`, `general` |
| `media_event` | `event`, `photographer`, `news`, `media`, `general` |
| All others | `general` (default) |

### Classification Decision Rules

Rules are evaluated in priority order — first match wins. All keyword checks scan **handle + display_name + bio** (not just bio):

```
1.  bio/handle/name contains "bank" or "financial" or "credit union"       → bank_financial
2.  bio/handle/name contains pet industry keywords¹
    AND (is_business=True OR commercial signal²)                           → pet_industry
3.  bio/handle/name contains "church","school","rotary","club","golf"
    AND NOT charity keywords                                               → organization
4.  bio/handle/name contains "rescue","humane","nonprofit","501c","shelter","charity"  → charity
5.  bio/handle/name contains "council","mayor","senator","representative",
    "governor" AND is_hawaii=True                                          → elected_official
6.  bio/handle/name contains "event","tournament","open","festival",
    "magazine","news","photographer","media","press"                       → media_event
7.  is_business=True AND is_hawaii=True                                    → business_local
8.  is_business=True AND is_hawaii=False                                   → business_national
9.  follower_count >= 10000 AND is_business=False                          → influencer
10. following_count > 10 * follower_count AND post_count < 5               → spam_bot
11. post_count > 50 AND !is_business                                       → personal_engaged
12. post_count <= 50 AND !is_business                                      → personal_passive
13. No signals match                                                       → unknown (confidence < 0.5)
```

¹ **Pet industry keywords:** "veterinar", "vet clinic", "pet ", "dog trainer", "groomer", "kennel", "animal hospital", "canine", "paws", "pet food", "pet supply", "dog gym"

² **Commercial signals:** handle/name/bio suggests a business (e.g., "shop", "store", "service", "clinic", "supply", "co", "inc")

**Key changes from earlier version:**
- `bank_financial` is rule 1 (fixes Hawaii bank → business_local misclassification)
- `pet_industry` is rule 2 — requires business signal to exclude nonprofits
- `organization` excludes charity keywords to prevent "foundation" overlap
- Rules scan **handle + display_name + bio** (not just bio) for keyword matches
- `business_local`/`business_national` moved after keyword-based categories

The classifier returns `{category, subcategory, confidence}` where confidence reflects signal strength (0.3–0.9).

### Location Detection Signals

Look for these Hawaii indicators in bio/name/handle:
- State: Hawaii, HI, Hawai'i, Hawaiʻi (with okina)
- Islands: Oahu, Maui, Kauai, Big Island, Molokai, Lanai
- Cities: Honolulu, Waikiki, Kailua, Hilo, Lahaina, Kona, Kapolei, Aiea, Pearl City, Kaneohe, Waipahu, Mililani
- Area code: 808
- Airport code: HNL
- Zip prefix: 967, 968
- Phrases: "Aloha", "Hawaiian"

### Location Confidence Scoring

`hawaii_confidence(text) -> float` returns 0.0–1.0 based on weighted signal matching:

| Signal Strength | Examples | Weight |
|----------------|----------|--------|
| Strong | City name (Honolulu, Kailua, Kapolei, Aiea, Pearl City, Kaneohe, Waipahu, Mililani), State name (Hawaii, HI, Hawai'i, Hawaiʻi), Area code (808) | +0.4 each |
| Medium | Island name (Oahu, Maui, Kauai), Airport code (HNL), Zip prefix (967, 968) | +0.3 each |
| Weak | Cultural ("Aloha", "Hawaiian") | +0.15 each |

Multiple signals compound (capped at 1.0). Examples:
- "Honolulu, Hawaii | Local pet shop" → >= 0.8 (city + state)
- "Aloha! Based in NYC" → <= 0.3 (weak signal alone)
- No Hawaii signals → 0.0

`is_hawaii(text) -> bool` returns True if `hawaii_confidence(text) >= 0.4`.

---

## Scoring Algorithm

### Priority Score Components (0-100 scale)

```
Base Score:
  - Hawaii-based:          +30 points
  - Bank/financial:        +30 points  (increased — larger donation capacity)
  - Pet industry:          +25 points  (NEW)
  - Organization:          +25 points
  - Elected official:      +25 points  (increased — gov't funding channels)
  - Business account:      +20 points
  - Media/event:           +15 points  (NEW)
  - Influencer:            +20 points  (NEW)
  - Verified:              +10 points

Reach Score (based on followers):
  - 50k+ followers:        +20 points
  - 10k-50k followers:     +15 points
  - 5k-10k followers:      +10 points
  - 1k-5k followers:       +5 points
  - <1k followers:         +0 points

Engagement Indicators:
  - Has website:                      +5 points
  - Active posting (>100 posts):      +5 points  (threshold now defined)
  - Bio mentions dogs/pets:           +10 points (does NOT stack with pet_industry)
  - Bio mentions community/giving:    +5 points

No-Stack Rule:
  If classified as `pet_industry`, the `dogs/pets bio` bonus (+10) does not apply
  (already factored into the pet_industry category score).

Penalties:
  - Other charity:         -50 points
  - Private account:       -20 points
  - Spam indicators:       -100 points
  - No bio:                -10 points
```

### Reference Scoring Examples

| Account | Factors | Score | Tier |
|---------|---------|-------|------|
| Hawaii bank | hawaii(30) + bank(30) + business(20) | 80 | Tier 1 |
| Hawaii pet store | hawaii(30) + pet(25) + business(20) | 75 | Tier 2 |
| Hawaii pet store + website | above + website(5) | 80 | Tier 1 |
| Hawaii councilmember, verified, 10k+ | hawaii(30) + elected(25) + verified(10) + reach(15) | 80 | Tier 1 |
| Hawaii church, 5k followers, website | hawaii(30) + org(25) + reach(10) + website(5) | 70 | Tier 2 |
| Non-Hawaii influencer, 50k+, website | influencer(20) + reach(20) + website(5) | 45 | Tier 3 |

### Final Tiers

| Score Range | Tier String | Meaning |
|-------------|------------|---------|
| 80–100 | `"Tier 1 - High Priority"` | Immediate outreach candidates |
| 60–79 | `"Tier 2 - Medium Priority"` | Strong prospects for engagement |
| 40–59 | `"Tier 3 - Low Priority"` | Worth monitoring/following |
| 0–39 | `"Tier 4 - Skip"` | Low priority |

Score is clamped to 0–100 (never negative). `priority_reason` is a string listing which factors applied, e.g. `"hawaii(+30), business(+20), website(+5)"`.

---

## Technical Requirements

### Dependencies

- Python 3, pytest, SQLite
- Claude Code with browser automation (Claude-in-Chrome MCP)

### Configuration

All pipeline settings live in `src/config.py` with environment variable overrides:

| Setting | Default | Env Override | Purpose |
|---------|---------|-------------|---------|
| `BATCH_SIZE` | 20 | `BATCH_SIZE` | Profiles per batch |
| `MAX_SUBAGENTS` | 2 | `MAX_SUBAGENTS` | Concurrent browser agents |
| `MAX_RETRIES` | 3 | `MAX_RETRIES` | Retry attempts per batch |

No external dependencies beyond stdlib for the config module.

### Resumability & Fault Tolerance

The system is designed for **cross-session resumability**:

| Feature | Implementation |
|---------|---------------|
| Batch size | 20 profiles per batch (~10 min) |
| State storage | SQLite (truth) |
| Crash recovery | 'processing' records >5 min auto-reset to 'pending' |
| Session handoff | New Claude session auto-detects and resumes |

### Rate Limiting Strategy

To avoid Instagram detection:
1. **Delays:** 3-5 second random delay between profile visits
2. **Parallelism:** Maximum 2 concurrent browser agents
3. **Sessions:** Use logged-in Instagram session (user must be authenticated)
4. **Backoff:** If rate limited, pause for 5 minutes then resume

### Error Handling

| Error | Action |
|-------|--------|
| Profile not found | Mark as `status=error`, continue |
| Private account | Mark as `status=private`, capture limited data |
| Rate limited | Pause 5 min, retry with longer delays |
| Page timeout | Retry once, then mark error |
| Browser crash | Resume from SQLite (truth)|

---

### Progress Display

During enrichment, show:
```
Follower Enrichment Progress
============================
Total: 830
Completed: 415 (50%)
Processing: 2
Pending: 401
Errors: 8
Private: 4

Currently processing:
  Agent 1: @aloha_coffee_co (416/830)
  Agent 2: @maui_surf_school (417/830)

Estimated time remaining: ~45 minutes
```

---

## Deliverables

### Phase 1 Output
- `data/followers.db` — SQLite database with parsed followers, all `status='pending'`

### Phase 2 Output
- Updated `data/followers.db` with enriched, classified, and scored records

### Phase 3 Output
- `.claude/skills/prospects.md` — /prospects slash command
- `.claude/skills/summary.md` — /summary slash command
- `.claude/skills/donors.md` — /donors slash command
- `.claude/skills/outreach.md` — /outreach slash command
- `.claude/skills/export.md` — /export slash command

---

## Module API Reference

### `src/config.py`
```python
BATCH_SIZE: int     # default 20, env override BATCH_SIZE
MAX_SUBAGENTS: int  # default 2, env override MAX_SUBAGENTS
MAX_RETRIES: int    # default 3, env override MAX_RETRIES
```

### `src/csv_parser.py`
```python
parse_followers(filepath: str) -> list[dict]
# Returns list of {handle, display_name, profile_url}
# Uses column headers (not positional indexing) to select fields.
# Extra columns beyond handle, display_name, profile_url are silently ignored.
# This ensures compatibility with the validated CSV which includes additional
# metadata columns (completeness_score, is_edge_case, edge_case_types, validation_notes).
# Deduplicates by handle, falls back display_name to handle if empty
# Preserves Unicode (Hawaiian diacritics)
# Raises FileNotFoundError for missing file
# Raises ParseError for missing 'handle' column

class ParseError(Exception): ...
```

### `src/database.py`
```python
init_db(db_path: str) -> None
# Creates SQLite file + followers table. Idempotent.

insert_followers(db_path: str, followers: list[dict]) -> int
# Returns count inserted. Skips duplicates by handle. Sets status='pending'.

get_pending(db_path: str, limit: int) -> list[dict]
# Returns up to `limit` followers with status='pending'

update_follower(db_path: str, handle: str, data: dict) -> None
# Updates arbitrary fields on the row matching handle

get_status_counts(db_path: str) -> dict
# Returns {'pending': N, 'completed': N, 'error': N, ...}
```

### `src/location_detector.py`
```python
is_hawaii(text: str) -> bool
# Returns True if any Hawaii signal matches. Safe on None/empty.

hawaii_confidence(text: str) -> float
# Returns 0.0–1.0 weighted confidence score. See Location Confidence Scoring.
```

### `src/classifier.py`
```python
classify(profile: dict) -> dict
# Returns {category: str, subcategory: str, confidence: float}
# See Classification Decision Rules for rule priority order.
# Uses location_detector for Hawaii determination.
```

### `src/scorer.py`
```python
score(profile: dict) -> dict
# Returns {priority_score: int, priority_reason: str}
# Score clamped 0–100. See Scoring Algorithm.

get_tier(score: int) -> str
# Maps score to tier string. See Final Tiers.
```

### `src/batch_orchestrator.py`
```python
create_batch(db_path: str) -> list[dict]
# Before claiming new records, resets any status='processing' records with
# processed_at older than 5 minutes back to status='pending' (crash recovery).
# Claims up to BATCH_SIZE pending records, marks them status='processing' atomically.
# Returns empty list when no pending records remain.

process_batch(db_path: str, batch: list[dict], fetcher_fn) -> dict
# Returns {completed: int, errors: int}
# For each follower: fetcher_fn(handle, profile_url) -> enriched dict
# Then classify(), score(), update_follower().
# Successes → status='completed'. Failures → status='error' with error_message.

run_with_retries(db_path: str, batch: list[dict], fetcher_fn) -> dict
# Returns {completed: int, errors: int, retries_used: int, exhausted: bool}
# Attempts up to MAX_RETRIES total times (including the initial attempt).
# Before each retry, filters the batch to only error records, then re-calls process_batch.
# Resets error records to 'pending' between attempts.
# After final retry, errors become permanent.

run_all(db_path: str, fetcher_fn) -> dict
# Returns {batches_run: int, total_completed: int, total_errors: int, stopped: bool, reason: str}
# Processes all pending in batches. Stops on exhausted retries with
# {stopped: True, reason: "batch_exhausted"}. Previously completed records untouched.
```

### `src/pipeline.py`
```python
run_phase1(csv_path: str, db_path: str) -> dict
# Returns {inserted: int}
# Calls: parse_followers → init_db → insert_followers
# Idempotent: re-running inserts 0 duplicates.

run_phase2(db_path: str, fetcher_fn) -> dict
# Returns {batches_run: int, total_completed: int, total_errors: int, stopped: bool}
# Calls: run_all (handles batching, retries internally)
# Returns immediately with {batches_run: 0} if no pending records.
```

---

## Batch Orchestrator Behavior

### Atomic Batch Claiming

`create_batch` first resets any `status='processing'` records with `processed_at` older than 5 minutes back to `status='pending'` (crash recovery). It then reads BATCH_SIZE from config, queries pending records, and marks them `status='processing'` in a single transaction. This prevents two concurrent agents from claiming the same records.

### Processing Pipeline Per Follower

```
fetcher_fn(handle, profile_url) → enriched profile dict
  ↓
combined_text = f"{handle} {display_name} {bio or ''}"
is_hawaii(combined_text) → boolean
hawaii_confidence(combined_text) → float
  ↓
classify(profile) → {category, subcategory, confidence}
  ↓
score(profile) → {priority_score, priority_reason}
  ↓
update_follower(db_path, handle, all_enriched_fields + status='completed')
```

> **Note:** Location detection function signatures are unchanged — callers provide richer combined text instead of bio alone.

On fetcher error for a single follower: `status='error'`, `error_message` saved, processing continues for remaining followers in the batch.

### Retry Semantics

1. `run_with_retries` calls `process_batch`
2. If errors remain, filters the batch to only error records, resets them from `status='error'` back to `status='pending'`
3. Re-calls `process_batch` with only the filtered error records (up to MAX_RETRIES total attempts including the initial attempt)
4. After final attempt, any remaining errors become permanent (`status='error'`)
5. Returns `{exhausted: True}` if errors remain after all retries

### Stop Behavior

`run_all` loops: `create_batch` → `run_with_retries` → repeat until no pending records. If a batch exhausts retries, processing **stops** (returns `{stopped: True, reason: "batch_exhausted"}`). Already-completed records are never touched.

---

## Build Order & Dependency Graph

### Story Groups

| Group | Module | Stories | Depends On |
|-------|--------|---------|------------|
| 0 | Project bootstrap | 0.1 Setup, 0.2 Config | — |
| 8 | Test fixtures | 8.1 Fixtures | Group 0 |
| 1 | `csv_parser` | 1.1 Parse, 1.2 Edge cases, 1.3 Errors | Group 8 |
| 2 | `database` | 2.1 Schema, 2.2 Insert, 2.3 Queries | Group 8 |
| 3 | `location_detector` | 3.1 Signals, 3.2 Confidence | Group 8 |
| 4 | `classifier` | 4.1 Categories, 4.2 Rules | Group 3 |
| 5 | `scorer` | 5.1 Score, 5.2 Factors, 5.3 Tiers | Group 3, 4 (test data only) |
| 6 | `batch_orchestrator` | 6.1 Batch, 6.2 Process, 6.3 Retry, 6.4 Loop | Groups 2, 3, 4, 5 |
| 7 | `pipeline` | 7.1 Phase 1, 7.2 Phase 2 | Groups 1, 6 |
| 9 | `skills` | 9.1 prospects, 9.2 summary, 9.3 donors, 9.4 outreach, 9.5 export | Groups 5, 7 |

### Parallelization Map

```
Sequential: Group 0 → Group 8
                       ↓
            ┌──────────┼──────────┐
            ↓          ↓          ↓
Parallel:  Group 1   Group 2   Group 3
                       ↓          ↓
                       │    ┌─────┤
                       │    ↓     ↓
                       │  Group 4  │
                       │    ↓     ↓
                       │  Group 5  │
                       ↓    ↓     ↓
Sequential:          Group 6 ←────┘
                       ↓
                    Group 7
                       ↓
                    Group 9
```

Groups 1, 2, and 3 can run as parallel subagents (they write to separate files with no shared imports). Group 4 depends on 3. Group 5 depends on 3 and 4. Group 6 depends on 2, 3, 4, 5. Group 7 depends on 1 and 6. Group 9 (skills) depends on 5 and 7.

---

## Test Fixture Specifications

All fixtures live in `tests/fixtures/` and must be created before module implementation begins.

### `sample_followers.csv`
5 records with clean data:
- One business account
- One organization
- One personal account
- One with Unicode (Hawaiian diacritics like Kuʻike)
- One with a website URL

### `edge_cases.csv`
- Duplicate handles (same handle appears twice)
- Empty display_name field
- Unicode characters (Kuʻike)
- Commas in display_name (quoted)
- Extra whitespace in fields
- Extra columns beyond core 3 (to verify parser ignores non-core columns)

### `invalid.csv`
- Missing the required `handle` column header

### `empty.csv`
- Header row only, no data rows

### `mock_profiles.json`
5 enriched profile dicts matching the handles in `sample_followers.csv`:

| Handle | Category | Key Fields |
|--------|----------|-----------|
| (business) | `business_local` | `is_hawaii=True`, `is_business=True`, bio "Pet supplies in Kailua" |
| (organization) | `organization` | `is_hawaii=True`, bio "Rotary Club of Honolulu" |
| (personal) | `influencer` | `follower_count >= 10000` |
| (unicode) | `personal_engaged` | `post_count > 50` |
| (website) | `spam_bot` | `following >> followers`, `post_count < 5` |

Each profile has: `follower_count`, `following_count`, `post_count`, `bio`, `website`, `is_verified`, `is_private`, `is_business`. Values must be deterministic so scoring tests in the scorer module can verify exact point totals.

---

## Development Workflow

### TDD Loop (per story)

```
1. Find the next story to implement (see Build Order)
2. RED:    Write failing test(s) from the acceptance criteria
           Run pytest — tests MUST fail
3. GREEN:  Write minimum code to make tests pass
           Run pytest — tests MUST pass
4. REFACTOR: Clean up while keeping all tests green
5. Run full suite: pytest tests/ -v
6. Commit with story reference
```

### Testing Commands

```bash
pytest tests/ -v                          # full suite
pytest tests/unit/test_<module>.py -v     # single module
pytest-watch tests/unit/test_<module>.py  # TDD watch mode
```

### Module Boundaries (for parallel subagent safety)

Each module lives in its own file. Import rules:
- `csv_parser.py` — no imports from other `src/` modules
- `database.py` — no imports from other `src/` modules
- `location_detector.py` — no imports from other `src/` modules
- `classifier.py` — imports `location_detector` only
- `scorer.py` — no imports from other `src/` modules
- `batch_orchestrator.py` — imports `database`, `location_detector`, `classifier`, `scorer`, `config`
- `pipeline.py` — imports all above

Parallel subagents building Groups 1, 2, and 3 write to separate files with no risk of merge conflicts.
