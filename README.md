![curllm.png](docs/curllm.png)
# curllm = curl + LLM - Shell Browser Automation with Local LLM

**[📚 Full Documentation](docs/INDEX.md)** | **[🚀 Quick Start](#-quick-start)** | **[📖 Examples](docs/EXAMPLES.md)** | **[⚙️ Installation](docs/Installation.md)**

---

<div align="center">
  <h3>🤖 Intelligent Browser Automation using 8GB GPU-Compatible Local LLMs (qwen2.5:14b) </h3>
  <p>
    <strong>curllm</strong> combines the power of local LLMs with browser automation for intelligent web scraping, 
    form filling, and workflow automation - all running on your local machine with complete privacy.
  </p>
</div>

## ✨ Features

- **🧠 Local LLM Integration**: Run on 8GB GPUs with models like Qwen 2.5, Mistral, or Llama
- **🎯 Hierarchical Planner**: 87% token reduction with intelligent 3-level decision tree ([docs](docs/HIERARCHICAL_PLANNER.md))
- **📝 Smart Form Filling**: Automated form completion with error detection and remediation ([docs](docs/FORM_FILLING.md))
- **🧩 Streamware DSL**: Atomic browser automation with replayable DSL commands ([streamware-js](https://github.com/wronai/streamware-js))
- **👁️ Visual Analysis**: Computer vision for CAPTCHA detection and page understanding  
- **🥷 Stealth Mode**: Advanced anti-bot detection bypass techniques
- **🔍 BQL Support**: Browser Query Language for structured data extraction
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

## 📚 Documentation

**[→ Complete Documentation Index](docs/INDEX.md)**

### Quick Links
- **[Installation Guide](docs/Installation.md)** - Detailed installation instructions
- **[Examples & Tutorials](docs/EXAMPLES.md)** - Practical use cases
- **[Hierarchical Planner](docs/HIERARCHICAL_PLANNER.md)** - NEW! 87% token reduction
- **[Form Filling](docs/FORM_FILLING.md)** - NEW! Automated form completion
- **[API Reference](docs/API.md)** - REST API endpoints
- **[Environment Config](docs/Environment.md)** - Configuration guide
- **[Troubleshooting](docs/Troubleshooting.md)** - Common issues
- **[Linux Testing](LINUX_TESTING.md)** - Cross-platform Linux tests

## 🚀 Quick Start

### Installation from PyPI (Recommended)

```bash
# Install curllm from PyPI
pip install -U curllm

# Run post-installation setup
curllm-setup

# Verify your installation
curllm-doctor
```

The `curllm-setup` command will:
- ✓ Check Python version (3.10+)
- ✓ Create necessary directories (`logs/`, `screenshots/`, `downloads/`, `workspace/`)
- ✓ Set up `.env` configuration file
- ✓ Install Playwright browsers
- ✓ Check for Ollama

The `curllm-doctor` command verifies all dependencies and configuration.

**[→ CLI Commands Documentation](CLI_COMMANDS_USAGE.md)**

### 🌐 Web Client (NEW!)
![img_1.png](img_1.png)

For users who prefer a graphical interface, curllm now includes a modern web client with **process management**:

```bash
# Start server in background
curllm-web start

# Check status
curllm-web status

# Stop server
curllm-web stop

# Restart server
curllm-web restart

# Or run in foreground (traditional way)
curllm-web
```

Open browser at **http://localhost:5000**

**Features:**
- 🎨 **Modern, responsive UI** with Tailwind CSS
- 📝 **19 pre-configured prompts** with custom editing
- 📤 **File upload support** (CSV, XLS, JSON, etc.)
- 📊 **Real-time log viewer** with embedded screenshots
- ⚙️ **Advanced options** - Visual mode, stealth, CAPTCHA
- 💾 **Prompt management** - Save/edit/delete custom prompts
- 🔄 **Process management** - Start/stop/restart/status commands
- 📈 **Status monitoring** - PID, memory usage, port status

**Quick Start:**
```bash
# One-step launch (starts both API and Web)
./start-web-full.sh

# Or manually:
python curllm_server.py &    # Terminal 1: API server
curllm-web start             # Terminal 2: Web client
```

**Documentation:**
- **[→ Web Client Guide](WEB_CLIENT_README.md)** - Full documentation
- **[→ Quick Start](QUICKSTART_WEB.md)** - Step-by-step guide
- **[→ Process Management](PROCESS_MANAGEMENT.md)** - Commands reference

### Development Installation

```shell
make install
```

### ⚠️ Troubleshooting: Missing Browsers

Jeśli widzisz błąd `Executable doesn't exist at ...playwright/chromium...`:

```bash
# Quick fix
playwright install

# Lub automatycznie przy starcie
make start  # Teraz automatycznie instaluje przeglądarki!
```

**Dlaczego?** `make clean` reinstaluje pakiet Python, ale **nie** instaluje przeglądarek Playwright (są osobne). 

**Rozwiązanie:** Zaktualizowany `make start` teraz **automatycznie instaluje przeglądarki**.

📚 **Więcej:** `PLAYWRIGHT_BROWSERS_FIX.md`

### Generate Example Scripts

Generate runnable example scripts:
```shell
make examples
# Scripts created in examples/ as curllm-*.sh
# Run with: ./examples/curllm-extract-links.sh
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

### How it works?

![img.png](img.png)

```bash
 curllm --visual --stealth --session kontakt \
  "https://www.prototypowanie.pl/kontakt/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, phone=+48123456789, subject=Test, message=Hello i need quota for my MVP project",
    "params":{"hierarchical_planner":true}
  }' \
  -v
```

## 🎭 Transparent LLM Orchestration (NAJNOWSZA FUNKCJA!)

### Multi-Phase Control z Pełną Transparentnością

**Problem:** Hardcoded algorytmy podejmują decyzje bez wiedzy LLM → błędy

**Rozwiązanie:** LLM widzi KAŻDĄ decyzję i kontroluje KAŻDY krok

### 5 Faz Orkiestracji

```
1. FIELD MAPPING     → LLM planuje mapowanie pól
2. VERIFICATION      → LLM weryfikuje i koryguje
3. FILLING PLAN      → LLM tworzy plan wypełnienia
4. EXECUTION         → LLM kontroluje każdy krok
5. VALIDATION        → LLM decyduje czy submit
```

### Quick Start

```bash
# Enable transparent orchestration
echo "CURLLM_LLM_ORCHESTRATOR=true" >> .env
echo "CURLLM_LLM_TRANSPARENT_ORCHESTRATOR=true" >> .env

# Test
curllm --visual --stealth \
  "https://www.prototypowanie.pl/" \
  -d '{"instruction":"Fill form: name=John Doe, email=john@example.com"}' -v
```

### Przykład Logu

```
🎭 TRANSPARENT LLM ORCHESTRATOR mode enabled

━━━ PHASE 1: Field Mapping ━━━
   🧠 LLM Planning...
   🎯 DECISION: email → field_A (reasoning: type='email')

━━━ PHASE 2: Verification ━━━
   🎯 DECISION: Approved

━━━ PHASE 3: Filling Plan ━━━
   🎯 DECISION: 2 steps plan

━━━ PHASE 4: Execution ━━━
   ⚡ Step 1 ✅
   ⚡ Step 2 ✅

━━━ PHASE 5: Validation ━━━
   🎯 DECISION: Ready to submit ✅

✅ Phases: 5, Decisions: 8, Success: true
```

### Dokumentacja

- **Quick Start:** `QUICKSTART_TRANSPARENT.md`
- **Full Docs:** `TRANSPARENT_ORCHESTRATION.md`

---

## 🤖 LLM Form Orchestrator (NOWA FUNKCJA!)

### Koncepcja

Zamiast hardcodować logikę wypełniania, **LLM podejmuje decyzje**:

```
1. Wykryj pola formularza (JavaScript) → [lista pól]
2. Udostępnij operacje (fill, split, check) → [dostępne akcje]
3. LLM planuje wypełnienie → [plan operacji]
4. System wykonuje plan → ✅ Wypełnione
```

### Quick Start

```bash
# 1. Restart serwera
make stop && make clean && make start

# 2. Włącz LLM Orchestrator
echo "CURLLM_LLM_ORCHESTRATOR=true" >> .env

# 3. Test!
curllm --visual --stealth \
  "https://softreck.com/contact/" \
  -d '{"instruction":"Fill form: name=John Doe, email=john@example.com"}' -v
```

### Zalety

| Funkcja | Deterministyczny | LLM Orchestrator |
|---------|-----------------|------------------|
| Elastyczność | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Split name fields | ❌ Trzeba hardcodować | ✅ Automatycznie |
| Title/Suffix fields | ❌ Nie wspierane | ✅ LLM wymyśla strategię |
| Debug reasoning | ❌ Brak | ✅ LLM wyjaśnia DLACZEGO |
| Maintenance | ❌ Dużo kodu | ✅ Minimalna |

### Tryb Hybrydowy (Rekomendowany!)

```bash
CURLLM_LLM_ORCHESTRATOR=true  # LLM próbuje pierwszy
```

Jeśli LLM zawiedzie → **automatyczny fallback** do deterministycznego!

```
🤖 LLM Orchestrator mode enabled
⚠️  LLM Orchestrator failed: timeout, falling back
🔧 Using deterministic form fill (fallback)
✅ Form submitted
```

### Dokumentacja

- **Quick Start:** `QUICKSTART_LLM_ORCHESTRATOR.md`
- **Pełna dokumentacja:** `LLM_FORM_ORCHESTRATOR.md`
- **Integracja:** `INTEGRATION_EXAMPLE.md`
- **Test:** `TEST_LLM_ORCHESTRATOR.md`


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

## 💡 Usage Recipes (quick)

- Extract all links

  ```bash
  curllm "https://example.com" -d "extract all links"
  ```

- Screenshot

  ```bash
  curllm "https://example.com" -d "screenshot"
  ```

- Export CSV/HTML/XLS

  ```bash
  curllm "https://example.com" -d "extract all links" --csv -o links.csv
  curllm "https://example.com" -d "extract all links" --html -o links.html
  curllm "https://example.com" -d "extract all links" --xls -o links.xls
  ```

- Public proxy rotation (Ceneo under 150 zł)

  ```bash
  export CURLLM_PUBLIC_PROXY_LIST="https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
  curllm "https://ceneo.pl" -d "Find all products under 150zł and extract names, prices and urls" \
    --stealth --proxy rotate:public --csv -o products.csv
  ```

- Registry rotation (po rejestracji przez curlx)

  ```bash
  # przykład rejestracji proxy:
  curlx register --host 203.0.113.10 --ports 3128,3129 --server http://localhost:8000
  curllm "https://ceneo.pl" -d "Find all products under 150zł and extract names, prices and urls" \
    --stealth --proxy rotate:registry --html -o products.html
  ```

- Sesja (persistent cookies)

  ```bash
  curllm --session my-site "https://example.com" -d "screenshot"
  ```

- WordPress: utwórz post

  ```bash
  curllm --session wp-s1 -d '{"wordpress_config":{"url":"https://example.wordpress.com","action":"create_post","title":"Hello","content":"Post body","status":"draft"}}'
  ```

- BQL: Hacker News links

  ```bash
  curllm --bql -d 'query { page(url: "https://news.ycombinator.com") { title links: select(css: "a.storylink, a.titlelink") { text url: attr(name: "href") } }}'
  ```

- Monitoring (cron + e-mail)

  ```bash
  # zobacz monitoring/README.md
  make -C monitoring setup
  make -C monitoring run
  make -C monitoring install-3h
  ```

## 🎯 Examples

For a comprehensive, curated set of examples and ready-to-run scripts, see:

- docs/EXAMPLES.md
- Generate scripts: make examples (scripts are created in examples/ as curllm-*.sh)

### Playwright + BQL (Sync) Agent — captcha/playwright_bql_framework.py

This repository now includes a simple synchronous Playwright + BQL agent you can run directly, with built-in cookie-consent handling and CAPTCHA detection (no bypass). The agent expects your LLM to return a JSON array of BQL actions (fill, click, wait, select, submit, scroll, screenshot).

Install prerequisites (inside your virtualenv):

```bash
pip install -r requirements.txt
pip install playwright
python -m playwright install
```

Run a demo:

```bash
python captcha/playwright_bql_framework.py
```

Use your preferred LLM:

- Default: Ollama (env: CURLLM_OLLAMA_HOST, CURLLM_MODEL)
- OpenAI: set BQL_FRAMEWORK_LLM=openai and OPENAI_API_KEY, optionally OPENAI_MODEL

Examples (pseudo-code snippets):

```python
from playwright.sync_api import sync_playwright
from captcha.playwright_bql_framework import BQLAgent, select_llm_caller

# WordPress Login
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://www.prototypowanie.pl/wp-login.php", wait_until="networkidle")
    agent = BQLAgent(page, call_llm=select_llm_caller())
    res = agent.run_instruction("Zaloguj się do WordPress. Login: admin, Hasło: test123.")
    print(res)
    browser.close()

# Contact form fill
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://softreck.com/contact", wait_until="networkidle")
    agent = BQLAgent(page, call_llm=select_llm_caller())
    res = agent.run_instruction("Wypełnij formularz: Imię Jan, Email jan@example.com, Wiadomość 'Test wysyłki'. Wyślij formularz.")
    print(res)
    browser.close()

# Structured product search (example site)
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://ceneo.pl", wait_until="networkidle")
    agent = BQLAgent(page, call_llm=select_llm_caller())
    res = agent.run_instruction("Znajdź wszystkie produkty poniżej 150 zł i zwróć nazwy, ceny i URL-e.")
    print(res)
    browser.close()
```

Notes:

- The agent detects CAPTCHA-like widgets and returns an interrupt; the core curllm executor can optionally solve widget CAPTCHAs using a 2captcha sitekey token injection if you enable captcha_solver and provide an API key.
- The agent clicks obvious cookie-consent buttons if found (configurable).

### product extractor from ceneo.pl

#### Find all products under 150zł and extract names, prices and urls
command:
```bash
curllm --stealth "https://www.ceneo.pl/Urzadzenia_sprzatajace;ptags:OfertySpecjalne.htm" -d "Find all products under 550zł"
```
output
```bash
{
  "evaluation": {
    "checks_performed": [
      "steps_check",
      "extraction_task_check"
    ],
    "evaluated": true,
    "failures": [],
    "warnings": [
      "Zero steps executed"
    ]
  },
  "hints": [],
  "reason": "Task completed successfully (0 steps taken)",
  "result": {
    "products": [
      {
        "name": "SHARK S1000EU\n 5,0\n/ 5\n4 opinie\nDodaj do ulubionych\nKolor: Bia\u0142e\nMoc: 1050 W",
        "price": 349,
        "url": "https://www.ceneo.pl/102723109##;02514#tag=nph_row_promotion"
      },
      {
        "name": "Bosch UniversalBrush 06033E0000\n 4,5\n/ 5\n33 opinie\n10+ kupionych ostatnio",
        "price": 168.3,
        "url": "https://www.ceneo.pl/110631727"
      },
      {
        "name": "Bosch EasyVac 3 06033D1000\n 4,3\n/ 5\n5 opinii",
        "price": 349,
        "url": "https://www.ceneo.pl/52315916"
      },
      {
        "name": "Bosch AdvancedVac 18V-8 06033E1000\nNapisz opini\u0119",
        "price": 317.99,
        "url": "https://www.ceneo.pl/118147335"
      },
      {
        "name": "Bosch UniversalVac 15 06033D1100\n 4,6\n/ 5\n11 opinii",
        "price": 338.9,
        "url": "https://www.ceneo.pl/52782460"
      },
      {
        "name": "Bosch UniversalBrush 06033E0002\n 5,0\n/ 5\n1 opinia",
        "price": 182.02,
        "url": "https://www.ceneo.pl/158836315"
      }
    ]
  },
  "run_log": "logs/run-20251125-222132.md",
  "screenshots": [],
  "steps_taken": 0,
  "success": true,
  "suggested_commands": [],
  "timestamp": "2025-11-25T22:22:01.397203"
}
```

command:
```aiignore
curllm --stealth "https://ceneo.pl"-d "Find all products under 150zł and extract names, prices and urls"
  
curllm --visual --stealth -H "Accept-Language: pl-PL,pl;q=0.9" "https://ceneo.pl" -d '{
  "instruction":"Find all products under 150zł and extract names, prices and urls"  
}'

curllm --stealth "https://www.ceneo.pl/Urzadzenia_sprzatajace;discount.htm" -d "Find all products under 150zł and extract names, prices and urls"

curllm --visual --stealth "https://www.ceneo.pl/Urzadzenia_sprzatajace;ptags:OfertySpecjalne.htm" -d "Set price filter max 150 zł, apply it, scroll to load items, then extract product names, prices and urls"

```
```bash
curllm --visual -H "Accept-Language: pl-PL,pl;q=0.9" "https://ceneo.pl" -d '{
  "instruction":"Find all products under 150zł and extract names, prices and urls",
  "params": {
    "include_dom_html": true,
    "no_click": true,
    "scroll_load": true,
    "action_timeout_ms": 120000,
    "use_external_slider_solver": true
  }
}'
```
output:
```bash
{
  "result": {
    "products": [
      {
        "name": "Bestseller\n4,9\n414\n\nIbuvit D3 4000Iu 150kaps.\n\n1000+ kupionych ostatnio\nod41,18z\u0142",
        "price": 41.18,
        "url": "https://redirect.ceneo.pl/offers/164000259/9026?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtD%2BafUImi8vsfWXXtr8DMq0X88TaxMLTJxeJJJaUCdmGyCBcPvOgXaqbCITGHMyX4V962NVaZY%2Bh2BDFZdla0ceoMYEHuJZOUGcft4g2WWpqA%3D%3D"
      },
      {
        "name": "Bestseller\n4,1\n4\n\nPucio urz\u0105dza wigili\u0119, czyli \u015bwi\u0105teczne s\u0142owa i zadania dla przedszkolak\u00f3w\n\n1000+ kupionych ostatnio\nod59,99z\u0142",
        "price": 59.99,
        "url": "https://redirect.ceneo.pl/offers/188774853/22637?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtCwjwfoZvABCMIa%2FwfTTUpPf4CAMmDEyEScec%2B8scvyCzN7ApkOegh4hO7WcMD5rND9Me7F6rLgCr57%2FozD%2BnbXTw2P4a2bsfGGmyuUb5%2B3hg%3D%3D"
      },
      {
        "name": "Popularny teraz\n4,9\n145\n\nPOLECANY Redmi Note 14 Pro 5G 8/256GB Czarny\n\n100+ kupionych ostatnio\nod1 149,00z\u0142",
        "price": 149,
        "url": "https://redirect.ceneo.pl/offers/179314788/16202?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtAvV6%2BS4wDNiNcN5EmHT8vDqqLH2IKSXS8KzGnDtg%2FbqsDHDbhVHROeNVvRqlGBtTeOdxI29gon%2BiwiDIya1tRUIgi%2BTBEfSGLmPlqqNWLwhYlxKTfZiD4Rmu5c76aN5UA%3D"
      },
      {
        "name": "Bestseller\n4,9\n290\n\nMagne B6 Forte 180tabl.\n\n1000+ kupionych ostatnio\nod51,39z\u0142",
        "price": 51.39,
        "url": "https://redirect.ceneo.pl/offers/179038790/53026?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtCmPDC7YdxN%2BF7%2Fy0ISj9ExuVkXTt2NudXZZU56TcEZ2uGAFeUdeZtQYVoyLrdjVtHkaMz4diwSkaxjcRkzBlz807saI8VD%2Fvb8scsPalmrQw%3D%3D"
      },
      {
        "name": "Wysoko oceniany\n4,8\n1256\n\nArkada TC16 Serum Kolagenowe Do Paznokci Regeneracja Sk\u00f3ry i Paznokci 11ml\n\n1000+ kupionych ostatnio\nod55,52z\u0142",
        "price": 55.52,
        "url": "https://redirect.ceneo.pl/offers/59277115/25070?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtAhLmvnQSQBSHnxEyLKI8qxLQ1Ov3dEovwLdmEUpc8ANFic2hPQTFmMasy%2BMujUksXpCwuxpyFt9y19r9FK%2FoMsezPwMnrTTugS2BRrRFxiuA%3D%3D"
      },
      {
        "name": "Wysoko oceniany\n4,8\n3677\n\nCalperos 1000mg 100 kaps.\n\n1000+ kupionych ostatnio\nod58,79z\u0142",
        "price": 58.79,
        "url": "https://redirect.ceneo.pl/offers/4775603/53026?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtBSU6%2B7XF%2F5RnZJSpyYGBIKDR1obcne7UAlbggOIO%2BGj9n2ommNYSmAtgJ3D%2FN81i%2FXENXjBiYZcHX8qh%2FMidtTISBIy0RqMmaUoHscKQ9TQg%3D%3D"
      },
      {
        "name": "Superceny do 100z\u0142\nWi\u0119cej supercen do 100z\u0142 \u2794",
        "price": 100,
        "url": "https://www.ceneo.pl/;n100;discount.htm#tag=insp-superceny-gfx"
      }
    ]
  },
  "run_log": "logs/run-20251124-082625.md",
  "screenshots": [],
  "steps_taken": 0,
  "success": true,
  "timestamp": "2025-11-24T08:27:36.528472"
}
```

#### Find all products under 50zł and extract names, prices and urls
command:
```bash
curllm --visual -H "Accept-Language: pl-PL,pl;q=0.9" "https://ceneo.pl" -d '{
  "instruction":"Find all products under 50zł and extract names, prices and urls"  
}'
```
output:
```bash
{
  "result": {
    "products": [
      {
        "name": "Bestseller\n4,9\n414\n\nIbuvit D3 4000Iu 150kaps.\n\n1000+ kupionych ostatnio\nod41,18z\u0142",
        "price": 41.18,
        "url": "https://redirect.ceneo.pl/offers/164000259/9026?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtD%2BafUImi8vsfWXXtr8DMq0X88TaxMLTJxeJJJaUCdmGyCBcPvOgXaqbCITGHMyX4V962NVaZY%2Bh2BDFZdla0ceoMYEHuJZOUGcft4g2WWpqA%3D%3D"
      }
    ]
  },
  "run_log": "logs/run-20251124-082824.md",
  "screenshots": [
    "screenshots/www.ceneo.pl/step_0_1763969385.938158.png"
  ],
  "steps_taken": 1,
  "success": true,
  "timestamp": "2025-11-24T08:29:48.844432"
}
```

#### CSV
```aiignore
curllm "https://ceneo.pl" -d "Find all products under 150zł and extract names, prices and urls" --csv -o products.csv
```
output:
```bash
{"hints":[],"result":{"products":[{"name":"Bestseller\n4,6\n11\n\nSamsung Galaxy S25 FE 8/256GB Granatowy\n\n50+ kupionych ostatnio\nod3 099,00z\u0142","price":99,"url":"https://redirect.ceneo.pl/offers/187704844/16202?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtAuOtYKLbGQbrXSM4NmcY%2BRz6ALdXwLYgWshZKWkyTjn3XyjS3rJCH84VGyVBmSHkswTiDjQqmQayxvwqGRLSOJnBq6ot4ekF%2F%2BEsNayEBatIkNShIeXEzld0Ey6kuXAEM%3D"},{"name":"Wysoko oceniany\n4,9\n70\n\nSamsung Galaxy S24 FE 5G SM-S721 8/256GB Grafitowy\n\n100+ kupionych ostatnio\nod2 099,00z\u0142","price":99,"url":"https://redirect.ceneo.pl/offers/173803420/4614?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtBYUVKV5i3hyOO53nSTTXI879XpVF9JgtGZMVu8tB6dFEoljbAuHBlv8RiqctyP6FXFyMjZUqCYsEMrtqeHA1USJ1Yi4aDrGpaNOwvkZxAmAG39DS2I2EkFzNffhrBUS%2Fo%3D"},{"name":"Bestseller\n4,1\n4\n\nPucio urz\u0105dza wigili\u0119, czyli \u015bwi\u0105teczne s\u0142owa i zadania dla przedszkolak\u00f3w\n\n1000+ kupionych ostatnio\nod59,99z\u0142","price":59.99,"url":"https://redirect.ceneo.pl/offers/188774853/22637?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtCwjwfoZvABCMIa%2FwfTTUpPn2TGG1oHS0v7VgJyOuKc9raN6uQ6jBgR%2FPPW8ERW6J6QjUMmEeHb%2BNtDGsfshcdH70cBYtw1D2SE%2FN0F5zfVhg%3D%3D"},{"name":"Bestseller\n4,9\n73\n\nNiacynobaza 25% Skoncentrowane serum z niacynamidem 30g\n\n1000+ kupionych ostatnio\nod21,79z\u0142","price":21.79,"url":"https://redirect.ceneo.pl/offers/182039369/9026?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtBdxjmWJ83EL%2FoWyjTi%2BWLsUME0Fg5%2FYHYj0LgQ%2BkjesBf55uhlTbj8S%2BHLlYURuseZ97XU%2BzkPDEyOpwWqmUKHILflawW7xGGsXiYRQnaBGA%3D%3D"},{"name":"Bestseller\n4,9\n18\n\nApple AirPods Pro 3\n\n500+ kupionych ostatnio\nod1 039,00z\u0142","price":39,"url":"https://redirect.ceneo.pl/offers/187595793/24403?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtAkD2hcmhNvx6EXlTCEYiO4k9XIBhExoCKlfHvs3zr2WFCGCs6TRUhrGe0Cw6AswYDDrsb1yxU%2F4OhoFhdqcMg9MLbGyIfKcrwsvZ0As7BdoNgzYl2rMwwdwB3bFPb8f58%3D"},{"name":"Bestseller\n4,9\n290\n\nMagne B6 Forte 180tabl.\n\n1000+ kupionych ostatnio\nod50,98z\u0142","price":50.98,"url":"https://redirect.ceneo.pl/offers/179038790/9026?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtDGOm1atwU81LhBgOjKTKO7NpOiWFioy7ean1a4wxT9kE3EWRUXGOyVbr3qk0xP649ruexm0e%2FSQ5EvODmj%2FH2sVWCqRVtnidxJykYq6fSjIg%3D%3D"},{"name":"4,9\n2304\n\nSamsung Galaxy S24 SM-S921 8/256GB Czarny\n\n100+ kupionych ostatnio\nod3 111,96z\u0142","price":111.96,"url":"https://redirect.ceneo.pl/offers/163090033/10772?e=EOpjbVPvmeU84eOvTVLW8x9ZNVMTIBt6BegLfpT4JtBdtqKfjUTK3TO2nvgxSCzNmsIXa5uveW0C%2BYGXclFTh7oeF0wt1XREvis059kiKl4MxfdWMfHPydpQRXZ58z4%2F56oCukbzagJ66HKzONrOZNifhOrShgpxPL0mh37ZobU%3D"},{"name":"Superceny do 100z\u0142\nWi\u0119cej supercen do 100z\u0142 \u2794","price":100,"url":"https://www.ceneo.pl/;n100;discount.htm#tag=insp-superceny-gfx"}]},"run_log":"logs/run-20251124-093441.md","screenshots":[],"steps_taken":0,"success":true,"suggested_commands":[],"timestamp":"2025-11-24T09:35:51.950884"}
✓ CSV exported to products.csv
```
![csv.png](docs/csv.png)

### Examples .env and autoload

- The examples directory includes `.env.examples` and `.env` (generate or update with `examples/setup_env.sh`).
- Shell scripts in `examples/curl_*.sh` now auto-load `examples/.env` (or project `.env`) at runtime.
- Node.js and PHP examples read `examples/.env` automatically.
- If your API picks a non-default port (e.g., 8002), ensure `CURLLM_API_HOST` is set in `.env` (handled by `curllm --start-services`).

Quick setup:

```bash
chmod +x examples/setup_env.sh
examples/setup_env.sh

