# curllm - Browser Automation with Local LLM

<div align="center">
  <h3>🤖 Intelligent Browser Automation using 8GB GPU-Compatible Local LLMs</h3>
  <p>
    <strong>curllm</strong> combines the power of local LLMs with browser automation for intelligent web scraping, 
    form filling, and workflow automation - all running on your local machine with complete privacy.
  </p>
</div>

## ✨ Features

- **🧠 Local LLM Integration**: Run on 8GB GPUs with models like Qwen 2.5, Mistral, or Llama
- **👁️ Visual Analysis**: Computer vision for CAPTCHA detection and page understanding  
- **🥷 Stealth Mode**: Advanced anti-bot detection bypass techniques
- **🔍 BQL Support**: Browser Query Language for structured data extraction
- **🎯 Smart Navigation**: AI-driven page interaction and form filling
- **🔒 Privacy-First**: Everything runs locally - no data leaves your machine
- **⚡ GPU Optimized**: Quantized models for efficient inference on consumer GPUs

## 📋 Requirements

### Minimum Hardware
- **GPU**: NVIDIA GPU with 6-8GB VRAM (RTX 3060, RTX 4060, etc.)
- **RAM**: 16GB system memory
- **Storage**: 10GB free space
- **CPU**: Modern processor (Intel i5/AMD Ryzen 5 or better)

### Software
- Python 3.11+ (tested on 3.13)
- Docker (optional, for Browserless features)
- CUDA toolkit (for GPU acceleration)

## 🚀 Quick Start

```shell
make install
```

```shell
Installing curllm dependencies...
╔════════════════════════════════════════════╗
║       curllm Installation Script           ║
║   Browser Automation with Local LLM        ║
╚════════════════════════════════════════════╝

[1/7] Checking system requirements...
✓ Python 3.13.5 found
✓ GPU detected: NVIDIA GeForce RTX 4060, 8188 MiB
✓ Docker is installed

[2/7] Installing Ollama...
✓ Ollama is already installed

...
```

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/softreck/curllm.git
cd curllm

# Run automatic installer
chmod +x install.sh
./install.sh

# Or manual installation
pip install -r requirements.txt
ollama pull qwen2.5:7b
```


### 2. Start Services

```bash
# Start all required services (auto-selects free ports and saves them to .env)
curllm --start-services

# Check status (reads ports from .env)
curllm --status
```

### 3. Basic Usage

```bash
# Simple extraction (ensure services are running)
curllm "https://example.com" -d "extract all links"

# Form automation with authentication
curllm -X POST --visual --stealth \
  -d '{"instruction": "Login and download invoice", 
       "credentials": {"user": "john@example.com", "pass": "secret"}}' \
  https://app.example.com

# BQL query for structured data
curllm --bql -d 'query {
  page(url: "https://news.ycombinator.com") {
    title
    links: select(css: "a.storylink, a.titlelink") { text url: attr(name: "href") }
  }
}'
```

## 🎯 Examples

### Extract Data from Dynamic Pages

```bash
curllm --visual "https://shop.com" \
  -d "Find all products under $50 and extract names, prices, and images"
```

### Handle 2FA Authentication

```bash
curllm --visual --captcha \
  -d '{"task": "login", "username": "user@example.com", 
       "password": "pass", "2fa_code": "123456"}' \
  https://secure-app.com
```

### Automated Form Filling with Honeypot Detection

```bash
curllm --stealth --visual \
  -d "Fill contact form: name=John Doe, email=john@example.com, message=Hello" \
  https://www.prototypowanie.pl/kontakt/
```

### Complex Workflow Automation

```bash
curllm -X POST --visual --stealth --captcha \
  -d '{
    "workflow": [
      {"action": "navigate", "url": "https://portal.example.com"},
      {"action": "login", "username": "user", "password": "pass"},
      {"action": "click", "text": "Reports"},
      {"action": "download", "pattern": "*.pdf"},
      {"action": "extract_table", "format": "csv"}
    ]
  }'
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# The installer creates .env (from .env.example). Key variables:
# Ports and hosts (auto-maintained when starting services)
CURLLM_API_PORT=8000
CURLLM_API_HOST=http://localhost:8000
CURLLM_OLLAMA_PORT=11434
CURLLM_OLLAMA_HOST=http://localhost:11434

# Model and runtime
CURLLM_MODEL=qwen2.5:7b
CURLLM_MAX_STEPS=20
CURLLM_NUM_CTX=8192
CURLLM_NUM_PREDICT=512
CURLLM_TEMPERATURE=0.3
CURLLM_TOP_P=0.9
CURLLM_DEBUG=false

# Browserless (optional)
CURLLM_BROWSERLESS=false
BROWSERLESS_URL=ws://localhost:3000
BROWSERLESS_PORT=3000
REDIS_PORT=6379

