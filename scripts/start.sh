#!/usr/bin/env bash
set -euo pipefail

echo "Starting curllm services..."
PY=$(if [ -x venv/bin/python3 ]; then echo venv/bin/python3; else echo python3; fi)
PORT=${CURLLM_API_PORT:-$(if [ -f /tmp/curllm_api_port ]; then cat /tmp/curllm_api_port; else echo 8000; fi)}
while ss -ltn | grep -q ":${PORT}\b"; do PORT=$((PORT+1)); done
OPORT=${CURLLM_OLLAMA_PORT:-$(if [ -f /tmp/ollama_port ]; then cat /tmp/ollama_port; else echo 11434; fi)}
while ss -ltn | grep -q ":${OPORT}\b"; do OPORT=$((OPORT+1)); done
echo ${PORT} > /tmp/curllm_api_port; echo ${OPORT} > /tmp/ollama_port
[ -f .env ] || touch .env
if grep -q '^CURLLM_API_PORT=' .env; then sed -i "s/^CURLLM_API_PORT=.*/CURLLM_API_PORT=${PORT}/" .env; else echo "CURLLM_API_PORT=${PORT}" >> .env; fi
if grep -q '^CURLLM_OLLAMA_PORT=' .env; then sed -i "s/^CURLLM_OLLAMA_PORT=.*/CURLLM_OLLAMA_PORT=${OPORT}/" .env; else echo "CURLLM_OLLAMA_PORT=${OPORT}" >> .env; fi
if grep -q '^CURLLM_API_HOST=' .env; then sed -i "s#^CURLLM_API_HOST=.*#CURLLM_API_HOST=http://localhost:${PORT}#" .env; else echo "CURLLM_API_HOST=http://localhost:${PORT}" >> .env; fi
if grep -q '^CURLLM_OLLAMA_HOST=' .env; then sed -i "s#^CURLLM_OLLAMA_HOST=.*#CURLLM_OLLAMA_HOST=http://localhost:${OPORT}#" .env; else echo "CURLLM_OLLAMA_HOST=http://localhost:${OPORT}" >> .env; fi

# Prepare workspace with fallbacks
WS_DEFAULT="${CURLLM_WORKSPACE:-$PWD/workspace}"
if ! mkdir -p "$WS_DEFAULT"/sessions "$WS_DEFAULT"/storage "$WS_DEFAULT"/proxy 2>/dev/null; then
  WS_FALLBACK1="${HOME}/.cache/curllm/workspace"
  if ! mkdir -p "$WS_FALLBACK1"/sessions "$WS_FALLBACK1"/storage "$WS_FALLBACK1"/proxy 2>/dev/null; then
    WS_FALLBACK2="/tmp/curllm/workspace"
    mkdir -p "$WS_FALLBACK2"/sessions "$WS_FALLBACK2"/storage "$WS_FALLBACK2"/proxy 2>/dev/null || true
    WS_DEFAULT="$WS_FALLBACK2"
  else
    WS_DEFAULT="$WS_FALLBACK1"
  fi
fi
if grep -q '^CURLLM_WORKSPACE=' .env; then sed -i "s#^CURLLM_WORKSPACE=.*#CURLLM_WORKSPACE=$WS_DEFAULT#" .env; else echo "CURLLM_WORKSPACE=$WS_DEFAULT" >> .env; fi
if grep -q '^CURLLM_STORAGE_DIR=' .env; then sed -i "s#^CURLLM_STORAGE_DIR=.*#CURLLM_STORAGE_DIR=$WS_DEFAULT/storage#" .env; else echo "CURLLM_STORAGE_DIR=$WS_DEFAULT/storage" >> .env; fi

if ! pgrep -x "ollama" > /dev/null; then
  echo "Starting Ollama..."
  OLLAMA_HOST="127.0.0.1:${OPORT}" ollama serve > /tmp/ollama.log 2>&1 &
  sleep 2
else
  for p in "${CURLLM_OLLAMA_PORT:-}" $(cat /tmp/ollama_port 2>/dev/null) 11434 11435 11436; do
    [ -n "$p" ] || continue
    if curl -s "http://localhost:${p}/api/tags" > /dev/null 2>&1; then
      OPORT="$p"; echo ${OPORT} > /tmp/ollama_port
      sed -i "s/^CURLLM_OLLAMA_PORT=.*/CURLLM_OLLAMA_PORT=${OPORT}/" .env 2>/dev/null || echo "CURLLM_OLLAMA_PORT=${OPORT}" >> .env
      sed -i "s#^CURLLM_OLLAMA_HOST=.*#CURLLM_OLLAMA_HOST=http://localhost:${OPORT}#" .env 2>/dev/null || echo "CURLLM_OLLAMA_HOST=http://localhost:${OPORT}" >> .env
      break
    fi
  done
fi

if ! curl -s http://localhost:${PORT}/health > /dev/null 2>&1; then
  echo "Starting curllm API server..."
  CURLLM_OLLAMA_HOST="http://localhost:${OPORT}" CURLLM_API_PORT=${PORT} CURLLM_DEBUG=false "$PY" curllm_server.py > /tmp/curllm.log 2>&1 &
  echo $! > /tmp/curllm.pid
  for i in $(seq 1 20); do
    if curl -s "http://localhost:${PORT}/health" > /dev/null 2>&1; then echo "API healthy on :${PORT}"; break; fi
    sleep 1
  done
fi

echo "Services started. Check status with: curllm --status"