# Optional: export CAPTCHA 2captcha key for widget solving in core curllm
export CAPTCHA_API_KEY=YOUR_2CAPTCHA_KEY

# Run any example
examples/curl_product_search.sh
```

If you saw `{ "detail": "Not Found" }`, you likely hit the wrong port. Fix by either:

```bash
# 1) Let scripts auto-load the updated host from .env (recommended)
curllm --start-services  # updates .env with the actual port
examples/curl_product_search.sh

# 2) Or export the API host manually
export CURLLM_API_HOST=http://localhost:8002
examples/curl_product_search.sh
```

### Node.js / PHP API examples

- Node.js: `examples/node_api_example.js`

```bash
node examples/node_api_example.js
# reads examples/.env, posts to ${CURLLM_API_HOST}/api/execute
```

- PHP: `examples/php_api_example.php`

```bash
php examples/php_api_example.php
# reads examples/.env, posts to ${CURLLM_API_HOST}/api/execute
```

### CAPTCHA solver

- Core curllm can optionally solve widget CAPTCHAs (sitekey-token via 2captcha). Set env and use `--captcha`:

```bash
export CAPTCHA_API_KEY=YOUR_2CAPTCHA_KEY
curllm --visual --captcha "https://example.com" -d "fill form"
```

### Docker devbox (venv) for testing installation and examples

A lightweight container to test install and examples without touching host.

```bash
# Build and start devbox + Ollama + API (optional)
docker compose up -d devbox ollama curllm-api

