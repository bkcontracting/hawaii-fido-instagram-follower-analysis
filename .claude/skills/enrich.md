---
name: enrich
description: Run Phase 2 profile enrichment on pending followers in the database
---

# /enrich — Phase 2 Profile Enrichment

Run the Phase 2 enrichment pipeline on followers in `data/followers.db`. Each pending follower's Instagram profile is visited via the Claude Chrome MCP browser, enriched with profile data, then classified and scored using the project's Python pipeline.

## Arguments

- **No argument (default):** Enrich ALL pending followers
- **`<N>`** (integer): Enrich only the first N pending followers (e.g., `/enrich 10`)

## Steps

1. **Check database status** — Run this SQL via the Bash tool against `data/followers.db`:
   ```sql
   SELECT status, COUNT(*) as count FROM followers GROUP BY status;
   ```
   Display the current status breakdown to the user.

2. **Determine scope** — If the user provided a number N, that is the limit. Otherwise the limit is ALL pending followers (no cap).

3. **Show enrichment plan** — Tell the user:
   - How many followers will be enriched (min of N and pending count)
   - Current config: batch size (`src/config.py` BATCH_SIZE, default 20), max retries (`src/config.py` MAX_RETRIES, default 3)
   - Estimated batches: ceil(followers_to_enrich / BATCH_SIZE)

4. **Browser setup (once)** — Before processing any batches:
   - Call `mcp__claude-in-chrome__tabs_context_mcp` once to get current tab context
   - Call `mcp__claude-in-chrome__tabs_create_mcp` once to create a single browser tab
   - Store the returned tab ID — reuse it for ALL follower profile visits

5. **Process followers in batches** — For each batch:

   a. **Claim batch** — Query up to BATCH_SIZE pending followers:
      ```sql
      SELECT handle, display_name, profile_url FROM followers WHERE status = 'pending' LIMIT 20;
      ```
      Mark them as `status = 'processing'`:
      ```sql
      UPDATE followers SET status = 'processing', processed_at = datetime('now')
      WHERE handle IN ('<handle1>', '<handle2>', ...);
      ```

   b. **For each follower in the batch:**

      **Step 1 — Visit profile via Claude-in-Chrome MCP:**
      Use the Claude-in-Chrome MCP browser tools (`mcp__claude-in-chrome__navigate`, `mcp__claude-in-chrome__read_page`, `mcp__claude-in-chrome__computer`, etc.) to operate the user's actual Chrome browser (which has their Instagram session):
      - Navigate to the follower's `profile_url` (e.g., `https://www.instagram.com/<handle>/`) using the tab ID from step 4
      - Wait for the page to load (wait for the profile header or username text to appear)
      - Read the page with `mcp__claude-in-chrome__read_page` to extract structured data

      **Step 2 — Extract profile data from the page:**
      From the `read_page` result, extract these fields:
      - `follower_count` (number of followers)
      - `following_count` (number following)
      - `post_count` (number of posts)
      - `bio` (profile bio text)
      - `website` (external link if present)
      - `is_verified` (blue checkmark present)
      - `is_private` (private account indicator)
      - `is_business` (business/creator account indicator)

      **Step 3 — Run Python pipeline to classify and score:**
      Use the Bash tool to call the project's Python modules directly. This ensures classification, scoring, and location detection stay in sync with the source code in `src/classifier.py`, `src/scorer.py`, and `src/location_detector.py`.

      ```bash
      python3 -c "
      import sys, json
      from src.location_detector import is_hawaii
      from src.classifier import classify
      from src.scorer import score

      data = json.load(sys.stdin)
      combined_text = f\"{data['handle']} {data['display_name']} {data['bio']}\"
      hawaii = is_hawaii(combined_text)
      profile = {**data, 'is_hawaii': hawaii}
      classification = classify(profile)
      profile['category'] = classification['category']
      profile['subcategory'] = classification['subcategory']
      scoring = score(profile)
      result = {
          'is_hawaii': hawaii,
          'location': 'Hawaii' if hawaii else None,
          'category': classification['category'],
          'subcategory': classification['subcategory'],
          'confidence': classification['confidence'],
          'priority_score': scoring['priority_score'],
          'priority_reason': scoring['priority_reason'],
      }
      print(json.dumps(result))
      " <<'PROFILE_EOF'
      <JSON object with all extracted fields — Claude JSON-encodes all string values>
      PROFILE_EOF
      ```

      **Step 4 — Persist to database:**
      Use the Bash tool to update the follower record:
      ```bash
      python3 -c "
      import sys, json, datetime
      from src.database import update_follower
      data = json.load(sys.stdin)
      handle = data.pop('handle')
      data['status'] = 'completed'
      data['processed_at'] = datetime.datetime.now().isoformat()
      update_follower('data/followers.db', handle, data)
      " <<'UPDATE_EOF'
      <JSON object with handle + all fields from Step 3 result + extracted fields — Claude JSON-encodes all string values>
      UPDATE_EOF
      ```

      **On error:** Set `status = 'error'` with the error message, then continue to the next follower.

   c. **Rate limiting** — Wait 3-5 seconds between profile visits to avoid Instagram detection.

   d. **Retry errors** — After the batch, retry any error records up to MAX_RETRIES (default 3) total attempts. Reset errors to `status = 'pending'` before each retry.

   e. **If retries exhausted** (errors remain after all attempts), stop processing and report to the user.

   f. **If user specified N** — After enriching N followers, stop (even if more are pending).

