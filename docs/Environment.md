# Environment

Docs: [Home](../README.md) | [Installation](Installation.md) | [Environment](Environment.md) | [API](API.md) | [Playwright+BQL](Playwright_BQL.md) | [Examples](EXAMPLES.md) | [Docker](Docker.md) | [Devbox](Devbox.md) | [Troubleshooting](Troubleshooting.md) | [Instrukcja](../INSTRUKCJA.md)

## .env files

- Project root: `.env` — auto-maintained by `curllm --start-services` (ports/hosts).
- Examples: `examples/.env` — generated from `examples/.env.examples` by `examples/setup_env.sh`.

Generate/merge examples env:

```bash
auth chmod +x examples/setup_env.sh
examples/setup_env.sh
```

Auto-load behavior:

- Shell examples `examples/curl_*.sh` load `examples/.env`, then project `./.env` (project overrides).
- Node.js (`examples/node_api_example.js`) and PHP (`examples/php_api_example.php`) read `examples/.env` automatically.
- Python examples (`examples/bql_*.py`) do not auto-load `.env`; export variables or `source examples/.env` before running.

## Common variables

- API/hosts
  - `CURLLM_API_HOST` (e.g., http://localhost:8000)
  - `CURLLM_OLLAMA_HOST` (e.g., http://localhost:11434)
- Model/runtime
  - `CURLLM_MODEL`, `CURLLM_TEMPERATURE`, `CURLLM_TOP_P`, `CURLLM_NUM_CTX`, `CURLLM_NUM_PREDICT`
- Locale
  - `CURLLM_LOCALE`, `CURLLM_TIMEZONE`, `ACCEPT_LANGUAGE`
- CAPTCHA
  - `CAPTCHA_API_KEY` (2captcha sitekey token service)
- Examples
  - `WP_LOGIN_URL`, `WP_USER`, `WP_PASS`
  - `CONTACT_URL`, `CONTACT_NAME`, `CONTACT_EMAIL`, `CONTACT_MESSAGE`
  - `SHOP_URL`, `PRICE_MAX`
- Flags (shell CLI)
  - `VISUAL_FLAG`, `STEALTH_FLAG`, `CAPTCHA_FLAG`
- Framework (Playwright+BQL)
  - `BQL_FRAMEWORK_LLM` ("ollama" default, set `openai` to use OpenAI)
  - `OPENAI_API_KEY`, `OPENAI_MODEL`

## Accept-Language

To prefer Polish content:

```bash
export ACCEPT_LANGUAGE="pl-PL,pl;q=0.9"
```
Shell examples add this header automatically if set.

## CAPTCHA

Enable widget CAPTCHA solving in core curllm:

```bash
export CAPTCHA_API_KEY=YOUR_2CAPTCHA_KEY
curllm --visual --captcha "https://example.com" -d "fill form"
```
