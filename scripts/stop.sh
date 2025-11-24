#!/usr/bin/env bash
set -euo pipefail

echo "Stopping curllm services..."
# Stop API server via PID file
if [ -f /tmp/curllm.pid ]; then
  PID=$(cat /tmp/curllm.pid)
  if echo "$PID" | grep -Eq '^[0-9]+$' && [ "$PID" -gt 1 ]; then
    kill "$PID" 2>/dev/null || true
    sleep 0.2
    kill -9 "$PID" 2>/dev/null || true
  fi
  rm -f /tmp/curllm.pid || true
  echo "Stopped curllm API server"
fi
# Kill any python bound to API port
PORT=$(cat /tmp/curllm_api_port 2>/dev/null || true)
if [ -n "${PORT:-}" ]; then
  PIDS=$(ss -ltnp 2>/dev/null | awk -v port=":${PORT} " 'index($4, port){print $7}' | sed -E 's/.*pid=([0-9]+).*/\1/' | sort -u)
  for pid in $PIDS; do
    if ps -p "$pid" -o comm= | grep -q python; then
      kill "$pid" 2>/dev/null || true
      sleep 0.2
      kill -9 "$pid" 2>/dev/null || true
      echo "Killed API server process PID=$pid on port $PORT"
    fi
  done
fi
# Stop services
pkill -f "ollama serve" 2>/dev/null || true
pkill -f "curllm_server.py" 2>/dev/null || true
# Optional docker services
(docker compose stop browserless redis || docker-compose stop browserless redis) 2>/dev/null || true
echo "Services stopped"
