# Token Optimization & Deterministic Parsing — Changes

Branch: `claude/optimize-batch-size-HN2Gp`
Date: 2026-02-06

## Problem

The `/enrich` skill's subagents were burning excessive tokens due to:
1. Large batch sizes causing quadratic context growth (full conversation replay each turn)
2. LLM reasoning to parse numbers, detect page states, and extract fields — work a regex can do perfectly
3. Accessibility tree reads returning 10-20K tokens of irrelevant page chrome

## Summary of Changes

| File | Change |
|------|--------|
| `src/config.py` | BATCH_SIZE default 20 → 5 |
| `src/profile_parser.py` | New deterministic parser (parse_count, detect_page_state, parse_profile_page) |
| `.claude/skills/enrich.md` | Token optimization docs, JS-first extraction, mandatory parser use |
| `.gitignore` | Exclude `__pycache__/` |
| `tests/unit/test_config.py` | Updated expected BATCH_SIZE default |
| `tests/unit/test_profile_parser.py` | 37 new tests for parser |

---

## Commit-by-Commit Detail

### 1. `ac48d62` — Reduce BATCH_SIZE from 20 to 5 to cut subagent token usage ~3x

**Why:** Claude Code subagents replay the full conversation history on every API turn.
With 20 profiles per batch (~40 turns), context grows quadratically. Each new turn
pays for all previous profile reads, tool calls, and results.

**What changed:**
- `src/config.py`: `BATCH_SIZE` default changed from `20` to `5`
- `tests/unit/test_config.py`: Updated assertion from `== 20` to `== 5`
- `.claude/skills/enrich.md`: Added token optimization rationale with cost comparison table

**Impact:**

| Batch Size | Est. input tokens per 20 profiles | Relative cost |
|------------|-----------------------------------|---------------|
| 20 (old)   | ~1.76M                            | 1.0x          |
| 10         | ~920K                             | 0.52x         |
| **5 (new)**| **~560K**                         | **0.32x**     |
| 1          | ~340K + high startup overhead     | ~0.25x        |

Batch size 5 is the sweet spot: ~3x cheaper than 20, without the excessive
subagent-launch overhead of batch size 1. Still overridable via `BATCH_SIZE` env var.

---

### 2. `3965384` — Add .gitignore to exclude Python \_\_pycache\_\_ bytecode files

**Why:** Running pytest generated `.pyc` files that showed up as untracked.
These should never be committed.

**What changed:**
- `.gitignore`: Added `__pycache__/`

---

### 3. `ce812cc` — Add deterministic profile parser to eliminate LLM parsing overhead

**Why:** Subagents were using LLM reasoning to parse "64.1K" → 64100, detect
"Sorry, this page isn't available" as a 404, and extract structured fields from
raw page text. This burns ~500-1000 reasoning tokens per profile for work that
regex handles perfectly — faster, cheaper, and 100% consistent.

**What changed:**

New file `src/profile_parser.py` with three functions:

- `parse_count(text)` — Converts Instagram abbreviated counts to integers.
  Handles K/M/B suffixes, commas, and floating point precision.
  `"64.1K"` → `64100`, `"2.5M"` → `2500000`, `"1,234"` → `1234`

- `detect_page_state(text)` — Identifies page condition from raw text.
  Returns: `normal`, `not_found`, `suspended`, `rate_limited`, or `login_required`

- `parse_profile_page(text)` — Full extraction from raw page text.
  Returns dict with: `follower_count`, `following_count`, `post_count`,
  `bio`, `website`, `is_verified`, `is_private`, `is_business`, `page_state`

Updated `.claude/skills/enrich.md`:
- Subagent instructions now mandate `parse_profile_page()` — no manual parsing
- Extraction method flipped to JS-first (small innerText) over accessibility tree (huge)
- Added "keep responses minimal" instruction to prevent narration bloat
- Error handling now driven by `page_state` from parser

New file `tests/unit/test_profile_parser.py` — 37 tests covering:
- All count formats (plain, commas, K/M/B, lowercase, whitespace, edge cases)
- All page states (normal, not_found, suspended, rate_limited, login_required)
- Full page parsing (counts, booleans, website, bio, private accounts, large counts)

---

### 4. `3695d21` — Round abbreviated counts to suffix-level granularity (64.1K → 64000)

