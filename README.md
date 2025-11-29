<p align="center">
  <img src="docs/curllm.png" alt="curllm logo" width="400">
</p>

<h1 align="center">curllm = curl + LLM</h1>

<p align="center">
  <strong>Intelligent Browser Automation with Local LLMs</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/curllm/"><img src="https://img.shields.io/pypi/v/curllm?color=blue&label=PyPI" alt="PyPI"></a>
  <a href="https://pypi.org/project/curllm/"><img src="https://img.shields.io/pypi/pyversions/curllm" alt="Python"></a>
  <a href="https://github.com/wronai/curllm/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License"></a>
  <a href="https://github.com/wronai/curllm/stargazers"><img src="https://img.shields.io/github/stars/wronai/curllm?style=social" alt="Stars"></a>
  <a href="https://github.com/wronai/curllm/issues"><img src="https://img.shields.io/github/issues/wronai/curllm" alt="Issues"></a>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-examples">Examples</a> •
  <a href="docs/INDEX.md">Documentation</a> •
  <a href="docs/API.md">API</a>
</p>

---

## 🎯 What is curllm?

**curllm** is a powerful CLI tool that combines browser automation with local LLMs (like Ollama's Qwen, Llama, Mistral) to intelligently extract data, fill forms, and automate web workflows - all running **locally** on your machine with **complete privacy**.

```bash
# Extract products with prices from any e-commerce site
curllm "https://shop.example.com" -d "Find all products under $100"

# Fill contact forms automatically
curllm --stealth "https://example.com/contact" -d "Fill form: name=John, email=john@example.com"

# Extract all emails from a page
curllm "https://example.com" -d "extract all email addresses"
```

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Local LLM** | Works with 8GB GPUs (Qwen 2.5, Llama 3, Mistral) |
| 🎯 **Smart Extraction** | LLM-guided DOM analysis - no hardcoded selectors |
| 📝 **Form Automation** | Auto-fill forms with intelligent field mapping |
| 🥷 **Stealth Mode** | Bypass anti-bot detection |
| 👁️ **Visual Mode** | See browser actions in real-time |
| 🔍 **BQL Support** | Browser Query Language for structured queries |
| 📊 **Export Formats** | JSON, CSV, HTML, XLS output |
| 🔒 **Privacy-First** | Everything runs locally - no cloud APIs needed |

## 🚀 Quick Start

### Installation

```bash
pip install -U curllm
curllm-setup      # One-time setup (installs Playwright browsers)
curllm-doctor     # Verify installation
```

### Requirements

- **Python** 3.10+
- **GPU**: NVIDIA with 6-8GB VRAM (RTX 3060/4060) or CPU mode
- **Ollama**: For local LLM inference

```bash
# Install Ollama (if not installed)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5:7b
```

## 📖 Examples

### Extract Data

```bash
# Extract all links
curllm "https://example.com" -d "extract all links"

# Extract emails
curllm "https://example.com/contact" -d "extract all email addresses"
# Output: {"emails": ["info@example.com", "sales@example.com"]}

# Extract products with price filter
curllm --stealth "https://shop.example.com" -d "Find all products under 500zł"
```

### Form Automation

```bash
# Fill contact form
curllm --visual --stealth "https://example.com/contact" \
  -d "Fill form: name=John Doe, email=john@example.com, message=Hello"

# Login automation
curllm --visual "https://app.example.com/login" \
  -d '{"instruction":"Login", "credentials":{"user":"admin", "pass":"secret"}}'
```

### Export Results

```bash
# Export to CSV
curllm "https://example.com" -d "extract all products" --csv -o products.csv

# Export to HTML
curllm "https://example.com" -d "extract all links" --html -o links.html

# Export to Excel
curllm "https://example.com" -d "extract all data" --xls -o data.xlsx
```

### Screenshots

```bash
# Take screenshot
curllm "https://example.com" -d "screenshot"

# Visual mode (watch browser)
curllm --visual "https://example.com" -d "extract all links"
```

### BQL Queries

```bash
curllm --bql -d 'query {
  page(url: "https://news.ycombinator.com") {
    title
    links: select(css: "a.titlelink") { text url: attr(name: "href") }
  }
}'
```

## 🌐 Web Interface

```bash
curllm-web start   # Start web UI at http://localhost:5000
curllm-web status  # Check status
curllm-web stop    # Stop server
```

Features:
- 🎨 Modern responsive UI
- 📝 19 pre-configured prompts
- 📊 Real-time log viewer
- 📤 File upload support

## 🔧 Configuration

Environment variables (`.env`):

```bash
CURLLM_MODEL=qwen2.5:7b          # LLM model
CURLLM_OLLAMA_HOST=http://localhost:11434
CURLLM_HEADLESS=true             # Run browser headlessly
CURLLM_STEALTH_MODE=false        # Anti-detection
CURLLM_LOCALE=en-US              # Browser locale
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      curllm CLI                         │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │  Planner    │  │  Extractor  │  │  Form Filler    │ │
│  │ (LLM-based) │  │ (Dynamic)   │  │ (Orchestrated)  │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │           Playwright Browser Engine             │   │
│  │    (Chromium with Stealth & Anti-Detection)    │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │              Ollama / LiteLLM                   │   │
│  │   (Local LLM: Qwen, Llama, Mistral, GPT, etc)  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 🤝 Multi-Provider LLM Support

curllm supports multiple LLM providers via LiteLLM:

```python
from curllm_core import LLMConfig

# OpenAI
config = LLMConfig(provider="openai/gpt-4o-mini")

# Anthropic
config = LLMConfig(provider="anthropic/claude-3-haiku-20240307")

# Google Gemini
config = LLMConfig(provider="gemini/gemini-2.0-flash")

# Local Ollama (default)
config = LLMConfig(provider="ollama/qwen2.5:7b")
```

## 📚 Documentation

- **[📖 Full Documentation](docs/INDEX.md)**
- **[⚙️ Installation Guide](docs/Installation.md)**
- **[📝 Examples & Tutorials](docs/EXAMPLES.md)**
- **[🔌 API Reference](docs/API.md)**
- **[🛠️ Environment Config](docs/Environment.md)**
- **[❓ Troubleshooting](docs/Troubleshooting.md)**

## 🧪 Development

```bash
# Clone and install
git clone https://github.com/wronai/curllm.git
cd curllm
make install

# Run tests
make test

# Run with Docker
docker compose up -d
```

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE)

## 🙏 Acknowledgments

Built with:
- [Playwright](https://playwright.dev/) - Browser automation
- [Ollama](https://ollama.ai/) - Local LLM inference
- [LiteLLM](https://github.com/BerriAI/litellm) - Multi-provider LLM support
- [Flask](https://flask.palletsprojects.com/) - Web framework

---

<p align="center">
  <strong>⭐ Star this repo if you find it useful!</strong>
</p>

<p align="center">
  Made with ❤️ by <a href="https://github.com/wronai">wronai</a>
</p>
