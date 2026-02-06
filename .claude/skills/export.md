---
name: export
description: Export analysis results to CSV and markdown files in output/
---

# /export — File Export

Query `data/followers.db` and write results to files in `output/`.

## Default Behavior
Writes all 3 files:
1. `output/top_prospects.csv` — followers with `priority_score >= 60`
2. `output/full_export.csv` — all followers
3. `output/analysis_summary.md` — statistical breakdown

## Optional Flags (from user arguments)
- `--prospects` — only write `top_prospects.csv`
- `--full` — only write `full_export.csv`
- `--summary` — only write `analysis_summary.md`

## File Specifications

### `top_prospects.csv`
- Filter: `priority_score >= 60` and `status = 'completed'`
- Sort: `priority_score DESC`
- Columns: `handle, display_name, category, priority_score, tier, priority_reason, follower_count, bio, website, is_hawaii, profile_url`
- Tier derived via CASE WHEN (not stored in DB)
- If no data: write header row only

```sql
SELECT handle, display_name, category, priority_score,
  CASE WHEN priority_score >= 80 THEN 'Tier 1 - High Priority'
       WHEN priority_score >= 60 THEN 'Tier 2 - Medium Priority'
       WHEN priority_score >= 40 THEN 'Tier 3 - Low Priority'
       ELSE 'Tier 4 - Skip' END AS tier,
  priority_reason, follower_count, bio, website, is_hawaii, profile_url
FROM followers
WHERE status = 'completed' AND priority_score >= 60
ORDER BY priority_score DESC;
```

### `full_export.csv`
- Filter: all followers
- Sort: `priority_score DESC NULLS LAST`
- Columns: `handle, display_name, category, subcategory, priority_score, tier, priority_reason, follower_count, following_count, post_count, bio, website, is_verified, is_private, is_business, is_hawaii, location, confidence, status, profile_url`
- If no data: write header row only

### `analysis_summary.md`
Include sections:
1. **Total Followers** — count + status breakdown
2. **Hawaii vs Non-Hawaii** — count + avg score
3. **Category Breakdown** — count + avg score per category
4. **Tier Distribution** — count per tier
5. **Top 10 Overall** — handle, category, score
6. **Top 10 Per Category** — for each category
7. **Needs Review** — unknown + error accounts
- If no enriched data: write "No enriched data available" in each section

## Instructions
1. Ensure `output/` directory exists (create if needed)
2. Connect to `data/followers.db` using the Bash tool with `sqlite3`
3. For CSV files: use `.mode csv` and `.headers on` in sqlite3, or write via Python one-liner
4. For the summary: format as readable markdown
5. Report which files were written and their row counts
6. If the database doesn't exist or has no completed records, create files with headers only and note "No enriched data available"