# Enter the devbox
docker compose exec devbox bash

# Inside devbox: create a venv and install deps
python3 -m venv venv
source venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install playwright && python -m playwright install chromium
# (optional, Linux) system deps for browsers
python -m playwright install-deps chromium || true

# Prepare examples env and point to services via docker network
examples/setup_env.sh
export CURLLM_API_HOST=http://curllm-api:8000
export CURLLM_OLLAMA_HOST=http://ollama:11434

# Run examples
bash examples/curl_product_search.sh
python examples/bql_product_search.py
```

Notes:

- For Accept-Language, set `ACCEPT_LANGUAGE` in examples/.env; shell scripts send it as a header automatically.
- The Playwright+BQL Python examples do not auto-load `.env`; load it via `source examples/.env` before `python ...` if needed.


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

### Proxy rotation and sessions

- curllm can use proxies per request and rotate them automatically.
- You can pass proxy config via the API `proxy` field, and persist logins via `session_id` (cookies saved under ./workspace/sessions/<session_id>.json).

Examples (API):

```bash
# 1) Rotate through a provided list (round-robin per host)
curl -s -X POST "$CURLLM_API_HOST/api/execute" -H 'Content-Type: application/json' -d '{
  "url": "https://example.com",
  "data": "extract all links",
  "proxy": {"rotate": true, "list": ["http://p1:8080","http://p2:8080","http://p3:8080"]},
  "session_id": "mysession"
}'

