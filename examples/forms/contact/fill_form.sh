#!/usr/bin/env bash
set -euo pipefail

# curllm CLI example: Contact form fill & submit
# Usage:
#   CONTACT_URL=https://softreck.com/contact \
#   CONTACT_NAME=Jan CONTACT_EMAIL=jan@example.com CONTACT_MESSAGE="Test wysyłki" \
#   examples/curllm_contact_form.sh

URL="${CONTACT_URL:-https://softreck.com/contact}"
NAME="${CONTACT_NAME:-Jan}"
EMAIL="${CONTACT_EMAIL:-jan@example.com}"
MESSAGE="${CONTACT_MESSAGE:-Test wysyłki}"

read -r -d '' PAYLOAD <<JSON
{
  "instruction": "Wypełnij formularz kontaktowy: Imię=${NAME}, Email=${EMAIL}, Wiadomość='${MESSAGE}'. Kliknij przycisk wysyłki i poczekaj 1500 ms.",
  "params": {
    "include_dom_html": true,
    "smart_click": true,
    "action_timeout_ms": 120000
  }
}
JSON

VISUAL_FLAG=${VISUAL_FLAG:-}
STEALTH_FLAG=${STEALTH_FLAG:---stealth}
CAPTCHA_FLAG=${CAPTCHA_FLAG:---captcha}

curllm ${VISUAL_FLAG} ${STEALTH_FLAG} ${CAPTCHA_FLAG} "${URL}" -d "${PAYLOAD}"
