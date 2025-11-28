# Quick Start - YAML Flows

## 5-Minute Guide

### 1. Instalacja

```bash
# Install CurLLM z YAML support
pip install -e .

# Verify installation
curllm-flow --help
```

### 2. Pierwszy Flow (2 minuty)

**Utwórz plik `hello.yaml`:**

```yaml
name: "Hello CurLLM"
description: "My first flow"

steps:
  - component: "curllm://browse"
    params:
      url: "https://example.com"
      stealth: true
      
  - component: "file://write"
    params:
      path: "/tmp/hello_result.json"
```

**Uruchom:**

```bash
curllm-flow run hello.yaml
```

### 3. Flow z Ekstrakcją (3 minuty)

**Utwórz `extract.yaml`:**

```yaml
name: "Extract Links"
description: "Get all links from a page"

diagnostics: true

input:
  data:
    url: "https://example.com"
    instruction: "Get all links"

steps:
  - component: "curllm://extract"
    params:
      url: "${url}"
      instruction: "${instruction}"
      stealth: true
      
  - component: "transform://csv"
  
  - component: "file://write"
    params:
      path: "/tmp/links.csv"
```

**Uruchom z custom variables:**

```bash
curllm-flow run extract.yaml --var url=https://news.ycombinator.com
```

### 4. Pipeline z Transformacjami (5 minut)

**Utwórz `pipeline.yaml`:**

```yaml
name: "Complete Pipeline"
description: "Browse, extract, transform, save"

diagnostics: true
trace: false

input:
  data:
    url: "https://shop.example.com/products"

steps:
  # 1. Browse with stealth
  - component: "curllm://browse"
    params:
      url: "${url}"
      stealth: true
      captcha: true
      
  # 2. Extract products
  - component: "curllm://extract"
    params:
      instruction: "Get all products with name and price"
      planner: true
      
  # 3. Extract items array
  - component: "transform://jsonpath"
    params:
      query: "$.items[*]"
      
  # 4. Save JSON
  - component: "file://write"
    params:
      path: "/tmp/products.json"
      
  # 5. Convert to CSV
  - component: "transform://csv"
    params:
      delimiter: ","
      
  # 6. Save CSV
  - component: "file://write"
    params:
      path: "/tmp/products.csv"
```

**Uruchom:**

```bash
curllm-flow run pipeline.yaml --verbose
```

## Cheat Sheet

### Podstawowe Komendy

```bash
# Run flow
curllm-flow run <file.yaml>

# With variables
curllm-flow run <file.yaml> --var key=value

# Validate
curllm-flow validate <file.yaml>

# List available flows
curllm-flow list flows/

# Show flow info
curllm-flow info <file.yaml>

# Verbose output
curllm-flow run <file.yaml> --verbose

# Save output
curllm-flow run <file.yaml> --output result.json
```

### Komponenty (Najczęściej Używane)

```yaml
# Browse webpage
- component: "curllm://browse"
  params:
    url: "https://example.com"
    stealth: true
    visual: false

# Extract data
- component: "curllm://extract"
  params:
    url: "https://example.com"
    instruction: "Get all products"
    planner: true

# Fill form
- component: "curllm://fill_form"
  params:
    url: "https://example.com/form"

# Write to file
- component: "file://write"
  params:
    path: "/tmp/output.json"

# Read from file
- component: "file://read"
  params:
    path: "/tmp/input.json"

# Transform to CSV
- component: "transform://csv"
  params:
    delimiter: ","

# JSONPath extract
- component: "transform://jsonpath"
  params:
    query: "$.items[*].name"

# HTTP request
- component: "http://api.example.com/data"
  params:
    method: "get"
```

### Zmienne

```yaml
# Define variables
input:
  data:
    my_var: "value"
    count: 10

# Use variables
steps:
  - component: "curllm://browse"
    params:
      url: "${my_var}"
```

**Override z CLI:**

