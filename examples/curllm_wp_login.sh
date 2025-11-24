#!/usr/bin/env bash
set -euo pipefail

# curllm CLI example: WordPress login
# Usage:
#   WP_LOGIN_URL=https://site/wp-login.php WP_USER=admin WP_PASS=secret examples/curllm_wp_login.sh

URL="${WP_LOGIN_URL:-https://www.prototypowanie.pl/wp-login.php}"
USER_NAME="${WP_USER:-admin}"
USER_PASS="${WP_PASS:-test123}"

read -r -d '' PAYLOAD <<JSON
{
  "instruction": "Wpisz nazwę użytkownika do pola #user_login: ${USER_NAME}, wpisz hasło do pola #user_pass: ${USER_PASS}, następnie kliknij #wp-submit i zaczekaj 1500 ms.",
  "params": {
    "include_dom_html": true,
    "smart_click": true,
    "action_timeout_ms": 120000
  }
}
JSON

# Optional flags can be toggled via envs
VISUAL_FLAG=${VISUAL_FLAG:-}
STEALTH_FLAG=${STEALTH_FLAG:---stealth}
CAPTCHA_FLAG=${CAPTCHA_FLAG:---captcha}

curllm ${VISUAL_FLAG} ${STEALTH_FLAG} ${CAPTCHA_FLAG} "${URL}" -d "${PAYLOAD}"
