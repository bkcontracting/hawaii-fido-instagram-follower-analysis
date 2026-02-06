---
name: donors
description: Show financial resource targets — banks, local businesses, organizations
---

# /donors — Financial Resource Targets

Query `data/followers.db` for potential donors and financial partners.

## Default Behavior
- Filter: `category IN ('bank_financial', 'business_local', 'organization')` and `priority_score >= 50` and `status = 'completed'`
- Sort: `priority_score DESC`

## Optional Filters (from user arguments)
- `--hawaii` — only show `is_hawaii = 1`
- `--min-score <N>` — override minimum score (default 50)
- `--category <value>` — filter to a single donor category (e.g., `bank_financial`, `business_local`, `organization`)
- `--limit <N>` — limit number of rows returned (default: no limit)

## Output Columns
| Column | Source |
|--------|--------|
| handle | `handle` |
| display_name | `display_name` |
| category | `category` |
| subcategory | `subcategory` |
| priority_score | `priority_score` |
| bio | `SUBSTR(bio, 1, 80)` (truncated to 80 chars) |
| website | `website` |
| is_hawaii | `is_hawaii` |
| profile_url | `profile_url` |

## Instructions
1. Connect to `data/followers.db` using the Bash tool with `sqlite3`
2. Build the SQL query applying defaults and any user-provided filters
3. Format results as a markdown table
4. Show total count at the bottom
5. If no results, say "No donor prospects found matching the criteria."

## Example SQL
```sql
SELECT handle, display_name, category, subcategory, priority_score,
  SUBSTR(bio, 1, 80) as bio, website, is_hawaii, profile_url
FROM followers
WHERE status = 'completed'
  AND category IN ('bank_financial', 'business_local', 'organization')
  AND priority_score >= 50
ORDER BY priority_score DESC
-- Add LIMIT N if --limit is provided
;
```