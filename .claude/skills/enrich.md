---
name: enrich
description: Run Phase 2 profile enrichment on pending followers in the database
---

# /enrich — Phase 2 Profile Enrichment

Run the Phase 2 enrichment pipeline on followers in `data/followers.db`. Each pending follower's Instagram profile is visited in a browser, enriched with profile data, classified, and scored.

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
   - Current config: batch size (from `src/config.py` BATCH_SIZE, default 20), max retries (MAX_RETRIES, default 3)
   - Estimated batches: ceil(followers_to_enrich / BATCH_SIZE)

4. **Process followers in batches** — For each batch:

   a. **Claim batch** — Query up to BATCH_SIZE pending followers:
      ```sql
      SELECT handle, display_name, profile_url FROM followers WHERE status = 'pending' LIMIT 20;
      ```
      Mark them as `status = 'processing'`.

   b. **For each follower in the batch:**
      - Navigate to their `profile_url` in the browser (using the Chrome MCP browser tools)
      - Wait 3-5 seconds between profile visits to avoid detection
      - Extract from the Instagram profile page:
        - `follower_count` (number of followers)
        - `following_count` (number following)
        - `post_count` (number of posts)
        - `bio` (profile bio text)
        - `website` (external link if present)
        - `is_verified` (blue checkmark)
        - `is_private` (private account)
        - `is_business` (business/creator account indicator)
      - Build combined text: `"{handle} {display_name} {bio}"`
      - Determine `is_hawaii` from combined text using Hawaii location signals:
        - Strong (+0.4): City names (Honolulu, Kailua, Kapolei, etc.), State (Hawaii, HI, Hawai'i), Area code (808)
        - Medium (+0.3): Island names (Oahu, Maui, Kauai), Airport (HNL), Zip prefix (967, 968)
        - Weak (+0.15): Cultural (Aloha, Hawaiian)
        - `is_hawaii = True` if confidence >= 0.4
      - Classify using the decision rules (in priority order):
        1. bank/financial keywords → `bank_financial`
        2. pet industry keywords + business signal → `pet_industry`
        3. church/school/rotary/club/golf + NOT charity → `organization`
        4. rescue/humane/nonprofit/501c/shelter/charity → `charity`
        5. council/mayor/senator/representative/governor + hawaii → `elected_official`
        6. event/tournament/festival/magazine/news/photographer/media/press → `media_event`
        7. is_business + is_hawaii → `business_local`
        8. is_business + NOT hawaii → `business_national`
        9. follower_count >= 10000 + NOT business → `influencer`
        10. following > 10x followers + posts < 5 → `spam_bot`
        11. posts > 50 + NOT business → `personal_engaged`
        12. posts <= 50 + NOT business → `personal_passive`
        13. No match → `unknown`
      - Score using the algorithm (0-100, clamped):
        - Hawaii: +30, Bank/financial: +30, Pet industry: +25, Organization: +25, Elected official: +25, Business: +20, Media/event: +15, Influencer: +20, Verified: +10
        - Reach: 50k+ → +20, 10k-50k → +15, 5k-10k → +10, 1k-5k → +5
        - Engagement: website +5, >100 posts +5, bio mentions dogs/pets +10 (not if pet_industry), community/giving +5
        - Penalties: charity -50, private -20, spam -100, no bio -10
      - Update the database row with all enriched fields and `status = 'completed'`
      - On error: set `status = 'error'` with `error_message`, continue to next follower

   c. **Retry errors** — After the batch, retry any error records up to MAX_RETRIES total attempts. Reset errors to pending before each retry.

   d. **If retries exhausted** (errors remain after all attempts), stop processing and report to the user.

   e. **If user specified N** — After enriching N followers, stop (even if more are pending).

5. **Show progress after each batch** — Display:
   ```
   Follower Enrichment Progress
   ============================
   Total: <total>
   Completed: <completed> (<percent>%)
   Processing: <processing>
   Pending: <pending>
   Errors: <errors>
   Private: <private>
   ```

6. **Final report** — When done, show the final status breakdown and a summary:
   - Total enriched this session
   - Total errors
   - Whether all followers are now complete or some remain pending

## Important Notes

- The user MUST be logged into Instagram in Chrome before running this command
- Respect rate limits: 3-5 second delays between profile visits
- If rate limited by Instagram, pause for 5 minutes then resume
- Private accounts: capture what limited data is visible, mark as `status = 'private'`
- The database is the source of truth — if the session crashes, re-running `/enrich` will pick up where it left off (pending records resume automatically)
