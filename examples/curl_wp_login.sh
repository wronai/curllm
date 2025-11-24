#!/usr/bin/env bash
set -euo pipefail

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
  -d "${PAYLOAD}" | jq .
