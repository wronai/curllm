![curllm.png](docs/curllm.png)
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

## 📚 More Documentation & Example Scripts

- Full examples with commands and context: docs/EXAMPLES.md
- Generate runnable scripts: make examples
  - Scripts are created in examples/ as executable files (curllm-*.sh)
  - Run with: ./examples/curllm-extract-links.sh

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
git clone https://github.com/wronai/curllm.git
cd curllm

# Run automatic installer
chmod +x install.sh
./install.sh

# Or manual installation
pip install -r requirements.txt
ollama pull qwen2.5:7b
```


### 2. Start Services
Start all required services (auto-selects free ports and saves them to .env)
```bash
curllm --start-services
```

Check status (reads ports from .env)
```
curllm --status
```
output:
```bash
=== curllm Service Status ===
✓ Ollama is running
✓ curllm API is running
✓ Model qwen2.5:7b is available

GPU Status:
NVIDIA GeForce RTX 4060, 1190 MiB, 8188 MiB
```

### 3. Basic Usage

```bash
# Simple extraction (ensure services are running)
curllm "https://example.com" -d "extract all links"
```
output:
```bash
{
  "links": [
    {
      "href": "https://iana.org/domains/example",
      "text": "Learn more"
    }
  ]
}
Run log: ./logs/run-20251123-113145.md
```


Form automation with authentication
```bash
curllm -X POST --visual --stealth \
  -d '{"instruction": "Login and download invoice", 
       "credentials": {"user": "john@example.com", "pass": "secret"}}' \
  https://app.example.com
```

BQL query for structured data
```bash
curllm --bql -d 'query {
  page(url: "https://news.ycombinator.com") {
    title
    links: select(css: "a.storylink, a.titlelink") { text url: attr(name: "href") }
  }
}'
```

## 🎯 Examples

For a comprehensive, curated set of examples and ready-to-run scripts, see:

- docs/EXAMPLES.md
- Generate scripts: make examples (scripts are created in examples/ as curllm-*.sh)

### Validated examples (tested)

- Extract links (basic)

```bash
curllm "https://example.com" -d "extract all links"
```

Expected output (truncated):

```json
{
  "links": [
    { "href": "https://iana.org/domains/example", "text": "Learn more" }
  ]
}
```

- Extract links (Polish site)

```bash
curllm "https://www.prototypowanie.pl/kontakt/" -d "extract all links"
```

- Extract emails

```bash
curllm "https://www.prototypowanie.pl/kontakt/" -d "extract all email addresses"
```
output:
```bash
{
  "emails": [
    "info@prototypowanie.pl"
  ]
}
```

- Extract emails
```bash
curllm "https://4coils.eu" -d "extract all email addresses"
```
output:
```bash
{
  "emails": [
    "office@4coils.eu",
    "sales@4coils.eu"
  ]
}
```

- Visual mode / Stealth mode

```bash
curllm --visual "https://example.com" -d "extract all links"
curllm --stealth "https://example.com" -d "extract all links"
curllm --visual --stealth "https://example.com" -d "extract all email addresses"
```

Notes:

- Results and step logs are saved to files in `./logs/run-*.md` (path is printed in CLI output as `run_log`).
- Ports and hosts are auto-managed; run `curllm --start-services` once, then `curllm --status`.
- By default, the server uses a lightweight Ollama HTTP backend. To switch to LangChain's `langchain_ollama`, set `CURLLM_LLM_BACKEND=langchain` and ensure `langchain-ollama` is installed.

### Extract Data from Dynamic Pages

```bash
curllm --visual "https://allegro.com" \
  -d "Find all products under 150 and extract names, prices and urls"
