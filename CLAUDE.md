# Hawaii Fi-Do Instagram Follower Analysis

## Project
Analyzing ~444 Instagram followers of Hawaii Fi-Do (service dog nonprofit) to identify
top 25 fundraising prospects and top 15 marketing partners for the annual fundraising dinner.

## Architecture
- Python scripts handle data extraction and formatting (NO intelligence)
- Claude AI performs ALL analysis, scoring, and ranking
- Sequential pipeline: shell loop calls `claude -p` once per task

## Key Files
- data/followers.db — SQLite database with enriched follower profiles
- data/AI_ANALYSIS_FRAMEWORK.md — 4-factor scoring system (READ THIS for analysis tasks)
- scripts/extract_raw_candidates.py — Extracts raw profiles from DB + fetches website content
- scripts/ai_analysis_orchestrator.py — Splits candidates into batches of 75
- scripts/format_reports.py — Formats final JSON into CSV + Markdown reports

## Working Directories
- data/analysis_batches/ — Batch input files (batch_1.json through batch_N.json)
- data/analysis_results/ — Batch output files (batch_1_results.json through batch_N_results.json)
- output/ — Final formatted reports (markdown + CSV)

## Conventions
- Run Python with: python3 scripts/<name>.py
- All paths relative to project root
- JSON output must be valid and parseable
- To APPEND to files (progress.txt, learnings.md): use Python open(f, 'a') or bash >>. Never overwrite.

## Logging
- progress.txt — Verbose developer log (append each iteration)
- learnings.md — Cross-iteration knowledge base (read at start, append at end)
