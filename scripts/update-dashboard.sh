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
NC='\033[0m'

echo ""
echo -e "${BLUE}🔄 Updating Hawaii Fi-Do Dashboard...${NC}"
echo ""

# Run the full build and deploy
./scripts/build-and-deploy-dashboard.sh

echo ""
echo -e "${GREEN}✅ Dashboard updated successfully!${NC}"
echo -e "${BLUE}🌐 View at: https://hawaii-fido-dashboard.pages.dev${NC}"
echo ""
