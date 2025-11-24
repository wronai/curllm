#!/usr/bin/env bash
set -euo pipefail

echo "Setting up curllm..."
ollama pull qwen2.5:7b
ollama pull mistral:7b-instruct-q4_0
venv/bin/python -m playwright install chromium || venv/bin/python -m playwright install
mkdir -p ~/.config/curllm
mkdir -p /tmp/curllm_screenshots
echo "Setup complete!"
