#!/bin/bash
# Hawaii Fi-Do Dashboard - Build and Deploy Script
#
# This script automates the complete build and deployment workflow:
# 1. Regenerates CSV reports from database (optional)
# 2. Converts CSVs to JavaScript
# 3. Generates self-contained HTML dashboard
# 4. Deploys to Cloudflare Pages
#
# Usage:
#   ./scripts/build-and-deploy-dashboard.sh [--skip-csv-generation]
#
# Environment Variables:
#   SKIP_CSV_GENERATION - Set to 1 to skip CSV regeneration
#   CLOUDFLARE_PROJECT_NAME - Cloudflare Pages project name (default: hawaii-fido-dashboard)

set -e  # Exit on error

# Configuration
PROJECT_ROOT="/home/user/hawaii-fido-instagram-follower-analysis"
CLOUDFLARE_PROJECT_NAME="${CLOUDFLARE_PROJECT_NAME:-hawaii-fido-dashboard}"
SKIP_CSV="${SKIP_CSV_GENERATION:-0}"

# Check for --skip-csv-generation flag
if [[ "$*" == *"--skip-csv-generation"* ]]; then
    SKIP_CSV=1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}🏗️  Hawaii Fi-Do Dashboard - Build & Deploy${NC}"
echo "=========================================="
echo ""

# Navigate to project root
cd "$PROJECT_ROOT"

# Step 1: Generate CSVs from database (optional)
if [ "$SKIP_CSV" = "0" ]; then
    echo -e "${BLUE}📊 Step 1/5: Generating latest CSV reports...${NC}"
    if [ -f "scripts/generate_db_reports.py" ]; then
        python3 scripts/generate_db_reports.py
        echo -e "${GREEN}✓ CSV reports generated${NC}"
    else
        echo -e "${YELLOW}⚠ Warning: generate_db_reports.py not found, skipping CSV generation${NC}"
    fi
else
    echo -e "${YELLOW}⏭  Step 1/5: Skipping CSV generation (using existing files)${NC}"
fi

echo ""

# Step 2: Convert CSVs to JavaScript
echo -e "${BLUE}🔄 Step 2/5: Converting CSVs to JavaScript...${NC}"
python3 dashboard/build/csv-to-js.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ CSV conversion successful${NC}"
else
    echo -e "${RED}❌ ERROR: CSV conversion failed${NC}"
    exit 1
fi

echo ""

# Step 3: Generate HTML
echo -e "${BLUE}🎨 Step 3/5: Generating self-contained HTML...${NC}"
python3 dashboard/build/generate-html.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ HTML generation successful${NC}"
else
    echo -e "${RED}❌ ERROR: HTML generation failed${NC}"
    exit 1
fi

echo ""

# Step 4: Validate output
echo -e "${BLUE}✅ Step 4/5: Validating generated HTML...${NC}"
if [ -f "dashboard/dist/index.html" ]; then
    SIZE=$(du -h dashboard/dist/index.html | cut -f1)
    echo -e "${GREEN}✓ Generated: dashboard/dist/index.html ($SIZE)${NC}"
else
    echo -e "${RED}❌ ERROR: Failed to generate dashboard/dist/index.html${NC}"
    exit 1
fi

echo ""

# Step 5: Deploy to Cloudflare Pages
echo -e "${BLUE}🚀 Step 5/5: Deploying to Cloudflare Pages...${NC}"

# Check if wrangler is available
if command -v wrangler &> /dev/null || command -v npx &> /dev/null; then
    echo "Deploying to Cloudflare Pages project: $CLOUDFLARE_PROJECT_NAME"
    echo ""

    cd dashboard/dist

    # Try wrangler first, fallback to npx
    if command -v wrangler &> /dev/null; then
        wrangler pages deploy . --project-name="$CLOUDFLARE_PROJECT_NAME"
    else
        npx wrangler pages deploy . --project-name="$CLOUDFLARE_PROJECT_NAME"
    fi

    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ Deployment successful!${NC}"
        echo -e "${BLUE}🌐 Dashboard URL: https://$CLOUDFLARE_PROJECT_NAME.pages.dev${NC}"
    else
        echo ""
        echo -e "${RED}❌ Deployment failed${NC}"
        echo ""
        echo "Troubleshooting:"
        echo "1. Ensure you're logged in to Cloudflare: wrangler login"
        echo "2. Verify project name is correct"
        echo "3. Check Cloudflare Pages dashboard for errors"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ Warning: Wrangler CLI not found${NC}"
    echo ""
    echo "To deploy, you have two options:"
    echo ""
    echo "Option 1: Install Wrangler CLI"
    echo "  npm install -g wrangler"
    echo "  wrangler login"
    echo "  wrangler pages deploy dashboard/dist --project-name=$CLOUDFLARE_PROJECT_NAME"
    echo ""
    echo "Option 2: Manual deployment via Cloudflare dashboard"
    echo "  1. Go to https://dash.cloudflare.com"
    echo "  2. Navigate to Pages"
    echo "  3. Create/select project: $CLOUDFLARE_PROJECT_NAME"
    echo "  4. Upload: dashboard/dist/index.html"
    echo ""
    echo "Dashboard built successfully and is ready for deployment!"
    echo "File location: $PROJECT_ROOT/dashboard/dist/index.html"
fi

echo ""
echo -e "${GREEN}✅ Build process complete!${NC}"
echo ""
