# Strategy Files - YAML Format for Web Automation

## Overview

Strategy files (`.yaml`) define reusable strategies for:
- **Extraction**: Product lists, articles, links
- **Form filling**: Contact forms, login, search
- **Navigation**: Multi-step workflows

## File Format

```yaml
# Strategy: Ceneo Product Extraction
url_pattern: "*.ceneo.pl/*"
task: extract_products
algorithm: statistical_containers

fallback_algorithms:
  - pattern_detection
  - llm_guided

selector: div.category-list-body > div

fields:
  name: a.go-to-product
  price: span.price
  url: a[href]
  image: img

filter: "price < 2000"
validate: "has(name, price) && count >= 5"

pre_actions:
  - wait: div.category-list-body
  - accept_cookies

metadata:
  success_rate: 0.92
  use_count: 47
  last_used: "2024-12-07"
```

## YAML Keys

| Key | Description | Example |
|-----|-------------|---------|
| `url_pattern` | URL pattern to match | `"*.shop.pl/*"` |
| `task` | Task type | `extract_products`, `fill_form` |
| `algorithm` | Primary algorithm | `statistical_containers` |
| `fallback_algorithms` | Fallback algorithms | `[pattern_detection, llm_guided]` |
| `selector` | Container selector | `div.product-card` |
| `fields` | Field mappings (dict) | `{name: h3.title, price: span.price}` |
| `filter` | Result filter expression | `"price < 1000"` |
| `validate` | Validation expression | `"has(name, price)"` |
| `form` | Form config (dict) | `{selector: form#contact, submit: button}` |
| `form.fields` | Form field mappings | `{email: input[name="email"]}` |
| `wait_for` | Wait condition | `div.loaded` |
| `pre_actions` | Actions before extraction | `[accept_cookies, scroll_load]` |
| `post_actions` | Actions after extraction | `[screenshot: result]` |
| `metadata` | Auto-generated stats | `{success_rate: 0.9, use_count: 10}` |

## Algorithms

| Algorithm | Description | Best For |
|-----------|-------------|----------|
| `statistical_containers` | Find repeating DOM patterns | Product grids |
| `pattern_detection` | Detect lists/tables | Structured data |
| `llm_guided` | LLM-assisted extraction | Complex layouts |
| `fallback_table` | Table-based extraction | Price tables |
| `fallback_links` | Link-based extraction | Product links |
| `form_fill` | Form filling | Contact forms |

## Knowledge Base

Strategies are automatically saved when successful:

```python
from curllm_core.dsl import KnowledgeBase

kb = KnowledgeBase("dsl/knowledge.db")

# Get best strategy for URL
best = kb.get_best_strategy("https://shop.pl/products", "extract_products")

# Get algorithm rankings
rankings = kb.get_algorithm_rankings(domain="shop.pl")

# Suggest algorithms for new URL
suggestions = kb.suggest_algorithms("https://new-site.com", "extract")
```

## Usage

### From Python

```python
from curllm_core.dsl import DSLParser, DSLExecutor

# Load strategy from file
parser = DSLParser()
strategy = parser.parse_file("dsl/ceneo_products.yaml")

# Execute strategy
executor = DSLExecutor(page, llm_client)
result = await executor.execute(
    url="https://www.ceneo.pl/Telefony",
    instruction="Extract products under 2000zł",
    strategy=strategy
)

if result.success:
    print(f"Extracted {len(result.data)} items")
    print(f"Algorithm: {result.algorithm_used}")
    print(f"Validation score: {result.validation_score}")
```

### From Command Line

```bash
# Use auto-detection
curllm "https://shop.pl/products" -d "Extract products"

# Use specific strategy file
curllm "https://shop.pl/products" --strategy dsl/shop_products.yaml

# Save successful strategy
curllm "https://shop.pl/products" -d "Extract products" --save-dsl
```

## Auto-Learning

The system automatically:
1. Records execution success/failure
2. Updates algorithm rankings per domain
3. Saves successful strategies to DSL files
4. Suggests best algorithms for new tasks

```python
# View knowledge base statistics
stats = kb.get_statistics()
print(f"Total strategies: {stats['total_strategies']}")
print(f"Success rate: {stats['overall_success_rate']:.2%}")
print(f"Top algorithms: {stats['top_algorithms']}")
```

## 📚 More Documentation

- **[🧬 DSL System Architecture](../docs/v2/architecture/DSL_SYSTEM.md)** - Full technical documentation
- **[⚛️ DOM Toolkit](../docs/v2/architecture/ATOMIC_QUERY_SYSTEM.md)** - Pure JS queries
- **[🏗️ Main Architecture](../docs/v2/architecture/ARCHITECTURE.md)** - System overview
- **[🏠 Main README](../README.md)** - Getting started
