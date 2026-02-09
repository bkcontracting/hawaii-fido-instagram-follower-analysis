# Forensic Deep Dive: Hawaii Fi-Do Instagram Follower Analysis Codebase

## What This Project Is (The 30-Second Version)

**Hawaii Fi-Do** is a service dog nonprofit in Hawaii. They exported ~830 Instagram followers to a CSV and want to answer: *"Which of these followers might donate money, partner with us, or spread our message?"*

This codebase is a **3-phase data pipeline** that turns that raw CSV into a prioritized, scored list of outreach targets.

```
Phase 1: CSV file  -->  SQLite database (parse & store)
Phase 2: Visit each Instagram profile --> classify & score each follower
Phase 3: Query the database with slash commands to find the best prospects
```

---

## Tracing a Single Follower: `aloha_coffee_co`

Here's exactly what happens to one follower record, function by function, line by line.

### Starting data (from the CSV)

```csv
handle,display_name,profile_url
aloha_coffee_co,Aloha Coffee Co,https://www.instagram.com/aloha_coffee_co/
```

### What the browser finds on their Instagram page

```json
{
  "follower_count": 2500,
  "following_count": 800,
  "post_count": 150,
  "bio": "Coffee roasters in Kailua. Locally sourced, freshly roasted.",
  "website": "https://alohacoffee.com",
  "is_verified": false,
  "is_private": false,
  "is_business": true
}
```

---

### PHASE 1: Getting into the database

**Step 1 - Entry point** (`src/pipeline.py:7-15`)

```python
def run_phase1(csv_path, db_path):
    followers = parse_followers(csv_path)   # Step 2
    init_db(db_path)                        # Step 3
    count = insert_followers(db_path, followers)  # Step 4
    return {"inserted": count}
```

**Step 2 - CSV parsing** (`src/csv_parser.py:14-67`)

The parser opens the CSV, reads by column headers (not position), and processes each row:

```
Line 34: Opens the file with UTF-8 encoding
Line 35: csv.DictReader reads headers → finds "handle", "display_name", "profile_url"
Line 38: Validates "handle" column exists → YES, continues
Line 48: handle = "aloha_coffee_co".strip() → "aloha_coffee_co"
Line 49: Not empty, not seen before → continues
Line 51: Adds to seen set
Line 53: display_name = "Aloha Coffee Co".strip() → "Aloha Coffee Co"
Line 54: Not empty → keeps it (otherwise would fall back to handle)
Line 57: profile_url = "https://www.instagram.com/aloha_coffee_co/"
Line 59-65: Appends dict to results
```

**Result after Step 2:**
```python
{"handle": "aloha_coffee_co", "display_name": "Aloha Coffee Co", "profile_url": "https://www.instagram.com/aloha_coffee_co/"}
```

**Step 3 - Database creation** (`src/database.py:49-56`)

```
Line 51: Opens SQLite connection to data/followers.db
Line 53: Runs CREATE TABLE IF NOT EXISTS → creates 22-column followers table
Line 54: Commits
```

**Step 4 - Insertion** (`src/database.py:59-81`)

```
Line 72-76: INSERT OR IGNORE INTO followers (handle, display_name, profile_url, status)
            VALUES ('aloha_coffee_co', 'Aloha Coffee Co', 'https://...', 'pending')
Line 77: rowcount = 1 (new record)
Line 78: Commits
```

**Database state after Phase 1:**
```
id: 1
handle: aloha_coffee_co
display_name: Aloha Coffee Co
profile_url: https://www.instagram.com/aloha_coffee_co/
status: pending
created_at: 2026-02-09T...
(all other 16 columns: NULL)
```

---

### PHASE 2: Enrichment Pipeline

**Step 5 - Entry point** (`src/pipeline.py:18-30`)

```python
def run_phase2(db_path, fetcher_fn):
    result = run_all(db_path, fetcher_fn)  # Step 6
```

**Step 6 - Main loop** (`src/batch_orchestrator.py:225-258`)

```
Line 236: batch = create_batch(db_path) → Step 7
Line 237: batch is not empty → continues
Line 247: result = run_with_retries(db_path, batch, fetcher_fn) → Step 8
```

**Step 7 - Batch claiming** (`src/batch_orchestrator.py:21-69`)

