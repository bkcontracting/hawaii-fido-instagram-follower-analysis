# AFK Pipeline: Architecture 2 + Ralph Wiggum Pattern + Back Pressure

## Context

The Hawaii Fi-Do Instagram Follower Analyzer has 12 scripts with no single
entry point. The goal: a single AFK command that goes from raw CSV to final
reports — creating the DB, scraping profiles, running AI analysis, and
generating deliverables. This plan addresses four concerns:

1. **Context isolation** — each phase runs in a fresh Claude session
2. **Observability** — extreme logging so developers can track every decision
3. **Self-healing** — the Ralph Wiggum pattern: agents write learnings to
   files that future agents read, enabling recovery without humans
4. **Back pressure** — every turn has verification gates. The pipeline does
   NOT advance until the current phase passes all its defined tests.

---

## How It Works (The Assembly Line + Gates)

```
┌──────────┐  GATE  ┌──────────┐  GATE  ┌──────────┐  GATE  ┌──────────┐  GATE
│ Station 1│──TEST──│ Station 2│──TEST──│ Station 3│──TEST──│ Station 4│──TEST──▶ DONE
│Import CSV│  ✓/✗   │Playwright│  ✓/✗   │AI Analyze│  ✓/✗   │ Reports  │  ✓/✗
└────┬─────┘        └────┬─────┘        └────┬─────┘        └────┬─────┘
     │                   │                   │                   │
     ▼                   ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    data/pipeline_state.md                               │
│  Shared memory: results, learnings, failures, gate pass/fail records   │
└─────────────────────────────────────────────────────────────────────────┘

GATE = Back Pressure Check:
  1. Shell runs verification tests (SQL queries, file checks, JSON validation)
  2. If ALL pass → proceed to next station
  3. If ANY fail → write failure details to state file → retry station
  4. After MAX_RETRIES failures → abort with full diagnostic in state file
```

**Key principle:** A station exit code of 0 is NOT sufficient. The shell
script independently verifies the station's output using concrete tests.
The agent could exit cleanly but produce garbage — the gate catches that.

---

## Back Pressure: Phase Gate Definitions

Each phase has explicit, testable success criteria. The shell script runs
these AFTER each station completes. No agent is trusted — verify everything.

### Phase 1 Gates: Import
```bash
gate_phase1() {
  local errors=0

  # G1.1: Database file exists and is valid SQLite
  if ! sqlite3 "$DB_PATH" "SELECT 1;" > /dev/null 2>&1; then
    log "GATE FAIL [G1.1]: Database is not valid SQLite"
    errors=$((errors + 1))
  fi

  # G1.2: followers table has rows
  local count
  count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers;" 2>/dev/null || echo "0")
  if [ "$count" -eq 0 ]; then
    log "GATE FAIL [G1.2]: followers table is empty (expected > 0 rows)"
    errors=$((errors + 1))
  else
    log "GATE PASS [G1.2]: followers table has $count rows"
  fi

  # G1.3: All rows have status = 'pending'
  local non_pending
  non_pending=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers WHERE status != 'pending';" 2>/dev/null || echo "-1")
  if [ "$non_pending" -ne 0 ]; then
    log "GATE FAIL [G1.3]: $non_pending rows have non-pending status (fresh import should all be pending)"
    errors=$((errors + 1))
  else
    log "GATE PASS [G1.3]: All rows have status=pending"
  fi

  # G1.4: Required columns exist
  local cols
  cols=$(sqlite3 "$DB_PATH" "PRAGMA table_info(followers);" 2>/dev/null | wc -l)
  if [ "$cols" -lt 5 ]; then
    log "GATE FAIL [G1.4]: followers table has only $cols columns (expected >= 5)"
    errors=$((errors + 1))
  else
    log "GATE PASS [G1.4]: followers table has $cols columns"
  fi

  return $errors
}
```

### Phase 2 Gates: Enrichment
```bash
gate_phase2() {
  local errors=0

  # G2.1: No rows still 'pending' (all attempted)
  local pending
  pending=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers WHERE status = 'pending';" 2>/dev/null || echo "-1")
  if [ "$pending" -gt 0 ]; then
    log "GATE WARN [G2.1]: $pending rows still pending (enrichment may be incomplete)"
    # Not a hard fail — partial enrichment is acceptable if rate-limited
  else
    log "GATE PASS [G2.1]: No pending rows remain"
  fi

  # G2.2: At least 50% of rows have status = 'completed' or 'private'
  local total completed_or_private
  total=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers;" 2>/dev/null || echo "0")
  completed_or_private=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers WHERE status IN ('completed', 'private');" 2>/dev/null || echo "0")
  local pct=$((completed_or_private * 100 / (total > 0 ? total : 1)))
  if [ "$pct" -lt 50 ]; then
    log "GATE FAIL [G2.2]: Only $pct% completed/private ($completed_or_private/$total) — expected >= 50%"
    errors=$((errors + 1))
  else
    log "GATE PASS [G2.2]: $pct% completed/private ($completed_or_private/$total)"
  fi

  # G2.3: No login_required errors (means session expired — unrecoverable)
  local login_errors
  login_errors=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers WHERE error_message LIKE '%login_required%';" 2>/dev/null || echo "0")
  if [ "$login_errors" -gt 0 ]; then
    log "GATE FAIL [G2.3]: $login_errors login_required errors — Instagram session expired"
    errors=$((errors + 1))
  else
    log "GATE PASS [G2.3]: No login_required errors"
  fi

  # G2.4: Database backup exists
  if [ ! -f "${DB_PATH}.bak" ]; then
    log "GATE FAIL [G2.4]: No database backup found"
    errors=$((errors + 1))
  else
    log "GATE PASS [G2.4]: Database backup exists"
  fi

  return $errors
}
```

### Phase 3a Gates: Extract + Prepare
```bash
gate_phase3a() {
  local errors=0

  # G3a.1: Candidates JSON exists and is valid JSON
  if [ ! -f "data/candidates_raw.json" ]; then
    log "GATE FAIL [G3a.1]: data/candidates_raw.json does not exist"
    errors=$((errors + 1))
  elif ! python3 -c "import json; json.load(open('data/candidates_raw.json'))" 2>/dev/null; then
    log "GATE FAIL [G3a.1]: data/candidates_raw.json is not valid JSON"
    errors=$((errors + 1))
  else
    local cand_count
    cand_count=$(python3 -c "import json; print(len(json.load(open('data/candidates_raw.json'))))" 2>/dev/null || echo "0")
    log "GATE PASS [G3a.1]: candidates_raw.json has $cand_count candidates"
  fi

  # G3a.2: Batch files exist in data/analysis_batches/
  local batch_count
  batch_count=$(ls -1 data/analysis_batches/batch_*.json 2>/dev/null | wc -l)
  if [ "$batch_count" -eq 0 ]; then
    log "GATE FAIL [G3a.2]: No batch files in data/analysis_batches/"
    errors=$((errors + 1))
  else
    log "GATE PASS [G3a.2]: $batch_count batch files created"
  fi

  # G3a.3: Each batch file is valid JSON
  local invalid_batches=0
  for f in data/analysis_batches/batch_*.json; do
    if ! python3 -c "import json; json.load(open('$f'))" 2>/dev/null; then
      log "GATE FAIL [G3a.3]: $f is not valid JSON"
      invalid_batches=$((invalid_batches + 1))
    fi
  done
  if [ "$invalid_batches" -gt 0 ]; then
    errors=$((errors + invalid_batches))
  else
    log "GATE PASS [G3a.3]: All $batch_count batch files are valid JSON"
  fi

  # G3a.4: Total profiles across batches equals candidates count
  local batch_total
  batch_total=$(python3 -c "
import json, glob
total = sum(len(json.load(open(f))) for f in glob.glob('data/analysis_batches/batch_*.json'))
print(total)
" 2>/dev/null || echo "0")
  local cand_total
  cand_total=$(python3 -c "import json; print(len(json.load(open('data/candidates_raw.json'))))" 2>/dev/null || echo "-1")
  if [ "$batch_total" -ne "$cand_total" ]; then
    log "GATE FAIL [G3a.4]: Batch total ($batch_total) != candidates ($cand_total)"
    errors=$((errors + 1))
  else
    log "GATE PASS [G3a.4]: Batch total matches candidates ($batch_total)"
  fi

  return $errors
}
```

