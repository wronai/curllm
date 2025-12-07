# DSL System - Strategy-Based Extraction with Knowledge Base

## Overview

The DSL (Domain Specific Language) system provides reusable extraction and form-filling strategies with automatic learning. It uses **YAML format** for human readability and wide IDE support.

```
┌─────────────────────────────────────────────────────────────────┐
│                      DSL System Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   URL    │───▶│ Knowledge DB │───▶│ Best Strategy Found? │  │
│  └──────────┘    └──────────────┘    └──────────────────────┘  │
│                                              │                   │
│                         ┌────────────────────┴───────────┐      │
│                         ▼                                ▼      │
│                   [YES: Reuse]                   [NO: Discover]  │
│                         │                                │      │
│                         ▼                                ▼      │
│              ┌──────────────────┐          ┌────────────────┐  │
│              │ Apply Strategy   │          │ DOM Toolkit    │  │
│              │ from .yaml file  │          │ (Pure JS)      │  │
│              └──────────────────┘          └────────────────┘  │
│                         │                                │      │
│                         └────────────┬───────────────────┘      │
│                                      ▼                          │
│                           ┌──────────────────┐                  │
│                           │  Validate Result │                  │
│                           │  (LLM: 1 call)   │                  │
│                           └──────────────────┘                  │
│                                      │                          │
│                                      ▼                          │
│                           ┌──────────────────┐                  │
│                           │ Save to .yaml    │                  │
│                           │ Update KB        │                  │
│                           └──────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. DSL Parser (`curllm_core/dsl/parser.py`)

Parses and generates YAML strategy files.

```python
from curllm_core.dsl import DSLParser, DSLStrategy

parser = DSLParser()

# Parse YAML file
strategy = parser.parse_file("dsl/ceneo_products.yaml")

# Generate from successful extraction
strategy = parser.generate_from_result(
    url="https://shop.pl/products",
    task="extract_products",
    selector="div.product",
    fields={"name": "h3", "price": ".price"},
    algorithm="statistical_containers",
    success=True
)

# Save to file
parser.save_strategy(strategy, "dsl/")
```

### 2. Knowledge Base (`curllm_core/dsl/knowledge_base.py`)

SQLite database tracking algorithm performance per domain.

```python
from curllm_core.dsl import KnowledgeBase, StrategyRecord

kb = KnowledgeBase("dsl/knowledge.db")

# Get best strategy for URL
best = kb.get_best_strategy("https://shop.pl/products", "extract_products")
# Returns: {"algorithm": "statistical", "selector": ".product", "success_rate": 0.95}

# Record execution result
kb.record_execution(StrategyRecord(
    url="https://shop.pl/products",
    domain="shop.pl",
    task="extract_products",
    algorithm="statistical_containers",
    selector=".product",
    fields={"name": "h3"},
    success=True,
    items_extracted=15,
    execution_time_ms=500
))

# Get algorithm rankings
rankings = kb.get_algorithm_rankings(domain="shop.pl")
# [{"algorithm": "statistical_containers", "success_rate": 0.95}, ...]

# Suggest algorithms for new URL
suggestions = kb.suggest_algorithms("https://new-site.com", "extract")
# ["statistical_containers", "pattern_detection", "llm_guided"]
```

### 3. Result Validator (`curllm_core/dsl/validator.py`)

Validates extraction results using deterministic checks + optional LLM.

```python
from curllm_core.dsl import ResultValidator

validator = ResultValidator(llm_client)

# Deterministic validation
result = validator.validate_structure(data, ["name", "price"], min_items=5)

# Price validation
result = validator.validate_prices(data)

# JSON repair
success, fixed_data = validator.try_fix_json('{"name": "test",}')

# Full validation with LLM
result = await validator.validate(
    data=extracted_items,
    instruction="Extract products under 1000zł",
    expected_fields=["name", "price", "url"],
    use_llm=True
)
```

### 4. DSL Executor (`curllm_core/dsl/executor.py`)

Orchestrates extraction with intelligent algorithm selection.

```python
from curllm_core.dsl import DSLExecutor

executor = DSLExecutor(
    page=playwright_page,
    llm_client=llm,
    run_logger=logger,
    kb_path="dsl/knowledge.db",
    dsl_dir="dsl"
)

