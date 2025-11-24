#!/usr/bin/env bash
set -euo pipefail

IMG="curlx-e2e:dev"
CID="curlx-e2e-$(date +%s)"
API_PORT=18080

# Build test image
docker build -t "$IMG" -f curlx_pkg/tests/e2e/Dockerfile .

# Run curllm API container
docker run -d --name "$CID" -p ${API_PORT}:8000 "$IMG"
trap 'docker logs $CID || true; docker rm -f $CID || true' EXIT

# Wait for health
echo "[*] Waiting for API to be healthy..."
for i in {1..30}; do
  if curl -s "http://localhost:${API_PORT}/health" | jq -e '.status=="healthy"' >/dev/null; then
    echo "API healthy"; break
  fi
  sleep 2
done

# Use curlx inside container
IN="http://localhost:8000"

# Start local proxies inside container
docker exec "$CID" bash -lc "nohup python3 -m proxy --hostname 0.0.0.0 --port 8888 >/tmp/proxy_8888.log 2>&1 & echo \$! > /tmp/proxy_8888.pid"
docker exec "$CID" bash -lc "nohup python3 -m proxy --hostname 0.0.0.0 --port 8889 >/tmp/proxy_8889.log 2>&1 & echo \$! > /tmp/proxy_8889.pid"
# Wait for ports to listen
docker exec "$CID" bash -lc 'for p in 8888 8889; do for i in {1..30}; do ss -ltn | grep -q ":$p " && break; sleep 0.2; done; done'

# Register proxies via curlx (simulate 127.0.0.1:8888,8889)
docker exec "$CID" bash -lc "curlx register --host 127.0.0.1 --ports 8888,8889 --server $IN"

# Verify list via curlx
docker exec "$CID" bash -lc "curlx list --server $IN" | tee /tmp/proxy_list.json
jq -e '.count>=2' /tmp/proxy_list.json

# Also verify via curl (host port mapping)
curl -s "http://localhost:${API_PORT}/api/proxy/list" | jq -e '.count>=2' >/dev/null

# Invoke curllm inside container using rotate:registry (should avoid LLM via fast-path 'extract links')
docker exec "$CID" bash -lc "curllm --proxy rotate:registry --session e2e-session 'https://example.com' -d 'extract links'" \
  | jq -e '.success==true' >/dev/null

echo "OK: e2e done"
