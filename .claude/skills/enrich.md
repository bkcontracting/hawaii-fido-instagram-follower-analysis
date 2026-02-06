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

4. **Process followers in batches** — For each batch:

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
      - Get tab context first with `mcp__claude-in-chrome__tabs_context_mcp`, then create a tab with `mcp__claude-in-chrome__tabs_create_mcp`
      - Navigate to the follower's `profile_url` (e.g., `https://www.instagram.com/<handle>/`)
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
      import json
      from src.location_detector import is_hawaii
      from src.classifier import classify
      from src.scorer import score

      # Data extracted from browser (fill in actual values)
      handle = '<handle>'
      display_name = '<display_name>'
      bio = '<bio>'
      combined_text = f'{handle} {display_name} {bio}'

      hawaii = is_hawaii(combined_text)

      profile = {
          'handle': handle,
          'display_name': display_name,
          'bio': bio,
          'website': '<website>',
          'follower_count': <follower_count>,
          'following_count': <following_count>,
          'post_count': <post_count>,
          'is_verified': <is_verified>,
          'is_private': <is_private>,
          'is_business': <is_business>,
          'is_hawaii': hawaii,
      }

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
      "
      ```

      **Step 4 — Persist to database:**
      Use the Bash tool to update the follower record:
      ```bash
      python3 -c "
      from src.database import update_follower
      update_follower('data/followers.db', '<handle>', {
          'follower_count': <follower_count>,
          'following_count': <following_count>,
          'post_count': <post_count>,
          'bio': '<bio>',
          'website': '<website>',
          'is_verified': <is_verified>,
          'is_private': <is_private>,
          'is_business': <is_business>,
          'category': '<category>',
          'subcategory': '<subcategory>',
          'confidence': <confidence>,
          'is_hawaii': <is_hawaii>,
          'location': '<location>',
          'priority_score': <priority_score>,
          'priority_reason': '<priority_reason>',
          'status': 'completed',
          'processed_at': __import__('datetime').datetime.now().isoformat(),
      })
      "
      ```

      **On error:** Set `status = 'error'` with the error message, then continue to the next follower.

   c. **Rate limiting** — Wait 3-5 seconds between profile visits to avoid Instagram detection.

   d. **Retry errors** — After the batch, retry any error records up to MAX_RETRIES (default 3) total attempts. Reset errors to `status = 'pending'` before each retry.

   e. **If retries exhausted** (errors remain after all attempts), stop processing and report to the user.

   f. **If user specified N** — After enriching N followers, stop (even if more are pending).

5. **Show progress after each batch** — Display:
   ```
   Follower Enrichment Progress
   ============================
   Total: <total>
   Completed: <completed> (<percent>%)
   Processing: <processing>
   Pending: <pending>
   Errors: <errors>
   ```

6. **Final report** — When done, show the final status breakdown and a summary:
   - Total enriched this session
   - Total errors
   - Whether all followers are now complete or some remain pending

## Important Notes

- The user MUST be logged into Instagram in their browser before running this command
- Respect rate limits: 3-5 second delays between profile visits
- If rate limited by Instagram, pause for 5 minutes then resume
- Private accounts: capture what limited data is visible, mark as `status = 'completed'` with `is_private = 1`
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
