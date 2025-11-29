#!/usr/bin/env bash
set -euo pipefail

# curllm CLI example: Product search under threshold
# Usage:
#   SHOP_URL=https://ceneo.pl PRICE_MAX=150 examples/curllm_product_search.sh

URL="${SHOP_URL:-https://ceneo.pl}"
THRESHOLD="${PRICE_MAX:-150}"

read -r -d '' PAYLOAD <<JSON
{
  "instruction": "Find all products under ${THRESHOLD}zł and extract names, prices and urls",
  "params": {
    "include_dom_html": true,
    "no_click": true,
    "scroll_load": true,
    "action_timeout_ms": 120000
  }
}
JSON

VISUAL_FLAG=${VISUAL_FLAG:---visual}
STEALTH_FLAG=${STEALTH_FLAG:-}
CAPTCHA_FLAG=${CAPTCHA_FLAG:---captcha}

curllm ${VISUAL_FLAG} ${STEALTH_FLAG} ${CAPTCHA_FLAG} "${URL}" -d "${PAYLOAD}"
