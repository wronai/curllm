#!/usr/bin/env bash
set -euo pipefail

# Paths
DC_FILE="$(dirname "$0")/docker-compose.yml"

# Bring up services
DOCKER_BUILDKIT=1 docker compose -f "$DC_FILE" up -d --build
trap 'DOCKER_BUILDKIT=1 docker compose -f "$DC_FILE" logs --no-color || true; DOCKER_BUILDKIT=1 docker compose -f "$DC_FILE" down -v || true' EXIT

# Wait for API health
for i in {1..40}; do
  if curl -s http://localhost:18080/health | jq -e '.status=="healthy"' >/dev/null; then
    echo "API healthy"; break
  fi
  sleep 2
done

# Register remote proxies (host is the service name on same docker network)
API_IN_CONT="http://localhost:8000"
CID=$(DOCKER_BUILDKIT=1 docker compose -f "$DC_FILE" ps -q api)

docker exec "$CID" bash -lc "curlx register --host remote-proxy --ports 3128,3129 --server $API_IN_CONT"

# Verify list via curlx and curl
DOCKER_BUILDKIT=1 docker exec "$CID" bash -lc "curlx list --server $API_IN_CONT" | tee /tmp/remote_proxy_list.json
jq -e '.count>=2' /tmp/remote_proxy_list.json
curl -s http://localhost:18080/api/proxy/list | jq -e '.count>=2' >/dev/null

# Health check (no prune)
curl -s -X POST http://localhost:18080/api/proxy/health -H 'Content-Type: application/json' \
  -d '{"url":"http://example.com","timeout":4,"limit":10,"prune":false}' | jq -e '.tested>=1' >/dev/null

# Run curllm inside container using rotate:registry
DOCKER_BUILDKIT=1 docker exec "$CID" bash -lc "curllm --proxy rotate:registry --session e2e-session 'https://example.com' -d 'extract links'" \
  | jq -e '.success==true' >/dev/null

# Run curllm inside container using rotate:public (falls back to registry if public empty)
DOCKER_BUILDKIT=1 docker exec "$CID" bash -lc "curllm --proxy rotate:public --session e2e-session 'https://example.com' -d 'extract links'" \
  | jq -e '.success==true' >/dev/null

echo "OK: compose e2e passed"
