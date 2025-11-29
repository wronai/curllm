# CurLLM 2.0 - Streamware Edition

<p align="center">
  <strong>Browser Automation with LLM + Modular Component Architecture</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0-blue.svg" alt="Version 2.0">
  <img src="https://img.shields.io/badge/python-3.10+-green.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/architecture-Streamware-orange.svg" alt="Streamware">
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License">
</p>

---

## 🚀 Quick Start (30 Seconds)

### Python API

```python
from curllm_core.streamware import flow

# Simple extraction
result = (
    flow("curllm://extract?url=https://news.ycombinator.com&instruction=Get top 5 stories&stealth=true")
    | "transform://csv"
    | "file://write?path=stories.csv"
).run()
```

### YAML Flow

**Create `scrape.yaml`:**

```yaml
name: "News Scraper"
steps:
  - component: "curllm://extract"
    params:
      url: "https://news.ycombinator.com"
      instruction: "Get top 5 stories"
      stealth: true
  - component: "transform://csv"
  - component: "file://write"
    params:
      path: "stories.csv"
```

**Run:**

```bash
curllm-flow run scrape.yaml
```

---

## 📦 What is CurLLM 2.0?

CurLLM 2.0 combines powerful browser automation with a **modular component architecture** inspired by Apache Camel:

### Core Features

✅ **Browser Automation with LLM** (from 1.x)
- Intelligent web scraping using local LLM
- Form filling automation
- CAPTCHA solving
- Stealth mode
- BQL (Browser Query Language)

✨ **NEW: Streamware Architecture** (2.0)
- **URI-based Components** - `curllm://`, `http://`, `file://`, `transform://`
- **Composable Pipelines** - Chain operations with `|` operator
- **YAML Flows** - Declarative workflow definitions
- **Advanced Patterns** - Split/Join, Multicast, Conditional routing
- **CLI Tools** - `curllm-flow` command suite

### Architecture Benefits

🎯 **Modular** - Reusable, testable components
📝 **Declarative** - YAML or Python syntax
🔄 **Composable** - Chain operations easily
🧪 **Testable** - Unit test individual components
📊 **Observable** - Built-in metrics and diagnostics

---

## 📋 Installation

```bash
# Clone repository
git clone https://github.com/wronai/curllm.git
cd curllm

# Install with dependencies
pip install -e .

# Setup browsers
curllm-setup

# Verify installation
curllm-flow --help
```

---

## 🎯 Use Cases

### 1. Web Scraping

**Python:**
```python
from curllm_core.streamware import flow

result = (
    flow("curllm://browse?url=https://shop.example.com&stealth=true")
    | "curllm://extract?instruction=Get all products with price"
    | "transform://csv"
    | "file://write?path=products.csv"
).run()
```

**YAML:**
```yaml
name: "Product Scraper"
steps:
  - component: "curllm://browse"
    params:
      url: "https://shop.example.com"
      stealth: true
  - component: "curllm://extract"
    params:
      instruction: "Get all products with price"
  - component: "transform://csv"
  - component: "file://write"
    params:
      path: "products.csv"
```

### 2. Form Automation

```python
form_data = {
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Automated message"
}

result = (
    flow("curllm://fill_form?url=https://example.com/contact&visual=true")
    .with_data(form_data)
    .run()
)
```

### 3. Multi-Site Data Collection

```yaml
name: "Multi-Site Scraper"
input:
  data:
    sites:
      - "https://site1.com"
      - "https://site2.com"
      - "https://site3.com"

steps:
  - component: "split://"
    params:
      type: "field"
      name: "sites"
  - component: "curllm://browse"
    params:
      stealth: true
  - component: "curllm://extract"
    params:
      instruction: "Get main content"
  - component: "join://"
  - component: "file://write"
    params:
      path: "multi_site_data.json"
```

### 4. API Integration

```python
from curllm_core.streamware import flow

result = (
    flow("http://api.example.com/urls?method=get")
    | "transform://jsonpath?query=$.urls[*]"
    | "split://"
    | "curllm://browse?stealth=true"
    | "join://"
    | "file://write?path=results.json"
).run()
```

