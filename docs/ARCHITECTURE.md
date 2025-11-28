# CurLLM Architecture Documentation

## Overview

CurLLM is an LLM-powered browser automation framework that uses semantic understanding instead of hardcoded patterns.

## Core Principles

### 1. NO HARDCODED PATTERNS
- **NO REGEX in application code** - LLM generates patterns dynamically
- **NO hardcoded CSS selectors** - LLM finds selectors based on DOM context
- **NO static field mappings** - LLM maps fields semantically

### 2. LLM-First Approach
Every decision is made by LLM:
- Page type detection
- Container identification
- Field mapping
- Data extraction
- Action planning

### 3. Atomic Functions
Each operation is a small, testable function that does ONE thing.

---

## Directory Structure

```
curllm/
├── curllm_core/
│   ├── streamware/
│   │   └── components/           # Modular components
│   │       ├── extraction/       # Product extraction (LLM-based)
│   │       ├── form/             # Form filling
│   │       ├── captcha/          # CAPTCHA handling
│   │       ├── bql/              # Browser Query Language
│   │       ├── llm/              # LLM clients
│   │       ├── vision/           # Visual analysis
│   │       ├── browser/          # Browser automation
│   │       ├── page/             # Page interactions
│   │       ├── data/             # Data processing
│   │       └── config/           # Configuration
│   ├── config.py                 # Global configuration
│   ├── llm.py                    # LLM client (SimpleOllama)
│   └── iterative_extractor.py    # Legacy (use extraction/ instead)
├── docs/                         # Documentation
├── logs/                         # Execution logs
└── screenshots/                  # Captured screenshots
```

---

## Components

### Extraction Component (`streamware/components/extraction/`)

Pure LLM-based product extraction. NO REGEX.

#### Modules

| Module | Purpose |
|--------|---------|
| `page_analyzer.py` | LLM-based page type detection |
| `container_finder.py` | LLM-based container discovery |
| `field_detector.py` | LLM-based field identification |
| `llm_patterns.py` | LLM generates regex/selectors on demand |
| `llm_extractor.py` | Main orchestrator |

#### Key Functions

```python
# Page Analysis
analyze_page_type(page, llm) -> {page_type, has_products, confidence}
detect_price_format(page, llm) -> {format, currency, sample}

# Container Detection
find_product_containers(page, llm, instruction) -> {found, containers, best}
analyze_container_content(page, llm, selector) -> {is_product_container, content_type}

# Field Detection
detect_product_fields(page, llm, container_selector) -> {found, fields, completeness}
extract_field_value(page, llm, element, field_name) -> str

# Pattern Generation (LLM creates regex)
generate_price_pattern(page, llm) -> {pattern, currency, format}
generate_product_link_pattern(page, llm) -> {pattern, selector}
generate_container_selector(page, llm, content_type) -> {selector, count, confidence}
generate_field_selector(page, llm, container, field_name) -> {selector, confidence}
generate_extraction_strategy(page, llm, instruction) -> {container_selector, fields, filters}

# Full Extraction
llm_extract_products(page, llm, instruction, max_items) -> {products, count, metadata}
```

#### Usage

```python
from curllm_core.streamware.components.extraction import llm_extract_products

result = await llm_extract_products(
    page=page,
    llm=llm,
    instruction="Find all products under 500zł",
    max_items=50
)

for product in result["products"]:
    print(f"{product['name']}: {product['price']} zł")
```

---

### Form Component (`streamware/components/form/`)

Intelligent form filling with LLM verification.

#### Modules

| Module | Purpose |
|--------|---------|
| `detect.py` | Form detection |
| `fill.py` | Field filling |
| `submit.py` | Form submission |
| `smart_orchestrator.py` | LLM-driven orchestration |

#### Key Features

- **Field type validation** - Prevents mapping text to file inputs
- **Per-field verification** - LLM verifies each fill
- **Post-submit evaluation** - LLM checks success
- **Retry mechanisms** - LLM-guided retries
- **CAPTCHA handling** - Visual LLM for CAPTCHA

#### Usage

```python
from curllm_core.streamware.components.form import SmartFormOrchestrator

orchestrator = SmartFormOrchestrator(page, llm, run_logger)
result = await orchestrator.orchestrate(
    user_data={"email": "test@example.com", "message": "Hello"},
    instruction="Fill contact form"
)
```

---

### Decision Component (`streamware/components/llm_decision.py`)

LLM-based decision making. Replaces hardcoded regex patterns.

#### Functions

```python
# Instruction Parsing (NO REGEX)
extract_fields_from_instruction_llm(llm, instruction) -> {field: value}
interpret_instruction_llm(llm, instruction) -> {intent, url, form_data, steps}

# Selector Generation (NO HARDCODED SELECTORS)
parse_selector_name_llm(llm, selector) -> field_name
generate_selector_for_field_llm(llm, field_name, form_fields) -> selector

# Action Planning
plan_next_action_llm(llm, instruction, page_context, history) -> {type, selector, value}
validate_action_llm(llm, action, before_state, after_state) -> {success, reason}
```

#### Before vs After

```python
# BEFORE (hardcoded regex):
patterns = {
    'email': r'email[=:]([^,]+)',
    'name': r'name[=:]([^,]+)',
}
match = re.search(patterns['email'], instruction)

# AFTER (LLM-based):
fields = await extract_fields_from_instruction_llm(llm, instruction)
# Returns: {"email": "test@example.com", "name": "John Doe"}
```

