#!/bin/bash
# Finalize the analysis once subagents are complete

set -e

BASEDIR="/Users/developer-sandbox/Desktop/Development/hawaii-fido-instagram-follower-analysis"
SCRIPTS="$BASEDIR/scripts"

echo "=== Hawaii FIDO AI Fundraising Analysis - Finalization ==="
echo ""

# Check if all analyzed profiles are ready
echo "Step 1: Aggregating subagent analyses..."
/usr/bin/python3 "$SCRIPTS/aggregate_and_rank.py"

echo ""
echo "Step 2: Formatting reports..."
/usr/bin/python3 "$SCRIPTS/format_reports.py"

echo ""
echo "=== Analysis Complete ==="
echo ""
echo "Output files created:"
ls -lh "$BASEDIR/output/"
echo ""
echo "Candidate data:"
ls -lh "$BASEDIR/data/top_*.json" 2>/dev/null || echo "Rankings pending..."
