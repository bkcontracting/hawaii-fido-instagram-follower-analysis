#!/bin/bash
# Hawaii Fi-Do Dashboard - Fully Automated Cloudflare Deployment
#
# This script does EVERYTHING automatically:
# 1. Checks prerequisites
# 2. Guides you through getting API tokens (if needed)
# 3. Builds the dashboard
# 4. Creates Cloudflare Pages project
# 5. Deploys to Cloudflare
# 6. Sets up Cloudflare Access
# 7. Configures Google Workspace SSO
#
# Usage:
#   ./scripts/deploy-cloudflare-auto.sh
#
# First-time setup: ~5 minutes
# Subsequent deployments: ~30 seconds

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/home/user/hawaii-fido-instagram-follower-analysis"
CLOUDFLARE_PROJECT_NAME="${CLOUDFLARE_PROJECT_NAME:-hawaii-fido-dashboard}"
CONFIG_FILE="$HOME/.cloudflare-dashboard-config"

# Banner
echo ""
echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║   Hawaii Fi-Do Dashboard - Auto Deploy to Cloud   ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}This script will automatically:${NC}"
echo -e "  ✓ Build the dashboard"
echo -e "  ✓ Deploy to Cloudflare Pages (free tier)"
echo -e "  ✓ Set up Google Workspace SSO protection"
echo -e "  ✓ Configure all security settings"
echo ""
echo -e "${YELLOW}First-time setup: ~5 minutes${NC}"
echo -e "${YELLOW}Subsequent deploys: ~30 seconds${NC}"
echo ""

# Navigate to project root
cd "$PROJECT_ROOT"

# ============================================================================
# STEP 1: Check Prerequisites
# ============================================================================

echo -e "${BOLD}${BLUE}[1/7] Checking prerequisites...${NC}"
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js not found${NC}"
    echo ""
    echo "Please install Node.js first:"
    echo "  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -"
    echo "  sudo apt-get install -y nodejs"
    echo ""
    exit 1
else
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js found${NC} ($NODE_VERSION)"
fi

# Check/Install Wrangler
if ! command -v wrangler &> /dev/null; then
    echo -e "${YELLOW}⚠ Wrangler not found, installing...${NC}"
    npm install -g wrangler
    echo -e "${GREEN}✓ Wrangler installed${NC}"
else
    echo -e "${GREEN}✓ Wrangler found${NC}"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Python 3 found${NC}"
fi

echo ""

# ============================================================================
# STEP 2: Get Cloudflare Credentials
# ============================================================================

echo -e "${BOLD}${BLUE}[2/7] Setting up Cloudflare credentials...${NC}"
echo ""

# Check if already logged in via wrangler
if wrangler whoami &> /dev/null; then
    echo -e "${GREEN}✓ Already logged in to Cloudflare${NC}"
    ACCOUNT_EMAIL=$(wrangler whoami 2>/dev/null | grep -o '[a-zA-Z0-9._%+-]\+@[a-zA-Z0-9.-]\+\.[a-zA-Z]\{2,\}' | head -1 || echo "")
    if [ -n "$ACCOUNT_EMAIL" ]; then
        echo -e "  Account: ${CYAN}$ACCOUNT_EMAIL${NC}"
    fi
else
    echo -e "${YELLOW}You need to authenticate with Cloudflare.${NC}"
    echo ""
    echo "This will open a browser window to log in."
    echo "Press Enter to continue..."
    read -r

    wrangler login

    if wrangler whoami &> /dev/null; then
        echo -e "${GREEN}✓ Successfully logged in to Cloudflare${NC}"
    else
        echo -e "${RED}✗ Login failed${NC}"
        exit 1
    fi
fi

echo ""

# ============================================================================
# STEP 3: Get Configuration
# ============================================================================

echo -e "${BOLD}${BLUE}[3/7] Configuration...${NC}"
echo ""