```bash
curllm-flow run flow.yaml --var my_var=new_value
```

### Diagnostics

```yaml
# Enable diagnostics
diagnostics: true

# Enable trace
trace: true
```

### Split/Join Pattern

```yaml
input:
  data:
    items: [1, 2, 3, 4, 5]

steps:
  # Split array
  - component: "split://"
    params:
      type: "field"
      name: "items"
      
  # Process each item
  - component: "curllm://browse"
  
  # Join results
  - component: "join://"
    params:
      type: "list"
```

## Przykłady z Życia

### Web Scraping

```yaml
name: "Product Scraper"
steps:
  - component: "curllm://browse"
    params:
      url: "https://shop.example.com"
      stealth: true
  - component: "curllm://extract"
    params:
      instruction: "Get products with price < $50"
  - component: "transform://csv"
  - component: "file://write"
    params:
      path: "/tmp/cheap_products.csv"
```

### Form Automation

```yaml
name: "Contact Form"
input:
  data:
    name: "John Doe"
    email: "john@example.com"
    message: "Hello!"

steps:
  - component: "curllm://fill_form"
    params:
      url: "https://example.com/contact"
      visual: true
```

### Multi-Site Data Collection

```yaml
name: "Multi-Site"
input:
  data:
    sites:
      - "https://site1.com"
      - "https://site2.com"

steps:
  - component: "split://"
    params:
      type: "field"
      name: "sites"
  - component: "curllm://extract"
    params:
      instruction: "Get title and description"
  - component: "join://"
  - component: "file://write"
    params:
      path: "/tmp/multi_site.json"
```

## Python API

### Basic

```python
from curllm_core.streamware import run_yaml_flow

result = run_yaml_flow("my_flow.yaml")
```

### With Variables

```python
result = run_yaml_flow(
    "my_flow.yaml",
    variables={"url": "https://example.com"}
)
```

### With Input Data

```python
result = run_yaml_flow(
    "my_flow.yaml",
    input_data={"custom": "data"}
)
```

## Troubleshooting

### Flow nie działa

```bash
# 1. Validate syntax
curllm-flow validate my_flow.yaml

# 2. Run with verbose
curllm-flow run my_flow.yaml --verbose

# 3. Check logs
tail -f logs/curllm.log
```

### Zmienna nie jest zastąpiona

```yaml
# ✗ BAD - undefined variable
params:
  url: "${undefined}"

# ✓ GOOD - define first
input:
  data:
    my_url: "https://example.com"
steps:
  - params:
      url: "${my_url}"
```

### Component error

```bash
# List available components
python -c "from curllm_core.streamware import list_available_components; print(list_available_components())"
```

## Następne Kroki

1. **Uruchom przykłady**: `curllm-flow list flows/`
2. **Wypróbuj flow**: `curllm-flow run flows/example_browse.yaml`
3. **Stwórz własny**: Skopiuj przykład i zmodyfikuj
4. **Czytaj docs**: `YAML_FLOWS.md` i `docs/STREAMWARE.md`

## Przydatne Linki

- **Full Documentation**: `YAML_FLOWS.md`
- **Architecture**: `STREAMWARE_ARCHITECTURE.md`
- **Examples**: `flows/README.md`
- **Python API**: `examples/streamware_examples.py`

## Gotowe Flows

```bash
# Browse example flows
ls flows/

# Run any example
curllm-flow run flows/example_extraction.yaml
```

**Dostępne przykłady:**
- `example_browse.yaml` - Simple browsing
- `example_extraction.yaml` - Data extraction
- `example_form_fill.yaml` - Form filling
- `example_scraping_pipeline.yaml` - Complete pipeline
- `example_bql.yaml` - BQL queries
- `example_multi_site.yaml` - Multi-site
- `example_http_pipeline.yaml` - API integration
- `example_screenshot.yaml` - Screenshots

Gotowe do pracy! 🚀
