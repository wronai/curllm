# Devbox (Docker)

**[📚 Documentation Index](INDEX.md)** | **[⬅️ Back to Main README](../README.md)**

---

A small container for testing installation and examples with an isolated virtualenv.

## Start

```bash
docker compose up -d devbox ollama curllm-api
```

## Enter

```bash
docker compose exec devbox bash
```

## Inside devbox

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install playwright && python -m playwright install chromium
python -m playwright install-deps chromium || true

examples/setup_env.sh
export CURLLM_API_HOST=http://curllm-api:8000
export CURLLM_OLLAMA_HOST=http://ollama:11434

bash examples/curl_product_search.sh
python examples/bql_product_search.py
```

Notes:

- Use `ACCEPT_LANGUAGE` in `examples/.env` to control language; shell examples add this header automatically.
- For CAPTCHA solving in core, set `CAPTCHA_API_KEY` and use `--captcha`.

---

**[📚 Documentation Index](INDEX.md)** | **[⬆️ Back to Top](#devbox-docker)** | **[Related: Docker →](Docker.md) | [Installation →](Installation.md)**