6. **Show progress after each batch** — Display:
   ```
   Follower Enrichment Progress
   ============================
   Total: <total>
   Completed: <completed> (<percent>%)
   Processing: <processing>
   Pending: <pending>
   Errors: <errors>
   ```

7. **Final report** — When done, show the final status breakdown and a summary:
   - Total enriched this session
   - Total errors
   - Whether all followers are now complete or some remain pending

## Instagram Error Scenarios

- **Login prompt ("Log in to continue"):** STOP immediately, report expired session to user, do NOT enter credentials.
- **CAPTCHA / "Confirm it's you":** STOP immediately, report to user, wait for manual resolution before resuming.
- **"Sorry, this page isn't available":** Mark as `status = 'error'` with `error_message = 'profile_not_found'`, continue to next follower. Do NOT retry — this is a permanent error.

## Important Notes

- The user MUST be logged into Instagram in their browser before running this command
- Respect rate limits: 3-5 second delays between profile visits
- If rate limited by Instagram, pause for 5 minutes then resume
- Private accounts: capture what limited data is visible, mark as `status = 'completed'` with `is_private = 1` (Note: PRD mentions `status = 'private'` but the code uses `status = 'completed'` — code is the source of truth.)
- The database is the source of truth — if the session crashes, re-running `/enrich` will pick up where it left off (pending records resume automatically)
- **Do NOT inline classification rules, scoring algorithms, or location detection logic** — always delegate to the Python modules in `src/`. This prevents drift between the skill and the source code.

## Source Code Reference

The enrichment pipeline is implemented in these modules:
- `src/batch_orchestrator.py` — batch creation, processing, retry logic (`create_batch()`, `process_batch()`, `run_with_retries()`, `run_all()`)
- `src/classifier.py` — 13 priority-ordered classification rules (`classify()`)
- `src/scorer.py` — priority scoring algorithm 0-100 (`score()`, `get_tier()`)
- `src/location_detector.py` — Hawaii location detection from text (`is_hawaii()`, `hawaii_confidence()`)
- `src/database.py` — SQLite persistence (`update_follower()`, `get_pending()`, `get_status_counts()`)
- `src/config.py` — BATCH_SIZE (default 20), MAX_RETRIES (default 3), MAX_SUBAGENTS (default 2)
