#!/bin/bash
# Sequential AI Analysis Pipeline for Hawaii FIDO
# Usage: ./run_analysis.sh <task_list_id>

TASK_LIST_ID="${1:?Usage: ./run_analysis.sh <task_list_id>}"
MAX_ITERATIONS=20
ITERATION=0
CONSECUTIVE_ERRORS=0
MAX_CONSECUTIVE_ERRORS=3

PROMPT=$(cat <<'PROMPT_EOF'
You are running inside a headless automation loop. Follow these instructions exactly.

## Step 1: Understand the project
Read CLAUDE.md (if it exists) for project context, conventions, and file layout.

## Step 2: Find your next task
Run TaskList to see all tasks. Find the first task with status "pending" that is NOT blocked (blockedBy is empty or all blockers are completed).

If there are NO pending tasks remaining, output the exact sentinel string ALL_TASKS_COMPLETE and stop immediately. Do not create any files or take any other action.

## Step 3: Execute the task
- Run TaskUpdate to set the task status to "in_progress".
- Run TaskGet to read the full task description.
- Execute the work described in the task. Write code, run commands, create files — whatever the task requires.
- When finished, run TaskUpdate to set the task status to "completed".

## Step 4: Stop
After completing exactly ONE task, stop. Do not continue to the next task. The outer loop will invoke you again for the next one.

## Rules
- Do NOT create or modify anything under .claude/skills/. Those are managed separately.
- Do NOT create CLAUDE.md files unless a task explicitly requires it.
- Do NOT invent tasks. Only work on tasks that already exist in the TaskList.
- If a task is unclear, mark it completed with a note rather than guessing.
- If you encounter an unrecoverable error (missing data files, permission denied, etc.), output the exact string FATAL_ERROR followed by a short description and stop.
PROMPT_EOF
)

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))
    echo "=== Iteration $ITERATION / $MAX_ITERATIONS ==="

    output=$(CLAUDE_CODE_TASK_LIST_ID="$TASK_LIST_ID" claude -p "$PROMPT" 2>&1)
    echo "$output"

    if echo "$output" | grep -q "ALL_TASKS_COMPLETE"; then
        echo "All tasks complete!"
        exit 0
    fi

    if echo "$output" | grep -q "FATAL_ERROR"; then
        echo "Fatal error detected. Stopping pipeline."
        exit 2
    fi

    # Detect consecutive failures (empty output or claude exit errors)
    if [ -z "$output" ] || echo "$output" | grep -qi "error\|exception\|panic"; then
        CONSECUTIVE_ERRORS=$((CONSECUTIVE_ERRORS + 1))
        echo "Warning: possible error (consecutive: $CONSECUTIVE_ERRORS/$MAX_CONSECUTIVE_ERRORS)"
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
