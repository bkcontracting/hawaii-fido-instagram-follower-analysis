# Instagram Profile Enrichment Skill

## Description
Enrich all Instagram followers in the database by visiting each profile via browser automation, extracting profile data, classifying, scoring, and storing results. Designed to run fully autonomously with crash recovery.

## Restart instructions
Run `/enrich` or point Claude at this file. It will check DB status and resume from wherever it left off. No additional instructions needed.

## Architecture
- Main orchestrator runs a thin loop: check DB → launch 2 subagents → wait → repeat
- Each subagent processes exactly 1 batch (20 profiles) then terminates
- All state lives in SQLite — recovery is automatic
- Exactly 2 browser tabs created at startup, navigated in-place (never create new tabs during processing)

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

Each subagent receives the tab_id and processes one batch:

1. Claim batch via `create_batch("data/followers.db")`
2. For each follower in batch:
   a. Navigate to profile_url in the assigned tab
   b. Wait 2s for page load
   c. Extract: follower_count, following_count, post_count, bio, website, is_verified, is_private, is_business
   d. Parse K/M suffixes: "1.2K"→1200, "5M"→5000000
   e. Run through pipeline: is_hawaii() → classify() → score() → update_follower()
   f. Random delay 3-5s before next profile
3. Return: "{completed: N, errors: M, rate_limited: bool}"

## Extraction Method
- Primary: `read_page(tabId)` accessibility tree → parse structured text
- Fallback: `javascript_tool(tabId)` for DOM queries
- Handle: private accounts, not found, suspended, rate limiting

## Error Handling
- Profile not found: status='error', error_message='not_found'
- Account suspended: status='error', error_message='suspended'
- Private account: extract visible data, is_private=True, status='completed'
- Rate limited: stop batch, return rate_limited=true to orchestrator
- Page timeout: retry once, then status='error'

## Key Files
- `src/batch_orchestrator.py` — create_batch() with crash recovery
- `src/classifier.py` — 13-rule classification
- `src/scorer.py` — priority scoring 0-100
- `src/location_detector.py` — is_hawaii() detection
- `src/database.py` — update_follower(), get_status_counts()
- `data/followers.db` — SQLite (830 records)
