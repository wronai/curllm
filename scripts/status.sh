#!/usr/bin/env bash
set -euo pipefail

echo "Service Status:"
echo "==============="
OPORT=$(cat /tmp/ollama_port 2>/dev/null || echo 11434)
if pgrep -x "ollama" > /dev/null; then
  echo "✓ Ollama: Running on :${OPORT}"
else
  echo "✗ Ollama: Not running"
fi
PORT=$(cat /tmp/curllm_api_port 2>/dev/null || echo 8000)
if curl -s "http://localhost:${PORT}/health" > /dev/null 2>&1; then
  echo "✓ curllm API: Running on :${PORT}"
else
  echo "✗ curllm API: Not running"
fi
if docker ps 2>/dev/null | grep -q "browserless"; then
  echo "✓ Browserless: Running"
else
  echo "✗ Browserless: Not running"
fi
