#!/bin/bash
#============================================================================
# test_pypi_install.sh - Cross-platform PyPI installation test
#============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test configuration
DISTRO=$(cat /etc/os-release | grep "^ID=" | cut -d= -f2 | tr -d '"')
VERSION=$(cat /etc/os-release | grep "VERSION_ID" | cut -d= -f2 | tr -d '"' || echo "rolling")
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
TEST_START=$(date +%s)

# Results
RESULTS_FILE="/test/results.json"
TESTS_PASSED=0
TESTS_FAILED=0
TEST_DETAILS=()

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   curllm PyPI Installation Test            ║${NC}"
echo -e "${BLUE}║   Platform: ${DISTRO} ${VERSION}${NC}"
echo -e "${BLUE}║   Python: ${PYTHON_VERSION}${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

#============================================================================
# Helper Functions
#============================================================================

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TEST_DETAILS+=("{\"name\":\"$1\",\"status\":\"pass\"}")
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TEST_DETAILS+=("{\"name\":\"$1\",\"status\":\"fail\",\"error\":\"$2\"}")
}

log_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
}

#============================================================================
# Test 1: Python Environment
#============================================================================

log_test "Python environment check"

if python3 --version > /dev/null 2>&1; then
    log_pass "Python 3 installed: $PYTHON_VERSION"
else
    log_fail "Python 3 not found" "python3 command not available"
    exit 1
fi

if python3 -m pip --version > /dev/null 2>&1; then
    log_pass "pip installed"
else
    log_fail "pip not found" "python3 -m pip not available"
    exit 1
fi

#============================================================================
# Test 2: Virtual Environment
#============================================================================

log_test "Creating virtual environment"

if python3 -m venv /test/venv; then
    log_pass "Virtual environment created"
else
    log_fail "Virtual environment creation failed" "venv module error"
fi

# Activate venv
source /test/venv/bin/activate

#============================================================================
# Test 3: PyPI Installation
#============================================================================

log_test "Installing curllm from PyPI"

# Check if we should use local wheel (PRIORITY)
WHEEL_FILE=$(ls /test/curllm-*.whl 2>/dev/null | head -1)

if [ -n "$WHEEL_FILE" ] && [ -f "$WHEEL_FILE" ]; then
    log_test "Local wheel found: $(basename $WHEEL_FILE)"
    if pip install "$WHEEL_FILE"; then
        log_pass "Installed from local wheel"
    else
        log_fail "Installation from wheel failed" "pip install wheel error"
        exit 1
    fi
elif [ "$USE_TEST_PYPI" = "true" ]; then
    log_test "Installing from TestPyPI"
    if pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ curllm; then
        log_pass "Installed from TestPyPI"
    else
        log_fail "Installation from TestPyPI failed" "pip install error"
        exit 1
    fi
else
    log_test "Installing from PyPI (NOTE: Package must be published first!)"
    if pip install curllm; then
        log_pass "Installed from PyPI"
    else
        log_fail "Installation from PyPI failed" "Package not published or pip error"
        log_test "TIP: Use local wheel by building package first: python3 -m build"
        exit 1
    fi
fi

#============================================================================
# Test 4: Package Import
#============================================================================

log_test "Importing curllm package"

if python3 -c "import curllm_core" 2>/dev/null; then
    log_pass "curllm_core module importable"
else
    log_fail "curllm_core import failed" "ImportError"
fi

if python3 -c "from curllm_core.executor import CurllmExecutor" 2>/dev/null; then
    log_pass "CurllmExecutor importable"
else
    log_fail "CurllmExecutor import failed" "ImportError"
fi

#============================================================================
# Test 5: Playwright Installation
#============================================================================

log_test "Installing Playwright browsers"

if python3 -m playwright install chromium --with-deps > /dev/null 2>&1; then
    log_pass "Playwright browsers installed"
else
    log_skip "Playwright browser installation (may require sudo)"
fi

#============================================================================
# Test 6: CLI Command
#============================================================================

log_test "Testing curllm CLI"

# Check if curllm command exists
if command -v curllm > /dev/null 2>&1; then
    log_pass "curllm command available"
    
    # Test help
    if curllm --help > /dev/null 2>&1; then
        log_pass "curllm --help works"
    else
        log_fail "curllm --help failed" "CLI help error"
    fi
    
    # Test version
    if curllm --version > /dev/null 2>&1; then
        log_pass "curllm --version works"
    else
        log_skip "curllm --version (may not be implemented)"
    fi
else
    log_skip "curllm CLI not in PATH (expected for pip install)"
fi

#============================================================================
# Test 7: Configuration Files
#============================================================================

log_test "Checking configuration"

if [ -f "$HOME/.config/curllm/config.yml" ]; then
    log_pass "Config file exists"
else
    log_skip "Config file not created (optional)"
fi

#============================================================================
# Test 8: Dependencies
#============================================================================

log_test "Checking dependencies"

# Key dependencies
DEPS=("playwright" "flask" "requests" "aiohttp")

for dep in "${DEPS[@]}"; do
    if python3 -c "import $dep" 2>/dev/null; then
        log_pass "Dependency: $dep installed"
    else
        log_fail "Dependency: $dep missing" "ImportError for $dep"
    fi
done

#============================================================================
# Test 9: Basic Functionality (without Ollama)
#============================================================================

log_test "Testing basic executor creation"

TEST_SCRIPT=$(cat <<'EOF'
from curllm_core.executor import CurllmExecutor
try:
    executor = CurllmExecutor(model="test", headless=True)
    print("Executor created successfully")
except Exception as e:
    print(f"Error: {e}")
    exit(1)
EOF
)

if echo "$TEST_SCRIPT" | python3; then
    log_pass "CurllmExecutor instantiation works"
else
    log_fail "CurllmExecutor instantiation failed" "Constructor error"
fi

#============================================================================
# Test 10: Module Structure
#============================================================================

log_test "Checking module structure"

MODULES=("curllm_core.config" "curllm_core.logger" "curllm_core.executor" "curllm_core.llm")

for mod in "${MODULES[@]}"; do
    if python3 -c "import $mod" 2>/dev/null; then
        log_pass "Module: $mod present"
    else
        log_fail "Module: $mod missing" "ImportError for $mod"
    fi
done

#============================================================================
# Generate Results
#============================================================================

TEST_END=$(date +%s)
TEST_DURATION=$((TEST_END - TEST_START))

echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
echo -e "${BLUE}Duration: ${TEST_DURATION}s${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"

# Generate JSON results
cat > "$RESULTS_FILE" <<EOF
{
  "distro": "$DISTRO",
  "version": "$VERSION",
  "python_version": "$PYTHON_VERSION",
  "tests_passed": $TESTS_PASSED,
  "tests_failed": $TESTS_FAILED,
  "duration": $TEST_DURATION,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "tests": [
    $(IFS=,; echo "${TEST_DETAILS[*]}")
  ]
}
EOF

echo ""
echo -e "${BLUE}Results saved to: $RESULTS_FILE${NC}"

# Exit with proper code
if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi
