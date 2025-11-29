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
    url = os.getenv("SHOP_URL", "https://ceneo.pl")
    headless = os.getenv("HEADLESS", "false").lower() in ("1", "true", "yes")

    instruction = (
        "Znajdź wszystkie produkty poniżej 150 zł i zwróć nazwy, ceny i URL-e. "
        "Jeśli to możliwe, kliknij odpowiednie filtry/sortowanie i poczekaj 1200 ms po zmianie."
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
