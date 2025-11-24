#!/usr/bin/env bash
set -euo pipefail

API_PORT="${API_PORT:-8000}"
if [ -f .env ]; then
  p=$(grep -E '^(API_PORT|CURLLM_API_PORT)=' .env | tail -n1 | cut -d= -f2- || true)
  if [ -n "${p:-}" ]; then API_PORT="$p"; fi
fi

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1" >&2; exit 1; }; }
need jq
need curl

check_api() {
  curl -s "http://localhost:${API_PORT}/health" | jq -e '.status == "healthy"' >/dev/null 2>&1
}

if ! check_api; then
  if command -v docker >/dev/null 2>&1 && [ -f docker-compose.yml ]; then
    echo "[e2e-diff] Starting docker compose..."
    docker compose up -d --build
    echo "[e2e-diff] Waiting for API on :$API_PORT ..."
    for i in {1..60}; do
      if check_api; then echo "[e2e-diff] API is healthy"; break; fi
      sleep 2
      if [ "$i" -eq 60 ]; then echo "[e2e-diff] API did not become healthy in time" >&2; exit 1; fi
    done
  else
    echo "[e2e-diff] API not running and docker not available; aborting" >&2
    exit 1
  fi
fi

key="e2e-example-$(date +%s)-$RANDOM"
query='query { page(url: "https://example.com") { select(css: "a") { text, attr(name: "href") } } }'
payload_first=$(jq -n --arg q "$query" --arg k "$key" '{
  url: "https://example.com",
  data: ({instruction: $q, params: {store_results: true, include_prev_results: true, result_key: $k, diff_mode: "new", diff_fields: ["url"], keep_history: 3}} | tostring),
  visual_mode: false,
  stealth_mode: false,
  captcha_solver: false,
  use_bql: true
}')

resp1=$(curl -s -X POST "http://localhost:${API_PORT}/api/execute" -H 'Content-Type: application/json' -d "$payload_first")
echo "$resp1" | jq . >/dev/null || { echo "[e2e-diff] Invalid JSON in first run" >&2; exit 1; }
count1=$(echo "$resp1" | jq -r '.result.articles | length // 0')
new1=$(echo "$resp1" | jq -r '.diff.new_count // 0')
if [ "$count1" -le 0 ] || [ "$new1" -le 0 ]; then
  echo "[e2e-diff] Expected first run to have new items (>0). Got count=$count1 new=$new1" >&2; exit 1
fi

echo "[e2e-diff] First run ok: articles=$count1 new=$new1"

# Second run with identical params should yield zero new items
resp2=$(curl -s -X POST "http://localhost:${API_PORT}/api/execute" -H 'Content-Type: application/json' -d "$payload_first")
echo "$resp2" | jq . >/dev/null || { echo "[e2e-diff] Invalid JSON in second run" >&2; exit 1; }
count2=$(echo "$resp2" | jq -r '.result.articles | length // 0')
new2=$(echo "$resp2" | jq -r '.diff.new_count // 0')
if [ "$new2" -ne 0 ]; then
  echo "[e2e-diff] Expected second run new_count==0; got $new2" >&2; exit 1
fi

echo "[e2e-diff] Second run ok: articles=$count2 new=$new2"

echo "[e2e-diff] Diff E2E passed"