---

## 🧩 Available Components

### CurLLM Components (`curllm://`)

| Component | Description | Example |
|-----------|-------------|---------|
| **browse** | Navigate to URL | `curllm://browse?url=...&stealth=true` |
| **extract** | Extract data with LLM | `curllm://extract?url=...&instruction=...` |
| **fill_form** | Fill web forms | `curllm://fill_form?url=...&visual=true` |
| **screenshot** | Take screenshots | `curllm://screenshot?url=...` |
| **bql** | Execute BQL queries | `curllm://bql?query=...` |

### HTTP/Web Components

| Component | Description | Example |
|-----------|-------------|---------|
| **http/https** | HTTP requests | `http://api.example.com?method=post` |
| **web** | Web helper | `web://get?url=...` |

### File Components (`file://`)

| Component | Description | Example |
|-----------|-------------|---------|
| **read** | Read file | `file://read?path=/tmp/input.json` |
| **write** | Write file | `file://write?path=/tmp/output.json` |
| **append** | Append to file | `file://append?path=/tmp/log.txt` |

### Transform Components

| Component | Description | Example |
|-----------|-------------|---------|
| **jsonpath** | Extract with JSONPath | `transform://jsonpath?query=$.items[*]` |
| **csv** | Convert to CSV | `transform://csv?delimiter=,` |
| **normalize** | Normalize data | `transform://normalize` |

### Pattern Components

| Component | Description | Example |
|-----------|-------------|---------|
| **split** | Split data | `split://?type=field&name=items` |
| **join** | Join data | `join://?type=list` |
| **multicast** | Multiple outputs | `multicast://?destinations=...` |
| **filter** | Filter data | `filter://?field=price&min=10` |
| **choose** | Conditional routing | `choose://` + `.when()` |

---

## 📚 Documentation

### Quick Starts
- **[5-Minute YAML Guide](QUICKSTART_YAML.md)** - Get started with YAML flows
- **[Python Quick Start](examples/streamware_quickstart.py)** - Python API guide

### Complete Documentation
- **[Streamware Architecture](STREAMWARE_ARCHITECTURE.md)** - System overview
- **[YAML Flows Guide](YAML_FLOWS.md)** - Complete YAML reference
- **[API Documentation](docs/STREAMWARE.md)** - Detailed API docs
- **[Version 2.0 Notes](VERSION_2.0.md)** - What's new in 2.0

### Examples
- **[Python Examples](examples/streamware_examples.py)** - 15 working examples
- **[YAML Examples](flows/)** - 8 example flows
- **[Flow Documentation](flows/README.md)** - Flow examples guide

---

## 🛠️ CLI Tools

### curllm-flow - YAML Flow Runner

```bash
# Run a flow
curllm-flow run my_flow.yaml

# With variables
curllm-flow run my_flow.yaml --var url=https://example.com

# Validate flow
curllm-flow validate my_flow.yaml

# List available flows
curllm-flow list flows/

# Show flow info
curllm-flow info my_flow.yaml

# Verbose output
curllm-flow run my_flow.yaml --verbose

# Save output
curllm-flow run my_flow.yaml --output result.json
```

### Legacy CLI (Still Available)

```bash
curllm-setup    # Setup browsers
curllm-doctor   # System diagnostics
curllm-web      # Web interface
```

---

## 🔄 Migration from 1.x

### Full Backward Compatibility ✅

All 1.x code works without changes:

```python
# Legacy API - still works
from curllm_core import CurllmExecutor

executor = CurllmExecutor()
result = executor.execute({
    "url": "https://example.com",
    "data": "Get data"
})
```

### Gradual Migration

Use both APIs together:

```python
# Legacy for existing features
executor = CurllmExecutor()
legacy_result = executor.execute({...})

# Streamware for new features
from curllm_core.streamware import flow
new_result = flow("curllm://extract?url=...").run()
```

