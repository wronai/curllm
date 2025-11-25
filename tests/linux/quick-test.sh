#!/bin/bash
# Quick single-platform test for debugging

PLATFORM=${1:-ubuntu}

echo "Testing on $PLATFORM..."

cd "$(dirname "$0")"

# Build package if needed
WHEEL_COUNT=$(ls ../../dist/curllm-*.whl 2>/dev/null | wc -l)
if [ "$WHEEL_COUNT" -eq 0 ]; then
    echo "No wheel found in dist/, building package..."
    cd ../..
    python3 -m build
    cd tests/linux
    echo "✓ Package built"
else
    echo "✓ Using existing wheel: $(ls ../../dist/curllm-*.whl | head -1 | xargs basename)"
fi

# Run test
mkdir -p results
docker-compose up --build test-$PLATFORM

# Show result
if [ -f "results/$PLATFORM.json" ]; then
    echo ""
    echo "=== Results ==="
    python3 -c "import json; r=json.load(open('results/$PLATFORM.json')); print(f\"✅ Passed: {r['tests_passed']}\"); print(f\"❌ Failed: {r['tests_failed']}\")"
else
    echo ""
    echo "⚠️  No results file generated - test may have failed early"
fi
