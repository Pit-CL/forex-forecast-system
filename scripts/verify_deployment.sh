#!/bin/bash
###############################################################################
# Deployment Verification Script
#
# Verifies that all MLOps Phase 2 components are deployed and working.
# Run this script to check system health after deployment.
#
# Usage:
#   ./scripts/verify_deployment.sh
###############################################################################

set -e
set -u

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

# Counters
PASSED=0
FAILED=0
TOTAL=0

# Test function
check_test() {
    local test_name="$1"
    local test_cmd="$2"

    TOTAL=$((TOTAL + 1))
    echo -n "[$TOTAL] Testing: $test_name ... "

    if eval "$test_cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}MLOps Phase 2 - Deployment Verification${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Activate venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo -e "${YELLOW}1. INFRASTRUCTURE CHECKS${NC}"
echo "-------------------------------------------"

check_test "Git repository" "[ -d .git ]"
check_test "Python venv" "[ -d venv ] || [ -d .venv ]"
check_test "requirements.txt" "[ -f requirements.txt ]"
check_test ".env file" "[ -f .env ]"
check_test "logs directory" "[ -d logs ]"
check_test "reports directory" "[ -d reports ]"
check_test "config directory" "[ -d config ]"
check_test "data directory" "[ -d data ]"

echo ""
echo -e "${YELLOW}2. DEPENDENCY CHECKS${NC}"
echo "-------------------------------------------"

check_test "pytest installed" "pip show pytest"
check_test "portalocker installed" "pip show portalocker"
check_test "scipy installed" "pip show scipy"
check_test "pandas installed" "pip show pandas"

echo ""
echo -e "${YELLOW}3. MODULE IMPORT CHECKS${NC}"
echo "-------------------------------------------"

check_test "validators module" "PYTHONPATH=src:\$PYTHONPATH python -c 'from forex_core.utils.validators import validate_horizon'"
check_test "file_lock module" "PYTHONPATH=src:\$PYTHONPATH python -c 'from forex_core.utils.file_lock import FileLock'"
check_test "regime_detector module" "PYTHONPATH=src:\$PYTHONPATH python -c 'from forex_core.mlops.regime_detector import MarketRegimeDetector'"
check_test "performance_monitor module" "PYTHONPATH=src:\$PYTHONPATH python -c 'from forex_core.mlops.performance_monitor import PerformanceMonitor'"
check_test "readiness module" "PYTHONPATH=src:\$PYTHONPATH python -c 'from forex_core.mlops.readiness import ChronosReadinessChecker'"
check_test "email module" "PYTHONPATH=src:\$PYTHONPATH python -c 'from forex_core.notifications.email import EmailSender'"

echo ""
echo -e "${YELLOW}4. SCRIPT CHECKS${NC}"
echo "-------------------------------------------"

check_test "weekly_validation.sh exists" "[ -f scripts/weekly_validation.sh ]"
check_test "weekly_validation.sh executable" "[ -x scripts/weekly_validation.sh ]"
check_test "daily_dashboard.sh exists" "[ -f scripts/daily_dashboard.sh ]"
check_test "daily_dashboard.sh executable" "[ -x scripts/daily_dashboard.sh ]"
check_test "check_performance.py exists" "[ -f scripts/check_performance.py ]"
check_test "check_performance.py executable" "[ -x scripts/check_performance.py ]"
check_test "calibrate_usdclp.py exists" "[ -f scripts/calibrate_usdclp.py ]"
check_test "calibrate_usdclp.py executable" "[ -x scripts/calibrate_usdclp.py ]"

echo ""
echo -e "${YELLOW}5. CRON JOB CHECKS${NC}"
echo "-------------------------------------------"

check_test "Crontab has entries" "crontab -l | grep -q 'forex-forecast-system'"
check_test "Weekly validation scheduled" "crontab -l | grep -q 'weekly_validation.sh'"
check_test "Daily dashboard scheduled" "crontab -l | grep -q 'daily_dashboard.sh'"
check_test "Performance check scheduled" "crontab -l | grep -q 'check_performance.py'"

echo ""
echo -e "${YELLOW}6. SECURITY CHECKS${NC}"
echo "-------------------------------------------"

# Run security tests if pytest available
if command -v pytest &> /dev/null; then
    check_test "Path traversal protection tests" "pytest tests/unit/test_validators.py::test_path_traversal_blocked -v"
    check_test "Shell metacharacters blocked" "pytest tests/unit/test_validators.py::test_shell_metacharacters_blocked -v"
    check_test "Null byte injection blocked" "pytest tests/unit/test_validators.py::test_null_byte_blocked -v"
else
    echo -e "${YELLOW}[SKIP] pytest not available - security tests skipped${NC}"
fi

echo ""
echo -e "${YELLOW}7. FUNCTIONAL TESTS${NC}"
echo "-------------------------------------------"

# Test readiness checker
check_test "Readiness checker runs" "PYTHONPATH=src:\$PYTHONPATH python -c 'from pathlib import Path; from forex_core.mlops.readiness import ChronosReadinessChecker; checker = ChronosReadinessChecker(data_dir=Path(\"data\")); report = checker.assess(); print(report.level.value)'"

# Test performance monitor
check_test "Performance monitor runs" "PYTHONPATH=src:\$PYTHONPATH python -c 'from pathlib import Path; from forex_core.mlops.performance_monitor import PerformanceMonitor; monitor = PerformanceMonitor(data_dir=Path(\"data\")); print(\"OK\")'"

# Test regime detector
check_test "Regime detector runs" "PYTHONPATH=src:\$PYTHONPATH python -c 'from forex_core.mlops.regime_detector import MarketRegimeDetector; import pandas as pd; detector = MarketRegimeDetector(); series = pd.Series([900]*100); report = detector.detect(series); print(report.regime.value)'"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}VERIFICATION SUMMARY${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "Total Tests:  $TOTAL"
echo -e "${GREEN}Passed:       $PASSED${NC}"

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed:       $FAILED${NC}"
    echo ""
    echo -e "${RED}❌ DEPLOYMENT VERIFICATION FAILED${NC}"
    echo "Some checks did not pass. Review errors above."
    exit 1
else
    echo -e "${GREEN}Failed:       0${NC}"
    echo ""
    echo -e "${GREEN}✅ DEPLOYMENT VERIFICATION SUCCESSFUL${NC}"
    echo "All checks passed. System is ready."

    # Show readiness status
    echo ""
    echo -e "${YELLOW}Current Readiness Status:${NC}"
    PYTHONPATH=src:$PYTHONPATH python -c "
from pathlib import Path
from forex_core.mlops.readiness import ChronosReadinessChecker

checker = ChronosReadinessChecker(data_dir=Path('data'))
report = checker.assess()

print(f'  Status: {report.level.value.upper()}')
print(f'  Score:  {report.score:.0f}/100')
print()
print(f'  {report.recommendation}')
" 2>/dev/null || echo "  (Readiness check requires prediction data)"

    exit 0
fi
