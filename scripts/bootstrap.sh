#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrapping curllm from scratch..."
# Install Ollama
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.ai/install.sh | sh
fi
# Playwright via pipx for system-level convenience (optional)
if ! command -v pipx >/dev/null 2>&1; then
  python3 -m pip install --user pipx || true
fi
if command -v pipx >/dev/null 2>&1; then
  pipx install playwright || true
  playwright install chromium || true
fi
# Project setup
make setup
make start

echo "Bootstrap complete! curllm is ready to use."