**What:** Changed `parse_count()` to round to suffix unit: `64.1K` → `64000`.

**Reverted in next commit** — this was the wrong direction.

---

### 5. `2333d70` — Revert rounding: preserve Instagram precision (64.1K → 64100)

**Why:** The goal is to preserve the precision Instagram provides, not discard it.
`64.1K` means approximately 64,100 — that's the best data we have.

**What changed:**
- `src/profile_parser.py`: Reverted to `round(number * multipliers[suffix])` which
  preserves decimal precision while fixing floating point drift
  (`64.1 * 1000 = 64099.999...` → `round()` → `64100`)
- `tests/unit/test_profile_parser.py`: All expectations restored to precision-preserving values

---

## Architecture — Subagent Flow for 1 Batch of 5 Followers

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (main agent)                        │
│  Launches 2 subagents in parallel, each with an assigned tab_id    │
└──────────────┬──────────────────────────────────┬───────────────────┘
               │                                  │
       ┌───────▼───────┐                  ┌───────▼───────┐
       │  SUBAGENT 1   │                  │  SUBAGENT 2   │
       │   (tab1_id)   │                  │   (tab2_id)   │
       └───────┬───────┘                  └───────────────┘
               │
═══════════════╪══════════════════════════════════════════════════════
               │
  STEP 1: CLAIM BATCH                    [batch_orchestrator.py:12-52]
               │
               ▼
  ┌─────────────────────────────┐
  │  create_batch(db_path)      │
  │                             │
  │  1. Crash recovery:         │
  │     Reset any 'processing'  │
  │     records older than 5min │
  │     back to 'pending'       │
  │                             │
  │  2. SELECT 5 pending rows   │  ◄── config.BATCH_SIZE = 5
  │                             │
  │  3. Atomically UPDATE all 5 │
  │     to status='processing'  │
  │     with timestamp          │
  │                             │
  │  Returns: [follower1..5]    │
  └──────────────┬──────────────┘
                 │
                 ▼
  ═══════════════════════════════
  STEP 2: LOOP OVER 5 FOLLOWERS          [batch_orchestrator.py:55-115]
  ═══════════════════════════════
                 │
       ┌─────── ▼ ──────── FOR EACH FOLLOWER ──────────────────────┐
       │                                                            │
       │  STEP 2a: FETCH PAGE                    [browser via MCP]  │
       │  ┌──────────────────────────────────────────────────────┐  │
       │  │  Navigate to profile_url in assigned tab             │  │
       │  │  Wait 2s for load                                    │  │
       │  │  javascript_tool(tabId):                             │  │
       │  │    document.querySelector('header')                  │  │
       │  │      ?.closest('main')?.innerText                    │  │
       │  │      || document.body.innerText                      │  │
       │  └────────────────────┬─────────────────────────────────┘  │
       │                       │ raw_text                           │
       │                       ▼                                    │
       │  STEP 2b: PARSE PAGE              [profile_parser.py:70-157]│
       │  ┌──────────────────────────────────────────────────────┐  │
       │  │  parse_profile_page(raw_text)                        │  │
       │  │                                                      │  │
       │  │  1. detect_page_state(text)                          │  │
       │  │     ├─ "sorry, this page isn't available" → not_found│  │
       │  │     ├─ "account has been suspended"       → suspended│  │
       │  │     ├─ "try again later"                  → rate_ltd │  │
       │  │     ├─ "log in" + "to see"                → login_req│  │
       │  │     └─ otherwise                          → normal   │  │
       │  │                                                      │  │
       │  │  If not normal → return early with page_state        │  │
       │  │                                                      │  │
       │  │  2. Extract counts via regex + parse_count():        │  │
       │  │     "64.1K followers" → parse_count("64.1K") → 64100│  │
       │  │     "2.5M followers"  → parse_count("2.5M")  → 2.5M │  │
       │  │     "1,234 posts"     → parse_count("1,234") → 1234 │  │
       │  │                                                      │  │
       │  │  3. Detect booleans:                                 │  │
       │  │     is_verified: "Verified badge" (not "Get verified")│  │
       │  │     is_private:  "This account is private"           │  │
       │  │     is_business: contact/email/call/category/shop    │  │
       │  │                                                      │  │
       │  │  4. Extract website URL (filter instagram.com)       │  │
       │  │  5. Extract bio text (between counts & posts grid)   │  │
       │  │                                                      │  │
       │  │  Returns: {                                          │  │
       │  │    follower_count, following_count, post_count,      │  │
       │  │    bio, website, is_verified, is_private,            │  │
       │  │    is_business, page_state                           │  │
       │  │  }                                                   │  │
       │  └────────────────────┬─────────────────────────────────┘  │
       │                       │ enriched                           │
       │                       ▼                                    │
       │  STEP 2c: HAWAII DETECTION      [location_detector.py:75-107]│
       │  ┌──────────────────────────────────────────────────────┐  │
       │  │  combined = "{handle} {display_name} {bio}"          │  │
       │  │  is_hawaii(combined) → hawaii_confidence() >= 0.4    │  │
       │  │                                                      │  │
       │  │  Signal tiers (additive, capped at 1.0):             │  │
       │  │  ┌────────┬────────┬──────────────────────────────┐  │  │
       │  │  │ Strong │  0.4   │ Hawaii, HI, Honolulu,        │  │  │
       │  │  │        │        │ Kailua, Kapolei, Waikiki,    │  │  │
       │  │  │        │        │ Hilo, Kona, 808, etc.        │  │  │
       │  │  ├────────┼────────┼──────────────────────────────┤  │  │
       │  │  │ Medium │  0.3   │ Oahu, Maui, Kauai,           │  │  │
       │  │  │        │        │ Big Island, HNL, 967xx/968xx │  │  │
       │  │  ├────────┼────────┼──────────────────────────────┤  │  │
       │  │  │ Weak   │  0.15  │ Aloha, Hawaiian              │  │  │
       │  │  └────────┴────────┴──────────────────────────────┘  │  │
       │  │                                                      │  │
       │  │  Returns: True/False                                 │  │
       │  └────────────────────┬─────────────────────────────────┘  │
       │                       │ is_hawaii: bool                    │
       │                       ▼                                    │
       │  STEP 2d: CLASSIFY               [classifier.py:103-194]   │
       │  ┌──────────────────────────────────────────────────────┐  │
       │  │  classify(profile) — 13 rules, first match wins:     │  │
       │  │                                                      │  │
       │  │   #  Category            Conf   Key trigger           │  │
       │  │  ─── ─────────────────── ────── ───────────────────  │  │
       │  │   1  bank_financial      0.90   bank/financial/credit │  │
       │  │   2  pet_industry        0.85   pet kw + is_business  │  │
       │  │   3  organization        0.80   church/school/club    │  │
       │  │   4  charity             0.85   rescue/nonprofit/501c │  │
       │  │   5  elected_official    0.80   council/mayor + hawaii│  │
       │  │   6  media_event         0.75   event/news/photo      │  │
       │  │   7  business_local      0.70   is_business + hawaii  │  │
       │  │   8  business_national   0.70   is_business + !hawaii │  │
       │  │   9  influencer          0.70   10K+ followers + !biz │  │
       │  │  10  spam_bot            0.80   following>10x & <5post│  │
       │  │  11  personal_engaged    0.60   50+ posts + !biz      │  │
       │  │  12  personal_passive    0.50   <=50 posts + !biz     │  │
       │  │  13  unknown             0.30   fallback              │  │
       │  │                                                      │  │
       │  │  Each also returns a subcategory (e.g. veterinary,   │  │
       │  │  credit_union, church, restaurant, etc.)             │  │
       │  │                                                      │  │
       │  │  Returns: {category, subcategory, confidence}        │  │
       │  └────────────────────┬─────────────────────────────────┘  │
       │                       │                                    │
       │                       ▼                                    │
       │  STEP 2e: SCORE                    [scorer.py:5-111]        │
       │  ┌──────────────────────────────────────────────────────┐  │
       │  │  score(profile) → 0-100 priority score               │  │
       │  │                                                      │  │
       │  │  BONUSES:                    PENALTIES:               │  │
       │  │  ┌─────────────────────┐     ┌──────────────────┐    │  │
       │  │  │ Hawaii       +30    │     │ charity    -50   │    │  │
       │  │  │ bank         +30    │     │ private    -20   │    │  │
       │  │  │ pet/org/elec +25    │     │ spam      -100   │    │  │
       │  │  │ business     +20    │     │ no_bio     -10   │    │  │
       │  │  │ influencer   +20    │     └──────────────────┘    │  │
       │  │  │ media        +15    │                              │  │
       │  │  │ verified     +10    │     REACH TIERS:             │  │
       │  │  │ reach      +5-20   │     50K+ (+20), 10K+ (+15)  │  │
       │  │  │ website       +5    │     5K+ (+10), 1K+ (+5)     │  │
       │  │  │ active posts  +5    │                              │  │
       │  │  │ dogs in bio  +10    │     TIERS:                   │  │
       │  │  │ community     +5    │     80+ = Tier 1 (High)     │  │
       │  │  └─────────────────────┘     60+ = Tier 2 (Medium)   │  │
       │  │                              40+ = Tier 3 (Low)      │  │
       │  │  Clamped to [0, 100]         <40 = Tier 4 (Skip)     │  │
       │  │                                                      │  │
       │  │  Returns: {priority_score, priority_reason}          │  │
       │  └────────────────────┬─────────────────────────────────┘  │
       │                       │                                    │
       │                       ▼                                    │
       │  STEP 2f: WRITE TO DB              [database.py:81-93]     │
       │  ┌──────────────────────────────────────────────────────┐  │
       │  │  update_follower(db_path, handle, {                  │  │
       │  │    follower_count:  64100,                           │  │
       │  │    following_count: 345,                             │  │
       │  │    post_count:      42,                              │  │
       │  │    bio:             "Hawaii dog rescue...",          │  │
       │  │    website:         "linktr.ee/hawaiidogs",          │  │
       │  │    is_verified:     True,                            │  │
       │  │    is_private:      False,                           │  │
       │  │    is_business:     True,                            │  │
       │  │    category:        "business_local",                │  │
       │  │    subcategory:     "general",                       │  │
       │  │    confidence:      0.7,                             │  │
       │  │    is_hawaii:       True,                            │  │
       │  │    location:        "Hawaii",                        │  │
       │  │    priority_score:  85,                              │  │
       │  │    priority_reason: "hawaii(+30), business(+20)...", │  │
       │  │    status:          "completed",                     │  │
       │  │    processed_at:    "2026-02-06T...",                │  │
       │  │  })                                                  │  │
       │  │                                                      │  │
       │  │  UPDATE followers SET ... WHERE handle = ?           │  │
       │  └──────────────────────────────────────────────────────┘  │
       │                                                            │
       │  On exception → update_follower(status='error', msg=str(e))│
       │                                                            │
       │  Random delay 3-5s before next profile                     │
       │                                                            │
       └───────────── NEXT FOLLOWER (repeat 5x) ───────────────────┘
                 │
                 ▼
  ═══════════════════════════════
  STEP 3: RETURN RESULT
  ═══════════════════════════════
                 │
                 ▼
  Return to orchestrator:
  {completed: 4, errors: 1, rate_limited: false}