### Full Migration

Refactor to Streamware for better code:

**Before:**
```python
executor = CurllmExecutor()
result = executor.execute({
    "url": "https://example.com",
    "data": "Extract products",
    "params": {"stealth_mode": True}
})
with open('/tmp/output.json', 'w') as f:
    json.dump(result, f)
```

**After:**
```python
from curllm_core.streamware import flow

result = (
    flow("curllm://extract?url=https://example.com&instruction=Extract products&stealth=true")
    | "file://write?path=/tmp/output.json"
).run()
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Streamware tests
pytest tests/test_streamware.py -v

# With coverage
pytest tests/ --cov=curllm_core.streamware

# Validate YAML flows
for flow in flows/*.yaml; do
    curllm-flow validate "$flow"
done
```

---

## 📊 Examples

### Example 1: News Aggregator

```yaml
name: "News Aggregator"
description: "Collect news from multiple sources"

input:
  data:
    sources:
      - url: "https://news.ycombinator.com"
        selector: "top stories"
      - url: "https://reddit.com/r/programming"
        selector: "hot posts"

steps:
  - component: "split://"
    params:
      type: "field"
      name: "sources"
  - component: "curllm://extract"
    params:
      stealth: true
  - component: "join://"
  - component: "transform://csv"
  - component: "file://write"
    params:
      path: "/tmp/daily_news.csv"
```

### Example 2: E-commerce Monitor

```python
from curllm_core.streamware import flow, metrics

with metrics.track("price_monitor"):
    result = (
        flow("curllm://browse?url=https://shop.example.com&stealth=true")
        | "curllm://extract?instruction=Get products under $50"
        | "transform://jsonpath?query=$.items[?(@.price<50)]"
        | "file://write?path=/tmp/deals.json"
    ).run()

stats = metrics.get_stats("price_monitor")
print(f"Processed: {stats['processed']}, Time: {stats['avg_time']:.2f}s")
```

### Example 3: Form Filling at Scale

```yaml
name: "Bulk Form Submission"
input:
  data:
    form_url: "https://example.com/survey"
    responses:
      - name: "Alice"
        email: "alice@example.com"
      - name: "Bob"
        email: "bob@example.com"

steps:
  - component: "split://"
    params:
      type: "field"
      name: "responses"
  - component: "curllm://fill_form"
    params:
      url: "${form_url}"
      visual: true
  - component: "join://"
  - component: "file://write"
    params:
      path: "/tmp/submission_results.json"
```

---

## 🎓 Learning Path

1. **Start Here**: [QUICKSTART_YAML.md](QUICKSTART_YAML.md) - 5 minutes
2. **Try Examples**: `curllm-flow list flows/` - 10 minutes
3. **Read Guide**: [YAML_FLOWS.md](YAML_FLOWS.md) - 20 minutes
4. **Explore API**: [docs/STREAMWARE.md](docs/STREAMWARE.md) - 30 minutes
5. **Build Your Flow**: Copy and modify examples - 1 hour

---

## 🤝 Contributing

We welcome contributions! Areas of interest:

- New components (databases, message queues, etc.)
- Advanced patterns
- Performance optimizations
- Documentation improvements
- Example flows

---

## 📄 License

Apache 2.0 - See [LICENSE](LICENSE) file

---

## 🙏 Acknowledgments

- **Apache Camel** - Inspiration for architecture
- **Playwright** - Browser automation
- **Ollama** - Local LLM support
- **Community** - Feedback and contributions

---

## 🔗 Links

- **GitHub**: https://github.com/wronai/curllm
- **Issues**: https://github.com/wronai/curllm/issues
- **Documentation**: [docs/](docs/)
- **Examples**: [examples/](examples/) & [flows/](flows/)

---

<p align="center">
  <strong>CurLLM 2.0 - Modular, Composable, Powerful</strong><br>
  Browser Automation + LLM + Streamware Architecture
</p>

<p align="center">
  Made with ❤️ for the automation community
</p>