```
Line 33: BEGIN IMMEDIATE → acquires write lock (prevents two agents grabbing same records)
Line 36-41: Crash recovery check → any records stuck in 'processing' > 5 min? Reset to 'pending'
Line 44: batch_size = 5 (from config)
Line 45-48: SELECT * FROM followers WHERE status = 'pending' LIMIT 5
            → Returns our aloha_coffee_co record (and up to 4 others)
Line 53-59: UPDATE followers SET status = 'processing' WHERE handle IN ('aloha_coffee_co', ...)
Line 62: COMMIT
```

**Step 8 - Process with retries** (`src/batch_orchestrator.py:153-222`)

```
Line 165: result = process_batch(db_path, batch, fetcher_fn) → Step 9
```

**Step 9 - Processing the follower** (`src/batch_orchestrator.py:72-150`)

This is the heart of the pipeline. For aloha_coffee_co:

```
Line 82: handle = "aloha_coffee_co"
Line 83: profile_url = "https://www.instagram.com/aloha_coffee_co/"
Line 87: enriched = fetcher_fn("aloha_coffee_co", "https://...")
         → Browser visits the Instagram page
         → profile_parser.py extracts structured data (see Step 9a)
         → Returns the JSON blob we saw above
Line 88: page_state = "normal"
Line 90: Not "not_found" or "suspended" → continues
Line 99: Not "rate_limited" or "login_required" → continues
Line 106: bio = "Coffee roasters in Kailua. Locally sourced, freshly roasted."
Line 107: combined_text = "aloha_coffee_co Aloha Coffee Co Coffee roasters in Kailua. Locally sourced, freshly roasted."
```

**Step 9a - Location detection** (`src/location_detector.py:75-107`)

```
Line 109 (batch_orchestrator): hi = is_hawaii(combined_text)
```

The location detector scans for Hawaii signals in the combined text:

```
Weak signals scanned first:
  - "aloha" → MATCH! (found in "aloha_coffee_co") → +0.15, blanks out that span
  - "hawaiian" → no match

Strong city signals:
  - "honolulu" → no match
  - "kailua" → MATCH! (found in "Coffee roasters in Kailua") → +0.40, blanks it out
  - (remaining cities) → no match

Strong state signals:
  - "hawai'i" → no match
  - "hawaii" → no match (note: "aloha" was already blanked out)
  - "HI" → no match (case-sensitive, only matches uppercase)
  - "808" → no match

Medium island signals → no matches
Medium other signals → no matches

Total confidence: 0.15 + 0.40 = 0.55
is_hawaii(0.55 >= 0.4) → TRUE
```

**Result:** `is_hawaii = True` with confidence 0.55. The "Kailua" city name alone would have been enough (0.40 >= 0.40 threshold).

**Step 9b - Classification** (`src/classifier.py:267-417`)

```
Line 113 (batch_orchestrator): classification = classify(profile)
```

The classifier checks rules in strict priority order. For aloha_coffee_co:

```
Line 273: text = "aloha_coffee_co aloha coffee co coffee roasters in kailua. locally sourced, freshly roasted." (lowercased)
Line 274: is_biz = True (Instagram marked this as a business account)
Line 275: is_hi = True (from location detection above)
Line 276: follower_count = 2500

Rule 0 - service_dog_aligned?
  Line 281: _has_any(text, ["service dog", "therapy dog", ...]) → NO. Skip.

Rule 1 - bank_financial?
  Line 287: regex for "bank" → NO. "financial", "credit union" → NO. Skip.

Rule 2 - corporate?
  Line 293: _has_any(text, ["electric", "utility", "airline", ...]) → NO
  Line 297: is_biz AND follower_count >= 25000? → True AND 2500 >= 25000? → NO. Skip.

Rule 3 - pet_industry?
  Line 304: _has_any(text, _STRONG_PET_KEYWORDS) → NO (no vet/trainer/kennel keywords)
  Line 309: _has_any(text, _PET_KEYWORDS) → NO. Skip.

Rule 4a - government?
  Line 315: _has_any(text, ["government organization", "military", ...]) → NO. Skip.

Rule 4b - organization?
  Line 321: _has_any(text, ["church", "school", "rotary", "club", ...]) → NO. Skip.

Rule 5 - charity?
  Line 357: _has_any(text, ["rescue", "humane", "nonprofit", ...]) → NO. Skip.

Rule 6 - elected_official?
  Line 364: _has_any(text, ["council", "mayor", ...]) → NO. Skip.

Rule 7 - media_event?
  Line 370: _has_any(text, ["event", "tournament", "photographer", ...]) → NO. Skip.

Rule 8 - business_local? ← THIS IS THE ONE
  Line 376: (is_biz=True OR _has_any(text, _STRONG_BUSINESS_KEYWORDS)?) AND is_hi=True?
            → True AND True → YES!
  Line 377-379: Returns category="business_local"

  _business_subcategory("...coffee roasters..."):
    Line 227: "restaurant" in text? NO. "cafe" in text? NO. "coffee" in text? YES!
    → Returns "restaurant" (coffee shops are grouped with restaurants)

FINAL: {"category": "business_local", "subcategory": "restaurant", "confidence": 0.7}
```

