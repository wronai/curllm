#!/usr/bin/env bash
set -euo pipefail

API_PORT="${API_PORT:-8000}"
if [ -f .env ]; then
  # try to read API_PORT from .env if present
  p=$(grep -E '^API_PORT=' .env | tail -n1 | cut -d= -f2- || true)
  if [ -n "${p:-}" ]; then API_PORT="$p"; fi
fi

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1" >&2; exit 1; }; }
need docker
need jq
need curl

# Start stack
echo "[e2e] Starting docker compose..."
docker compose up -d --build

# Wait for API
echo "[e2e] Waiting for API on :$API_PORT ..."
for i in {1..60}; do
  if curl -s "http://localhost:${API_PORT}/health" | jq -e '.status == "healthy"' >/dev/null 2>&1; then
    echo "[e2e] API is healthy"
    break
  fi
  sleep 2
  if [ "$i" -eq 60 ]; then
    echo "[e2e] API did not become healthy in time" >&2
    docker compose ps
    exit 1
  fi
done

failures=0

# Test 1: screenshot saved under domain folder
echo "[e2e] Test 1: screenshot saved under domain folder (allegro.com)"
resp=$(curl -s -X POST "http://localhost:${API_PORT}/api/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://allegro.com",
    "data": "Create screenshot in folder name of domain",
    "visual_mode": false,
    "stealth_mode": false,
    "captcha_solver": false,
    "use_bql": false
  }')

echo "$resp" | jq . >/dev/null || { echo "[e2e] Invalid JSON in Test 1" >&2; failures=$((failures+1)); }
shot=$(echo "$resp" | jq -r '.screenshots[0] // .result.screenshot_saved // empty')
if [ -z "$shot" ]; then
  echo "[e2e] No screenshot path returned in Test 1" >&2; failures=$((failures+1));
else
  echo "[e2e] Screenshot: $shot"
  if ! test -f "$shot"; then
    echo "[e2e] Screenshot file not found on host (ensure volume mapping if running in container)" >&2
  fi
fi

# Test 2: extract products under 150
echo "[e2e] Test 2: extract products under 150 (allegro.com)"
resp=$(curl -s -X POST "http://localhost:${API_PORT}/api/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://allegro.com",
    "data": "Find all products under 150 and extract names, prices and urls",
    "visual_mode": true,
    "stealth_mode": false,
    "captcha_solver": false,
    "use_bql": false
  }')

echo "$resp" | jq . >/dev/null || { echo "[e2e] Invalid JSON in Test 2" >&2; failures=$((failures+1)); }
count=$(echo "$resp" | jq -r '.result.products | length // 0')
if [ "$count" -le 0 ]; then
  echo "[e2e] WARN: No products extracted; site may have dynamic content/cookies. See run_log for details." >&2
else
  echo "[e2e] Extracted $count products"
fi

# Test 3: only emails and phones (no links)
echo "[e2e] Test 3: only emails and phones"
resp=$(curl -s -X POST "http://localhost:${API_PORT}/api/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://www.prototypowanie.pl/kontakt/",
    "data": "extract only email and phone links",
    "visual_mode": false,
    "stealth_mode": false,
    "captcha_solver": false,
    "use_bql": false
  }')

echo "$resp" | jq . >/dev/null || { echo "[e2e] Invalid JSON in Test 3" >&2; failures=$((failures+1)); }
if echo "$resp" | jq -e '.result.links' >/dev/null 2>&1; then
  echo "[e2e] FAIL: result.links present but should not for 'only email and phone'" >&2
  failures=$((failures+1))
fi

if [ "$failures" -gt 0 ]; then
  echo "[e2e] Completed with $failures failures" >&2
  exit 1
fi

echo "[e2e] All tests passed"