result = await executor.execute(
    url="https://shop.pl/products",
    instruction="Extract all products",
    max_fallbacks=3
)

if result.success:
    print(f"Items: {len(result.data)}")
    print(f"Algorithm: {result.algorithm_used}")
    print(f"Validation: {result.validation_score}")
```

## YAML Strategy Format

```yaml
# dsl/shop_products.yaml
url_pattern: "*.shop.pl/*"
task: extract_products
algorithm: statistical_containers

fallback_algorithms:
  - pattern_detection
  - llm_guided

selector: div.product-card

fields:
  name: h3.title
  price: span.price
  url: a[href]
  image: img[src]

filter: "price < 2000"
validate: "has(name, price) && count >= 5"

expected_fields:
  - name
  - price
  - url
min_items: 3

pre_actions:
  - wait: div.products-container
  - accept_cookies
  - scroll_load

post_actions:
  - screenshot: result

metadata:
  success_rate: 0.95
  use_count: 42
  last_used: "2024-12-07"
```

### Form Filling Strategy

```yaml
# dsl/contact_form.yaml
url_pattern: "*.example.com/contact"
task: fill_form
algorithm: form_fill

form:
  selector: form#contact
  fields:
    email: input[name="email"]
    name: input[name="name"]
    message: textarea[name="message"]
    consent: input[type="checkbox"]
  submit: button[type="submit"]

validate: "form_submitted && no_errors"

pre_actions:
  - wait: form
  - accept_cookies

post_actions:
  - wait: .success-message
  - screenshot: confirmation

metadata:
  success_rate: 1.0
  use_count: 10
```

## Available Algorithms

| Algorithm | Description | Best For | LLM Calls |
|-----------|-------------|----------|-----------|
| `statistical_containers` | Find repeating DOM patterns | Product grids | 0 |
| `pattern_detection` | Detect lists/tables | Structured data | 0 |
| `llm_guided` | LLM-assisted extraction | Complex layouts | 1-3 |
| `fallback_table` | Table-based extraction | Price tables | 0 |
| `fallback_links` | Link-based extraction | Product links | 0 |
| `form_fill` | Form automation | Contact forms | 0-1 |

## Configuration

Environment variables:

```bash
CURLLM_DSL_ENABLED=true              # Enable DSL system
CURLLM_DSL_DIR=dsl                   # Strategy files directory
CURLLM_DSL_KNOWLEDGE_DB=dsl/knowledge.db  # Knowledge base path
CURLLM_DSL_AUTO_SAVE=true            # Auto-save successful strategies
CURLLM_DSL_MAX_FALLBACKS=3           # Max fallback algorithms to try
```

## Integration with DOM Toolkit

The DSL system uses the DOM Toolkit for atomic JavaScript queries:

```
curllm_core/
├── dom_toolkit/
│   ├── analyzers/       # Pure JS queries (0 LLM calls)
│   │   ├── structure.py # DOM depth, repeating elements
│   │   ├── patterns.py  # Container patterns, grids
│   │   ├── selectors.py # Generate stable selectors
│   │   └── prices.py    # Price detection
│   ├── statistics/      # Statistical analysis (0 LLM calls)
│   │   ├── frequency.py # Class frequencies
│   │   ├── clustering.py # Element clustering
│   │   └── scoring.py   # Candidate scoring
│   └── orchestrator/    # Minimal LLM (1-3 calls)
│       └── task_router.py
└── dsl/
    ├── parser.py        # YAML parsing
    ├── knowledge_base.py # SQLite persistence
    ├── validator.py     # Result validation
    └── executor.py      # Orchestration
```

## Auto-Learning

The system automatically learns from each execution:

1. **Records** success/failure per algorithm per domain
2. **Ranks** algorithms by success rate
3. **Saves** successful strategies to `.yaml` files
4. **Suggests** best algorithms for new domains based on history

```python
# View learning statistics
stats = kb.get_statistics()
print(f"Total strategies: {stats['total_strategies']}")
print(f"Overall success rate: {stats['overall_success_rate']:.2%}")
print(f"Top algorithms: {stats['top_algorithms']}")
```

## See Also

- [DOM Toolkit Architecture](./ATOMIC_QUERY_SYSTEM.md)
- [Semantic Query System](./SEMANTIC_QUERY_ARCHITECTURE.md)
- [Components Overview](./COMPONENTS.md)