### Phase 3b Gates: AI Analysis Results
```bash
gate_phase3b() {
  local errors=0
  local batch_count
  batch_count=$(ls -1 data/analysis_batches/batch_*.json 2>/dev/null | wc -l)

  # G3b.1: Every batch has a result file
  local missing=0
  for i in $(seq 1 "$batch_count"); do
    if [ ! -f "data/analysis_results/batch_${i}_results.json" ]; then
      log "GATE FAIL [G3b.1]: batch_${i}_results.json missing"
      missing=$((missing + 1))
    fi
  done
  if [ "$missing" -gt 0 ]; then
    errors=$((errors + missing))
  else
    log "GATE PASS [G3b.1]: All $batch_count result files exist"
  fi

  # G3b.2: Every result file is valid JSON array
  local invalid=0
  for i in $(seq 1 "$batch_count"); do
    local rf="data/analysis_results/batch_${i}_results.json"
    if [ -f "$rf" ]; then
      if ! python3 -c "
import json
data = json.load(open('$rf'))
assert isinstance(data, list), 'not a list'
" 2>/dev/null; then
        log "GATE FAIL [G3b.2]: batch_${i}_results.json is not a valid JSON array"
        invalid=$((invalid + 1))
      fi
    fi
  done
  if [ "$invalid" -gt 0 ]; then
    errors=$((errors + invalid))
  else
    log "GATE PASS [G3b.2]: All result files are valid JSON arrays"
  fi

  # G3b.3: Each result has required fields (score, entity_type, username)
  local schema_fails=0
  for i in $(seq 1 "$batch_count"); do
    local rf="data/analysis_results/batch_${i}_results.json"
    if [ -f "$rf" ]; then
      local bad
      bad=$(python3 -c "
import json
data = json.load(open('$rf'))
required = {'username', 'score', 'entity_type'}
bad = [p.get('username','?') for p in data if not required.issubset(p.keys())]
print(len(bad))
" 2>/dev/null || echo "-1")
      if [ "$bad" != "0" ]; then
        log "GATE FAIL [G3b.3]: batch_$i has $bad profiles missing required fields"
        schema_fails=$((schema_fails + 1))
      fi
    fi
  done
  if [ "$schema_fails" -gt 0 ]; then
    errors=$((errors + schema_fails))
  else
    log "GATE PASS [G3b.3]: All profiles have required fields"
  fi

  # G3b.4: Result count matches input count
  local input_total result_total
  input_total=$(python3 -c "
import json, glob
print(sum(len(json.load(open(f))) for f in glob.glob('data/analysis_batches/batch_*.json')))
" 2>/dev/null || echo "0")
  result_total=$(python3 -c "
import json, glob
print(sum(len(json.load(open(f))) for f in glob.glob('data/analysis_results/batch_*_results.json')))
" 2>/dev/null || echo "0")
  if [ "$input_total" -ne "$result_total" ]; then
    log "GATE FAIL [G3b.4]: Input profiles ($input_total) != result profiles ($result_total)"
    errors=$((errors + 1))
  else
    log "GATE PASS [G3b.4]: Profile count matches ($result_total)"
  fi

  return $errors
}
```

### Phase 3c Gates: Aggregation
```bash
gate_phase3c() {
  local errors=0

  # G3c.1: Analysis results written back to database
  local analyzed
  analyzed=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers WHERE score IS NOT NULL;" 2>/dev/null || echo "0")
  if [ "$analyzed" -eq 0 ]; then
    log "GATE FAIL [G3c.1]: No followers have scores in database"
    errors=$((errors + 1))
  else
    log "GATE PASS [G3c.1]: $analyzed followers have scores"
  fi

  # G3c.2: Score distribution is reasonable (not all zeros, not all 100s)
  local distinct_scores
  distinct_scores=$(sqlite3 "$DB_PATH" "SELECT COUNT(DISTINCT score) FROM followers WHERE score IS NOT NULL;" 2>/dev/null || echo "0")
  if [ "$distinct_scores" -lt 3 ]; then
    log "GATE FAIL [G3c.2]: Only $distinct_scores distinct scores — distribution too narrow"
    errors=$((errors + 1))
  else
    log "GATE PASS [G3c.2]: $distinct_scores distinct score values"
  fi

  return $errors
}
```

### Phase 4 Gates: Reports
```bash
gate_phase4() {
  local errors=0
  local expected_files=(
    "output/db_fundraising_outreach.csv"
    "output/db_fundraising_recommendations.md"
    "output/db_marketing_partners.csv"
    "output/fundraising_outreach.csv"
    "output/fundraising_recommendations.md"
    "output/combined_top_followers.csv"
  )

  # G4.1: All expected report files exist and are non-empty
  for f in "${expected_files[@]}"; do
    if [ ! -f "$f" ]; then
      log "GATE FAIL [G4.1]: $f does not exist"
      errors=$((errors + 1))
    elif [ ! -s "$f" ]; then
      log "GATE FAIL [G4.1]: $f is empty"
      errors=$((errors + 1))
    else
      local lines
      lines=$(wc -l < "$f")
      log "GATE PASS [G4.1]: $f exists ($lines lines)"
    fi
  done

  # G4.2: CSV files have headers
  for f in output/*.csv; do
    if [ -f "$f" ]; then
      local header
      header=$(head -1 "$f")
      if [ -z "$header" ]; then
        log "GATE FAIL [G4.2]: $f has no header row"
        errors=$((errors + 1))
      else
        log "GATE PASS [G4.2]: $f header: $header"
      fi
    fi
  done

  return $errors
}
```

---

## The State File: `data/pipeline_state.md`

This is the shared brain. Every station reads it first, writes to it last.
It accumulates across the entire pipeline run — and across RETRIES.
Gate results are written here too, so retry sessions can see exactly what failed.

```markdown
# Pipeline State
# This file is the shared memory between pipeline stations.
# Each station reads this before starting and writes results when done.
# Gate results and learnings accumulate here so retries can self-heal.

## Current Run
- Started: 2026-02-13 14:30:00
- CSV: data/followers_validated.csv
- DB: data/followers.db

## Phase 1: Import — COMPLETED
- Time: 14:30:05 — 14:30:08 (3 seconds)
- Result: 830 records inserted, 0 duplicates skipped
- DB size: 830 rows, all status=pending
- Gate results:
  - G1.1 PASS: valid SQLite ✓
  - G1.2 PASS: 830 rows ✓
  - G1.3 PASS: all pending ✓
  - G1.4 PASS: 12 columns ✓

## Phase 2: Enrichment — COMPLETED (with issues)
- Time: 14:30:10 — 15:42:33 (72 minutes)
- Result: 444 completed, 12 errors, 374 private
- Gate results:
  - G2.1 PASS: 0 pending ✓
  - G2.2 PASS: 98% completed/private ✓
  - G2.3 PASS: 0 login_required ✓
  - G2.4 PASS: backup exists ✓
- LEARNING: Rate-limits after ~300 profiles. 10-min pause handles it.
- LEARNING: login_required = abort, needs human re-login.

## Phase 3c: AI Analysis — attempt 1 FAILED
- batch_13 produced markdown-wrapped JSON instead of raw JSON
- Gate results:
  - G3b.1 PASS: 15/15 files exist ✓
  - G3b.2 FAIL: batch_13 not valid JSON ✗
  - G3b.3 SKIPPED (blocked by G3b.2)
  - G3b.4 FAIL: count mismatch ✗
- LEARNING: batch_13 wrapped output in ```json fences. Retry prompt MUST
  say "No markdown code fences. No explanation text. Pure JSON only."

## Phase 3c: AI Analysis — attempt 2 COMPLETED
- batch_13 re-analyzed successfully with explicit JSON-only instructions
- Gate results:
  - G3b.1 PASS: 15/15 files ✓
  - G3b.2 PASS: all valid JSON ✓
  - G3b.3 PASS: all have required fields ✓
  - G3b.4 PASS: 444 in = 444 out ✓
- LEARNING: AI batch retries work when the error is specific in the state file

## Learnings (accumulated across all runs)
- Rate limit pause: 10 min is sufficient, 5 min is not
- login_required = abort, needs human intervention
- AI analysis: some batches produce prose instead of JSON — retry prompt
  must emphasize "JSON only, no markdown wrapping"
- Website fetch timeout: 10s is too short for some Hawaii small business
  sites, 15s works better
- Gate G3b.2 catches invalid JSON reliably — good safety net
```

---

## Periodic Code Review Stations

At two critical junctures, the pipeline runs a **review station** — a Claude
session whose ONLY job is to audit the state file, verify the plan is on
track, and flag any drift or issues.

### Review Station 1: After Phase 2 (before AI analysis)

```bash
run_station "Review 1: Pre-Analysis Audit" \
  "You are a CODE REVIEWER auditing the pipeline state before AI analysis begins.

Read data/pipeline_state.md carefully.

CHECK THESE ITEMS:
1. Phase 1 completed with all gates passed
2. Phase 2 completed with >= 50% success rate
3. No login_required errors (unrecoverable)
4. The database has enriched profile data (bio, follower_count, etc.)
5. All learnings from previous phases make sense and are actionable

