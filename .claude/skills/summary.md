---
name: summary
description: Full analysis dashboard of the follower database
---

# /summary — Analysis Dashboard

Query `data/followers.db` and display a comprehensive statistical overview.

## Sections to Display

### 1. Total Follower Count + Status Breakdown
```sql
SELECT status, COUNT(*) as count FROM followers GROUP BY status;
SELECT COUNT(*) as total FROM followers;
```

### 2. Hawaii vs Non-Hawaii
```sql
SELECT
  CASE WHEN is_hawaii = 1 THEN 'Hawaii' ELSE 'Non-Hawaii' END AS location,
  COUNT(*) as count,
  ROUND(AVG(priority_score), 1) as avg_score
FROM followers WHERE status = 'completed'
GROUP BY is_hawaii;
```

### 3. Category Breakdown
```sql
SELECT category, COUNT(*) as count,
  ROUND(AVG(priority_score), 1) as avg_score
FROM followers WHERE status = 'completed'
GROUP BY category ORDER BY avg_score DESC;
```

### 4. Tier Distribution
```sql
SELECT
  CASE WHEN priority_score >= 80 THEN 'Tier 1 - High Priority'
       WHEN priority_score >= 60 THEN 'Tier 2 - Medium Priority'
       WHEN priority_score >= 40 THEN 'Tier 3 - Low Priority'
       ELSE 'Tier 4 - Skip' END AS tier,
  COUNT(*) as count
FROM followers WHERE status = 'completed'
GROUP BY tier ORDER BY tier;
```

### 5. Top 10 Overall
```sql
SELECT handle, display_name, category, priority_score, is_hawaii
FROM followers WHERE status = 'completed'
ORDER BY priority_score DESC LIMIT 10;
```

### 6. Top 10 Per Category
For each category with completed records:
```sql
SELECT handle, display_name, priority_score
FROM followers WHERE status = 'completed' AND category = ?
ORDER BY priority_score DESC LIMIT 10;
```

### 7. Needs Review
```sql
SELECT handle, display_name, category, status, error_message
FROM followers WHERE category = 'unknown' OR status = 'error'
ORDER BY status, handle;
```

## Instructions
1. Connect to `data/followers.db` using the Bash tool with `sqlite3`
2. Run each query above
3. Format each section with a header and markdown table
4. If the database has no completed records, show "No enriched data available — run Phase 2 first."
