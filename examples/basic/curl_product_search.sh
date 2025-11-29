#!/usr/bin/env bash
set -euo pipefail

# Auto-load env from examples/.env or project .env if present
ENV_DIR="$(cd "$(dirname "$0")" && pwd)"
for CAND in "$ENV_DIR/.env" "$ENV_DIR/../.env"; do
  if [ -f "$CAND" ]; then set -a; . "$CAND"; set +a; break; fi
done

API_HOST="${CURLLM_API_HOST:-http://localhost:8000}"
URL="${SHOP_URL:-https://ceneo.pl}"
THRESHOLD="${PRICE_MAX:-150}"

PAYLOAD=$(cat <<JSON
{
  "url": "${URL}",
  "data": "Znajdź wszystkie produkty poniżej ${THRESHOLD} zł i zwróć nazwy, ceny i URL-e.",
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
