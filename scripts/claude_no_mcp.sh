#!/bin/bash
# Launch a clean Claude session to execute AI_IMPLEMENTATION_PLAN.md
# Disables: plugins, MCP servers, skills — keeps only core tools
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

exec claude \
  --strict-mcp-config \
  --disable-slash-commands \
  --settings "$PROJECT_ROOT/.claude/settings.automation.json"
