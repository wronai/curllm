# curllm Tool Orchestration Architecture

## Filozofia

Każde zadanie rozkładamy na **wyspecjalizowane narzędzia** (tools), które:
1. **Robią jedną rzecz dobrze** - single responsibility
2. **Są composable** - można je łączyć w pipelines
3. **Mają manifest JSON** - deklaratywny opis (parameters, output schema, przykłady)
4. **Są type-safe** - walidacja wejścia/wyjścia

## Struktura Folderów

```
curllm_core/tools/
  ├── __init__.py
  ├── registry.py              # Tool registry + autodiscovery
  ├── base.py                  # BaseTool abstract class
  ├── orchestrator.py          # LLM-driven tool selection & execution
  │
  ├── extraction/              # Data extraction tools
  │   ├── __init__.py
  │   ├── products_ceneo.py    # Specialized for Ceneo.pl products
  │   ├── products_amazon.py   # Amazon product extraction
  │   ├── products_generic.py  # Generic e-commerce
  │   ├── articles_hn.py       # HackerNews articles
  │   ├── articles_reddit.py   # Reddit posts
  │   ├── links_by_pattern.py  # Links matching pattern
  │   └── tables_to_json.py    # HTML tables → JSON
  │
  ├── forms/                   # Form manipulation tools
  │   ├── __init__.py
  │   ├── price_filter.py      # Set price min/max filters
  │   ├── search_query.py      # Fill search boxes
  │   ├── date_picker.py       # Date range selection
  │   └── dropdown_select.py   # Dropdown/select manipulation
  │
  ├── navigation/              # Page navigation tools
  │   ├── __init__.py
  │   ├── scroll_load.py       # Infinite scroll handler
  │   ├── pagination.py        # Multi-page navigation
  │   ├── category_select.py   # Category tree navigation
  │   └── click_by_text.py     # Click element by text content
  │
  └── validation/              # Data validation tools
      ├── __init__.py
      ├── price_range_check.py # Validate prices in range
      ├── url_format_check.py  # Validate URL formats
      └── required_fields.py   # Check required fields present
```

## Tool Manifest Schema

Każde narzędzie ma plik `{tool_name}.json`:

```json
{
  "name": "products_ceneo",
  "version": "1.0.0",
  "description": "Extract product listings from Ceneo.pl with price filtering",
  "category": "extraction",
  "triggers": [
    "product.*ceneo",
    "ceneo.*product",
    "product.*polish.*site"
  ],
  "parameters": {
    "type": "object",
    "properties": {
      "max_price": {
        "type": "number",
        "description": "Maximum price threshold in PLN",
        "default": 999999
      },
      "min_price": {
        "type": "number",
        "description": "Minimum price threshold in PLN",
        "default": 0
      },
      "category": {
        "type": "string",
        "description": "Product category filter",
        "optional": true
      }
    },
    "required": ["max_price"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "products": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "price": {"type": "number"},
            "url": {"type": "string", "format": "uri"}
          }
        }
      }
    }
  },
  "examples": [
    {
      "instruction": "Find products under 150zł on Ceneo",
      "parameters": {"max_price": 150},
      "expected_output": {"products": [{"name": "Example", "price": 149.99, "url": "..."}]}
    }
  ],
  "dependencies": ["playwright", "page"],
  "timeout_ms": 30000
}
```

## Tool Execution DSL (JSON-based)

LLM generuje execution plan jako JSON:

```json
{
  "plan": [
    {
      "tool": "navigation.scroll_load",
      "parameters": {"times": 6, "wait_ms": 600},
      "description": "Load more products by scrolling"
    },
    {
      "tool": "forms.price_filter",
      "parameters": {"max": 150, "submit": true},
      "description": "Apply price filter ≤150 PLN"
    },
    {
      "tool": "extraction.products_ceneo",
      "parameters": {"max_price": 150},
      "description": "Extract filtered products"
    },
    {
      "tool": "validation.price_range_check",
      "parameters": {"min": 0, "max": 150},
      "description": "Validate all prices ≤150"
    }
  ],
  "expected_output": "products",
  "fallback": "extraction.products_generic"
}
```

## Tool Orchestrator Flow

```
┌─────────────────────────────────────┐
│   Instruction from User             │
└──────────────┬──────────────────────┘
               │
               v
┌─────────────────────────────────────┐
│   Tool Orchestrator (LLM)           │
│   - Analyzes instruction            │
│   - Queries tool registry           │
│   - Generates execution plan (JSON) │
└──────────────┬──────────────────────┘
               │
               v
┌─────────────────────────────────────┐
│   Tool Executor                     │
│   - Validates parameters            │
│   - Executes tools sequentially     │
│   - Passes output as input to next  │
│   - Handles errors & fallbacks      │
└──────────────┬──────────────────────┘
               │
               v
┌─────────────────────────────────────┐
│   Result Validator                  │
│   - Checks output schema            │
│   - Runs validation tools           │
│   - Returns final result            │
└─────────────────────────────────────┘
```

## Benefits

1. **Specialized & Fast**: Each tool optimized for specific site/task
2. **Composable**: Tools can be chained (pipeline)
3. **Extensible**: Add new tools without changing core
4. **Type-safe**: JSON schema validation
5. **Testable**: Each tool unit-testable
6. **LLM-friendly**: Clear manifests help LLM choose correct tool
7. **Fallback-ready**: Generic tools as fallback for specialized ones

## Example: Ceneo Product Extraction

**User instruction:**
```
Find all products under 150zł on Ceneo special offers page
```

**LLM generates plan:**
```json
{
  "plan": [
    {
      "tool": "forms.price_filter",
      "parameters": {"max": 150, "submit": true}
    },
    {
      "tool": "navigation.scroll_load",
      "parameters": {"times": 8}
    },
    {
      "tool": "extraction.products_ceneo",
      "parameters": {"max_price": 150}
    }
  ]
}
```

**Tools execute:**
1. `forms.price_filter` → fills price form, clicks submit
2. `navigation.scroll_load` → scrolls 8 times to load products
3. `extraction.products_ceneo` → specialized Ceneo extraction

**Output:**
```json
{
  "products": [
    {"name": "Odkurzacz XYZ", "price": 149.99, "url": "https://..."},
    ...
  ]
}
```

## Migration Path

1. Convert existing heuristics → specialized tools
2. Create manifests for each tool
3. Implement tool registry & orchestrator
4. Update task_runner to use orchestrator
5. Deprecate old monolithic extraction.py
