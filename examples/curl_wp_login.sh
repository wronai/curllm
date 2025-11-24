#!/usr/bin/env bash
set -euo pipefail

# Auto-load env from examples/.env or project .env if present
ENV_DIR="$(cd "$(dirname "$0")" && pwd)"
for CAND in "$ENV_DIR/.env" "$ENV_DIR/../.env"; do
  if [ -f "$CAND" ]; then set -a; . "$CAND"; set +a; break; fi
done

API_HOST="${CURLLM_API_HOST:-http://localhost:8000}"
URL="${WP_LOGIN_URL:-https://www.prototypowanie.pl/wp-login.php}"
USER_NAME="${WP_USER:-admin}"
USER_PASS="${WP_PASS:-test123}"

PAYLOAD=$(cat <<JSON
{
  "url": "${URL}",
  "data": "Wpisz nazwę użytkownika do pola #user_login: ${USER_NAME}, wpisz hasło do pola #user_pass: ${USER_PASS}, a następnie kliknij #wp-submit. Poczekaj 1500 ms.",
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
