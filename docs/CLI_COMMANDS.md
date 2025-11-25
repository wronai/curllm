# Curllm CLI Commands

This document describes the command-line interface (CLI) tools available after installing curllm via pip.

## Installation

```bash
pip install -U curllm
```

## Available Commands

### `curllm-setup`

Post-installation setup command that prepares your environment for using curllm.

**Usage:**
```bash
curllm-setup
```

**What it does:**
1. ✓ Checks Python version (3.10+ required)
2. ✓ Creates necessary directories (`logs/`, `screenshots/`, `downloads/`, `workspace/`)
3. ✓ Creates `.env` configuration file from template
4. ✓ Installs Playwright Chromium browser
5. ✓ Checks for Ollama installation

**When to use:**
- Right after installing curllm for the first time
- When setting up a new project
- After a fresh clone of your project repository

**Example output:**
```
======================================================================
  Curllm Post-Installation Setup
======================================================================

[1/5] Checking Python version
✓ Python 3.10.12

[2/5] Creating necessary directories
✓ Created directory: logs/
✓ Created directory: screenshots/
  Directory already exists: downloads/
  Directory already exists: workspace/

[3/5] Setting up configuration
✓ Created .env from package template

[4/5] Installing Playwright browsers
Installing Playwright browsers (this may take a few minutes)...
✓ Playwright Chromium browser installed

[5/5] Checking for Ollama
✓ Ollama is installed

======================================================================
  Setup Complete!
======================================================================

✓ All setup steps completed successfully!

Next steps:
  1. Review and configure .env file if needed
  2. Install Ollama if not already installed: https://ollama.ai
  3. Pull the LLM model: ollama pull qwen2.5:7b
  4. Verify your installation: curllm-doctor
```

---

### `curllm-doctor`

Diagnostic tool that verifies your curllm installation and checks all dependencies.

**Usage:**
```bash
curllm-doctor
```

**What it checks:**
1. ✓ Python version (3.10+)
2. ✓ Curllm package installation and version
3. ✓ All Python dependencies (Flask, Playwright, etc.)
4. ✓ Playwright browsers
5. ⚠ Required directories
6. ⚠ Configuration file (.env)
7. ⚠ Ollama installation and service status
8. ⚠ Port availability (8000 for Curllm API)
9. ⚠ Tesseract OCR (for CAPTCHA solving)
10. ✓ Curllm core modules

Legend:
- ✓ Critical checks (must pass)
- ⚠ Optional checks (warnings if not available)

**When to use:**
- After running `curllm-setup`
- When troubleshooting installation issues
- Before starting development
- After system updates

**Example output:**
```
======================================================================
  Curllm Installation Verification
======================================================================

Running diagnostics...

Checking Python version... ✓ OK
  Python 3.10.12
Checking curllm package... ✓ OK
  Version: 1.0.22
Checking Python dependencies... ✓ OK
Checking Playwright browsers... ✓ OK
  Playwright Version 1.40.0
Checking required directories... ✓ OK
Checking .env configuration... ✓ OK
Checking Ollama installation... ✓ OK
Checking Ollama service... ✓ OK
  Available models: qwen2.5:7b, llama2, mistral
Checking Curllm API port (8000)... ⚠ WARNING (port 8000 not in use)
Checking Tesseract OCR... ✓ OK
  tesseract 5.3.0
Checking curllm_core modules... ✓ OK

======================================================================
  Summary
======================================================================

Total checks: 10
  ✓ Passed:   9
  ⚠ Warnings: 1

⚠ Installation is functional but some optional features may be limited.

Recommended actions:
  1. Run: curllm-setup
  2. Install Ollama if needed: https://ollama.ai
  3. Install Tesseract OCR if needed

✓ All checks passed! Your installation is ready to use.

Start the server with:
  python -m curllm_core.server
```

---

## Quick Start Workflow

```bash
# 1. Install curllm
pip install -U curllm

# 2. Run post-installation setup
curllm-setup

# 3. Verify installation
curllm-doctor

# 4. Configure (optional)
nano .env  # Edit configuration if needed

# 5. Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# 6. Pull LLM model
ollama pull qwen2.5:7b

# 7. Start the server
python -m curllm_core.server
```

---

## Troubleshooting

### `curllm-setup` fails with "Permission denied"

**Solution:** Make sure you have write permissions in the current directory, or run in a directory where you have proper permissions.

### `curllm-doctor` shows "Playwright browsers" warning

**Solution:** Run:
```bash
playwright install chromium
```

### `curllm-doctor` shows "Ollama not installed"

**Solution:** Install Ollama:
```bash
# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# macOS
brew install ollama

# Or download from https://ollama.ai
```

### `curllm-doctor` shows "Tesseract OCR not installed"

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Fedora
sudo dnf install tesseract
```

### Commands not found after installation

**Solution:** Make sure your Python scripts directory is in PATH:
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# Then reload
source ~/.bashrc
```

---

## Exit Codes

Both commands return standard exit codes:

- `0` - Success (all critical checks passed)
- `1` - Failure (critical checks failed or setup incomplete)

This allows integration into CI/CD pipelines:
```bash
if curllm-doctor; then
    echo "Installation verified!"
    python -m curllm_core.server
else
    echo "Installation issues detected"
    exit 1
fi
```

---

## Integration with Package Manager

These commands are automatically installed as console scripts when you install curllm via pip. They are managed by setuptools and can be found in your Python environment's `bin/` or `Scripts/` directory.

### Developer Mode

When developing curllm itself, install in editable mode:
```bash
pip install -e .
```

This allows you to modify the CLI code and test changes immediately without reinstalling.

---

## See Also

- [README.md](../README.md) - Main project documentation
- [Installation Guide](../README.md#installation) - Detailed installation instructions
- [Configuration Guide](../README.md#configuration) - Environment variables and settings
