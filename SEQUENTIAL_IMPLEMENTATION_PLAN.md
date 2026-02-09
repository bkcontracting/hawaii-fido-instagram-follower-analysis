# Sequential AI Analysis Pipeline

## Overview

This pipeline analyzes 444 Instagram followers sequentially using Claude's built-in task system. An outer shell script loops, calling Claude with fresh context each time. Claude checks the task list, executes the next pending task, marks it done, and exits.

## How to Run

```bash
./run_analysis.sh <task_list_id>
```

The task list ID is the session ID from the Claude session where tasks were created.

## Task Sequence (14 tasks)

| # | Task | Type | Output |
|---|------|------|--------|
| 1 | Extract raw candidates | Python script | `data/candidates_raw.json` |
| 2 | Create analysis batches | Python script | `data/analysis_batches/batch_*.json` |
| 3-11 | Analyze batch 1-9 | AI analysis | `data/analysis_results/batch_N_results.json` |
| 12 | Aggregate results | AI aggregation | `data/all_analyzed_profiles.json` |
| 13 | Final ranking | AI ranking | `data/top_50_fundraising.json`, `data/top_15_marketing_partners.json` |
| 14 | Format reports | Python script | `output/fundraising_recommendations.md`, CSVs |

## Architecture

- **Shell script** (`run_analysis.sh`): Loops up to 20 iterations, calls Claude each time
- **Task list**: Claude's built-in TaskCreate/TaskList/TaskUpdate system
- **Fresh context**: Each Claude invocation starts fresh, accesses tasks via `CLAUDE_CODE_TASK_LIST_ID` env var
- **Sentinel**: Claude prints `ALL_TASKS_COMPLETE` when no tasks remain; shell script exits

## Existing Scripts (unchanged)

- `scripts/extract_raw_candidates.py` - Extracts raw data from `data/followers.db`
- `scripts/ai_analysis_orchestrator.py` - Splits candidates into batches of 50
- `scripts/format_reports.py` - Formats JSON results into CSV + Markdown
- `data/AI_ANALYSIS_FRAMEWORK.md` - Analysis criteria for Claude

## Output Files

After completion:
- `data/candidates_raw.json` - 444 raw profiles
- `data/analysis_batches/batch_*.json` - 9 batch files
- `data/analysis_results/batch_*_results.json` - 9 analyzed batch results
- `data/all_analyzed_profiles.json` - All 444 analyzed profiles
- `data/top_50_fundraising.json` - Top 50 fundraising prospects
- `data/top_15_marketing_partners.json` - Top 15 marketing partners
- `output/fundraising_recommendations.md` - Full report
- `output/fundraising_outreach.csv` - Outreach spreadsheet
- `output/marketing_partners.csv` - Marketing spreadsheet
