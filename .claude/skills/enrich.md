# Instagram Profile Enrichment Skill

## Description
Enrich all Instagram followers in the database by visiting each profile via browser automation, extracting profile data, classifying, scoring, and storing results. Designed to run fully autonomously with crash recovery.

## Restart instructions
Run `/enrich` or point Claude at this file. It will check DB status and resume from wherever it left off. No additional instructions needed.

## Architecture
- Main orchestrator runs a thin loop: check DB → launch 2 subagents → wait → repeat
- Each subagent processes exactly 1 batch (5 profiles) then terminates
- All state lives in SQLite — recovery is automatic
- Exactly 2 browser tabs created at startup, navigated in-place (never create new tabs during processing)

## Token Optimization — Why Batch Size 5
Claude Code subagents send full conversation history on every turn, so context
grows quadratically with profiles processed. Smaller batches keep each subagent's
context window short and discard accumulated page data between launches.

| Batch | Est. input tokens per 20 profiles | Relative cost |
|-------|-----------------------------------|---------------|
| 20    | ~1.76M                            | 1.0x (baseline) |
| 10    | ~920K                             | 0.52x         |
| **5** | **~560K**                         | **0.32x**     |
| 1     | ~340K + high startup overhead     | ~0.25x        |

Batch size 5 is the sweet spot: ~3x cheaper than 20, without the excessive
subagent-launch overhead of batch size 1. Override via `BATCH_SIZE` env var.

## Main Orchestrator Loop

```
STARTUP:
  1. Python: get_status_counts("data/followers.db")
  2. If no pending → FINISH
  3. Create MCP tab group + exactly 2 tabs
  4. Verify Instagram login on both tabs
  5. If first run (0 completed): run test batch of 5 first

LOOP (repeat until no pending):
  6. Check DB counts
  7. Print progress: "Completed: X/830 | Pending: Y | Errors: Z"
  8. If pending == 0 → FINISH
  9. Launch 2 Task subagents IN PARALLEL (general-purpose):
     - Agent 1: process 1 batch using tab1_id
     - Agent 2: process 1 batch using tab2_id
  10. Wait for both to return
  11. If rate_limited: sleep 5 minutes
  12. Go to step 6

FINISH:
  13. Print final DB status
  14. Display error records
  15. Run /summary
```

## Subagent Prompt Template

Each subagent receives the tab_id and processes one batch.
IMPORTANT: Keep responses minimal. Do not echo extracted data or explain
reasoning. Just call Python functions and return the final count.

1. Claim batch via `create_batch("data/followers.db")`
2. For each follower in batch:
   a. Navigate to profile_url in the assigned tab
   b. Wait 2s for page load
   c. Grab raw page text via `javascript_tool(tabId)`:
      `document.querySelector('header')?.closest('main')?.innerText || document.body.innerText`
   d. Pass raw text to deterministic parser — DO NOT parse counts yourself:
      `from src.profile_parser import parse_profile_page`
      `enriched = parse_profile_page(raw_text)`
   e. Check `enriched["page_state"]`: if "rate_limited" → stop and return
   f. Run through pipeline: is_hawaii() → classify() → score() → update_follower()
   g. Random delay 3-5s before next profile
3. Return ONLY: "{completed: N, errors: M, rate_limited: bool}"

## Extraction Method
- Primary: `javascript_tool(tabId)` → grab innerText → `parse_profile_page(text)`
- Fallback: `read_page(tabId)` accessibility tree → `parse_profile_page(text)`
- NEVER parse counts, detect page state, or extract fields manually — always
  use `parse_profile_page()` which handles K/M suffixes, page states, and all
  field extraction deterministically

## Error Handling
Page state is detected automatically by `parse_profile_page()`:
- `page_state == "not_found"`: status='error', error_message='not_found'
- `page_state == "suspended"`: status='error', error_message='suspended'
- `page_state == "rate_limited"`: stop batch, return rate_limited=true
- `page_state == "login_required"`: stop batch, return rate_limited=true
- `page_state == "normal"` + is_private=True: status='private' (enriched data captured)
- Page timeout: retry once, then status='error'

## Key Files
- `src/profile_parser.py` — **deterministic page parser** (parse_count, parse_profile_page, detect_page_state)
- `src/batch_orchestrator.py` — create_batch() with crash recovery
- `src/classifier.py` — 13-rule classification
- `src/scorer.py` — priority scoring 0-100
- `src/location_detector.py` — is_hawaii() detection
- `src/database.py` — update_follower(), get_status_counts()
- `data/followers.db` — SQLite (830 records)
