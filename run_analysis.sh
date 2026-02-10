#!/bin/bash
# Sequential AI Analysis Pipeline for Hawaii FIDO
# Usage: ./run_analysis.sh <task_list_id>

TASK_LIST_ID="${1:?Usage: ./run_analysis.sh <task_list_id>}"

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
- Execute the work described in the task. Write code, run commands, create files — whatever the task requires.
- When finished, run TaskUpdate to set the task status to "completed".

## Step 4: Log progress
Append a brief entry to progress.txt using Python open('progress.txt', 'a') or bash >> operator.
Do NOT use the Write tool (it overwrites). If the file does not exist, create it.

Include: timestamp, task ID and subject, key result, files created/modified.
Format each entry as a timestamped block separated by ---.

## Step 5: Save learnings
If you discovered anything genuinely new (data quality issues, scoring patterns, edge cases),
append a brief note to learnings.md using Python open('learnings.md', 'a') or bash >>.
Do NOT use the Write tool. Do not repeat what is already in the file.

## Step 6: Stop
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
    echo "=== Iteration $ITERATION / $MAX_ITERATIONS ==="

    output=$(timeout 600 env CLAUDE_CODE_TASK_LIST_ID="$TASK_LIST_ID" claude -p "$PROMPT" 2>&1)
    claude_exit=$?
    echo "$output"

    if echo "$output" | grep -q "ALL_TASKS_COMPLETE"; then
        echo "All tasks complete!"
        exit 0
    fi

    if echo "$output" | grep -q "FATAL_ERROR"; then
        echo "Fatal error detected. Stopping pipeline."
        exit 2
    fi

    # Detect consecutive failures via exit code (not keyword grep)
    if [ -z "$output" ] || [ $claude_exit -ne 0 ]; then
        CONSECUTIVE_ERRORS=$((CONSECUTIVE_ERRORS + 1))
        echo "Warning: claude exited with code $claude_exit (consecutive: $CONSECUTIVE_ERRORS/$MAX_CONSECUTIVE_ERRORS)"
        if [ $CONSECUTIVE_ERRORS -ge $MAX_CONSECUTIVE_ERRORS ]; then
            echo "Too many consecutive errors. Stopping pipeline."
            exit 3
        fi
    else
        CONSECUTIVE_ERRORS=0
    fi

    sleep 2
done

echo "Reached max iterations ($MAX_ITERATIONS). Check task list for status."
exit 1