---

### BQL Component (`streamware/components/bql/`)

Browser Query Language for declarative browser automation.

#### Example Queries

```bql
QUERY products FROM "https://shop.example.com" {
    name: .product-title
    price: .price
    url: a@href
}
WHERE price < 500
```

---

### Vision Component (`streamware/components/vision/`)

Visual analysis using OpenCV and Vision LLM.

#### Features

- CAPTCHA detection and solving
- Form field analysis from screenshots
- Distorted text detection
- Visual element identification

---

## Configuration

### Environment Variables

```bash
# LLM Configuration
CURLLM_LLM_MODEL=qwen2.5:7b
CURLLM_OLLAMA_HOST=http://localhost:11434
CURLLM_LLM_BACKEND=ollama

# Planner Configuration
CURLLM_PLANNER_MAX_CHARS=8000
CURLLM_PLANNER_GROWTH_PER_STEP=2000
CURLLM_PLANNER_MAX_CAP=20000
CURLLM_STALL_LIMIT=5

# Browser Configuration
CURLLM_HEADLESS=true
CURLLM_STEALTH=true
CURLLM_TIMEOUT=30000

# Vision Configuration
CURLLM_VISION_MODEL=llava:7b
CURLLM_VISION_FORM_ANALYSIS=false
```

---

## Pipeline Architecture

### Product Extraction Pipeline

```
1. Page Analysis (LLM)
   ↓
2. Container Detection (LLM)
   ↓
3. Field Detection (LLM)
   ↓
4. Data Extraction (LLM for each item)
   ↓
5. Filtering (LLM interprets criteria)
```

### Form Filling Pipeline

```
1. Form Detection
   ↓
2. Field Mapping (LLM)
   ↓
3. Fill with Verification (LLM per field)
   ↓
4. CAPTCHA Handling (Vision LLM)
   ↓
5. Submit with Evaluation (LLM)
   ↓
6. Retry if needed (LLM guidance)
```

---

## Best Practices

### 1. Always Use LLM for Pattern Matching

```python
# ❌ BAD - Hardcoded regex
price = re.search(r'\d+[,.]?\d*\s*zł', text)

# ✅ GOOD - LLM generates pattern
pattern_info = await generate_price_pattern(page, llm)
# Use pattern_info["pattern"] if needed, or let LLM extract directly
```

### 2. Always Use LLM for Selectors

```python
# ❌ BAD - Hardcoded selector
selector = "[name='email']"

# ✅ GOOD - LLM finds selector
selector_info = await generate_selector_for_field_llm(llm, "email", form_fields)
selector = selector_info["selector"]
```

### 3. Atomic Functions

```python
# ❌ BAD - Monolithic function
async def extract_everything(page):
    # 500 lines of code...

# ✅ GOOD - Atomic functions
page_type = await analyze_page_type(page, llm)
containers = await find_product_containers(page, llm)
fields = await detect_product_fields(page, llm, container)
products = await extract_products(page, llm, container, fields)
```

### 4. Logging Everything

```python
# Always use run_logger for transparency
if run_logger:
    run_logger.log_text("🔍 Analyzing page type...")
    run_logger.log_code("json", json.dumps(result, indent=2))
```

---

## Testing

### Unit Tests

```python
from curllm_core.streamware.components.extraction import analyze_page_type

async def test_page_analysis():
    result = await analyze_page_type(mock_page, mock_llm)
    assert "page_type" in result
    assert result["page_type"] in ["product_listing", "single_product", "category", "homepage", "other"]
```

### Integration Tests

```bash
# Test extraction on real site
curllm --stealth "https://example-shop.com/products" -d "Find all products"
```

---

## Migration Guide

### From Old iterative_extractor.py

```python
# OLD (deprecated)
from curllm_core.iterative_extractor import IterativeExtractor
extractor = IterativeExtractor(page, llm, instruction)
result = await extractor.run()

# NEW (recommended)
from curllm_core.streamware.components.extraction import llm_extract_products
result = await llm_extract_products(page, llm, instruction)
```

### From Hardcoded Patterns

```python
# OLD (hardcoded)
if "email" in field_name:
    selector = f"[name='{field_name}']"

# NEW (LLM-based)
selector = await generate_selector_for_field_llm(llm, "email", form_fields)
```

---

## Troubleshooting

### LLM Returns Invalid JSON

The `_parse_json_response()` helper handles this:
- Tries multiple regex patterns to find JSON
- Falls back gracefully

### No Products Found

1. Check page type: `await analyze_page_type(page, llm)`
2. Check containers: `await find_product_containers(page, llm)`
3. Verify with screenshot: Check `screenshots/` folder

### Form Not Submitting

1. Use `SmartFormOrchestrator` with verification
2. Check for CAPTCHA: `await orchestrator._detect_captcha()`
3. Review LLM logs for field mapping issues

---

## Contributing

1. **No hardcoded patterns** - Always use LLM
2. **Atomic functions** - One function, one purpose
3. **Full logging** - Use run_logger everywhere
4. **Type hints** - All functions must have type hints
5. **Docstrings** - Document all public functions