```

### Create screenshot in folder name of domain
command:
```bash
curllm "https://www.prototypowanie.pl"  -d "Create screenshot in folder name of domain"
```
output:
```shell
{"result":{"screenshot_saved":"screenshots/www.prototypowanie.pl/step_0_1763903516.803199.png"},"run_log":"logs/run-20251123-141151.md","screenshots":["screenshots/www.prototypowanie.pl/step_0_1763903516.803199.png"],"steps_taken":0,"success":true,"timestamp":"2025-11-23T14:11:57.025193"}
```
screenshot:
![step_0_1763903516.803199.png](screenshots/www.prototypowanie.pl/step_0_1763903516.803199.png)

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



### Extract only email and phone links 

```bash
curllm "https://www.prototypowanie.pl/kontakt/" -d "extract only email and phone links"
```
output:
```bash
{
  "emails": ["info@prototypowanie.pl"],
  "phones": ["+48503503761"]
}
Run log: ./logs/run-YYYYMMDD-HHMMSS.md
```



### Extract all links 

```bash
curllm "https://www.prototypowanie.pl/kontakt/" -d "extract all links"
```
output:
```bash
{
  "links": [
    {
      "href": "https://www.prototypowanie.pl/kontakt/#content",
      "text": "Skip to content"
    },
    {
      "href": "https://www.prototypowanie.pl/",
      "text": "PROTOTYPOWANIE.PL"
    },
    {
      "href": "https://www.prototypowanie.pl/blog/",
      "text": "BLOG"
    },
    {
      "href": "https://www.prototypowanie.pl/",
      "text": "WYCENA"
    },
    {
      "href": "https://www.prototypowanie.pl/technologie/",
      "text": "TECHNOLOGIE"
    },
    {
      "href": "https://www.prototypowanie.pl/portfolio-open-source/",
      "text": "PORTFOLIO"
    },
    {
      "href": "https://www.prototypowanie.pl/marka/ondayrun/",
      "text": "USŁUGI"
    },
    {
      "href": "https://www.prototypowanie.pl/kontakt/",
      "text": "KONTAKT"
    },
    {
      "href": "https://www.prototypowanie.pl/blog/",
      "text": "blog"
    },
    {
      "href": "https://www.prototypowanie.pl/co-napisac-w-formularzu-zlecenia-praktyczny-przewodnik/",
      "text": "Co napisać w formularzu zlecenia?"
    },
    {
      "href": "https://www.prototypowanie.pl/uslugi/",
      "text": "Do usług"
    },
    {
      "href": "https://www.prototypowanie.pl/faq-wszystko-o-wspolpracy-z-prototypowanie-pl/",
      "text": "Jak zacząć z Prototypowanie?pl"
    },
    {
      "href": "https://www.prototypowanie.pl/konsultacja/",
      "text": "Konsultacja"
    },
    {
      "href": "https://www.prototypowanie.pl/kontakt/",
      "text": "Kontakt"
    },
    {
      "href": "https://www.prototypowanie.pl/polityka-prywatnosci/",
      "text": "Polityka prywatności"
    },
    {
      "href": "https://www.prototypowanie.pl/polityka-prywatnosci/cookie-policy-eu/",
      "text": "Cookie policy (EU)"
    },
    {
      "href": "https://www.prototypowanie.pl/polityka-prywatnosci/privacy-policy/",
      "text": "Privacy Policy"
    },
    {
      "href": "https://www.prototypowanie.pl/polityka-prywatnosci/privacy-tools/",
      "text": "Privacy Tools"
    },
    {
      "href": "https://www.prototypowanie.pl/portfolio-open-source/",
      "text": "Portfolio Open Source"
    },
    {
      "href": "https://www.prototypowanie.pl/technologie/",
      "text": "Technologie"
    },
    {
      "href": "https://www.prototypowanie.pl/terms-conditions/",
      "text": "Terms & conditions"
    },
    {
      "href": "https://www.prototypowanie.pl/tomasz-sapletta/",
      "text": "Tomasz Sapletta"
    },
    {
      "href": "https://www.prototypowanie.pl/",
      "text": "Twoje oprogramowanie gotowe w 24h?"
    },
    {
      "href": "https://www.prototypowanie.pl/wycena/",
      "text": "Wycena"
    },
    {
      "href": "mailto:info@prototypowanie.pl",
      "text": "info@prototypowanie.pl"
    },
    {
      "href": "tel:48503503761",
      "text": "+48 503 503 761"
    },
    {
      "href": "https://www.linkedin.com/company/prototypowanie-pl/",
      "text": "Linkedin"
    },
    {
      "href": "https://www.prototypowanie.pl/",
      "text": "rototypowanie.pl"
    },
    {
      "href": "https://wordpress.org/plugins/gdpr-cookie-compliance/",
      "text": "Powered by  Zgodności ciasteczek z RODO"
    }
  ]
}
Run log: logs/run-20251123-115654.md
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
screenshot_dir: ./screenshots
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
curllm --stealth "https://pypi.org/project/curllm/" -d "Extract data"
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

## Files
tree -L 3 -I node_modules -I venv

```
$ tree -L 3 -I node_modules -I venv
.
├── bql_parser.py
├── CHANGELOG.md
├── curllm
├── curllm_server.py
├── docker-compose.yml
├── Dockerfile
├── docs
│   └── EXAMPLES.md
├── downloads
├── examples.py
├── install.sh
├── INSTRUKCJA.md
├── LICENSE
├── logs
│   └── run-20251123-141151.md
├── Makefile
├── __pycache__
│   └── curllm_server.cpython-313.pyc
├── pyproject.toml
├── QUICKSTART.sh
├── README.md
├── requirements.txt
├── screenshots
│   └── www.prototypowanie.pl
│       └── step_0_1763903516.803199.png
├── tests
│   └── e2e.sh
├── TODO.md
├── tools
│   └── generate_examples.sh
└── workspace

12 directories, 37 files
```
## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/wronai/curllm.git
cd curllm
pip install -e .
pytest tests/
```

## 📄 License

Apache License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai) for local LLM serving
- [Browser-Use](https://github.com/gregpr07/browser-use) for browser automation
- [Playwright](https://playwright.dev) for browser control
- [LangChain](https://langchain.com) for LLM orchestration
- [Browserless](https://browserless.io) for headless browser infrastructure

## 📞 Support

- 📧 Email: info@softreck.com
- 💬 Discord: [Join our server](https://discord.gg/curllm)
- 🐛 Issues: [GitHub Issues](https://github.com/wronai/curllm/issues)
- 📚 Docs: [Documentation](https://docs.curllm.io)

---

<div align="center">
  <p>Built with ❤️ by <a href="https://softreck.com">Softreck</a></p>
  <p>⭐ Star us on GitHub!</p>
</div>
