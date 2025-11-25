# curllm Tools System

Wyspecjalizowany system narzędzi z orchestracją LLM.

## Struktura

```
tools/
  ├── base.py              # BaseTool - klasa bazowa
  ├── registry.py          # Auto-discovery i rejestracja narzędzi
  ├── orchestrator.py      # LLM-driven selection & execution
  │
  ├── extraction/          # Narzędzia ekstrakcji danych
  │   ├── products_ceneo.py + .json
  │   └── [inne specjalizowane extractory]
  │
  ├── forms/               # Narzędzia manipulacji formularzy
  │   ├── price_filter.py + .json
  │   └── [inne form tools]
  │
  ├── navigation/          # Narzędzia nawigacji
  │   ├── scroll_load.py + .json
  │   └── [inne navigation tools]
  │
  └── validation/          # Narzędzia walidacji
      └── [validation tools]
```

## Jak działa?

### 1. Każde narzędzie = 2 pliki

**Python (logika):**
```python
from ..base import BaseTool

class ProductsCeneoTool(BaseTool):
    async def execute(self, page, parameters, context=None):
        # Implementacja
        return {"products": [...]}
```

**JSON (manifest):**
```json
{
  "name": "products_ceneo",
  "category": "extraction",
  "triggers": ["product.*ceneo", "ceneo.*product"],
  "parameters": {
    "type": "object",
    "properties": {
      "max_price": {"type": "number", "default": 999999}
    },
    "required": ["max_price"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "products": {"type": "array"}
    }
  }
}
```

### 2. Registry - auto-discovery

```python
from curllm_core.tools import init_tools, get_registry

# Inicjalizacja - automatyczne ładowanie wszystkich narzędzi
registry = init_tools()

# Dostęp do narzędzia
tool = registry.get("products_ceneo")
```

### 3. Orchestrator - LLM wybiera narzędzia

```python
from curllm_core.tools.orchestrator import orchestrate_with_tools

# LLM automatycznie generuje plan wykonania
result = await orchestrate_with_tools(
    instruction="Find products under 150zł on Ceneo",
    page=page,
    llm=llm,
    run_logger=logger
)
```

LLM generuje JSON plan:
```json
{
  "plan": [
    {
      "tool": "forms.price_filter",
      "parameters": {"max": 150, "submit": true},
      "description": "Apply price filter"
    },
    {
      "tool": "navigation.scroll_load",
      "parameters": {"times": 8},
      "description": "Load more products"
    },
    {
      "tool": "extraction.products_ceneo",
      "parameters": {"max_price": 150},
      "description": "Extract products"
    }
  ]
}
```

## Tworzenie nowego narzędzia

### Krok 1: Stwórz Python file

`tools/extraction/my_tool.py`:
```python
from ..base import BaseTool

class MyTool(BaseTool):
    async def execute(self, page, parameters, context=None):
        self.validate_parameters(parameters)
        value = parameters.get("value")
        
        # Twoja logika
        result = await page.evaluate("...")
        
        return {"output": result}
```

### Krok 2: Stwórz manifest JSON

`tools/extraction/my_tool.json`:
```json
{
  "name": "my_tool",
  "version": "1.0.0",
  "description": "Co robi to narzędzie",
  "category": "extraction",
  "triggers": ["keyword1", "keyword2"],
  "parameters": {
    "type": "object",
    "properties": {
      "value": {"type": "number", "default": 0}
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "output": {"type": "string"}
    }
  }
}
```

### Krok 3: Auto-register

Narzędzie zostanie automatycznie zarejestrowane przy `init_tools()`.

## Korzyści

1. **Single Responsibility** - każde narzędzie robi jedną rzecz
2. **Type-safe** - walidacja JSON schema
3. **Composable** - łączenie w pipelines
4. **LLM-friendly** - manifesty pomagają LLM wybrać właściwe narzędzie
5. **Testowalne** - każde narzędzie unit-testable
6. **Rozszerzalne** - dodaj nowe bez zmiany core

## Przykłady użycia

### Bezpośrednie wywołanie narzędzia

```python
registry = get_registry()
tool = registry.get("products_ceneo")

result = await tool.execute(
    page=page,
    parameters={"max_price": 150, "min_price": 0},
    context={}
)

print(result["products"])  # Lista produktów
```

### Orchestracja przez LLM

```python
# LLM automatycznie wybiera i łączy narzędzia
result = await orchestrate_with_tools(
    "Find cheap vacuums on Ceneo under 150zł",
    page, llm, logger
)
```

### Pipeline narzędzi

```python
# 1. Zastosuj filtr
await price_filter_tool.execute(page, {"max": 150, "submit": True})

# 2. Scrolluj aby załadować
await scroll_tool.execute(page, {"times": 8})

# 3. Wyciągnij produkty
result = await ceneo_tool.execute(page, {"max_price": 150})
```

## Debugging

Każde narzędzie loguje swoje działanie do `run_logger`:

```
🔧 ═══ TOOL ORCHESTRATOR ═══
Instruction: Find products under 150zł

📋 Execution Plan:
{
  "plan": [...]
}

🔧 Step 1/3: Apply price filter
   Tool: forms.price_filter
   Parameters: {"max": 150, "submit": true}
   ✅ Success: {"filled_fields": ["max=150"], ...}

🔧 Step 2/3: Load more products
   Tool: navigation.scroll_load
   Parameters: {"times": 8}
   ✅ Success: {"scrolls_performed": 8, ...}

🔧 Step 3/3: Extract products
   Tool: extraction.products_ceneo
   Parameters: {"max_price": 150}
   ✅ Success: {"products": [...]}
```

## Migracja z starych heuristics

Stare:
```python
result = await product_heuristics(instruction, page, logger)
```

Nowe:
```python
result = await orchestrate_with_tools(instruction, page, llm, logger)
```

LLM automatycznie wybierze właściwe narzędzie na podstawie:
- Triggersów w manifestach
- Instrukcji użytkownika
- Kontekstu strony (URL, DOM)

## Więcej informacji

Zobacz:
- `ARCHITECTURE.md` - pełna architektura systemu
- `base.py` - klasa bazowa BaseTool
- `orchestrator.py` - implementacja orkiestracji LLM
- `extraction/products_ceneo.py` - przykład specjalizowanego narzędzia