RUN THESE VERIFICATION QUERIES:
  sqlite3 data/followers.db 'SELECT status, COUNT(*) FROM followers GROUP BY status;'
  sqlite3 data/followers.db 'SELECT COUNT(*) FROM followers WHERE bio IS NOT NULL AND bio != \"\";'

WRITE YOUR REVIEW to data/pipeline_state.md:
## Review 1: Pre-Analysis Audit
- Status: PASS or FAIL
- Issues found: (list)
- Recommendations: (list)
- Cleared for Phase 3: YES or NO

If you write 'Cleared for Phase 3: NO', explain exactly what needs to
be fixed. The shell script will abort if you say NO." \
  "$DISABLE_EXEC"

# Parse the review result
if grep -q "Cleared for Phase 3: NO" "$STATE_FILE"; then
  log "FATAL: Review 1 flagged issues. Check $STATE_FILE for details."
  exit 1
fi
```

### Review Station 2: After Phase 3c aggregation (before reports)

```bash
run_station "Review 2: Pre-Reports Audit" \
  "You are a CODE REVIEWER auditing the pipeline before final report generation.

Read data/pipeline_state.md carefully.

CHECK THESE ITEMS:
1. All AI analysis batches completed with gates passed
2. Aggregation wrote scores to the database
3. Score distribution looks reasonable (not all 0s, not all identical)
4. No phases were skipped or partially completed
5. All accumulated learnings are consistent (no contradictions)

RUN THESE VERIFICATION QUERIES:
  sqlite3 data/followers.db 'SELECT COUNT(*) FROM followers WHERE score IS NOT NULL;'
  sqlite3 data/followers.db 'SELECT MIN(score), AVG(score), MAX(score) FROM followers WHERE score IS NOT NULL;'
  sqlite3 data/followers.db 'SELECT entity_type, COUNT(*) FROM followers WHERE entity_type IS NOT NULL GROUP BY entity_type;'

WRITE YOUR REVIEW to data/pipeline_state.md:
## Review 2: Pre-Reports Audit
- Status: PASS or FAIL
- Score distribution: (min/avg/max)
- Entity type breakdown: (counts)
- Cleared for Phase 4: YES or NO

If you write 'Cleared for Phase 4: NO', explain exactly what needs fixing." \
  "$DISABLE_EXEC"

if grep -q "Cleared for Phase 4: NO" "$STATE_FILE"; then
  log "FATAL: Review 2 flagged issues. Check $STATE_FILE for details."
  exit 1
fi
```

---

## Tool Inventory Per Station

### What each station needs vs. what's disabled

```
ALL AVAILABLE: Bash, Read, Edit, Write, Glob, Grep, Task, TodoWrite,
               WebFetch, WebSearch, NotebookEdit, Skill, AskUserQuestion,
               ExitPlanMode
```

| Station | Needs | Disables |
|---------|-------|----------|
| Phase 1 (Import) | Bash, Read | Everything else |
| Phase 2 (Enrich) | Bash, Read | Everything else |
| Phase 3a (Extract) | Bash, Read | Everything else |
| AI Analysis (×15) | Read, Write | Everything else (including Bash) |
| Phase 3b (Aggregate) | Bash, Read | Everything else |
| Review 1 | Bash, Read | Everything else |
| Review 2 | Bash, Read | Everything else |
| Phase 4 (Reports) | Bash, Read | Everything else |

```bash
# Executor stations (run Python, read results):
DISABLE_EXEC="Task,Edit,Write,Glob,Grep,WebFetch,WebSearch,NotebookEdit,Skill,TodoWrite,AskUserQuestion,ExitPlanMode"

# AI analyzer stations (read profiles, write JSON):
DISABLE_AI="Bash,Task,Edit,Glob,Grep,WebFetch,WebSearch,NotebookEdit,Skill,TodoWrite,AskUserQuestion,ExitPlanMode"
```

All stations also get:
- `--strict-mcp-config` — no MCP servers
- `--settings .claude/settings.automation.json` — all 10 plugins disabled

---

## Context Budget Per Station

| Station | Prompt | State file | Work | Peak | Risk |
|---------|--------|-----------|------|------|------|
| Phase 1 | ~200 | ~500 (short) | 1 Bash | ~2,700 | None |
| Phase 2 | ~300 | ~800 | ~14 polls | ~9,000 | Low |
| Phase 3a | ~300 | ~1,200 | 2 Bash | ~3,500 | None |
| AI Analysis | ~400 | ~1,500 | Read 30 profiles | ~12,000 | Low |
| Phase 3b | ~200 | ~2,000 | 1 Bash | ~4,000 | None |
| Review 1 | ~400 | ~2,500 | 3 SQL queries | ~5,000 | None |
| Review 2 | ~400 | ~3,000 | 3 SQL queries | ~5,500 | None |
| Phase 4 | ~200 | ~3,500 | 1 Bash | ~5,500 | None |
| **Shell script** | **N/A** | **N/A** | **N/A** | **0** | **None** |

---

## The Complete Orchestrator: `scripts/run_afk_pipeline.sh`

```bash
#!/bin/bash
# ============================================================================
# Hawaii FIDO AFK Pipeline — One Command, Walk Away
# ============================================================================
#
# Usage:
#   ./scripts/run_afk_pipeline.sh
#
# Prerequisites:
#   1. Chrome running with: google-chrome --remote-debugging-port=9222
#   2. Logged into Instagram in that Chrome window
#   3. data/followers_validated.csv exists
#
# Architecture:
#   - Each phase runs in an isolated Claude session (context isolation)
#   - data/pipeline_state.md is the shared memory (Ralph Wiggum pattern)
#   - Gates verify output BEFORE advancing (back pressure)
#   - Review stations audit the pipeline at critical junctures
#   - Failed phases write learnings → retries read and self-heal
#
# Outputs:
#   output/db_fundraising_outreach.csv
#   output/db_fundraising_recommendations.md
#   output/db_marketing_partners.csv
#   output/fundraising_outreach.csv
#   output/fundraising_recommendations.md
#   output/combined_top_followers.csv
#
# Logs:
#   data/pipeline_state.md          — structured state + learnings (agents RW)
#   logs/pipeline_YYYYMMDD_HHMMSS.log — raw session output (forensic)
#
# ============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# --- Config ---
SETTINGS="$PROJECT_ROOT/.claude/settings.automation.json"
STATE_FILE="$PROJECT_ROOT/data/pipeline_state.md"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"
DB_PATH="data/followers.db"
CSV_PATH="data/followers_validated.csv"
MAX_RETRIES=2
AI_WAVE_SIZE=5

# Tools to disable per station type
DISABLE_EXEC="Task,Edit,Write,Glob,Grep,WebFetch,WebSearch,NotebookEdit,Skill,TodoWrite,AskUserQuestion,ExitPlanMode"
DISABLE_AI="Bash,Task,Edit,Glob,Grep,WebFetch,WebSearch,NotebookEdit,Skill,TodoWrite,AskUserQuestion,ExitPlanMode"

# Common claude flags
CLAUDE_FLAGS="--strict-mcp-config --settings $SETTINGS"

# --- Logging ---
mkdir -p "$LOG_DIR"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

log_section() {
  local sep="============================================================"
  log "$sep"
  log "$1"
  log "$sep"
}

# --- State file helpers ---

init_state() {
  mkdir -p "$(dirname "$STATE_FILE")"

  # Preserve learnings from previous runs
  local prev_learnings=""
  if [ -f "$STATE_FILE" ]; then
    prev_learnings=$(sed -n '/^## Learnings/,$ p' "$STATE_FILE" 2>/dev/null | tail -n +2 || true)
  fi

  cat > "$STATE_FILE" << EOF
# Pipeline State
# Shared memory between pipeline stations (Ralph Wiggum pattern).
# Each station reads this FIRST, writes results LAST.
# Gate results and learnings accumulate so retries can self-heal.

## Current Run
- Started: $(date '+%Y-%m-%d %H:%M:%S')
- CSV: $CSV_PATH
- DB: $DB_PATH
- Log: $LOG_FILE

## Learnings (accumulated across all runs)
${prev_learnings:-"- First run, no learnings yet."}
EOF
}

write_gate_result() {
  local phase_name="$1"
  local gate_output="$2"
  local pass_fail="$3"

  cat >> "$STATE_FILE" << EOF

## Gate: $phase_name — $pass_fail
- Time: $(date '+%Y-%m-%d %H:%M:%S')
$gate_output
EOF
}

# --- Run a claude station with retry + gate verification ---

