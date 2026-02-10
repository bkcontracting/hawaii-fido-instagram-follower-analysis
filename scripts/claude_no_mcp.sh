#!/bin/bash
# Minimal Claude session for task list execution
# Fresh context (no --resume), task list connected via env var
# Disables: MCP servers, plugins, unnecessary built-in tools
# Keeps: built-in / commands (/clear, /context, etc.)

#  Read AI_IMPLEMENTATION_PLAN.md for context then run TaskList to  see all
#  pending tasks. Work through each task in order — mark each as in_progress when you start it
#  and completed when done. For each task, read its full description with TaskGet before
#  starting.

# Run TaskList to see remaining tasks. Continue executing pending tasks.


set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

TASK_LIST_ID="${1:?Usage: $0 <task-list-id>}"

exec env \
  CLAUDE_CODE_TASK_LIST_ID="$TASK_LIST_ID" \
  claude \
    --disallowed-tools "WebFetch,WebSearch,NotebookEdit,Skill,EnterPlanMode,ExitPlanMode" \
    --strict-mcp-config \
    --settings "$PROJECT_ROOT/.claude/settings.automation.json"
