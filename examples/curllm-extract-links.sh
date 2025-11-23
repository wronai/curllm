#!/usr/bin/env bash
set -euo pipefail

# Ensure services are running first:
#   curllm --start-services
#   curllm --status

curllm "https://example.com" -d "extract all links" -v
