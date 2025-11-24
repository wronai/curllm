# Installation

**[📚 Documentation Index](INDEX.md)** | **[⬅️ Back to Main README](../README.md)**

---

## Quick install (recommended)

```bash
chmod +x install.sh
./install.sh
curllm --start-services
curllm --status
```

## Manual install

```bash
# 1) Create virtualenv
python3 -m venv venv
source venv/bin/activate
python -m pip install -U pip setuptools wheel

# 2) Python deps
python -m pip install -r requirements.txt

# 3) Playwright package and browsers
python -m pip install playwright
python -m playwright install chromium
# (Linux) optional system deps
python -m playwright install-deps chromium || true

# 4) Models
ollama pull qwen2.5:7b

# 5) Start services
curllm --start-services
```

Notes:

- Uses a local `venv` to avoid PEP 668 externally-managed-environment errors.
- Always prefer `python -m pip ...` and `python -m playwright ...` within the venv.
- For CAPTCHA solving, set `CAPTCHA_API_KEY`.

---

**[📚 Documentation Index](INDEX.md)** | **[⬆️ Back to Top](#installation)** | **[Next: Environment Configuration →](Environment.md)**
