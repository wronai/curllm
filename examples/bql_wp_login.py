#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

# Ensure project root is on sys.path to import local packages
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright
from captcha.playwright_bql_framework import BQLAgent, select_llm_caller


def main():
    url = os.getenv("WP_LOGIN_URL", "https://www.prototypowanie.pl/wp-login.php")
    user = os.getenv("WP_USER", "admin")
    password = os.getenv("WP_PASS", "test123")
    headless = os.getenv("HEADLESS", "false").lower() in ("1", "true", "yes")

    instruction = (
        "Zaloguj się do WordPress. Użyj dokładnie następujących selektorów: "
        "wpisz nazwę użytkownika do pola '#user_login', wpisz hasło do pola '#user_pass', "
        "a następnie kliknij przycisk '#wp-submit'. Po kliknięciu poczekaj 1500 ms."
        f" Dane: login='{user}', hasło='{password}'."
    )

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        agent = BQLAgent(page, call_llm=select_llm_caller())
        res = agent.run_instruction(instruction)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