# 2) Rotate using a file of proxies (one per line)
curl -s -X POST "$CURLLM_API_HOST/api/execute" -H 'Content-Type: application/json' -d '{
  "url": "https://example.com",
  "data": "extract all links",
  "proxy": {"rotate": true, "file": "./workspace/proxy/public_proxies.txt"}
}'

# 3) Use public proxy list via URL or env (CURLLM_PUBLIC_PROXY_LIST)
export CURLLM_PUBLIC_PROXY_LIST="https://myhost/proxies.txt"  # or file:///abs/path/list.txt or comma list
curl -s -X POST "$CURLLM_API_HOST/api/execute" -H 'Content-Type: application/json' -d '{
  "url": "https://example.com",
  "data": "extract all links",
  "proxy": {"rotate": "public"}
}'

# 4) Single static proxy (string or dict)
curl -s -X POST "$CURLLM_API_HOST/api/execute" -H 'Content-Type: application/json' -d '{
  "url": "https://example.com",
  "data": "extract all links",
  "proxy": "http://user:pass@proxy.example.com:8080"
}'
```

Notes:

- Rotation is stored per-target host (round-robin). State is saved in `./workspace/proxy/rotation_state.json`.
- With `session_id`, cookies persist across requests. Use the same `session_id` to keep you logged in.

WordPress automation in one session (no proxy):

```bash
curl -s -X POST "$CURLLM_API_HOST/api/execute" -H 'Content-Type: application/json' -d '{
  "wordpress_config": {
    "url": "https://example.wordpress.com",
    "username": "admin",
    "password": "secret123",
    "action": "create_post",
    "title": "Nowy artykuł",
    "content": "# Tytuł\n\nTreść...",
    "status": "publish",
    "categories": ["Technologia"],
    "tags": ["AI","Automation"]
  },
  "session_id": "wp-mysession"
}'
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
  "use_bql": false,
  "proxy": "http://user:pass@proxy:8080" | {"server":"...","username":"...","password":"..."} | {"rotate":true, "list":["http://..."], "file":"path"} | {"rotate":"public"},
  "session_id": "my-session-id",
  "wordpress_config": {"url":"https://...","username":"...","password":"...","action":"create_post", "title":"...", "content":"...", "status":"draft|publish", "categories":["..."], "tags":["..."]}
}
```

CLI flag `--proxy` (planned): pass the same JSON (or shorthand like `rotate:public`). Until then, use the API `proxy` field as above or set `CURLLM_PUBLIC_PROXY_LIST`.

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

## curlx: Proxy companion

curlx to osobna paczka Python wspierająca curllm w zarządzaniu proxy (rejestracja, lista, uruchamianie serwerów proxy na zdalnych hostach przez SSH).

Instalacja (dev):

```bash
pip install -e ./curlx_pkg
```

Użycie:

```bash
# Rejestracja istniejących proxy (host:port) w rejestrze curllm
curlx register --host 203.0.113.10 --ports 3128,3129 --server http://localhost:8000