# CAPTCHA (optional)
CAPTCHA_API_KEY=
```

### Configuration File

Edit `~/.config/curllm/config.yml`:

```yaml
# Model settings
model: qwen2.5:7b
ollama_host: http://localhost:11434
temperature: 0.3
top_p: 0.9

# Browser settings
max_steps: 20
screenshot_dir: /tmp/curllm_screenshots
headless: true

# Features
visual_mode: false
stealth_mode: false
captcha_solver: false
use_bql: false

# Performance
num_ctx: 8192
num_predict: 512
gpu_layers: 35
```

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# Scale browserless instances
docker-compose up -d --scale browserless=3

# View logs
docker-compose logs -f curllm-api
```

### Standalone Docker

```bash
# Build image
docker build -t curllm:latest .

# Run container
docker run -d \
  --name curllm \
  --gpus all \
  -p 8000:8000 \
  -v ~/.ollama:/root/.ollama \
  curllm:latest
```

## 🎮 Advanced Features

### Visual Mode

Visual mode enables screenshot analysis for:
- CAPTCHA detection
- Dynamic content verification  
- Visual element interaction
- Honeypot field detection

```bash
curllm --visual "https://example.com" -d "Click the red button"
```

### Stealth Mode

Bypasses common bot detection:
- Removes automation indicators
- Randomizes behavior patterns
- Mimics human interactions
- Custom user agents and headers

```bash
curllm --stealth "https://protected-site.com" -d "Extract data"
```

### BQL (Browser Query Language)

GraphQL-like syntax for structured extraction:

```graphql
query {
  page(url: "https://example.com") {
    title
    meta: select(css: "meta[property^='og:']") {
      property: attr(name: "property")
      content: attr(name: "content")
    }
    links: select(css: "a[href^='http']") {
      text
      url: attr(name: "href")
    }
  }
}
```

## 📊 Performance Benchmarks

| Model | VRAM Usage | Inference Speed | Tool-calling F1 | Avg Response Time |
|-------|------------|-----------------|-----------------|-------------------|
| Qwen 2.5 7B | 6.8GB | 40 tok/sec | 93.3% | 8-12 sec |
| Mistral 7B | 6.5GB | 45 tok/sec | 89.1% | 7-10 sec |
| Llama 3.2 8B | 7.2GB | 35 tok/sec | 87.5% | 10-15 sec |
| Phi-3 Mini | 3.8GB | 60 tok/sec | 82.3% | 5-8 sec |

## 🛠️ API Reference

### REST Endpoints

```http
POST /api/execute
Content-Type: application/json

{
  "url": "https://example.com",
  "data": "instruction or query",
  "visual_mode": true,
  "stealth_mode": false,
  "captcha_solver": false,
  "use_bql": false
}
```

### Python Client

```python
from curllm import CurllmClient

client = CurllmClient(
    model="qwen2.5:7b",
    visual_mode=True
)

result = await client.execute(
    url="https://example.com",
    instruction="Extract all product prices"
)

print(result.data)
```

## 🐛 Troubleshooting

### Common Issues

**Out of Memory (OOM)**
```bash
# Reduce context length
export CURLLM_NUM_CTX=4096

# Use smaller model
ollama pull phi3:mini
```

**Slow Response**
```bash
# Check GPU utilization
nvidia-smi

# Use quantized model
ollama pull qwen2.5:7b-q4_K_M
```

**CAPTCHA Detection Issues**
```bash
# Enable visual mode
curllm --visual --captcha ...

# Increase screenshot quality
export SCREENSHOT_QUALITY=100
```

## 🗺️ Roadmap

- [ ] Multi-agent orchestration
- [ ] Fine-tuning interface for domain-specific tasks  
- [ ] WebSocket support for real-time automation
- [ ] Integration with Selenium Grid
- [ ] Voice-guided automation
- [ ] Mobile browser support
- [ ] Distributed scraping with Ray
- [ ] Custom model training pipeline

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/softreck/curllm.git
cd curllm
pip install -e .
pytest tests/
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai) for local LLM serving
- [Browser-Use](https://github.com/gregpr07/browser-use) for browser automation
- [Playwright](https://playwright.dev) for browser control
- [LangChain](https://langchain.com) for LLM orchestration
- [Browserless](https://browserless.io) for headless browser infrastructure

## 📞 Support

- 📧 Email: support@softreck.com
- 💬 Discord: [Join our server](https://discord.gg/curllm)
- 🐛 Issues: [GitHub Issues](https://github.com/softreck/curllm/issues)
- 📚 Docs: [Documentation](https://docs.curllm.io)

---

<div align="center">
  <p>Built with ❤️ by <a href="https://softreck.com">Softreck</a></p>
  <p>⭐ Star us on GitHub!</p>
</div>