run_station() {
  local phase_name="$1"
  local prompt="$2"
  local disabled_tools="$3"
  local attempt=0

  while [ $attempt -le $MAX_RETRIES ]; do
    attempt=$((attempt + 1))
    log "$phase_name — attempt $attempt/$((MAX_RETRIES + 1))"

    local full_prompt
    full_prompt=$(cat << PROMPT_EOF
You are a pipeline station running in AFK mode. No human is available.

FIRST: Read data/pipeline_state.md to understand:
- What has happened so far in this pipeline run
- Any learnings from previous stations or previous retries
- Any gate failures that explain why you are being retried

YOUR TASK:
$prompt

WHEN DONE — Update data/pipeline_state.md by APPENDING:
## $phase_name — attempt $attempt
- Time: [start] — [end]
- Result: [what happened, with counts]
- Errors: [any errors, with exact messages]
- LEARNINGS: [anything the next station or a retry should know]
  Be SPECIFIC: include exact error messages, workarounds that worked,
  settings that needed adjustment, timing observations.

IMPORTANT: Be extremely verbose in your state file entries. The developer
will read this file to understand everything that happened. Include counts,
timing, error messages, and decisions you made.
PROMPT_EOF
    )

    if claude -p "$full_prompt" \
         --disallowed-tools "$disabled_tools" \
         $CLAUDE_FLAGS \
         2>&1 | tee -a "$LOG_FILE"; then
      log "$phase_name — station exited successfully"
      return 0
    else
      local exit_code=$?
      log "$phase_name — station FAILED (exit code $exit_code)"

      cat >> "$STATE_FILE" << FAIL_EOF

## $phase_name — FAILED (attempt $attempt, exit code $exit_code)
- Time: $(date '+%Y-%m-%d %H:%M:%S')
- Exit code: $exit_code
- Full output in: $LOG_FILE
- RETRY INSTRUCTION: Read this state file for what went wrong, then
  adjust your approach based on the learnings above.
FAIL_EOF

      if [ $attempt -le $MAX_RETRIES ]; then
        local wait=$((attempt * 10))
        log "$phase_name — retrying in ${wait}s..."
        sleep $wait
      fi
    fi
  done

  log "FATAL: $phase_name failed after $((MAX_RETRIES + 1)) attempts."
  exit 1
}

# --- Run a gate (back pressure check) ---

run_gate() {
  local gate_name="$1"
  local gate_func="$2"
  local gate_output
  local gate_errors

  log "Running gate: $gate_name"

  # Capture gate output and exit code
  gate_output=$($gate_func 2>&1) || true
  gate_errors=$?

  # Log every line
  while IFS= read -r line; do
    log "  $line"
  done <<< "$gate_output"

  if [ "$gate_errors" -eq 0 ]; then
    log "GATE PASSED: $gate_name"
    write_gate_result "$gate_name" "$gate_output" "PASSED"
    return 0
  else
    log "GATE FAILED: $gate_name ($gate_errors failures)"
    write_gate_result "$gate_name" "$gate_output" "FAILED ($gate_errors issues)"
    return 1
  fi
}

# ============================================================================
# GATE DEFINITIONS
# ============================================================================

gate_phase1() {
  local errors=0

  # G1.1: Database is valid SQLite
  if ! sqlite3 "$DB_PATH" "SELECT 1;" > /dev/null 2>&1; then
    echo "FAIL [G1.1]: Database is not valid SQLite"; errors=$((errors + 1))
  else
    echo "PASS [G1.1]: Database is valid SQLite"
  fi

  # G1.2: followers table has rows
  local count
  count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers;" 2>/dev/null || echo "0")
  if [ "$count" -eq 0 ]; then
    echo "FAIL [G1.2]: followers table is empty"; errors=$((errors + 1))
  else
    echo "PASS [G1.2]: followers table has $count rows"
  fi

  # G1.3: All rows have status = 'pending'
  local non_pending
  non_pending=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers WHERE status != 'pending';" 2>/dev/null || echo "-1")
  if [ "$non_pending" -ne 0 ]; then
    echo "FAIL [G1.3]: $non_pending rows have non-pending status"; errors=$((errors + 1))
  else
    echo "PASS [G1.3]: All rows status=pending"
  fi

  return $errors
}

gate_phase2() {
  local errors=0

  # G2.1: No pending rows remain
  local pending
  pending=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers WHERE status = 'pending';" 2>/dev/null || echo "-1")
  if [ "$pending" -gt 0 ]; then
    echo "WARN [G2.1]: $pending rows still pending (partial enrichment)"
  else
    echo "PASS [G2.1]: No pending rows"
  fi

  # G2.2: >= 50% completed or private
  local total cp
  total=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers;" 2>/dev/null || echo "1")
  cp=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers WHERE status IN ('completed','private');" 2>/dev/null || echo "0")
  local pct=$((cp * 100 / total))
  if [ "$pct" -lt 50 ]; then
    echo "FAIL [G2.2]: Only ${pct}% completed/private ($cp/$total)"; errors=$((errors + 1))
  else
    echo "PASS [G2.2]: ${pct}% completed/private ($cp/$total)"
  fi

  # G2.3: No login_required errors
  local login_err
  login_err=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers WHERE error_message LIKE '%login_required%';" 2>/dev/null || echo "0")
  if [ "$login_err" -gt 0 ]; then
    echo "FAIL [G2.3]: $login_err login_required errors (session expired)"; errors=$((errors + 1))
  else
    echo "PASS [G2.3]: No login_required errors"
  fi

  return $errors
}

gate_phase3a() {
  local errors=0

  # G3a.1: candidates_raw.json exists and is valid
  if [ ! -f "data/candidates_raw.json" ]; then
    echo "FAIL [G3a.1]: candidates_raw.json missing"; errors=$((errors + 1))
  elif ! python3 -c "import json; json.load(open('data/candidates_raw.json'))" 2>/dev/null; then
    echo "FAIL [G3a.1]: candidates_raw.json invalid JSON"; errors=$((errors + 1))
  else
    local n
    n=$(python3 -c "import json; print(len(json.load(open('data/candidates_raw.json'))))" 2>/dev/null)
    echo "PASS [G3a.1]: $n candidates extracted"
  fi

  # G3a.2: Batch files exist
  local bc
  bc=$(ls -1 data/analysis_batches/batch_*.json 2>/dev/null | wc -l)
  if [ "$bc" -eq 0 ]; then
    echo "FAIL [G3a.2]: No batch files"; errors=$((errors + 1))
  else
    echo "PASS [G3a.2]: $bc batch files"
  fi

  # G3a.3: All batch files valid JSON
  local invalid=0
  for f in data/analysis_batches/batch_*.json; do
    if ! python3 -c "import json; json.load(open('$f'))" 2>/dev/null; then
      echo "FAIL [G3a.3]: $f invalid JSON"; invalid=$((invalid + 1))
    fi
  done
  [ "$invalid" -gt 0 ] && errors=$((errors + invalid)) || echo "PASS [G3a.3]: All batches valid JSON"

  return $errors
}

