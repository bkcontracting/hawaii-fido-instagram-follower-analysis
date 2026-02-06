---
name: outreach
description: Actionable contact list grouped by tier for outreach planning
---

# /outreach — Actionable Contact List

Query `data/followers.db` for outreach candidates, grouped by tier.

## Default Behavior
- Filter: `priority_score >= 40` and `status = 'completed'`
- Sort: `priority_score DESC`
- Group by tier
- Limit: 20 total

## Optional Filters (from user arguments)
- `--category <value>` — filter by category
- `--tier <N>` — show only tier N (1, 2, 3, or 4)
- `--hawaii` — only show `is_hawaii = 1`
- `--limit <N>` — override row limit (default 20)

## Output Columns
| Column | Source |
|--------|--------|
| handle | `handle` |
| display_name | `display_name` |
| category | `category` |
| priority_score | `priority_score` |
| bio | `SUBSTR(bio, 1, 80)` (truncated) |
| website | `website` |
| profile_url | `profile_url` |

## Instructions
1. Connect to `data/followers.db` using the Bash tool with `sqlite3`
2. Query completed followers with score >= 40 (or filtered by --tier/--category)
3. Group output by tier with headers:
   - **Tier 1 — High Priority (80-100)**
   - **Tier 2 — Medium Priority (60-79)**
   - **Tier 3 — Low Priority (40-59)**
   - **Tier 4 — Skip (0-39)** (only shown when `--tier 4` is explicitly requested)
4. Format each group as a markdown table
5. Show total at the bottom: "Showing X outreach candidates across Y tiers"
6. If no results, say "No outreach candidates found matching the criteria."

## Example SQL
```sql
SELECT handle, display_name, category, priority_score,
  SUBSTR(bio, 1, 80) as bio, website, profile_url,
  CASE WHEN priority_score >= 80 THEN 1
       WHEN priority_score >= 60 THEN 2
       WHEN priority_score >= 40 THEN 3
       ELSE 4 END AS tier_num
FROM followers
WHERE status = 'completed' AND priority_score >= 40
ORDER BY priority_score DESC
LIMIT 20;
```