**Key insight:** Even though "coffee" isn't in `_STRONG_BUSINESS_KEYWORDS`, the `is_business` flag from Instagram was enough to trigger Rule 8. The `is_hawaii` flag from the location detector made it "local" instead of "national".

**Step 9c - Priority scoring** (`src/scorer.py:5-147`)

```
Line 117 (batch_orchestrator): scoring = score(profile)
```

Walking through every scoring check:

```
Line 13: category = "business_local"
Line 15: is_hawaii = True
Line 16: is_business = True
Line 17: is_verified = False
Line 18: is_private = False
Line 19: follower_count = 2500
Line 20: post_count = 150
Line 21: bio = "Coffee roasters in Kailua. Locally sourced, freshly roasted."
Line 22: website = "https://alohacoffee.com"

BASE SCORES:
  Line 25-27: is_hawaii=True → +30, reasons: ["hawaii(+30)"]
  Line 50-52: category="business_local" → +20, reasons: [..., "local_biz(+20)"]
  Line 63-65: is_business=True → +20, reasons: [..., "business(+20)"]
  Line 67-69: is_verified=False → skip

Running total: 70

REACH SCORE:
  Line 72: 2500 >= 50000? NO
  Line 74: 2500 >= 10000? NO
  Line 76: 2500 >= 5000? NO
  Line 78: 2500 >= 1000? YES → +5, reasons: [..., "reach(+5)"]

Running total: 75

ENGAGEMENT INDICATORS:
  Line 86-88: website="https://alohacoffee.com" (truthy) → +5, reasons: [..., "website(+5)"]
  Line 90-92: post_count=150 > 100? YES → +5, reasons: [..., "active_posting(+5)"]

  bio_lower = "coffee roasters in kailua. locally sourced, freshly roasted."

  Line 97-101: Mission alignment? "service dog|therapy dog|assistance|disability" in bio? → NO
  Line 104-108: Dogs/pets bio? "dogs?|pets?|dog mom|..." in bio? → NO
  Line 110-112: "community|giving" in bio? → NO
  Line 115-117: "veteran|military" in bio? → NO
  Line 120-122: "sponsor|partner|donate|fundrais" in bio? → NO

Running total: 85

PENALTIES:
  Line 125-127: charity with non-partner subcategory? → NO (not charity)
  Line 129-131: is_private? → NO
  Line 133-135: spam_bot? → NO
  Line 137-139: no bio? → NO (has bio)

Running total: 85

CLAMP:
  Line 142: max(0, min(100, 85)) → 85

FINAL: {
  "priority_score": 85,
  "priority_reason": "hawaii(+30), local_biz(+20), business(+20), reach(+5), website(+5), active_posting(+5)"
}
```

**Tier assignment** (`src/scorer.py:150-159`):
```
Line 152: 85 >= 80 → "Tier 1 - High Priority"
```

**Step 9d - Database update** (`src/batch_orchestrator.py:119-138`)

```python
update_data = {
    "follower_count": 2500,
    "following_count": 800,
    "post_count": 150,
    "bio": "Coffee roasters in Kailua. Locally sourced, freshly roasted.",
    "website": "https://alohacoffee.com",
    "is_verified": False,
    "is_private": False,
    "is_business": True,
    "category": "business_local",
    "subcategory": "restaurant",
    "confidence": 0.7,
    "is_hawaii": True,
    "location": "Hawaii",
    "priority_score": 85,
    "priority_reason": "hawaii(+30), local_biz(+20), business(+20), reach(+5), website(+5), active_posting(+5)",
    "status": "completed",     # Not private, so "completed" (not "private")
    "processed_at": "2026-02-09T..."
}
```

