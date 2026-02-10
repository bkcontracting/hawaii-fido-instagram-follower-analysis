# Hawaii Fi-Do Instagram Follower Analyzer

Service dog nonprofit. DB: `data/followers.db` (git-tracked, irreplaceable — NEVER delete/drop, back up before bulk writes).
All `src/` is **stdlib only** — no pip installs except `pytest`/`playwright`.
`classifier.py` rules are priority-ordered, first match wins — never reorder.

## Quick Ref

- `pytest tests/ -v` before/after classifier or scorer changes
- `python3 scripts/rescore.py --db data/followers.db --dry-run` before real rescore
