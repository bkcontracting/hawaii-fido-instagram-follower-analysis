---
name: prospects
description: Show top engagement candidates from the follower analysis database
---

# /prospects — Top Engagement Candidates

Query `data/followers.db` and display a ranked table of high-value prospects.

## Default Behavior
- Filter: `priority_score >= 60` and `status = 'completed'`
- Sort: `priority_score DESC`
- Limit: 25
- Derive tier using: `CASE WHEN priority_score >= 80 THEN 'Tier 1 - High Priority' WHEN priority_score >= 60 THEN 'Tier 2 - Medium Priority' WHEN priority_score >= 40 THEN 'Tier 3 - Low Priority' ELSE 'Tier 4 - Skip' END`

## Optional Filters (from user arguments)
- `--category <value>` — filter by category (e.g., `business_local`, `pet_industry`)
- `--min-score <N>` — override minimum score (default 60)
- `--hawaii` — only show `is_hawaii = 1`
- `--limit <N>` — override row limit (default 25)

## Output Columns
| Column | Source |
|--------|--------|
| handle | `handle` |
| display_name | `display_name` |
| category | `category` |
| priority_score | `priority_score` |
| tier | Derived via CASE WHEN |
| priority_reason | `priority_reason` |
| follower_count | `follower_count` |
| is_hawaii | `is_hawaii` |

## Instructions
1. Connect to `data/followers.db` using the Bash tool with `sqlite3`
2. Build the SQL query applying defaults and any user-provided filters
3. Format results as a markdown table
4. Show total count at the bottom: "Showing X of Y total completed followers"
5. If no results, say "No prospects found matching the criteria."

## Example SQL
```sql
SELECT handle, display_name, category, priority_score,
  CASE WHEN priority_score >= 80 THEN 'Tier 1 - High Priority'
       WHEN priority_score >= 60 THEN 'Tier 2 - Medium Priority'
       WHEN priority_score >= 40 THEN 'Tier 3 - Low Priority'
       ELSE 'Tier 4 - Skip' END AS tier,
  priority_reason, follower_count, is_hawaii
FROM followers
WHERE status = 'completed' AND priority_score >= 60
ORDER BY priority_score DESC
LIMIT 25;
```
