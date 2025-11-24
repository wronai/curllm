# Playwright + BQL Framework

Docs: [Home](../README.md) | [Installation](Installation.md) | [Environment](Environment.md) | [API](API.md) | [Playwright+BQL](Playwright_BQL.md) | [Examples](EXAMPLES.md) | [Docker](Docker.md) | [Devbox](Devbox.md) | [Troubleshooting](Troubleshooting.md) | [Instrukcja](../INSTRUKCJA.md)

## Overview

Synchronous Playwright + BQL agent for page automation with:

- Semantic DOM snapshot (reduced DOM)
- Interactive elements snapshot
- Iframe info and CAPTCHA-like detection
- Consent banner detection (auto-click)
- BQLExecutor: fill, click, wait, select, submit, screenshot, evaluate, scroll, type
- LLM integration (Ollama by default; OpenAI optional)

Module: `captcha/playwright_bql_framework.py`

## LLM selection

- Default: Ollama HTTP
  - `CURLLM_OLLAMA_HOST` (default http://localhost:11434)
  - `CURLLM_MODEL` (default qwen2.5:7b)
- OpenAI:
  - Set `BQL_FRAMEWORK_LLM=openai` and `OPENAI_API_KEY`
  - Optional `OPENAI_MODEL` (default gpt-4o-mini)

## Usage (Python)

```bash
python -m pip install playwright
python -m playwright install chromium
```

```python
from playwright.sync_api import sync_playwright
from captcha.playwright_bql_framework import BQLAgent, select_llm_caller

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://www.prototypowanie.pl/wp-login.php", wait_until="networkidle")

    agent = BQLAgent(page, call_llm=select_llm_caller())
    res = agent.run_instruction("Zaloguj się do WordPress. Login: admin, Hasło: test123.")
    print(res)
    browser.close()
```

## Examples in repo

- Python scripts:
  - `examples/bql_wp_login.py`
  - `examples/bql_contact_form.py`
  - `examples/bql_product_search.py`

- Shell (API):
  - `examples/curl_wp_login.sh`
  - `examples/curl_contact_form.sh`
  - `examples/curl_product_search.sh`

## CAPTCHA note

This framework only detects CAPTCHA-like widgets and returns an interrupt action. The core curllm executor can solve widget CAPTCHAs via 2captcha token injection if `--captcha` is enabled and `CAPTCHA_API_KEY` is set.