# Lista zarejestrowanych proxy
curlx list --server http://localhost:8000

# Uruchomienie proxy.py na zdalnym hoście przez SSH i rejestracja w curllm
curlx spawn --host ubuntu@203.0.113.10 --ports 3128,3129 --server http://localhost:8000
```

Integracja z curllm (rotacja z rejestru):

```bash
curllm --proxy rotate:registry "https://example.com" -d "extract links"
```

Zmienne środowiskowe:

- CURLLM_API_HOST — domyślny host API curllm (np. http://localhost:8000)
- SSH_BIN — polecenie SSH (domyślnie: ssh)
- PY_BIN_REMOTE — Python na hoście zdalnym (domyślnie: python3)

### Proxy health-check i pruning

Sprawdź działanie proxy i usuń niedziałające wpisy z rejestru:

```bash
# Sprawdzenie (bez usuwania)
curl -s -X POST "$CURLLM_API_HOST/api/proxy/health" -H 'Content-Type: application/json' \
  -d '{"url":"http://example.com","timeout":4,"limit":20,"prune":false}' | jq .

# Auto-pruning (usuwanie martwych)
curl -s -X POST "$CURLLM_API_HOST/api/proxy/health" -H 'Content-Type: application/json' \
  -d '{"url":"http://example.com","timeout":4,"prune":true}' | jq .
