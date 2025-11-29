#!/usr/bin/env bash
set -euo pipefail

# Auto-load env from examples/.env or project .env if present
ENV_DIR="$(cd "$(dirname "$0")" && pwd)"
for CAND in "$ENV_DIR/.env" "$ENV_DIR/../.env"; do
  if [ -f "$CAND" ]; then set -a; . "$CAND"; set +a; break; fi
done

API_HOST="${CURLLM_API_HOST:-http://localhost:8000}"
URL="${CONTACT_URL:-https://softreck.com/contact}"
NAME="${CONTACT_NAME:-Jan}"
EMAIL="${CONTACT_EMAIL:-jan@example.com}"
MESSAGE="${CONTACT_MESSAGE:-Test wysyłki}"

PAYLOAD=$(cat <<JSON
{
  "url": "${URL}",
  "data": "Wypełnij formularz kontaktowy: Imię=${NAME}, Email=${EMAIL}, Wiadomość='${MESSAGE}'. Kliknij przycisk wysyłki i poczekaj 1500 ms.",
  "visual_mode": false,
  "stealth_mode": true,
  "captcha_solver": true,
  "use_bql": false
}
JSON
)

curl -sS -X POST "${API_HOST}/api/execute" \
  -H 'Content-Type: application/json' \
  ${ACCEPT_LANGUAGE:+-H "Accept-Language: ${ACCEPT_LANGUAGE}"} \
  -d "${PAYLOAD}" | jq .