`database.update_follower()` at `src/database.py:96-113` builds a dynamic UPDATE:
```sql
UPDATE followers SET follower_count=?, following_count=?, post_count=?, bio=?, ...
WHERE handle = 'aloha_coffee_co'
```

---

### PHASE 3: Querying with Slash Commands

Now aloha_coffee_co sits in the database as a fully enriched record. Here's how each slash command surfaces it:

**`/prospects`** — Score 85 >= 60 threshold? YES. Shows up as:
```
| aloha_coffee_co | Aloha Coffee Co | business_local | 85 | Tier 1 | hawaii(+30), local_biz(+20)... | 2500 | Yes |
```

**`/donors`** — Category in ('bank_financial', 'business_local', 'organization')? YES (business_local). Score >= 50? YES (85). Shows up with bio, website, and profile URL.

**`/outreach`** — Score >= 40? YES. Grouped under "Tier 1" section.

**`/summary`** — Counted in: business_local category, Hawaii bucket, Tier 1 bucket, potentially top 10 overall.

**`/export`** — Written to `output/top_prospects.csv` (score >= 60) and `output/full_export.csv` (all records).

---

## Every Script: Quick Reference Card

### Core Pipeline (`src/`)

| File | One-Line Purpose | Called By |
|------|-----------------|-----------|
| `config.py` | 3 tuneable settings (batch size, subagents, retries) | batch_orchestrator |
| `csv_parser.py` | CSV → clean list of dicts | pipeline.py |
| `database.py` | All SQLite reads/writes | pipeline.py, batch_orchestrator |
| `profile_parser.py` | Raw Instagram page text → structured data (regex, no AI) | fetcher_fn in enrich.py |
| `location_detector.py` | Bio text → is this person in Hawaii? | batch_orchestrator |
| `classifier.py` | Profile → 1 of 14 categories (first-match rules) | batch_orchestrator |
| `scorer.py` | Profile + category → 0-100 score + tier | batch_orchestrator |
| `batch_orchestrator.py` | Pulls batches, runs the pipeline, handles crashes/retries | pipeline.py |
| `pipeline.py` | Two clean entry points: `run_phase1()` and `run_phase2()` | User/slash commands |

### Utility Scripts (`scripts/`)

| File | One-Line Purpose | When You'd Use It |
|------|-----------------|-------------------|
| `enrich.py` | Standalone browser enrichment via Playwright | Running enrichment without Claude Code |
| `monitor_enrichment.py` | Prints processed count every 30s | While enrichment is running (hours) |
| `rescore.py` | Re-applies classifier + scorer to all completed records | After changing classification/scoring rules |
| `reset_errors.py` | Resets error records to pending for retry | After transient failures (network, rate limits) |
| `extract_raw_candidates.py` | Dumps completed profiles to JSON + fetches websites | Before AI analysis track |
| `ai_analysis_orchestrator.py` | Splits candidates into batches of 50 | Before parallel AI subagent analysis |
| `analyze_fundraising_candidates.py` | Prints summary statistics of candidate data | Sanity check before AI analysis |
| `format_reports.py` | AI output JSON → markdown report + CSV spreadsheets | After AI analysis completes |
| `finalize_analysis.sh` | Runs aggregation + formatting in one command | One-click finalization |

### Slash Commands (`.claude/skills/`)

| Command | What It Shows |
|---------|--------------|
| `/prospects` | Top engagement candidates (score >= 60) |
| `/summary` | Full statistical dashboard |
| `/donors` | Banks, businesses, organizations worth asking for money |
| `/outreach` | Tiered contact list with profile URLs |
| `/export` | Writes CSV + markdown files to `output/` |

---

## Two Parallel Analysis Approaches

This project has **two ways** to analyze the data:

### Approach 1: Deterministic (the `src/` modules)
- Rule-based keywords + scoring formulas
- Fast, cheap, reproducible
- Good for broad categorization
- This is the primary pipeline (Phases 1-2-3)

### Approach 2: AI-Driven (the `scripts/` AI files)
- Claude reads each profile holistically
- Understands context a keyword matcher can't
- More expensive but more nuanced
- Supplementary track for deep analysis of ~444 completed profiles
- Flow: `extract_raw_candidates.py` → `ai_analysis_orchestrator.py` → parallel Claude subagents → `format_reports.py`

---

## Key Architecture Decisions (Why Things Are the Way They Are)

