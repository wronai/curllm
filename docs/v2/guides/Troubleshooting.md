# Troubleshooting

**[📚 Documentation Index](INDEX.md)** | **[⬅️ Back to Main README](../README.md)**

---

## Common issues

- "Not Found" from examples/curl_*.sh
  - Cause: API listening on non-default port (e.g., 8002) but scripts use 8000.
  - Fix:
    - Run `curllm --start-services` (or `make start`) to update `.env` with the actual port.
    - Scripts auto-load `examples/.env` and project `./.env` so the new `CURLLM_API_HOST` is used.

- Playwright browsers missing
  - Error: `BrowserType.launch: Executable doesn't exist ... run playwright install`
  - Fix (in venv):
    ```bash
    python -m playwright install chromium
    # Linux deps
    python -m playwright install-deps chromium || true
    ```

- PEP 668 / externally-managed-environment
  - Fix: always install in local virtualenv.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    python -m pip install -U pip setuptools wheel
    python -m pip install -r requirements.txt
    ```

- GPU OOM / slow
  - Reduce context and/or use a smaller model:
    ```bash
    export CURLLM_NUM_CTX=4096
    ollama pull phi3:mini
    export CURLLM_MODEL=phi3:mini
    ```

- CAPTCHA handling
  - Core executor can solve widget CAPTCHAs via 2captcha sitekey token:
    ```bash
    export CAPTCHA_API_KEY=YOUR_2CAPTCHA_KEY
    curllm --visual --captcha ...
    ```

- Language of content
  - Set header via env for examples:
    ```bash
    export ACCEPT_LANGUAGE="pl-PL,pl;q=0.9"
    ```

## Verify services

```bash
curllm --start-services
curllm --status
```

## Run examples

```bash
# Prepare examples env
examples/setup_env.sh

# Shell
bash examples/curl_product_search.sh

# Python (load env first if needed)
set -a; source examples/.env; set +a
python examples/bql_product_search.py
```

---

**[📚 Documentation Index](INDEX.md)** | **[⬆️ Back to Top](#troubleshooting)** | **[Related: Hierarchical Planner →](HIERARCHICAL_PLANNER.md) | [Form Filling →](FORM_FILLING.md)**
