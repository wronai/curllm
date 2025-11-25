#!/bin/bash
#============================================================================
# run_tests.sh - Run cross-platform Linux tests
#============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   curllm Cross-Platform Linux Tests       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Change to test directory
cd "$(dirname "$0")"

# Create results directory
mkdir -p results
rm -f results/*.json

# Build package if dist doesn't exist
if [ ! -d "../../dist" ] || [ -z "$(ls -A ../../dist/*.whl 2>/dev/null)" ]; then
    echo -e "${YELLOW}Building package...${NC}"
    cd ../..
    python3 -m build
    cd tests/linux
    echo -e "${GREEN}✓ Package built${NC}"
fi

# Start tests
echo -e "${BLUE}Starting tests on all platforms...${NC}"
echo ""

# Run docker-compose (let all tests complete, don't abort on first failure)
if command -v docker-compose > /dev/null 2>&1; then
    docker-compose up --build
    EXIT_CODE=$?
else
    docker compose up --build
    EXIT_CODE=$?
fi

# Wait for all containers to finish
sleep 2

echo ""
echo -e "${BLUE}Tests completed. Generating report...${NC}"

# Generate Markdown report
python3 generate_report.py

echo ""
echo -e "${GREEN}✓ Report generated: LINUX_TEST_RESULTS.md${NC}"
echo ""

# Show summary
if [ -f "LINUX_TEST_RESULTS.md" ]; then
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
    echo -e "${BLUE}Test Summary:${NC}"
    grep "^| " LINUX_TEST_RESULTS.md | head -6
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
fi

# Cleanup containers
echo ""
echo -e "${YELLOW}Cleaning up containers...${NC}"
if command -v docker-compose > /dev/null 2>&1; then
    docker-compose down
else
    docker compose down
fi

exit $EXIT_CODE
