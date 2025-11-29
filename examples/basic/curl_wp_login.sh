#!/usr/bin/env bash
set -euo pipefail

# Auto-load env from examples/.env and then project .env (project overrides)
ENV_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$ENV_DIR/.env" ]; then set -a; . "$ENV_DIR/.env"; set +a; fi
if [ -f "$ENV_DIR/../.env" ]; then set -a; . "$ENV_DIR/../.env"; set +a; fi

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