1. **No external dependencies** — stdlib-only Python (except pytest and playwright) keeps it lightweight
2. **Batch size = 5** — Optimized for Claude Code subagent token costs
3. **Deterministic parsing** — Regex extraction of Instagram pages saves ~500-1000 LLM tokens per profile vs having AI read the page
4. **Crash recovery** — Records stuck in 'processing' > 5 min auto-reset. You can kill the process and restart safely.
5. **WAL journal mode** — Allows 2 parallel subagents to read/write the same SQLite database without locking conflicts
6. **First-match classification** — Rules are checked in priority order; first match wins. This means "service dog trainer" matches `service_dog_aligned` (Rule 0) not `pet_industry` (Rule 3).
7. **Span blanking in location detection** — When "aloha" matches as a weak signal, that text span is replaced with spaces so the strong "hawaii" pattern can't re-match overlapping text.
8. **Private accounts get status "private"** — Not "completed" or "error". They're enriched but have limited data.

---

## Real Database Examples

Here are actual records from the live database (830 followers, 444 completed, 386 private):

### Highest-Scored Followers

| Handle | Category | Score | Reason |
|--------|----------|-------|--------|
| `hawaiidoggiebakery` | pet_industry | 95 | hawaii(+30), pet(+25), business(+20), reach(+10), website(+5), active_posting(+5) |
| `vibecreativehawaii` | business_local | 95 | hawaii(+30), local_biz(+20), business(+20), reach(+15), website(+5), active_posting(+5) |
| `assistancedogsofhawaii` | service_dog_aligned | 85 | hawaii(+30), service_dog(+35), reach(+5), website(+5), active_posting(+5), donor_language(+5) |
| `guidedogsofhawaii` | service_dog_aligned | 80 | hawaii(+30), service_dog(+35), reach(+5), website(+5), active_posting(+5) |

### All 15 Categories in the Database

```
bank_financial, business_local, business_national, charity,
corporate, elected_official, influencer, media_event,
organization, personal_engaged, personal_passive, pet_industry,
service_dog_aligned, spam_bot, unknown
```

### How `assistancedogsofhawaii` Traces Through (Real Data)

This is an actual record — not a hypothetical:

```
Handle:          assistancedogsofhawaii
Display Name:    Assistance Dogs Of Hawaii
Followers:       4,152
Bio:             "Nonprofit organization. Assistance Dogs of Hawaii is a 501(c)(3)
                  charitable organization that provides children and adults with
                  professionally..."
Website:         www.assistancedogshawaii.org/donate
Is Business:     No (Instagram didn't flag it)
Is Verified:     No
Is Private:      No

Location Detection:
  "assistance dogs of hawaii" → "hawaii" matches strong state signal → +0.40
  is_hawaii = True (0.40 >= 0.40 threshold)

Classification:
  Rule 0 check: "assistance dog" in text? YES → service_dog_aligned
  (Never reaches Rule 5 charity despite having "nonprofit", "501c")

Scoring:
  hawaii(+30) + service_dog(+35) + reach(+5) [4152 >= 1000]
  + website(+5) + active_posting(+5) [970 posts > 100]
  + donor_language(+5) ["donate" in bio]
  = 85 → Tier 1

Status: completed
```

---

## How to Run Each Phase

### Phase 1: Import CSV
```bash
# Via Python
python3 -c "from src.pipeline import run_phase1; print(run_phase1('data/followers.csv', 'data/followers.db'))"
```

### Phase 2: Enrich profiles
```bash
# 1. Launch Chrome with remote debugging
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug

# 2. Log into Instagram in that Chrome window

# 3. Run enrichment
python3 scripts/enrich.py --db data/followers.db --delay-min 3 --delay-max 5

# Monitor progress in another terminal
python3 scripts/monitor_enrichment.py --db data/followers.db
```

### Phase 3: Query results
```
/prospects    — see top candidates
/donors       — see financial targets
/outreach     — see tiered contact list
/summary      — see full dashboard
/export       — write CSV/markdown to output/
```

### Maintenance
```bash
# After changing scoring rules
python3 scripts/rescore.py --db data/followers.db --dry-run   # preview
python3 scripts/rescore.py --db data/followers.db              # apply

# After network errors
python3 scripts/reset_errors.py

# AI analysis track
python3 scripts/extract_raw_candidates.py
python3 scripts/ai_analysis_orchestrator.py
# (run Claude subagents on batch files)
python3 scripts/format_reports.py
```
