# curllm Examples

This directory contains organized examples demonstrating curllm capabilities.

## 📁 Structure

```
examples/
├── extraction/              # Data extraction examples
│   ├── products/           # Product scraping
│   └── links/              # Link extraction
├── forms/                   # Form automation examples
│   ├── contact/            # Contact form filling
│   └── login/              # Login automation
├── llm-providers/           # Multi-provider LLM examples
├── bql/                     # Browser Query Language examples
├── streamware/              # Streamware component examples
└── api-clients/             # API client examples (Node.js, PHP, etc.)
```

## 🚀 Quick Start

### 1. Extract Links (Simplest Example)

```bash
# Using CLI
curllm "https://example.com" -d "Extract all links"

# Using Python
python examples/extraction/links/extract_links.py
```

### 2. Extract Products

```bash
# CLI with price filter
curllm "https://shop.example.com/products" -d "Extract products under $100"

# Python
python examples/extraction/products/extract_products.py
```

### 3. Fill Contact Form

```bash
# CLI
curllm "https://example.com/contact" -d "Fill form: name=John Doe, email=john@example.com"

# Python
python examples/forms/contact/fill_form.py
```

### 4. Use Different LLM Providers

```python
from curllm_core import CurllmExecutor, LLMConfig

# OpenAI
executor = CurllmExecutor(LLMConfig(provider="openai/gpt-4o-mini"))

# Anthropic
executor = CurllmExecutor(LLMConfig(provider="anthropic/claude-3-haiku-20240307"))

# Gemini
executor = CurllmExecutor(LLMConfig(provider="gemini/gemini-2.0-flash"))

# Local Ollama (default)
executor = CurllmExecutor(LLMConfig(provider="ollama/qwen2.5:7b"))
```

## 📖 Example Projects

| Project | Description | Files |
|---------|-------------|-------|
| [extraction/products](extraction/products/) | Product data extraction | Python, Bash |
| [extraction/links](extraction/links/) | Link extraction | Python, Bash |
| [forms/contact](forms/contact/) | Contact form filling | Python, Bash |
| [forms/login](forms/login/) | Login automation | Python, Bash |
| [llm-providers](llm-providers/) | Multi-provider LLM usage | Python |
| [bql](bql/) | Browser Query Language | Python, Bash |
| [streamware](streamware/) | Streamware components | Python |
| [api-clients](api-clients/) | API clients (Node.js, PHP) | JS, PHP |

## 🔗 Related Documentation

- [Main README](../README.md)
- [Installation Guide](../docs/v2/guides/Installation.md)
- [LLM Providers](../docs/v2/README.md#-llm-providers)
- [API Reference](../docs/v2/api/API.md)
- [Streamware Architecture](../docs/v2/architecture/STREAMWARE.md)