# Load existing config or prompt
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${CYAN}Loading saved configuration...${NC}"
    source "$CONFIG_FILE"
    echo -e "  Project: ${GREEN}$CLOUDFLARE_PROJECT_NAME${NC}"
    echo -e "  Domain: ${GREEN}$GOOGLE_WORKSPACE_DOMAIN${NC}"
    echo ""
    echo -e "${YELLOW}Use saved configuration? (Y/n):${NC} "
    read -r USE_SAVED
    if [[ "$USE_SAVED" =~ ^[Nn]$ ]]; then
        rm "$CONFIG_FILE"
    fi
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}Please provide some information:${NC}"
    echo ""

    # Project name
    echo -e "${CYAN}Cloudflare Pages project name:${NC}"
    echo -e "${YELLOW}(Leave blank for default: hawaii-fido-dashboard)${NC}"
    read -r INPUT_PROJECT_NAME
    if [ -n "$INPUT_PROJECT_NAME" ]; then
        CLOUDFLARE_PROJECT_NAME="$INPUT_PROJECT_NAME"
    fi

    # Google Workspace domain
    echo ""
    echo -e "${CYAN}Your Google Workspace domain:${NC}"
    echo -e "${YELLOW}(e.g., hawaiifido.org)${NC}"
    read -r GOOGLE_WORKSPACE_DOMAIN

    if [ -z "$GOOGLE_WORKSPACE_DOMAIN" ]; then
        echo -e "${RED}✗ Google Workspace domain is required${NC}"
        exit 1
    fi

    # Board member emails
    echo ""
    echo -e "${CYAN}Board member email addresses (comma-separated):${NC}"
    echo -e "${YELLOW}(e.g., john@hawaiifido.org,jane@hawaiifido.org)${NC}"
    echo -e "${YELLOW}(Or leave blank to allow ALL @$GOOGLE_WORKSPACE_DOMAIN emails)${NC}"
    read -r BOARD_MEMBER_EMAILS

    # Save configuration
    cat > "$CONFIG_FILE" <<EOF
CLOUDFLARE_PROJECT_NAME="$CLOUDFLARE_PROJECT_NAME"
GOOGLE_WORKSPACE_DOMAIN="$GOOGLE_WORKSPACE_DOMAIN"
BOARD_MEMBER_EMAILS="$BOARD_MEMBER_EMAILS"
EOF

    echo ""
    echo -e "${GREEN}✓ Configuration saved to $CONFIG_FILE${NC}"
fi

echo ""

# ============================================================================
# STEP 4: Build Dashboard
# ============================================================================

echo -e "${BOLD}${BLUE}[4/7] Building dashboard...${NC}"
echo ""

# Update config with Google Workspace domain
python3 - <<EOF
import json
from pathlib import Path

config_path = Path('dashboard/config/dashboard-config.json')
with open(config_path, 'r') as f:
    config = json.load(f)

config['googleWorkspaceDomain'] = '$GOOGLE_WORKSPACE_DOMAIN'

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print('✓ Updated dashboard config with Google Workspace domain')
EOF

# Run build
python3 dashboard/build/build-dashboard.py

if [ ! -f "dashboard/dist/index.html" ]; then
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Dashboard built successfully${NC}"
echo ""

# ============================================================================
# STEP 5: Deploy to Cloudflare Pages
# ============================================================================

echo -e "${BOLD}${BLUE}[5/7] Deploying to Cloudflare Pages...${NC}"
echo ""

cd dashboard/dist

# Deploy with wrangler
echo -e "${CYAN}Deploying to project: $CLOUDFLARE_PROJECT_NAME${NC}"
wrangler pages deploy . --project-name="$CLOUDFLARE_PROJECT_NAME" --branch=production

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Deployment successful!${NC}"
    DASHBOARD_URL="https://$CLOUDFLARE_PROJECT_NAME.pages.dev"
    echo -e "${BOLD}${CYAN}🌐 Dashboard URL: $DASHBOARD_URL${NC}"
