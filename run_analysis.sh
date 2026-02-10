#!/bin/bash
# Sequential AI Analysis Pipeline for Hawaii FIDO
# Usage: ./run_analysis.sh <task_list_id>

TASK_LIST_ID="${1:?Usage: ./run_analysis.sh <task_list_id>}"

# --- Configuration ---
TIMEOUT_SECS=1200  # 20 minutes per iteration
LOGDIR="/tmp/hawaii-fido-analysis"
mkdir -p "$LOGDIR"

# Calculate max iterations from DB profile count
PROFILE_COUNT=$(sqlite3 data/followers.db "SELECT COUNT(*) FROM followers WHERE status = 'completed';" 2>/dev/null || echo 444)
BATCH_COUNT=$(( (PROFILE_COUNT + 74) / 75 ))
TOTAL_TASKS=$(( BATCH_COUNT + 5 ))
MAX_ITERATIONS=$(( TOTAL_TASKS + 5 ))

ITERATION=0
CONSECUTIVE_ERRORS=0
MAX_CONSECUTIVE_ERRORS=3

echo "=== Hawaii FIDO AI Analysis Pipeline ==="
echo "Completed profiles: $PROFILE_COUNT"
echo "Expected batches: $BATCH_COUNT"
echo "Total tasks: $TOTAL_TASKS"
echo "Max iterations: $MAX_ITERATIONS"
echo "Timeout per iteration: ${TIMEOUT_SECS}s"
echo ""

PROMPT=$(cat <<'PROMPT_EOF'
You are running inside a headless automation loop. Follow these instructions exactly.

## Step 1: Understand the project
Read CLAUDE.md for project context, conventions, and file layout.
If learnings.md exists, read it for accumulated knowledge from previous iterations.

## Step 2: Find your next task
Run TaskList to see all tasks. Find the first task with status "pending" that is NOT blocked (blockedBy is empty or all blockers are completed).

If there are NO pending tasks remaining, output the exact sentinel string ALL_TASKS_COMPLETE and stop immediately. Do not create any files or take any other action.

## Step 3: Execute the task
- Run TaskUpdate to set the task status to "in_progress".
- Run TaskGet to read the full task description.
- Before executing, append a brief "Starting task [ID]: [subject]" entry with timestamp to progress.txt using Python open('progress.txt', 'a') or bash >> operator.
- Execute the work described in the task. Write code, run commands, create files — whatever the task requires.
- When finished, run TaskUpdate to set the task status to "completed".
- Append a completion entry to progress.txt with timestamp, task ID, subject, key result, and files created/modified.

## Step 4: Save learnings
If you discovered anything genuinely new (data quality issues, scoring patterns, edge cases),
append a brief note to learnings.md using Python open('learnings.md', 'a') or bash >>.
Do NOT use the Write tool. Do not repeat what is already in the file.

## Step 5: Stop
After completing exactly ONE task and logging, stop. Do not continue to the next task.
The outer loop will invoke you again.

## Rules
- Do NOT create or modify anything under .claude/
- Do NOT create CLAUDE.md files
- Do NOT invent tasks. Only work on tasks that already exist in the TaskList.
- If a task is unclear, mark it completed with a note rather than guessing.
- If you encounter an unrecoverable error, output the exact string FATAL_ERROR followed by a short description and stop.
PROMPT_EOF
)

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))
    iter_start=$(date +%s)
    echo ""
    echo "=== Iteration $ITERATION / $MAX_ITERATIONS === $(date '+%Y-%m-%d %H:%M:%S') ==="

    # Log iteration start to progress.txt
    echo "--- $(date '+%Y-%m-%d %H:%M:%S') --- Iteration $ITERATION STARTING ---" >> progress.txt

    # Set up log file and stream output in real-time
    logfile="$LOGDIR/iteration_${ITERATION}.log"
    > "$logfile"
    tail -f "$logfile" &
    tail_pid=$!

    # Launch claude in background, output to log file
    env CLAUDE_CODE_TASK_LIST_ID="$TASK_LIST_ID" claude -p "$PROMPT" >> "$logfile" 2>&1 &
    claude_pid=$!

    # Watchdog timer to kill claude if it exceeds timeout
    ( sleep "$TIMEOUT_SECS" && kill "$claude_pid" 2>/dev/null ) &
    watchdog_pid=$!

    # Wait for claude to finish (or be killed by watchdog)
    wait "$claude_pid" 2>/dev/null
    claude_exit=$?

    # Clean up watchdog and tail
    kill "$watchdog_pid" 2>/dev/null
    kill "$tail_pid" 2>/dev/null
    wait "$watchdog_pid" 2>/dev/null
    wait "$tail_pid" 2>/dev/null

    # Read output from log file
    output=$(cat "$logfile")

    # Timing info
    iter_end=$(date +%s)
    elapsed=$(( iter_end - iter_start ))
    echo ""
    echo "--- Iteration $ITERATION finished in ${elapsed}s (exit code: $claude_exit) ---"

    # Log iteration result to progress.txt
    echo "--- $(date '+%Y-%m-%d %H:%M:%S') --- Iteration $ITERATION FINISHED (exit=$claude_exit, elapsed=${elapsed}s) ---" >> progress.txt

    if echo "$output" | grep -q "ALL_TASKS_COMPLETE"; then
        echo "All tasks complete!"
        echo "--- $(date '+%Y-%m-%d %H:%M:%S') --- ALL TASKS COMPLETE ---" >> progress.txt
        exit 0
    fi

    if echo "$output" | grep -q "FATAL_ERROR"; then
        echo "Fatal error detected. Stopping pipeline."
        echo "--- $(date '+%Y-%m-%d %H:%M:%S') --- FATAL ERROR - pipeline stopped ---" >> progress.txt
        exit 2
    fi

    # Detect consecutive failures via exit code (not keyword grep)
    if [ -z "$output" ] || [ $claude_exit -ne 0 ]; then
        CONSECUTIVE_ERRORS=$((CONSECUTIVE_ERRORS + 1))
        echo "Warning: claude exited with code $claude_exit (consecutive: $CONSECUTIVE_ERRORS/$MAX_CONSECUTIVE_ERRORS)"
        if [ $CONSECUTIVE_ERRORS -ge $MAX_CONSECUTIVE_ERRORS ]; then
            echo "Too many consecutive errors. Stopping pipeline."
            echo "--- $(date '+%Y-%m-%d %H:%M:%S') --- TOO MANY ERRORS - pipeline stopped ---" >> progress.txt
            exit 3
        fi
    else
        CONSECUTIVE_ERRORS=0
    fi

    sleep 2
done

echo "Reached max iterations ($MAX_ITERATIONS). Check task list for status."
echo "--- $(date '+%Y-%m-%d %H:%M:%S') --- MAX ITERATIONS REACHED ---" >> progress.txt
exit 1
