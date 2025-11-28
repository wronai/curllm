# CLI Commands Usage Guide

This guide shows how to use the `curllm-setup`, `curllm-doctor`, and `curllm-web` commands after installing curllm via pip.

## Installation

```bash
pip install -U curllm
```

## Post-Installation Setup

After installing curllm, run the setup command to configure your environment:

```bash
curllm-setup
```

### What `curllm-setup` Does

1. **Checks Python Version** - Ensures Python 3.10+ is installed
2. **Creates Directories** - Sets up required directories:
   - `logs/` - For application logs
   - `screenshots/` - For captured screenshots
   - `downloads/` - For downloaded files
   - `workspace/` - For temporary workspace files
3. **Creates Configuration** - Sets up `.env` file with default settings
4. **Installs Playwright Browsers** - Downloads Chromium for browser automation
5. **Checks Ollama** - Verifies if Ollama is installed for LLM features

### Example Output

```
======================================================================
  Curllm Post-Installation Setup
======================================================================

[1/5] Checking Python version
✓ Python 3.13.7

[2/5] Creating necessary directories
✓ Created directory: logs/
✓ Created directory: screenshots/
✓ Created directory: downloads/
✓ Created directory: workspace/

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

Start the server with:
  python -m curllm_core.server
```

## Verify Installation

After setup, verify everything is working correctly:

```bash
curllm-doctor
```

### What `curllm-doctor` Checks

The doctor command performs comprehensive diagnostics:

#### Critical Checks (Must Pass)
- ✓ Python version (3.10+)
- ✓ Curllm package installation
- ✓ Python dependencies (Flask, Playwright, etc.)
- ✓ Curllm core modules

#### Optional Checks (Warnings Only)
- ⚠ Playwright browsers
- ⚠ Required directories
- ⚠ Configuration file (.env)
- ⚠ Ollama installation and service
- ⚠ Port availability (8000)
- ⚠ Tesseract OCR (for CAPTCHA)

### Example Output

```
======================================================================
  Curllm Installation Verification
======================================================================

Running diagnostics...

Checking Python version... ✓ OK
  Python 3.13.7
Checking curllm package... ✓ OK
  Version: 1.0.22
Checking Python dependencies... ✓ OK
Checking Playwright browsers... ✓ OK
  Playwright Version 1.56.0
Checking required directories... ✓ OK
Checking .env configuration... ✓ OK
Checking Ollama installation... ✓ OK
Checking Ollama service... ✓ OK
  Available models: qwen2.5:7b, llama2, mistral
Checking Curllm API port (8000)... ✓ OK
  Service appears to be running on port 8000
Checking Tesseract OCR... ✓ OK
  tesseract 5.5.0
Checking curllm_core modules... ✓ OK

======================================================================
  Summary
======================================================================

Total checks: 10
  ✓ Passed:   10

✓ All checks passed! Your installation is ready to use.

Start the server with:
  python -m curllm_core.server
```

## Complete Workflow

Here's the recommended workflow for new installations:

```bash
# 1. Install curllm from PyPI
pip install -U curllm

# 2. Run post-installation setup
curllm-setup

# 3. Verify installation
curllm-doctor

# 4. (Optional) Edit configuration
nano .env

# 5. Install Ollama if needed
curl -fsSL https://ollama.ai/install.sh | sh

# 6. Pull required LLM model
ollama pull qwen2.5:7b

# 7. Start the server
python -m curllm_core.server
```

## Troubleshooting

### Commands Not Found

If the commands are not found after installation:

```bash
# Make sure your Python scripts directory is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Reload your shell
source ~/.bashrc  # or ~/.zshrc
```

### Playwright Installation Issues

If Playwright browser installation fails:

```bash
# Manually install Playwright browsers
python -m playwright install chromium

# Or install all browsers
python -m playwright install
```

### Ollama Not Found

Install Ollama for LLM features:

```bash
# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# macOS
brew install ollama

# Or download from https://ollama.ai
```

### Tesseract OCR Not Found

Install Tesseract for CAPTCHA solving:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Fedora
sudo dnf install tesseract
```

## Development Mode

If you're developing curllm itself, install in editable mode:

```bash
# Clone the repository
git clone https://github.com/wronai/curllm.git
cd curllm

# Install in editable mode
pip install -e .

# Now the commands will reflect code changes immediately
curllm-setup
curllm-doctor
```

## CI/CD Integration

Both commands return standard exit codes for automation:

```bash
#!/bin/bash
set -e

# Install
pip install curllm

# Setup
if ! curllm-setup; then
    echo "Setup failed"
    exit 1
fi

# Verify
if ! curllm-doctor; then
    echo "Installation verification failed"
    exit 1
fi

# Start server
python -m curllm_core.server
```

## Exit Codes

- `0` - Success (all critical checks passed)
- `1` - Failure (critical checks failed or setup incomplete)

## Getting Help

For more information:

- **Main Documentation**: See [README.md](README.md)
- **Detailed CLI Guide**: See [docs/CLI_COMMANDS.md](docs/CLI_COMMANDS.md)
- **Issues**: https://github.com/wronai/curllm/issues
- **Installation Guide**: See README.md#installation
