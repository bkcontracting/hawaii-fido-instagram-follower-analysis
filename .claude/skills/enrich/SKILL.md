---
name: enrich
description: Enrich all Instagram followers in the database by visiting each profile via browser automation
---

# Instagram Profile Enrichment Skill

## Description
Enrich all Instagram followers in the database by visiting each profile via browser automation, extracting profile data, classifying, scoring, and storing results.

## Recommended: Standalone Script (runs unattended)

The standalone Python script is the preferred way to enrich all followers.
It uses Selenium to drive Chrome directly — no Claude subagents, no context
window limits, no compaction stalls. Processes all 830+ profiles in a single
unattended session.

```bash
# 1. Launch Chrome with remote debugging (leave this terminal open)
google-chrome --remote-debugging-port=9222

# 2. Log into Instagram in that Chrome window if not already logged in

# 3. Run the enrichment script (in a separate terminal)
python scripts/enrich_browser.py
```

Options:
```
--port PORT              Chrome debugging port (default: 9222)
--db PATH                Database path (default: data/followers.db)
--delay-min SECONDS      Min delay between profiles (default: 3)
--delay-max SECONDS      Max delay between profiles (default: 5)
--rate-limit-wait MIN    Minutes to wait on rate limit (default: 5)
--max-errors N           Stop after N consecutive errors (default: 15)
--dry-run                Show pending profiles without processing
```

The script is fully restartable — it reads pending records from the DB and
picks up where it left off. If killed mid-run, stale 'processing' records
are reset to 'pending' on the next run.

### Why the standalone script instead of Claude subagents?

The original Claude-driven approach hits context window compaction after ~120
profiles, causing the session to stall and ask about Playwright MCP. The
standalone script eliminates this entirely because:

1. **No LLM in the loop** — all parsing, classification, and scoring is
   already deterministic Python code. Claude was only navigating URLs and
   running `document.body.innerText`. Selenium does this without any tokens.
2. **No context growth** — the script processes profiles sequentially in a
   constant-memory loop. No conversation history to replay.
3. **No compaction stalls** — runs until done or rate-limited. Rate limits
   are handled with automatic sleep + resume.
4. **Single AFK session** — 830 profiles at ~4s/profile + delays ≈ 90 minutes.

## Legacy: Claude Subagent Approach

The `/enrich` skill can still be invoked for small batches or when the
standalone script isn't available. It spawns 2 parallel subagents that
each process 5 profiles per batch via Claude-in-Chrome MCP. However, it
will hit context limits after ~120 profiles and require manual restart.

### Architecture (legacy)
- Main orchestrator runs a thin loop: check DB → launch 2 subagents → wait → repeat
- Each subagent processes exactly 1 batch (5 profiles) then terminates
- All state lives in SQLite — recovery is automatic
- Exactly 2 browser tabs created at startup, navigated in-place

### Main Orchestrator Loop (legacy)

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
  9. Launch 2 Task subagents IN PARALLEL (general-purpose, model: sonnet):
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

### Subagent Prompt Template (legacy)

Each subagent receives the tab_id and processes one batch.

1. Claim batch via `create_batch("data/followers.db")`
2. For each follower in batch:
   a. Navigate to profile_url in the assigned tab
   b. Wait 2s for page load
   c. Grab raw page text via `javascript_tool(tabId)`:
      `document.querySelector('header')?.closest('main')?.innerText || document.body.innerText`
   d. Pass raw text to `parse_profile_page(raw_text)`
   e. Check `enriched["page_state"]`: if "rate_limited" → stop and return
   f. Run through pipeline: is_hawaii() → classify() → score() → update_follower()
   g. Random delay 3-5s before next profile
3. Return ONLY: "{completed: N, errors: M, rate_limited: bool}"

## Error Handling
Page state is detected automatically by `parse_profile_page()`:
- `page_state == "not_found"`: status='error', error_message='not_found'
- `page_state == "suspended"`: status='error', error_message='suspended'
- `page_state == "rate_limited"`: sleep and retry (standalone) or stop batch (legacy)
- `page_state == "login_required"`: wait for login (standalone) or stop batch (legacy)
- `page_state == "normal"` + is_private=True: status='private' (enriched data captured)
- Page timeout: retry once, then status='error'

## Key Files
- `scripts/enrich_browser.py` — **standalone enrichment script** (Selenium, no LLM)
- `src/profile_parser.py` — deterministic page parser (parse_count, parse_profile_page, detect_page_state)
- `src/batch_orchestrator.py` — create_batch() with crash recovery (used by legacy approach)
- `src/classifier.py` — 13-rule classification
- `src/scorer.py` — priority scoring 0-100
- `src/location_detector.py` — is_hawaii() detection
- `src/database.py` — update_follower(), get_status_counts()
- `data/followers.db` — SQLite (830 records)
