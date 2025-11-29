# LLM Providers Examples

Examples showing how to use curllm with different LLM providers.

## Supported Providers

curllm supports multiple LLM providers via [litellm](https://docs.litellm.ai/docs/providers):

| Provider | Format | Environment Variable |
|----------|--------|---------------------|
| Ollama (local) | `ollama/qwen2.5:7b` | - |
| OpenAI | `openai/gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-3-haiku-20240307` | `ANTHROPIC_API_KEY` |
| Gemini | `gemini/gemini-2.0-flash` | `GEMINI_API_KEY` |
| Groq | `groq/llama3-70b-8192` | `GROQ_API_KEY` |
| DeepSeek | `deepseek/deepseek-chat` | `DEEPSEEK_API_KEY` |

## Examples

### Basic Usage

```python
from curllm_core import CurllmExecutor, LLMConfig

# Default: local Ollama
executor = CurllmExecutor()

# OpenAI (auto-detects OPENAI_API_KEY)
executor = CurllmExecutor(LLMConfig(provider="openai/gpt-4o-mini"))

# Explicit API token
executor = CurllmExecutor(LLMConfig(
    provider="anthropic/claude-3-haiku-20240307",
    api_token="sk-ant-..."
))
```

### Run Examples

```bash
# Set your API key first
export OPENAI_API_KEY="sk-..."

# Run example
python examples/llm-providers/openai_example.py
python examples/llm-providers/multi_provider_benchmark.py
```

## Files

- `openai_example.py` - OpenAI GPT-4o usage
- `anthropic_example.py` - Anthropic Claude usage
- `gemini_example.py` - Google Gemini usage
- `groq_example.py` - Groq (fast Llama) usage
- `multi_provider_benchmark.py` - Compare providers
- `auto_detect_provider.py` - Auto-detect from environment

## Related

- [LLMConfig Documentation](../../docs/v2/README.md#-llm-providers)
- [Main Examples](../README.md)
