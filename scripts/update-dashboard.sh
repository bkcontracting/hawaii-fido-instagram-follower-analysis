#!/bin/bash
# Hawaii Fi-Do Dashboard - Quick Update Script
#
# This script provides a simple one-command workflow to:
# 1. Regenerate CSV reports from the database
# 2. Rebuild the dashboard
# 3. Deploy to Cloudflare Pages
#
# Usage:
#   ./scripts/update-dashboard.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="/home/user/hawaii-fido-instagram-follower-analysis"
CONFIG_FILE="$HOME/.cloudflare-dashboard-config"

echo ""
echo -e "${BLUE}🔄 Updating Hawaii Fi-Do Dashboard...${NC}"
echo ""

# Navigate to project root
cd "$PROJECT_ROOT"

# Load config if exists
CLOUDFLARE_PROJECT_NAME="hawaii-fido-dashboard"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Step 1: Regenerate CSVs
echo -e "${BLUE}📊 Regenerating CSV reports from database...${NC}"
if [ -f "scripts/generate_db_reports.py" ]; then
    python3 scripts/generate_db_reports.py
    echo -e "${GREEN}✓ CSV reports generated${NC}"
else
    echo -e "${YELLOW}⚠ Warning: generate_db_reports.py not found, using existing CSVs${NC}"
fi
echo ""

# Step 2: Build dashboard
echo -e "${BLUE}🏗️  Building dashboard...${NC}"
python3 dashboard/build/build-dashboard.py | tail -10
echo ""

# Step 3: Deploy
echo -e "${BLUE}🚀 Deploying to Cloudflare...${NC}"
cd dashboard/dist
wrangler pages deploy . --project-name="$CLOUDFLARE_PROJECT_NAME" --branch=production
cd "$PROJECT_ROOT"

echo ""
echo -e "${GREEN}✅ Dashboard updated successfully!${NC}"
echo -e "${BLUE}🌐 View at: https://$CLOUDFLARE_PROJECT_NAME.pages.dev${NC}"
echo ""