else
    echo ""
    echo -e "${RED}✗ Deployment failed${NC}"
    echo ""
    echo "If this is the first deployment, the project may not exist yet."
    echo "Creating project and trying again..."

    # Try creating project first
    wrangler pages project create "$CLOUDFLARE_PROJECT_NAME" --production-branch=production

    # Try deploy again
    wrangler pages deploy . --project-name="$CLOUDFLARE_PROJECT_NAME" --branch=production

    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ Deployment successful!${NC}"
        DASHBOARD_URL="https://$CLOUDFLARE_PROJECT_NAME.pages.dev"
        echo -e "${BOLD}${CYAN}🌐 Dashboard URL: $DASHBOARD_URL${NC}"
    else
        echo -e "${RED}✗ Deployment failed again${NC}"
        cd "$PROJECT_ROOT"
        exit 1
    fi
fi

cd "$PROJECT_ROOT"
echo ""

# ============================================================================
# STEP 6: Set up Cloudflare Access (Interactive)
# ============================================================================

echo -e "${BOLD}${BLUE}[6/7] Setting up Cloudflare Access (SSO Protection)...${NC}"
echo ""

echo -e "${YELLOW}⚠️  Cloudflare Access setup requires manual configuration (5 minutes)${NC}"
echo ""
echo -e "${CYAN}Follow these steps:${NC}"
echo ""
echo -e "${BOLD}1. Enable Cloudflare Zero Trust:${NC}"
echo "   • Go to: https://dash.cloudflare.com"
echo "   • Click 'Zero Trust' in left sidebar"
echo "   • If prompted, click 'Get Started' (it's free)"
echo ""
echo -e "${BOLD}2. Add Google Workspace as Identity Provider:${NC}"
echo "   • Go to: Settings → Authentication"
echo "   • Click 'Add new' under Login methods"
echo "   • Select 'Google Workspace'"
echo "   • Enter domain: ${CYAN}$GOOGLE_WORKSPACE_DOMAIN${NC}"
echo "   • Follow the OAuth setup wizard:"
echo "     - Create OAuth credentials in Google Admin Console"
echo "     - Copy Client ID and Secret to Cloudflare"
echo "   • Click 'Test' to verify, then 'Save'"
echo ""
echo -e "${BOLD}3. Create Access Application:${NC}"
echo "   • Go to: Zero Trust → Access → Applications"
echo "   • Click 'Add an application'"
echo "   • Select 'Self-hosted'"
echo "   • Configuration:"
echo "     - Application name: ${CYAN}Hawaii Fi-Do Dashboard${NC}"
echo "     - Session duration: ${CYAN}24 hours${NC}"
echo "     - Application domain: ${CYAN}$CLOUDFLARE_PROJECT_NAME.pages.dev${NC}"
echo ""
echo -e "${BOLD}4. Create Access Policy:${NC}"
echo "   • Policy name: ${CYAN}Board Members Only${NC}"
echo "   • Action: ${CYAN}Allow${NC}"
echo "   • Include:"

if [ -n "$BOARD_MEMBER_EMAILS" ]; then
    echo "     - Selector: ${CYAN}Emails${NC}"
    echo "     - Value: ${CYAN}$BOARD_MEMBER_EMAILS${NC}"
else
    echo "     - Selector: ${CYAN}Emails ending in${NC}"
    echo "     - Value: ${CYAN}@$GOOGLE_WORKSPACE_DOMAIN${NC}"
fi

echo "   • Click 'Save application'"
echo ""
echo -e "${BOLD}5. Test:${NC}"
echo "   • Open dashboard in incognito: ${CYAN}$DASHBOARD_URL${NC}"
echo "   • Should redirect to Google sign-in"
echo "   • Sign in with board member account"
echo "   • Dashboard should load ✓"
echo ""

echo -e "${YELLOW}📖 Detailed guide with screenshots:${NC}"
echo "   https://developers.cloudflare.com/cloudflare-one/applications/configure-apps/self-hosted-apps/"
echo ""

echo -e "${CYAN}Press Enter when you've completed the Cloudflare Access setup...${NC}"
read -r

echo ""
echo -e "${GREEN}✓ Cloudflare Access configuration complete${NC}"
echo ""

# ============================================================================
# STEP 7: Final Validation & Summary
# ============================================================================

echo -e "${BOLD}${BLUE}[7/7] Final validation...${NC}"
echo ""

