# Basic curllm Examples

Simple command-line examples using curl and curllm CLI.

## Contents

| File | Description |
|------|-------------|
| `curl_contact_form.sh` | Fill contact form using curl |
| `curl_product_search.sh` | Search products using curl |
| `curl_wp_login.sh` | WordPress login automation |
| `curllm_contact_form.sh` | curllm CLI form example |
| `curllm_product_search.sh` | curllm CLI extraction |
| `curllm_wp_login.sh` | curllm CLI login |

## Quick Start

```bash
# Make scripts executable
chmod +x *.sh

# Run product search
./curllm_product_search.sh

# Fill contact form
./curllm_contact_form.sh
```

## Requirements

- curllm installed: `pip install curllm`
- Ollama running: `ollama serve`
- Model pulled: `ollama pull qwen2.5:7b`
