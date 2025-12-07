# curllm Documentation v2

Current documentation for curllm - Browser Automation with Multi-Provider LLM support.

## 🚀 Quick Start

```bash
# Install
pip install curllm

# Extract data (uses local Ollama by default)
curllm "https://example.com" -d "Extract all links"

# Use cloud provider (auto-detects API key from environment)
CURLLM_LLM_PROVIDER=openai/gpt-4o-mini curllm "https://example.com" -d "Extract products"
```

## 🤖 LLM Providers

curllm supports multiple LLM providers via **litellm**:

| Provider | Format | Environment Variable |
|----------|--------|---------------------|
| Ollama (local) | `ollama/qwen2.5:7b` | - |
| OpenAI | `openai/gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-3-haiku-20240307` | `ANTHROPIC_API_KEY` |
| Gemini | `gemini/gemini-2.0-flash` | `GEMINI_API_KEY` |
| Groq | `groq/llama3-70b-8192` | `GROQ_API_KEY` |
| DeepSeek | `deepseek/deepseek-chat` | `DEEPSEEK_API_KEY` |

```python
from curllm_core import CurllmExecutor, LLMConfig

# Auto-detects API key from OPENAI_API_KEY
executor = CurllmExecutor(LLMConfig(provider="openai/gpt-4o-mini"))

# Or specify explicitly
executor = CurllmExecutor(LLMConfig(
    provider="anthropic/claude-3-haiku-20240307",
    api_token="sk-ant-..."
))
```

## 📁 Documentation Structure

```
docs/v2/
├── architecture/                  # System architecture docs
│   ├── ARCHITECTURE.md            # Core architecture
│   ├── DSL_SYSTEM.md              # 🆕 Strategy-based extraction
│   ├── ATOMIC_QUERY_SYSTEM.md     # DOM Toolkit
│   ├── STREAMWARE.md              # Component system
│   ├── LLM.md                     # LLM integration
│   └── COMPONENTS.md              # Component reference
├── features/                      # Feature documentation
│   ├── FORM_FILLING.md            # Form automation
│   ├── ITERATIVE_EXTRACTOR.md     # Atomic extraction
│   ├── HIERARCHICAL_PLANNER.md    # 3-level LLM optimization
│   └── VISION_FORM_ANALYSIS.md    # Visual form detection
├── guides/                        # User guides
│   ├── Installation.md            # Setup instructions
│   ├── EXAMPLES.md                # Code examples
│   ├── Docker.md                  # Docker deployment
│   └── Troubleshooting.md
└── api/                           # API reference
    ├── API.md                     # REST API
    └── CLI_COMMANDS.md            # CLI reference
```

## 🆕 Recent Additions

### December 2024

- **[DSL System](architecture/DSL_SYSTEM.md)** - Strategy-based extraction with auto-learning
  - YAML strategy files for reusable extraction recipes
  - SQLite Knowledge Base tracks algorithm success per domain
  - Automatic fallback algorithms when primary fails
  - 80% reduction in LLM calls through pure JS DOM Toolkit

- **[DOM Toolkit](architecture/ATOMIC_QUERY_SYSTEM.md)** - Pure JavaScript atomic queries
  - Zero LLM calls for DOM analysis
  - Statistical container detection
  - Pattern recognition and selector generation

### November 2024

- **[Hierarchical Planner](features/HIERARCHICAL_PLANNER.md)** - Revolutionary 3-level LLM optimization
  - 87% reduction in token usage
  - Interactive detail requesting
  - Automatic threshold-based activation

- **[Form Filling Guide](features/FORM_FILLING.md)** - Complete form automation documentation
  - Priority-based value handling
  - Automatic error detection
  - Email validation fallbacks

## 📂 Code Examples

See the [examples/](../../examples/) directory for runnable code:

| Example | Description | Link |
|---------|-------------|------|
| **LLM Providers** | Use OpenAI, Anthropic, Gemini, Groq | [examples/llm-providers/](../../examples/llm-providers/) |
| **Product Extraction** | Extract product data | [examples/extraction/products/](../../examples/extraction/products/) |
| **Form Filling** | Automate contact forms | [examples/forms/contact/](../../examples/forms/contact/) |
| **BQL Queries** | Browser Query Language | [examples/bql/](../../examples/bql/) |
| **Streamware** | Component pipelines | [examples/streamware/](../../examples/streamware/) |
| **API Clients** | Node.js, PHP clients | [examples/api-clients/](../../examples/api-clients/) |

## 🔗 External Links

- [Main Project README](../../README.md)
- [Examples Directory](../../examples/)
- [GitHub Repository](https://github.com/wronai/curllm)
- [TODO List](../../TODO.md)

## 📝 Contributing to Documentation

Documentation improvements are welcome! To contribute:

1. Edit the relevant `.md` file in `docs/`
2. Ensure navigation links are maintained
3. Test all internal links
4. Submit a pull request

### Documentation Standards

- **Navigation**: Every page should have header and footer navigation
- **Formatting**: Use clear headings, code blocks, and examples
- **Links**: Always use relative links for internal documentation
- **Examples**: Include practical, runnable code samples

## 💡 Tips

- Use browser's search (Ctrl+F / Cmd+F) to find topics quickly
- Check the [INDEX](INDEX.md) for a complete documentation map
- Start with [Examples](EXAMPLES.md) if you learn by doing
- Refer to [Troubleshooting](Troubleshooting.md) when encountering issues

---

**[📚 Documentation Index](INDEX.md)** | **[⬆️ Back to Top](#curllm-documentation)** | **[Main README](../README.md)**
