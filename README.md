# Hawaii Fi-Do Instagram Follower Analyzer

Automated tool to analyze [Hawaii Fi-Do's](https://www.instagram.com/hawaiifido/) Instagram followers (~830) and identify high-value engagement candidates for fundraising, partnerships, and community outreach.

## What It Does

1. **Parses** follower data from a CSV export into a SQLite database
2. **Enriches** each profile via browser automation (follower count, bio, business status, etc.)
3. **Classifies** accounts into categories: local business, organization, bank/financial, pet industry, influencer, elected official, and more
4. **Scores** followers 0–100 based on Hawaii location, reach, engagement signals, and category
5. **Surfaces** results through interactive Claude Code slash commands

## Tech Stack

- Python 3 + SQLite (stdlib only, no external dependencies)
- pytest for testing
- Claude Code slash commands for Phase 3 analysis
- Claude-in-Chrome MCP for browser automation (Phase 2)

## Project Structure

```
├── PRD.md                  # Product requirements (v1.3)
├── data/
│   ├── followers_validated.csv   # Source CSV (~830 followers, gitignored)
│   └── followers.db              # SQLite database (generated)
├── src/
│   ├── config.py               # Pipeline settings (batch size, retries)
│   ├── csv_parser.py           # Phase 1: CSV → dict list
│   ├── database.py             # SQLite CRUD operations
│   ├── location_detector.py    # Hawaii confidence scoring
│   ├── classifier.py           # Account categorization (13 categories)
│   ├── scorer.py               # Priority scoring (0–100) + tier assignment
│   ├── batch_orchestrator.py   # Batch processing with retry logic
│   └── pipeline.py             # End-to-end phase runners
├── tests/
│   ├── fixtures/               # CSV + JSON test data
│   └── unit/                   # Per-module test files
├── output/                     # Generated exports (CSV + markdown)
└── .claude/skills/             # Phase 3 slash commands
```

## Setup

```bash
git clone git@github.com:bkcontracting/hawaii-fido-instagram-follower-analysis.git
cd hawaii-fido-instagram-follower-analysis
```

Place your `followers_validated.csv` in `data/`.

## Usage

### Phase 1 — Parse CSV into database

```python
from src.pipeline import run_phase1
result = run_phase1("data/followers_validated.csv", "data/followers.db")
# {'inserted': 830}
```

### Phase 2 — Enrich profiles via browser

```python
from src.pipeline import run_phase2
result = run_phase2("data/followers.db", fetcher_fn)
# {'batches_run': 42, 'total_completed': 822, 'total_errors': 8}
```

Requires a logged-in Instagram session via Claude-in-Chrome MCP. Processes in batches of 5 with 3–5 second delays between profile visits.

### Phase 3 — Analyze with slash commands

Run these in Claude Code with the project open:

| Command | Description |
|---------|-------------|
| `/prospects` | Top engagement candidates (score >= 60) |
| `/summary` | Full statistical dashboard |
| `/donors` | Financial resource targets (banks, businesses, orgs) |
| `/outreach` | Actionable contact list grouped by tier |
| `/export` | Write CSV/markdown files to `output/` |

Each command supports optional filters — run the command with no arguments for smart defaults.

## Scoring Overview

| Score | Tier | Action |
|-------|------|--------|
| 80–100 | Tier 1 — High Priority | Immediate outreach |
| 60–79 | Tier 2 — Medium Priority | Strong prospects |
| 40–59 | Tier 3 — Low Priority | Worth monitoring |
| 0–39 | Tier 4 — Skip | Low priority |

Key scoring factors: Hawaii location (+30), bank/financial (+30), pet industry (+25), organization (+25), business account (+20), follower reach (up to +20), and engagement signals.

## Development

TDD workflow — write failing tests first, then implement.

```bash
# Run full test suite
pytest tests/ -v

# Run single module tests
pytest tests/unit/test_csv_parser.py -v
```

### Configuration

Settings in `src/config.py` with env var overrides:

| Setting | Default | Env Var |
|---------|---------|---------|
| `BATCH_SIZE` | 5| `BATCH_SIZE` |
| `MAX_SUBAGENTS` | 2 | `MAX_SUBAGENTS` |
| `MAX_RETRIES` | 3 | `MAX_RETRIES` |

## License

Private — Hawaii Fi-Do internal use.
