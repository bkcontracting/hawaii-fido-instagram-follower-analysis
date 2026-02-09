#!/bin/bash
# Sequential AI Analysis Pipeline for Hawaii FIDO
# Usage: ./run_analysis.sh <task_list_id>

TASK_LIST_ID="${1:?Usage: ./run_analysis.sh <task_list_id>}"
MAX_ITERATIONS=20
ITERATION=0

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))
    echo "=== Iteration $ITERATION / $MAX_ITERATIONS ==="

    output=$(CLAUDE_CODE_TASK_LIST_ID="$TASK_LIST_ID" claude -p "resume next task" 2>&1)
    echo "$output"

    if echo "$output" | grep -q "ALL_TASKS_COMPLETE"; then
        echo "All tasks complete!"
        exit 0
    fi

    sleep 2
done

echo "Reached max iterations ($MAX_ITERATIONS). Check task list for status."
exit 1