```

### WordPress + Sesje (PL)

Utrwalaj logowanie do WordPress przy pomocy `session_id` i twórz posty:

```bash
curl -s -X POST "$CURLLM_API_HOST/api/execute" -H 'Content-Type: application/json' -d '{
  "wordpress_config": {
    "url": "https://example.wordpress.com",
    "username": "admin",
    "password": "secret123",
    "action": "create_post",
    "title": "Nowy artykuł",
    "content": "# Tytuł\n\nTreść...",
    "status": "publish"
  },
  "session_id": "wp-s1"
}'
```

Kolejne posty w tej samej sesji (bez ponownego logowania):

```bash
curllm --session wp-s1 -d '{"wordpress_config":{"url":"https://example.wordpress.com","action":"create_post","title":"Kolejny","content":"Treść","status":"draft"}}'
```

### WordPress + Sessions (EN)

Persist WordPress login with `session_id` and create posts:

```bash
curl -s -X POST "$CURLLM_API_HOST/api/execute" -H 'Content-Type: application/json' -d '{
  "wordpress_config": {
    "url": "https://example.wordpress.com",
    "username": "admin",
    "password": "secret123",
    "action": "create_post",
    "title": "New Post",
    "content": "# Title\n\nContent...",
    "status": "publish"
  },
  "session_id": "wp-s1"
}'
```

Next posts in the same session:

```bash
curllm --session wp-s1 -d '{"wordpress_config":{"url":"https://example.wordpress.com","action":"create_post","title":"Next","content":"Text","status":"draft"}}'
```

### Publikacja curlx (PyPI)

W katalogu `curlx_pkg/` znajdują się cele Makefile i workflow CI do wydania curlx:

```bash
cd curlx_pkg
make release           # build sdist/wheel do dist/
make publish-test      # publikacja do TestPyPI (wymaga TWINE_PASSWORD token)
make publish           # publikacja do PyPI
```

Repo zawiera także workflow `.github/workflows/publish-curlx.yml` uruchamiany tagiem `curlx-v*`.

## 🗺️ Roadmap

- [ ] CLI `--proxy` flag with rotation presets (public/list/file)
- [ ] `curlx` companion: remote proxy provisioning + registry API for curllm
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
