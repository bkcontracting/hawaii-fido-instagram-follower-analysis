#!/bin/bash
# Hawaii Fi-Do Dashboard - Comprehensive Test Runner
#
# Runs all tests: Unit tests (pytest) + E2E tests (Playwright)
# Provides detailed coverage and reporting
#
# Usage:
#   ./dashboard/tests/run_all_tests.sh
#
# Options:
#   --unit-only    Run only unit tests
#   --e2e-only     Run only E2E tests
#   --quick        Run quick tests only (skip slow E2E browsers)
#   --ci           CI mode (strict, fail fast)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/home/user/hawaii-fido-instagram-follower-analysis"
DASHBOARD_DIR="$PROJECT_ROOT/dashboard"
RUN_UNIT=true
RUN_E2E=true
QUICK_MODE=false
CI_MODE=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --unit-only)
            RUN_E2E=false
            ;;
        --e2e-only)
            RUN_UNIT=false
            ;;
        --quick)
            QUICK_MODE=true
            ;;
        --ci)
            CI_MODE=true
            ;;
    esac
done

echo ""
echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║      Hawaii Fi-Do Dashboard - Test Suite          ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Track test results
UNIT_PASSED=false
E2E_PASSED=false

cd "$PROJECT_ROOT"

# ============================================================================
# STEP 0: Build Dashboard (if dist doesn't exist)
# ============================================================================

if [ ! -f "dashboard/dist/index.html" ]; then
    echo -e "${BLUE}🏗️  Building dashboard first...${NC}"
    python3 dashboard/build/build-dashboard.py | tail -10
    echo ""
fi

# ============================================================================
# STEP 1: Unit Tests (Python/pytest)
# ============================================================================

if [ "$RUN_UNIT" = true ]; then
    echo -e "${BOLD}${BLUE}[1/2] Running Unit Tests (pytest)...${NC}"
    echo ""

    # Check pytest is installed
    if ! command -v pytest &> /dev/null; then
        echo -e "${YELLOW}⚠ pytest not found, installing...${NC}"
        pip install pytest
    fi

    # Run unit tests
    echo -e "${CYAN}Testing: Build scripts, data processing, configuration${NC}"
    echo ""

    if pytest dashboard/tests/unit/ -v --tb=short --color=yes; then
        echo ""
        echo -e "${GREEN}✅ Unit Tests PASSED${NC}"
        UNIT_PASSED=true
    else
        echo ""
        echo -e "${RED}❌ Unit Tests FAILED${NC}"
        if [ "$CI_MODE" = true ]; then
            exit 1
        fi
    fi

    echo ""
else
    UNIT_PASSED=true # Skip
fi

# ============================================================================
# STEP 2: E2E Tests (Playwright)
# ============================================================================

if [ "$RUN_E2E" = true ]; then
    echo -e "${BOLD}${BLUE}[2/2] Running End-to-End Tests (Playwright)...${NC}"
    echo ""

    # Check if node is installed
    if ! command -v node &> /dev/null; then
        echo -e "${RED}✗ Node.js not found${NC}"
        echo "Please install Node.js first"
        exit 1
    fi

    cd "$DASHBOARD_DIR"

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 Installing Playwright dependencies...${NC}"
        npm install
        npx playwright install
        echo ""
    fi

    # Run E2E tests
    echo -e "${CYAN}Testing: UI components, interactions, responsiveness${NC}"
    echo ""

    if [ "$QUICK_MODE" = true ]; then
        # Quick mode: Only Chromium
        echo -e "${YELLOW}Quick mode: Testing Chromium only${NC}"
        if npx playwright test --project=chromium; then
            echo ""
            echo -e "${GREEN}✅ E2E Tests PASSED (Chromium)${NC}"
            E2E_PASSED=true
        else
            echo ""
            echo -e "${RED}❌ E2E Tests FAILED${NC}"
            if [ "$CI_MODE" = true ]; then
                exit 1
            fi
        fi
    else
        # Full mode: All browsers
        echo -e "${CYAN}Testing browsers: Chromium, Firefox, WebKit, Mobile${NC}"
        if npx playwright test; then
            echo ""
            echo -e "${GREEN}✅ E2E Tests PASSED (All Browsers)${NC}"
            E2E_PASSED=true
        else
            echo ""
            echo -e "${RED}❌ E2E Tests FAILED${NC}"
            if [ "$CI_MODE" = true ]; then
                exit 1
            fi
        fi
    fi

    cd "$PROJECT_ROOT"
    echo ""
else
    E2E_PASSED=true # Skip
fi

# ============================================================================
# SUMMARY
# ============================================================================

echo ""
echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║              Test Summary                          ║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$RUN_UNIT" = true ]; then
    if [ "$UNIT_PASSED" = true ]; then
        echo -e "  ${GREEN}✅ Unit Tests: PASSED${NC}"
    else
        echo -e "  ${RED}❌ Unit Tests: FAILED${NC}"
    fi
fi

if [ "$RUN_E2E" = true ]; then
    if [ "$E2E_PASSED" = true ]; then
        echo -e "  ${GREEN}✅ E2E Tests: PASSED${NC}"
    else
        echo -e "  ${RED}❌ E2E Tests: FAILED${NC}"
    fi
fi

echo ""

# View detailed reports
if [ "$RUN_E2E" = true ] && [ "$E2E_PASSED" = false ]; then
    echo -e "${CYAN}View detailed E2E test report:${NC}"
    echo "  npx playwright show-report dashboard/tests/reports/html"
    echo ""
fi

# Overall result
if [ "$UNIT_PASSED" = true ] && [ "$E2E_PASSED" = true ]; then
    echo -e "${GREEN}${BOLD}✅ ALL TESTS PASSED${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}${BOLD}❌ SOME TESTS FAILED${NC}"
    echo ""
    exit 1
fi