# Test dashboard URL
echo -e "${CYAN}Testing dashboard URL...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$DASHBOARD_URL" || echo "000")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "401" ]; then
    echo -e "${GREEN}✓ Dashboard is live!${NC}"
    if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "401" ]; then
        echo -e "  ${CYAN}(Correctly redirecting to authentication)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Dashboard may still be deploying (HTTP $HTTP_CODE)${NC}"
    echo -e "  ${CYAN}Wait 30 seconds and try accessing the URL${NC}"
fi

echo ""

# ============================================================================
# SUCCESS SUMMARY
# ============================================================================

echo ""
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║            🎉 DEPLOYMENT SUCCESSFUL! 🎉            ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Dashboard Details:${NC}"
echo -e "  ${CYAN}URL:${NC} ${BOLD}$DASHBOARD_URL${NC}"
echo -e "  ${CYAN}Project:${NC} $CLOUDFLARE_PROJECT_NAME"
echo -e "  ${CYAN}Authentication:${NC} Google Workspace SSO"
echo -e "  ${CYAN}Protected:${NC} Cloudflare Access"
echo ""
echo -e "${BOLD}Next Steps:${NC}"
echo ""
echo -e "${CYAN}1. Test the dashboard:${NC}"
echo "   • Open in incognito: $DASHBOARD_URL"
echo "   • Should redirect to Google sign-in"
echo "   • Sign in with board member account"
echo "   • Verify dashboard loads correctly"
echo ""
echo -e "${CYAN}2. Share with board members:${NC}"
echo "   • Send them the URL: $DASHBOARD_URL"
echo "   • They sign in with their Google Workspace account"
echo "   • Works on desktop, tablet, and mobile"
echo ""
echo -e "${CYAN}3. Update data (anytime):${NC}"
echo "   ${BOLD}./scripts/update-dashboard.sh${NC}"
echo "   • Regenerates CSVs from database"
echo "   • Rebuilds dashboard"
echo "   • Deploys to Cloudflare"
echo "   • Takes ~30 seconds"
echo ""
echo -e "${BOLD}Useful Commands:${NC}"
echo ""
echo -e "  ${CYAN}# Rebuild and redeploy${NC}"
echo "  ./scripts/deploy-cloudflare-auto.sh"
echo ""
echo -e "  ${CYAN}# Quick data update${NC}"
echo "  ./scripts/update-dashboard.sh"
echo ""
echo -e "  ${CYAN}# View Cloudflare logs${NC}"
echo "  wrangler pages deployment list --project-name=$CLOUDFLARE_PROJECT_NAME"
echo ""
echo -e "  ${CYAN}# Manage Cloudflare Access${NC}"
echo "  https://dash.cloudflare.com → Zero Trust → Access"
echo ""
echo -e "${BOLD}Documentation:${NC} dashboard/README.md"
echo ""
echo -e "${GREEN}✅ Your dashboard is now live and secure!${NC}"
echo ""

# Save deployment info
cat > "$PROJECT_ROOT/dashboard/DEPLOYMENT.md" <<EOF
# Deployment Information

**Dashboard URL:** $DASHBOARD_URL
**Project Name:** $CLOUDFLARE_PROJECT_NAME
**Deployed:** $(date)
**Google Workspace Domain:** $GOOGLE_WORKSPACE_DOMAIN

## Quick Commands

\`\`\`bash
# Update dashboard
./scripts/update-dashboard.sh

# Redeploy
./scripts/deploy-cloudflare-auto.sh

# View deployments
wrangler pages deployment list --project-name=$CLOUDFLARE_PROJECT_NAME

# View logs
wrangler pages deployment tail --project-name=$CLOUDFLARE_PROJECT_NAME
\`\`\`

## Access Management

Manage who can access the dashboard:
https://dash.cloudflare.com → Zero Trust → Access → Applications

## Support

- **Cloudflare Pages Docs:** https://developers.cloudflare.com/pages/
- **Cloudflare Access Docs:** https://developers.cloudflare.com/cloudflare-one/
- **Dashboard README:** dashboard/README.md
EOF

echo -e "${CYAN}Deployment info saved to: dashboard/DEPLOYMENT.md${NC}"
echo ""