gate_phase3b_ai() {
  local errors=0
  local bc
  bc=$(ls -1 data/analysis_batches/batch_*.json 2>/dev/null | wc -l)

  # G3b.1: All result files exist
  local missing=0
  for i in $(seq 1 "$bc"); do
    [ ! -f "data/analysis_results/batch_${i}_results.json" ] && missing=$((missing + 1))
  done
  [ "$missing" -gt 0 ] && { echo "FAIL [G3b.1]: $missing result files missing"; errors=$((errors + missing)); } \
                        || echo "PASS [G3b.1]: All $bc result files exist"

  # G3b.2: All result files are valid JSON arrays
  local invalid=0
  for i in $(seq 1 "$bc"); do
    local rf="data/analysis_results/batch_${i}_results.json"
    if [ -f "$rf" ] && ! python3 -c "import json; assert isinstance(json.load(open('$rf')), list)" 2>/dev/null; then
      echo "FAIL [G3b.2]: batch_${i}_results.json not a valid JSON array"
      invalid=$((invalid + 1))
    fi
  done
  [ "$invalid" -gt 0 ] && errors=$((errors + invalid)) || echo "PASS [G3b.2]: All results are JSON arrays"

  # G3b.3: Required fields present
  local schema_fails=0
  for i in $(seq 1 "$bc"); do
    local rf="data/analysis_results/batch_${i}_results.json"
    if [ -f "$rf" ]; then
      local bad
      bad=$(python3 -c "
import json
data = json.load(open('$rf'))
print(sum(1 for p in data if not {'username','score','entity_type'}.issubset(p.keys())))
" 2>/dev/null || echo "99")
      [ "$bad" != "0" ] && { echo "FAIL [G3b.3]: batch_$i: $bad profiles missing fields"; schema_fails=$((schema_fails + 1)); }
    fi
  done
  [ "$schema_fails" -gt 0 ] && errors=$((errors + schema_fails)) || echo "PASS [G3b.3]: All profiles have required fields"

  return $errors
}

gate_phase3c() {
  local errors=0

  # G3c.1: Scores in database
  local scored
  scored=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM followers WHERE score IS NOT NULL;" 2>/dev/null || echo "0")
  if [ "$scored" -eq 0 ]; then
    echo "FAIL [G3c.1]: No scores in database"; errors=$((errors + 1))
  else
    echo "PASS [G3c.1]: $scored followers scored"
  fi

  # G3c.2: Score diversity
  local distinct
  distinct=$(sqlite3 "$DB_PATH" "SELECT COUNT(DISTINCT score) FROM followers WHERE score IS NOT NULL;" 2>/dev/null || echo "0")
  if [ "$distinct" -lt 3 ]; then
    echo "FAIL [G3c.2]: Only $distinct distinct scores"; errors=$((errors + 1))
  else
    echo "PASS [G3c.2]: $distinct distinct score values"
  fi

  return $errors
}

gate_phase4() {
  local errors=0
  local files=("output/db_fundraising_outreach.csv" "output/db_fundraising_recommendations.md"
               "output/db_marketing_partners.csv" "output/fundraising_outreach.csv"
               "output/fundraising_recommendations.md" "output/combined_top_followers.csv")

  for f in "${files[@]}"; do
    if [ ! -s "$f" ]; then
      echo "FAIL [G4.1]: $f missing or empty"; errors=$((errors + 1))
    else
      echo "PASS [G4.1]: $f ($(wc -l < "$f") lines)"
    fi
  done

  return $errors
}

# --- Run phase with gate (back pressure loop) ---

run_phase_with_gate() {
  local phase_name="$1"
  local prompt="$2"
  local disabled_tools="$3"
  local gate_func="$4"
  local attempt=0

  while [ $attempt -le $MAX_RETRIES ]; do
    attempt=$((attempt + 1))

    # Run the station
    run_station "$phase_name (attempt $attempt)" "$prompt" "$disabled_tools"

    # Run the gate
    if run_gate "$phase_name gate" "$gate_func"; then
      log "$phase_name: ALL GATES PASSED"
      git_checkpoint "$phase_name"
      return 0
    else
      log "$phase_name: GATE FAILED — writing context for retry"

      cat >> "$STATE_FILE" << GATE_FAIL_EOF

## $phase_name — GATE FAILED (attempt $attempt)
- Time: $(date '+%Y-%m-%d %H:%M:%S')
- The station exited OK but its output did not pass verification.
- See gate results above for specific failures.
- RETRY: The next attempt must fix the gate failures listed above.
GATE_FAIL_EOF

      if [ $attempt -le $MAX_RETRIES ]; then
        log "$phase_name — retrying (gate failure recovery)..."
        sleep 5
      fi
    fi
  done

  log "FATAL: $phase_name gate failed after $((MAX_RETRIES + 1)) attempts."
  exit 1
}

# --- Git checkpoint (commit after each passing gate) ---

git_checkpoint() {
  local phase_name="$1"
  local gate_summary
  gate_summary=$(grep -c "PASS \[" "$STATE_FILE" 2>/dev/null || echo "?")

  log "Git checkpoint: $phase_name"
  # Only commit trackable files — intermediary files are gitignored
  git add data/pipeline_state.md data/followers.db "$LOG_FILE" 2>/dev/null || true
  git add output/ 2>/dev/null || true
  git commit -m "$phase_name — gate passed [$gate_summary checks]" \
    --allow-empty 2>&1 | tee -a "$LOG_FILE" || true
  log "Git checkpoint committed"
}

# ============================================================================
# PIPELINE EXECUTION
# ============================================================================

log_section "PREFLIGHT CHECKS"

if [ ! -f "$CSV_PATH" ]; then
  log "FATAL: CSV not found at $CSV_PATH"; exit 1
fi
log "OK: CSV exists: $CSV_PATH"

if curl -s http://localhost:9222/json/version > /dev/null 2>&1; then
  log "OK: Chrome remote debugging on port 9222"
else
  log "WARNING: Chrome not on port 9222 — Phase 2 will fail"
fi

init_state
log "OK: State file: $STATE_FILE"
log "OK: Log file: $LOG_FILE"

# ---- PHASE 1: Import ----
log_section "PHASE 1: Import CSV → Database"

run_phase_with_gate "Phase 1: Import" \
  "Run: python3 scripts/run_pipeline.py --phase 1 --csv $CSV_PATH --db $DB_PATH
Report: records inserted, duplicates skipped, final row count." \
  "$DISABLE_EXEC" \
  gate_phase1

# ---- PHASE 2: Enrich ----
log_section "PHASE 2: Enrich profiles via Playwright (~70 min)"

# Back up DB (CLAUDE.md: irreplaceable)
[ -f "$DB_PATH" ] && cp "$DB_PATH" "${DB_PATH}.bak" && log "OK: DB backed up"

run_phase_with_gate "Phase 2: Enrich" \
  "Run Instagram profile enrichment (40-70 min):
1. python3 scripts/run_pipeline.py --phase 2 --db $DB_PATH
2. When complete: python3 scripts/run_pipeline.py --status --db $DB_PATH
Report: completed, errors, private, pending counts.
If login_required errors: note as CRITICAL in state file." \
  "$DISABLE_EXEC" \
  gate_phase2

# ---- REVIEW 1: Pre-Analysis Audit ----
log_section "REVIEW 1: Pre-Analysis Audit"

run_station "Review 1: Pre-Analysis" \
  "You are auditing the pipeline before AI analysis.
Read data/pipeline_state.md. Verify:
1. Phase 1 & 2 completed with gates passed
2. No login_required errors
3. Database has enriched data:
   sqlite3 $DB_PATH 'SELECT status, COUNT(*) FROM followers GROUP BY status;'
   sqlite3 $DB_PATH 'SELECT COUNT(*) FROM followers WHERE bio IS NOT NULL AND bio != \"\";'
Append review to data/pipeline_state.md:
## Review 1: Pre-Analysis Audit
- Status: PASS/FAIL
- Cleared for Phase 3: YES/NO
- (details)" \
  "$DISABLE_EXEC"

if grep -q "Cleared for Phase 3: NO" "$STATE_FILE"; then
  log "FATAL: Review 1 blocked pipeline. See $STATE_FILE"; exit 1
fi
log "Review 1: CLEARED"

# ---- PHASE 3a: Extract + Prepare ----
log_section "PHASE 3a: Extract candidates + prepare batches"

run_phase_with_gate "Phase 3a: Extract" \
  "Run in sequence:
1. python3 scripts/run_pipeline.py --phase 3 --step extract --db $DB_PATH
2. python3 scripts/run_pipeline.py --phase 3 --step prepare --db $DB_PATH
Report: candidates extracted, website content count, batch files created." \
  "$DISABLE_EXEC" \
  gate_phase3a

# ---- PHASE 3b: AI Analysis (parallel waves) ----
log_section "PHASE 3b: AI Analysis (parallel batches)"

mkdir -p data/analysis_results

BATCH_COUNT=$(ls -1 data/analysis_batches/batch_*.json 2>/dev/null | wc -l)
WAVE_COUNT=$(( (BATCH_COUNT + AI_WAVE_SIZE - 1) / AI_WAVE_SIZE ))
log "Batches: $BATCH_COUNT | Waves: $WAVE_COUNT | Wave size: $AI_WAVE_SIZE"

for wave in $(seq 1 $WAVE_COUNT); do
  ws=$(( (wave - 1) * AI_WAVE_SIZE + 1 ))
  we=$(( wave * AI_WAVE_SIZE ))
  [ $we -gt $BATCH_COUNT ] && we=$BATCH_COUNT

  log "Wave $wave/$WAVE_COUNT: batches $ws-$we"

  pids=()
  for i in $(seq $ws $we); do
    bf="data/analysis_batches/batch_${i}.json"
    rf="data/analysis_results/batch_${i}_results.json"

    # Resume-friendly: skip completed batches
    if [ -f "$rf" ] && [ -s "$rf" ]; then
      log "  Batch $i: exists, skipping"
      continue
    fi

    log "  Batch $i: launching..."

    claude -p "You analyze Instagram profiles for fundraising potential.

FIRST: Read data/pipeline_state.md for learnings (esp. about JSON formatting).

Read: $bf (profiles) and data/AI_ANALYSIS_FRAMEWORK.md (scoring rules).

For EACH profile:
- Check exclusion rules FIRST
- If excluded: score=0, entity_type=EXCLUDE_*, outreach_type=SKIP
- If not excluded: score on 4 factors per framework
- Include specific reasoning citing bio/website evidence

CRITICAL OUTPUT RULES:
- Write ONLY valid JSON to $rf
- No markdown code fences. No explanation. No prose.
- Start with [ and end with ]
- Each element: {\"username\":..., \"score\":..., \"entity_type\":..., ...}

After writing, append to data/pipeline_state.md:
- Batch $i: COMPLETED/FAILED
- Profiles: N scored, M excluded
- Any issues" \
      --disallowed-tools "$DISABLE_AI" \
      $CLAUDE_FLAGS \
      2>&1 | tee -a "$LOG_FILE" &

    pids+=($!)
  done

  # Wait + count failures
  fails=0
  for pid in "${pids[@]}"; do
    wait "$pid" || fails=$((fails + 1))
  done

  if [ $fails -gt 0 ]; then
    log "  Wave $wave: $fails failures, retrying..."
    for i in $(seq $ws $we); do
      rf="data/analysis_results/batch_${i}_results.json"
      if [ ! -f "$rf" ] || [ ! -s "$rf" ]; then
        log "  Batch $i: RETRY"
        claude -p "RETRY: batch $i failed. Read data/pipeline_state.md for why.
Read data/analysis_batches/batch_${i}.json + data/AI_ANALYSIS_FRAMEWORK.md.
Write ONLY a valid JSON array to data/analysis_results/batch_${i}_results.json.
NO markdown fences. NO explanation. Start with [ end with ].
Update data/pipeline_state.md with retry result." \
          --disallowed-tools "$DISABLE_AI" \
          $CLAUDE_FLAGS \
          2>&1 | tee -a "$LOG_FILE" || true
      fi
    done
  fi

  log "  Wave $wave: done"
done

# Gate: verify all AI results
if ! run_gate "Phase 3b: AI Results" gate_phase3b_ai; then
  log "FATAL: AI analysis gate failed. See $STATE_FILE"; exit 1
fi

# ---- PHASE 3c: Aggregate ----
log_section "PHASE 3c: Aggregate results"

run_phase_with_gate "Phase 3c: Aggregate" \
  "Run: python3 scripts/run_pipeline.py --phase 3 --step aggregate --db $DB_PATH
Report: total profiles, excluded, scored, score distribution." \
  "$DISABLE_EXEC" \
  gate_phase3c

# ---- REVIEW 2: Pre-Reports Audit ----
log_section "REVIEW 2: Pre-Reports Audit"

run_station "Review 2: Pre-Reports" \
  "You are auditing the pipeline before report generation.
Read data/pipeline_state.md. Verify:
1. All analysis batches completed with gates passed
2. Aggregation wrote scores to DB
3. Score distribution is reasonable:
   sqlite3 $DB_PATH 'SELECT MIN(score), AVG(score), MAX(score) FROM followers WHERE score IS NOT NULL;'
   sqlite3 $DB_PATH 'SELECT entity_type, COUNT(*) FROM followers WHERE entity_type IS NOT NULL GROUP BY entity_type;'
Append to data/pipeline_state.md:
## Review 2: Pre-Reports Audit
- Status: PASS/FAIL
- Cleared for Phase 4: YES/NO
- Score range: [min]-[max], avg [avg]
- Entity breakdown: [counts]" \
  "$DISABLE_EXEC"

if grep -q "Cleared for Phase 4: NO" "$STATE_FILE"; then
  log "FATAL: Review 2 blocked pipeline. See $STATE_FILE"; exit 1
fi
log "Review 2: CLEARED"

# ---- PHASE 4: Reports ----
log_section "PHASE 4: Generate reports"

run_phase_with_gate "Phase 4: Reports" \
  "Run: python3 scripts/run_pipeline.py --phase 4 --db $DB_PATH
Report: files generated, line counts, locations." \
  "$DISABLE_EXEC" \
  gate_phase4

# ============================================================================
# CLEANUP: Remove intermediary files, keep logs + learnings
# ============================================================================

log_section "CLEANUP: Intermediary files"

# Intermediary files are gitignored — they never enter git history.
# They exist only on disk during the pipeline run.
# These are transformation artifacts — the data they contain is now in
# the database and the final reports. Safe to remove.
INTERMEDIARY_FILES=(
  "data/candidates_raw.json"
  "data/analysis_batches"
  "data/analysis_results"
  "data/followers.db.bak"
)

# These are RETAINED (and committed to git):
#   data/pipeline_state.md    — learnings for future runs (Ralph Wiggum memory)
#   logs/pipeline_*.log       — forensic session logs
#   data/followers.db         — the database (git-tracked per CLAUDE.md)
#   output/*                  — the final deliverables

log "Intermediary files (gitignored, local only):"
for item in "${INTERMEDIARY_FILES[@]}"; do
  if [ -e "$item" ]; then
    if [ -d "$item" ]; then
      local count
      count=$(find "$item" -type f | wc -l)
      log "  $item/ ($count files)"
    else
      log "  $item ($(wc -c < "$item") bytes)"
    fi
  fi
done
log ""
log "Retained (committed to git):"
log "  data/pipeline_state.md  — learnings for future runs"
log "  logs/                   — session logs"
log "  data/followers.db       — database"
log "  output/                 — final reports"

# Prompt-gated: only clean up if CLEANUP_INTERMEDIARY=1 is set
# Default: show what would be deleted but don't delete
# NOTE: No git commit needed — these files are gitignored
if [ "${CLEANUP_INTERMEDIARY:-0}" = "1" ]; then
  for item in "${INTERMEDIARY_FILES[@]}"; do
    if [ -e "$item" ]; then
      rm -rf "$item"
      log "  DELETED: $item"
    fi
  done
  log "Intermediary files cleaned up (no git commit needed — gitignored)."
else
  log ""
  log "To delete intermediary files, re-run with:"
  log "  CLEANUP_INTERMEDIARY=1 ./scripts/run_afk_pipeline.sh"
  log "Or delete manually:"
  for item in "${INTERMEDIARY_FILES[@]}"; do
    [ -e "$item" ] && log "  rm -rf $item"
  done
fi

# ============================================================================
# DONE
# ============================================================================

log_section "PIPELINE COMPLETE"
log ""
log "Reports:"
ls -la output/ 2>/dev/null | while read -r line; do log "  $line"; done
log ""
log "State:  $STATE_FILE (retained — learnings for future runs)"
log "Log:    $LOG_FILE (retained — forensic record)"
log ""
log "Git history:"
git log --oneline -10 2>/dev/null | while read -r line; do log "  $line"; done
log ""
log "To review: /top-prospects"
```

---

## The Ralph Wiggum Pattern + Back Pressure — How They Work Together

### The Loop

```
┌─────────────────────────────────────┐
│ Shell runs Station N                │
│   ↓                                 │
│ Station reads pipeline_state.md     │
│   ↓                                 │
│ Station does work (Python/AI)       │
│   ↓                                 │
│ Station writes results + learnings  │
│   to pipeline_state.md              │
│   ↓                                 │
│ Shell runs Gate N                   │──── PASS → proceed to Station N+1
│   ↓                                 │
│ Gate FAILS                          │
│   ↓                                 │
│ Shell writes gate failure details   │
│   to pipeline_state.md              │
│   ↓                                 │
│ Shell retries Station N             │
│   ↓                                 │
│ NEW session reads pipeline_state.md │
│   sees: what was tried, what failed,│
│   what the gate expected, learnings │
│   ↓                                 │
│ Station adjusts approach and retries│
│   ↓                                 │
│ Shell runs Gate N again             │──── PASS → proceed
│   ↓                                 │
│ Gate FAILS again?                   │──── After MAX_RETRIES → ABORT
└─────────────────────────────────────┘
```

### Self-Healing Example: AI batch produces invalid JSON

**Turn 1:**
```
Station AI-13 runs → writes batch_13_results.json
Shell gate G3b.2 checks: python3 -c "json.load(...)" → FAILS (markdown fences)
Shell writes to pipeline_state.md:
  "## Phase 3b: AI Results gate — FAILED
   FAIL [G3b.2]: batch_13_results.json not a valid JSON array"
```

**Turn 2 (automatic retry):**
```
Station AI-13 retry starts
Reads pipeline_state.md → sees "FAIL [G3b.2]" and the learning
  "markdown-wrapped JSON" from the state file
The retry prompt already says "NO markdown fences"
Writes clean JSON → Gate passes → Pipeline continues
```

**The state file now has:**
```markdown
## Phase 3b batch 13 — attempt 1
- FAILED: wrote markdown-wrapped JSON
- LEARNING: Claude wrapped output in ```json fences despite instructions.
  Retry prompt must be more emphatic: "Start with [ end with ]"

## Phase 3b batch 13 — attempt 2
- COMPLETED: 30 profiles scored, clean JSON
- LEARNING: The emphatic "Start with [ end with ]" instruction works.
```

### Review Stations: The Periodic Audit

At two critical points, a dedicated Claude session does nothing but audit:

1. **Review 1 (after enrichment, before AI):** Checks that the database has
   real data, that enrichment didn't silently fail, that no unrecoverable
   errors occurred. Can block the pipeline with "Cleared for Phase 3: NO".

2. **Review 2 (after AI, before reports):** Checks score distribution makes
   sense (not all zeros, not all identical), entity types are populated,
   counts match. Can block with "Cleared for Phase 4: NO".

These are the "are we on track?" checkpoints. They catch drift that individual
gates might miss — like "every gate passed but the overall numbers don't
add up."

### Git Checkpoints in Practice

After every passing gate (both build and runtime), the shell commits:

```
$ git log --oneline
a8d9e0f Phase 4: Reports — gate passed [8 checks]
7c6b5a4 Review 2: Pre-Reports — CLEARED
3e2d1c0 Phase 3c: Aggregate — gate passed [6 checks]
9f8e7d6 Phase 3b: AI Results — gate passed [12 checks]
4a3b2c1 Phase 3a: Extract — gate passed [7 checks]
d5e6f7a Review 1: Pre-Analysis — CLEARED
8b9c0d1 Phase 2: Enrich — gate passed [6 checks]
2a1b3c4 Phase 1: Import — gate passed [5 checks]
e4f5a6b Phase C gate PASS — 7 old scripts deleted [all tests green]
b7c8d9e Phase B gate PASS — pipeline CLI wired up [all tests green]
1a2b3c4 Phase A gate PASS — 5 modules moved to src/ [all tests green]
```

If Phase 3c corrupts the DB, roll back:
```
git diff 9f8e7d6..3e2d1c0 -- data/followers.db
git checkout 9f8e7d6 -- data/followers.db  # restore pre-aggregation DB
```

### File Lifecycle: What's Created, What's Kept, What's Cleaned

**Intermediary files are `.gitignore`d — they NEVER enter git history.**

The build adds these entries to `.gitignore`:
```gitignore
# Pipeline intermediary files — never committed
data/candidates_raw.json
data/analysis_batches/
data/analysis_results/
data/followers.db.bak
```

```
CREATED DURING PIPELINE → DISPOSITION          → IN GIT?
──────────────────────────────────────────────────────────
data/candidates_raw.json        → INTERMEDIARY  → NO (gitignored)
data/analysis_batches/*.json    → INTERMEDIARY  → NO (gitignored)
data/analysis_results/*.json    → INTERMEDIARY  → NO (gitignored)
data/followers.db.bak           → INTERMEDIARY  → NO (gitignored)
/tmp/phase_b_test.db            → INTERMEDIARY  → NO (tmp)

data/pipeline_state.md          → RETAINED      → YES (learnings)
logs/pipeline_*.log             → RETAINED      → YES (forensic)
data/followers.db               → RETAINED      → YES (per CLAUDE.md)

output/db_fundraising_outreach.csv        → FINAL OUTPUT → YES
output/db_fundraising_recommendations.md  → FINAL OUTPUT → YES
output/db_marketing_partners.csv          → FINAL OUTPUT → YES
output/fundraising_outreach.csv           → FINAL OUTPUT → YES
output/fundraising_recommendations.md     → FINAL OUTPUT → YES
output/combined_top_followers.csv         → FINAL OUTPUT → YES
```

**Cleanup is prompt-gated:** By default, the pipeline shows what would be
deleted but does NOT delete. The developer must explicitly opt in:
```bash
CLEANUP_INTERMEDIARY=1 ./scripts/run_afk_pipeline.sh
```

Or run cleanup after reviewing:
```bash
rm -rf data/candidates_raw.json data/analysis_batches/ data/analysis_results/
git add -A && git commit -m "Manual cleanup — intermediary files removed"
```

---

## What Needs to Be Built (Code Changes)

### New `src/` modules (move from scripts, don't merge)

| Module | ~Lines | From | Purpose |
|--------|--------|------|---------|
| `src/browser.py` | 180 | Extract from `scripts/enrich.py` | BrowserConnectionManager + make_fetcher |
| `src/candidate_extractor.py` | 250 | Move `scripts/extract_raw_candidates.py` | DB → candidates JSON + website fetch |
| `src/analysis.py` | 160 | Merge 2 small scripts (83+129) | Batch split + aggregate results |
| `src/db_reports.py` | 390 | Move `scripts/generate_db_reports.py` | DB-direct report generation |
| `src/ai_reports.py` | 300 | Move `scripts/format_reports.py` | AI JSON → markdown/CSV formatting |
| `src/pipeline.py` | 100 | Expand existing 30-line file | Phase 1-4 entry points (JSON stdout) |

### New scripts

| Script | ~Lines | Purpose |
|--------|--------|---------|
| `scripts/run_pipeline.py` | 100 | CLI entry point — each `--phase` prints JSON |
| `scripts/run_afk_pipeline.sh` | ~350 | Shell orchestrator with gates + reviews |

### Modified
- `scripts/enrich.py` — slimmed to ~120 lines (imports from `src/browser`)
- `.gitignore` — add pipeline intermediary files:
  ```
  # Pipeline intermediary files — never committed
  data/candidates_raw.json
  data/analysis_batches/
  data/analysis_results/
  data/followers.db.bak
  ```

### Deleted (7 scripts)
- `extract_raw_candidates.py`, `ai_analysis_orchestrator.py`, `aggregate_and_rank.py`
- `format_reports.py`, `generate_db_reports.py`, `merge_top_followers.py`
- `analyze_fundraising_candidates.py`

### New tests
- `tests/unit/test_browser.py` (~150 lines)
- `tests/unit/test_candidate_extractor.py` (~200 lines)
- `tests/unit/test_analysis.py` (~150 lines)
- `tests/unit/test_ai_reports.py` (~200 lines)
- Rename `test_generate_db_reports.py` → `test_report_generator.py`

---

## Build Order (with Back Pressure Gates)

**Iron rule:** No build phase advances until ALL of the following pass:
1. All tests for that phase pass (`pytest` — zero failures)
2. A code review station verifies the deliverables match the spec
3. Any failures are written to the state file and the phase retries
4. On PASS: the phase commits to git — creating a rollback checkpoint

The build itself follows the Ralph Wiggum pattern. If Phase A's review
station finds that `browser.py` is missing a function, it writes the
specific failure to the state file. The next loop turn reads it and fixes it.

### Git Checkpoints

Every passing gate commits its work to git. This gives us a clean rollback
history if a later phase breaks something. The commit messages follow a
strict format so the history is readable:

```
Phase A gate PASS — 5 modules moved to src/ [all tests green]
Phase B gate PASS — pipeline CLI + shell orchestrator wired up [all tests green]
Phase C gate PASS — 7 old scripts deleted, CLAUDE.md updated [all tests green]
```

In the AFK runtime pipeline, gates also commit after each phase:
```
Pipeline Phase 1 — 830 records imported [gate: 3/3 passed]
Pipeline Phase 2 — 444 enriched, 374 private, 12 errors [gate: 3/3 passed]
Pipeline Phase 3a — 444 candidates, 15 batches [gate: 3/3 passed]
Pipeline Phase 3b — 15/15 AI batches analyzed [gate: 4/4 passed]
Pipeline Phase 3c — scores aggregated to DB [gate: 2/2 passed]
Pipeline Phase 4 — 6 report files generated [gate: 2/2 passed]
```

If something goes wrong in Phase C, you can `git log` to see every
checkpoint, and `git diff Phase_B..Phase_C` to see exactly what changed.
If a runtime pipeline phase corrupts the DB, the backup is there AND
you have the pre-phase commit to diff against.

### Phase A: Move modules (5 parallel sub-agents)

| Task | Reads | Writes |
|------|-------|--------|
| A1: browser.py | enrich.py (445) | browser.py (~180) + test (~150) |
| A2: candidate_extractor.py | extract_raw_candidates.py (274) | candidate_extractor.py (~250) + test (~200) |
| A3: analysis.py | orchestrator (83) + aggregator (129) | analysis.py (~160) + test (~150) |
| A4: db_reports.py | generate_db_reports.py (391) | db_reports.py (~390) |
| A5: ai_reports.py | format_reports.py (303) | ai_reports.py (~300) + test (~200) |

#### Phase A Gate: Code Review + Test Verification

After all 5 sub-agents complete, run this gate before proceeding to Phase B:

```
PHASE A GATE (back pressure — blocks until all pass):

1. TEST GATE: Run `pytest tests/ -v`
   - PASS criteria: zero failures, zero errors
   - If FAIL: write failing test names + tracebacks to state file
   - Back pressure: next turn reads failures, fixes code, re-runs

2. CODE REVIEW GATE: A review station reads each deliverable and verifies:

   For each module (browser.py, candidate_extractor.py, analysis.py,
   db_reports.py, ai_reports.py):

   a. FILE EXISTS: src/{module}.py exists
   b. IMPORTS VALID: `python3 -c "import src.{module}"` succeeds
   c. FUNCTIONS PRESENT: All functions from the source script are present
      in the new module (grep for function names)
   d. NO EXTERNAL DEPS: No `import` statements for non-stdlib packages
      (except playwright where expected)
   e. TEST EXISTS: tests/unit/test_{module}.py exists
   f. TEST COVERAGE: Each public function has at least one test

   For each item: write PASS/FAIL + details to state file.
   If ANY item fails: the phase retries.

3. REGRESSION GATE: Run `pytest tests/ -v` again (catches anything the
   review station's fixes might have broken)
   - Must be zero failures

4. GIT CHECKPOINT: If all above pass:
   git add src/browser.py src/candidate_extractor.py src/analysis.py \
           src/db_reports.py src/ai_reports.py \
           tests/unit/test_browser.py tests/unit/test_candidate_extractor.py \
           tests/unit/test_analysis.py tests/unit/test_ai_reports.py
   git commit -m "Phase A gate PASS — 5 modules moved to src/ [all tests green]"

STATE FILE ENTRY after Phase A gate:
  ## Build Phase A Gate
  - Tests: X passed, Y failed
  - Code review:
    - browser.py: EXISTS ✓, IMPORTS ✓, FUNCTIONS ✓, NO_DEPS ✓, TEST ✓
    - candidate_extractor.py: EXISTS ✓, IMPORTS ✓, FUNCTIONS ✓, ...
    - analysis.py: EXISTS ✓, IMPORTS ✗ (missing aggregate_results)
    - ...
  - Git commit: [hash] (or SKIPPED if gate failed)
  - Cleared for Phase B: YES/NO
```

### Phase B: Wire up (2 parallel sub-agents)

| Task | Writes |
|------|--------|
| B1 | pipeline.py (~100) + run_pipeline.py (~100) + run_afk_pipeline.sh (~350) |
| B2 | enrich.py slimmed (~120) |

#### Phase B Gate: Integration Verification

```
PHASE B GATE (back pressure — blocks until all pass):

1. TEST GATE: `pytest tests/ -v` — zero failures

2. CODE REVIEW GATE:
   a. src/pipeline.py: has functions for phase_1(), phase_2(), phase_3(),
      phase_4() that each return JSON-serializable dicts
   b. scripts/run_pipeline.py: `python3 scripts/run_pipeline.py --help`
      exits 0 and shows usage
   c. scripts/run_afk_pipeline.sh: file exists, is executable (chmod +x),
      starts with #!/bin/bash
   d. scripts/enrich.py: imports from src.browser (not inline browser code)
   e. All src/ modules import correctly:
      python3 -c "from src.browser import BrowserConnectionManager"
      python3 -c "from src.candidate_extractor import extract_candidates"
      python3 -c "from src.analysis import split_batches, aggregate_results"
      python3 -c "from src.db_reports import generate_db_reports"
      python3 -c "from src.ai_reports import format_ai_reports"

3. INTEGRATION TEST: Run phase 1 with test fixture:
   python3 scripts/run_pipeline.py --phase 1 \
     --csv tests/fixtures/sample_followers.csv --db /tmp/phase_b_test.db
   - Must exit 0 and produce valid JSON output

4. REGRESSION GATE: `pytest tests/ -v` — zero failures

5. GIT CHECKPOINT:
   git add src/pipeline.py scripts/run_pipeline.py scripts/run_afk_pipeline.sh \
           scripts/enrich.py
   git commit -m "Phase B gate PASS — pipeline CLI + shell orchestrator wired up [all tests green]"

STATE FILE ENTRY after Phase B gate:
  ## Build Phase B Gate
  - Tests: X passed, Y failed
  - Pipeline CLI: --help ✓, --phase 1 ✓
  - Shell script: exists ✓, executable ✓
  - Imports: all 5 modules ✓
  - Git commit: [hash]
  - Cleared for Phase C: YES/NO
```

### Phase C: Cleanup (sequential)

1. Rename test file, update imports
2. Delete 7 old scripts
3. Run `pytest tests/ -v` — must be all green

#### Phase C Gate: Final Verification

```
PHASE C GATE (back pressure — blocks until all pass):

1. DELETION VERIFICATION: The 7 old scripts no longer exist:
   - scripts/extract_raw_candidates.py — GONE
   - scripts/ai_analysis_orchestrator.py — GONE
   - scripts/aggregate_and_rank.py — GONE
   - scripts/format_reports.py — GONE
   - scripts/generate_db_reports.py — GONE
   - scripts/merge_top_followers.py — GONE
   - scripts/analyze_fundraising_candidates.py — GONE

2. NO DANGLING IMPORTS: grep all src/ and scripts/ files for imports
   of the deleted scripts. Must find zero matches.
   grep -r "extract_raw_candidates\|ai_analysis_orchestrator\|aggregate_and_rank\|format_reports\|generate_db_reports\|merge_top_followers\|analyze_fundraising" src/ scripts/ tests/

3. TEST GATE: `pytest tests/ -v` — zero failures, zero errors

4. FULL CODE REVIEW: A review station reads the ENTIRE build plan and
   verifies every deliverable exists and functions:

   Checklist:
   [ ] src/browser.py — exists, imports clean
   [ ] src/candidate_extractor.py — exists, imports clean
   [ ] src/analysis.py — exists, imports clean
   [ ] src/db_reports.py — exists, imports clean
   [ ] src/ai_reports.py — exists, imports clean
   [ ] src/pipeline.py — exists, has phase_1 through phase_4
   [ ] scripts/run_pipeline.py — exists, --help works
   [ ] scripts/run_afk_pipeline.sh — exists, executable
   [ ] scripts/enrich.py — exists, imports from src.browser
   [ ] 7 old scripts deleted
   [ ] All tests pass
   [ ] CLAUDE.md updated with pipeline docs
   [ ] No stdlib-only violations in src/

   If ANY item unchecked: write failure to state file, retry.

5. GIT CHECKPOINT:
   git add -A  # Everything: deletions, new files, CLAUDE.md
   git commit -m "Phase C gate PASS — 7 old scripts deleted, CLAUDE.md updated [all tests green]"

STATE FILE ENTRY after Phase C gate:
  ## Build Phase C Gate — FINAL
  - Deleted scripts: 7/7 confirmed gone
  - Dangling imports: 0 found
  - Tests: X passed, 0 failed
  - Full checklist: 13/13 items verified
  - Git commit: [hash]
  - BUILD COMPLETE: YES/NO
```

### Build Phase Back Pressure Flow

```
┌──────────────────────────────────────────────────┐
│ Phase A: 5 parallel agents write modules + tests │
│   ↓                                              │
│ Phase A Gate:                                    │
│   1. pytest → all pass?                          │──── NO → write failures
│   2. code review → all deliverables correct?     │       to state file
│   3. regression pytest → still all pass?         │       ↓
│   4. git commit checkpoint                       │   RETRY Phase A
│   ↓                                              │   (reads state file,
│ ALL PASS → proceed                               │    fixes specific issues)
│   ↓                                              │
│ Phase B: 2 parallel agents wire up               │
│   ↓                                              │
│ Phase B Gate:                                    │
│   1. pytest                                      │──── NO → retry Phase B
│   2. code review (imports, CLI, script)          │
│   3. integration test (phase 1 with fixture)     │
│   4. regression pytest                           │
│   5. git commit checkpoint                       │
│   ↓                                              │
│ ALL PASS → proceed                               │
│   ↓                                              │
│ Phase C: Cleanup + delete old scripts            │
│   ↓                                              │
│ Phase C Gate:                                    │
│   1. deletion verification                       │──── NO → retry Phase C
│   2. no dangling imports                         │
│   3. pytest                                      │
│   4. FULL code review (entire checklist)         │
│   5. git commit checkpoint                       │
│   ↓                                              │
│ ALL PASS                                         │
│   ↓                                              │
│ BUILD COMPLETE                                   │
└──────────────────────────────────────────────────┘
```

At every gate boundary, failures are written to `pipeline_state.md` with
specific details (which test failed, which file is missing, which import
broke). The next turn of the Ralph loop reads these and knows exactly
what to fix. No guessing, no starting over — targeted self-healing.

---

## Constraints

- `data/followers.db` is irreplaceable — back up before Phase 2
- `src/` is stdlib-only (except pytest/playwright)
- `classifier.py` rules: priority-ordered, NEVER reorder
- All 1,354 lines of existing report tests preserved

## Verification

After build:
1. `pytest tests/ -v` — all green (run at EVERY gate, not just at the end)
2. `python3 scripts/run_pipeline.py --phase 1 --csv tests/fixtures/sample_followers.csv --db /tmp/test.db`
3. `./scripts/run_afk_pipeline.sh` — full end-to-end (with Chrome running)
4. Check `data/pipeline_state.md` — complete build + run history with gate results
5. Check `output/` — all 6 report files present and non-empty
6. Review gate pass/fail log in terminal output
7. Verify all build phase gates show PASS in state file
8. `git log --oneline` — verify checkpoint commits at every gate boundary
9. Verify intermediary files handled: either cleaned up (if CLEANUP_INTERMEDIARY=1)
   or listed for manual review