```

### Data Flow — Single Follower

```
Instagram page (raw HTML)
  │
  ▼ javascript_tool → innerText (~200 tokens vs ~15K for accessibility tree)
  │
  ▼ parse_profile_page()        ← deterministic, zero LLM tokens
  │  ├─ parse_count("64.1K") → 64100
  │  ├─ is_verified, is_private, is_business
  │  └─ bio, website
  │
  ▼ is_hawaii("{handle} {name} {bio}")   ← regex signal scoring
  │  └─ "Honolulu" → confidence 0.4 → True
  │
  ▼ classify(profile)            ← 13 keyword rules, first match wins
  │  └─ is_business + is_hawaii → "business_local" (0.7)
  │
  ▼ score(profile)               ← additive bonuses/penalties, clamp 0-100
  │  └─ hawaii(+30) + business(+20) + reach(+5) + website(+5) = 60
  │
  ▼ update_follower()            ← single UPDATE to SQLite
```

### Estimated Combined Token Savings

| Optimization                    | Savings        |
|---------------------------------|----------------|
| Batch 20 → 5                   | ~3x fewer      |
| JS instead of accessibility tree| ~5x less data  |
| Deterministic parser            | ~500-1000/profile |
| Minimal output instructions     | ~1.5x less bloat |
| **Combined estimate**           | **~20-30x cheaper per run** |
