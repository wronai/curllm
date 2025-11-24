# Docker

Docs: [Home](../README.md) | [Installation](Installation.md) | [Environment](Environment.md) | [API](API.md) | [Playwright+BQL](Playwright_BQL.md) | [Examples](EXAMPLES.md) | [Docker](Docker.md) | [Devbox](Devbox.md) | [Troubleshooting](Troubleshooting.md) | [Instrukcja](../INSTRUKCJA.md)

## Docker Compose

```bash
# Start all services
docker compose up -d

# Scale browserless
docker compose up -d --scale browserless=3

# Logs
docker compose logs -f curllm-api
```

Services:

- browserless: Headless Chrome with stealth
- ollama: Local LLM server (GPU)
- redis: Cache/session store
- curllm-api: Flask API using Ollama & (optionally) Browserless

## Standalone build

```bash
# Build image
docker build -t curllm:latest .

# Run
docker run -d \
  --name curllm \
  --gpus all \
  -p 8000:8000 \
  -v ~/.ollama:/root/.ollama \
  curllm:latest
```

## Notes

- For GPU passthrough ensure NVIDIA Container Toolkit is installed.
- The API health endpoint: http://localhost:8000/health
