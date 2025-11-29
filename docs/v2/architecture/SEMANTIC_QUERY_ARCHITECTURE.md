# Semantic Query Architecture

## Problem z Obecnym Systemem

### Monolityczne Heuristics (stare podejście):
```python
result = await product_heuristics(instruction, page, logger)
# Zwraca: {"products": []} lub {"products": [...]}
```

**Problemy:**
1. ❌ **Black box** - nie wiesz DLACZEGO nie działa
2. ❌ **Brak debugowania** - all-or-nothing
3. ❌ **Brak feedback** - LLM nie może dostosować strategii
4. ❌ **Nieelastyczne** - jeden sposób dla wszystkich stron
5. ❌ **Niewydajne** - skanuje cały DOM za każdym razem

### Log z monolitycznego systemu:
```
🔧 Step 1/3: Scroll to load items
   ✅ Success

🔧 Step 2/3: Extract products  
   Tool: products.heuristics
   ❌ count: 0
   
Dlaczego 0? Co poszło nie tak?
- Nie znalazł kontenerów?
- Znalazł kontenery ale nie price?
- Price był ale URL był zły?
- ???
```

## ✨ Nowe Rozwiązanie: Semantic Query Engine

### Trójwarstwowa Architektura

```
┌─────────────────────────────────────────────────────┐
│ Layer 3: Natural Language (User Input)              │
│ "Find products under 150zł with ratings > 4"        │
└────────────────────┬────────────────────────────────┘
                     │ LLM parses
                     v
┌─────────────────────────────────────────────────────┐
│ Layer 2: Structured Query (Semantic)                │
│ {                                                    │
│   "intent": "extract_products",                     │
│   "entity_type": "product",                         │
│   "fields": [                                        │
│     {"name": "name", "type": "text"},               │
│     {"name": "price", "type": "number"},            │
│     {"name": "rating", "type": "number"}            │
│   ],                                                 │
│   "filters": [                                       │
│     {"field": "price", "op": "lte", "value": 150},  │
│     {"field": "rating", "op": "gt", "value": 4}     │
│   ]                                                  │
│ }                                                    │
└────────────────────┬────────────────────────────────┘
                     │ Breaks down into
                     v
┌─────────────────────────────────────────────────────┐
│ Layer 1: Atomic Functions (Composable)              │
│                                                      │
│ Step 1: find_containers("product", min=1)           │
│   → Found 15 containers with .product-box           │
│                                                      │
│ Step 2: extract_field(container[0], "name")         │
│   → "Odkurzacz ABC XYZ"                             │
│                                                      │
│ Step 3: extract_field(container[0], "price")        │
│   → 149.99                                           │
│                                                      │
│ Step 4: extract_field(container[0], "rating")       │
│   → 4.5                                              │
│                                                      │
│ Step 5: filter(entities, price <= 150)              │
│   → 12 entities pass                                 │
│                                                      │
│ Step 6: validate(entities, required_fields)         │
│   → 10 entities valid                                │
└─────────────────────────────────────────────────────┘
```

## Przykład Użycia

### Kod:
```python
from curllm_core.semantic_query import semantic_extract

result = await semantic_extract(
    instruction="Find products under 150zł with ratings",
    page=page,
    llm=llm,
    run_logger=logger
)

print(result)
```

### Output:
```json
{
  "entities": [
    {
      "name": "Odkurzacz ABC XYZ",
      "price": 149.99,
      "url": "https://ceneo.pl/12345",
      "rating": 4.5
    },
    {
      "name": "Mop parowy DEF",
      "price": 139.00,
      "url": "https://ceneo.pl/67890",
      "rating": 4.8
    }
  ],
  "count": 10,
  "quality": {
    "completeness": 0.95,
    "containers_found": 15,
    "extraction_rate": 0.67
  }
}
```

### Log (pełna transparentność):
```
🔍 Parsed Semantic Query:
{
  "intent": "extract_products",
  "entity_type": "product",
  "fields": [
    {"name": "name", "type": "text", "required": true},
    {"name": "price", "type": "number", "required": true},
    {"name": "url", "type": "url", "required": true},
    {"name": "rating", "type": "number", "required": false}
  ],
  "filters": [
    {"field": "price", "operator": "lte", "value": 150}
  ]
}

⚙️ Executing Query with Atomic Functions
   Found 15 potential containers
   
   • find_containers: Looking for product containers...
   • find_containers: Found 15 with .product-box
   
   Container 0:
      • extract_field(name): "Odkurzacz ABC XYZ"
      • extract_field(price): 149.99
      • extract_field(url): "https://ceneo.pl/12345"
      • extract_field(rating): 4.5
      ✅ Passes filters
   
   Container 1:
      • extract_field(name): "Mop parowy DEF"
      • extract_field(price): 139.00
      • extract_field(url): "https://ceneo.pl/67890"
      • extract_field(rating): 4.8
      ✅ Passes filters
   
   Container 2:
      • extract_field(name): "Produkt XYZ"
      • extract_field(price): 189.99
      • extract_field(url): "https://ceneo.pl/11111"
      ❌ Filtered out (price > 150)
   
   ...
   
   Extracted 12 entities after filtering
   • validate_entities: Validated 10/12 entities
   
✅ Success: 10 products
   Quality: 95% complete, 67% extraction rate
```

## Korzyści

### 1. **Pełna Obserwowalność**
Widzisz dokładnie:
- Ile kontenerów znaleziono
- Jakie wartości wyciągnięto z każdego
- Które pola się nie powiodły
- Dlaczego entity zostało odrzucone

### 2. **Granularne Debugowanie**
```
Problem: products_count = 0

Stary system:
- ??? (black box)

Nowy system:
Log pokazuje:
   • find_containers: Found 15 with .product-box
   • extract_field(name): ✅ "Product..."
   • extract_field(price): ❌ None
   → Problem: nie potrafi wyciągnąć price!
   → Rozwiązanie: dodaj pattern dla tego formatu ceny
```

### 3. **Adaptive Extraction**
LLM może:
- Próbować różne selektory
- Dostosowywać strategię na podstawie feedback
- Iterować jeśli pierwsza próba nie działa

```python
# Iteracja 1: Próba z .product-box
containers = await executor.find_containers("product")
if len(containers) == 0:
    # Iteracja 2: Próba heurystyczna
    containers = await executor._find_containers_heuristic("product")
```

### 4. **Composable & Reusable**
```python
# Można łączyć funkcje atomowe w różne sposoby
# Przykład 1: Produkty z Ceneo
containers = await find_containers("product")
for c in containers:
    name = await extract_field(c, FieldSpec("name", "text"))
    price = await extract_field(c, FieldSpec("price", "number"))

# Przykład 2: Artykuły z Hacker News
containers = await find_containers("article")
for c in containers:
    title = await extract_field(c, FieldSpec("title", "text"))
    url = await extract_field(c, FieldSpec("url", "url"))
```

### 5. **Quality Metrics**
```json
{
  "quality": {
    "completeness": 0.95,      // 95% pól wypełnionych
    "containers_found": 15,    // Znaleziono 15 kontenerów
    "extraction_rate": 0.67    // 67% kontenerów → valid entities
  }
}
```

Widzisz **jakość** ekstrakcji - nie tylko count!

## Porównanie

| Feature | Monolithic Heuristics | Semantic Query Engine |
|---------|----------------------|----------------------|
| **Debugowanie** | ❌ Black box | ✅ Full trace |
| **Feedback dla LLM** | ❌ Tylko count | ✅ Szczegółowe metryki |
| **Elastyczność** | ❌ One-size-fits-all | ✅ Adaptive strategy |
| **Composability** | ❌ Monolityczne | ✅ Atomic functions |
| **Quality metrics** | ❌ Tylko count | ✅ Completeness, rate, etc. |
| **Iteracja** | ❌ All-or-nothing | ✅ Może próbować alternatyw |
| **Testowanie** | ⚠️ Trudne | ✅ Każda funkcja testowalna |

## Integracja z Obecnym Systemem

### Dodaj jako Layer przed Heuristics:

```python
# task_runner.py

# 1. Próba: Semantic Query Engine (najlepsze)
result = await semantic_extract(instruction, page, llm, logger)
if result and result["count"] > 0:
    return result

# 2. Próba: Tool Orchestrator (dobre)
result = await orchestrate_with_tools(instruction, page, llm, logger)
if result and result.get("products"):
    return result

# 3. Fallback: Monolithic Heuristics (stare)
result = await product_heuristics(instruction, page, logger)
```

### Lub jako Flag:
```bash
CURLLM_USE_SEMANTIC_QUERY=true curllm --stealth "..." -d "..."
```

## Roadmap

### Phase 1: Atomic Functions (DONE ✅)
- `find_containers()` - identyfikacja kontenerów
- `extract_field()` - ekstrakcja pojedynczego pola
- `validate_entities()` - walidacja wyników

### Phase 2: Semantic Query Parser (DONE ✅)
- Natural language → Structured query
- LLM parsuje intent, entity_type, fields, filters

### Phase 3: Quality Metrics (DONE ✅)
- Completeness rate
- Extraction rate
- Container detection stats

### Phase 4: Adaptive Strategy (TODO)
- LLM może zmieniać strategię na podstawie feedback
- Iteracyjne ulepszanie selektorów
- Auto-learning patterns

### Phase 5: Multi-Strategy Execution (TODO)
- Próbuj DOM heuristic + Vision + BQL równolegle
- Wybierz najlepszy wynik
- Ensemble voting

### Phase 6: Caching & Learning (TODO)
- Cache patterns dla popularnych stron
- Learn selectors from successful extractions
- Build site-specific knowledge base

## Przykłady

### E-commerce (Ceneo.pl):
```python
result = await semantic_extract(
    "Find products under 150zł",
    page, llm, logger
)
# → Full trace, quality metrics, 10 products
```

### News (Hacker News):
```python
result = await semantic_extract(
    "Extract article titles and URLs",
    page, llm, logger
)
# → Full trace, quality metrics, 30 articles
```

### Custom entities:
```python
result = await semantic_extract(
    "Find comments with rating > 4 stars",
    page, llm, logger
)
# → Full trace, quality metrics, 15 comments
```

## Migracja

### Stary kod:
```python
# Monolityczny
result = await product_heuristics(instruction, page, logger)
if not result or result.get("products") == []:
    # ??? Co teraz?
    pass
```

### Nowy kod:
```python
# Semantic + Atomic
result = await semantic_extract(instruction, page, llm, logger)

if result["count"] == 0:
    # Widzisz DLACZEGO:
    if result["quality"]["containers_found"] == 0:
        # Problem: nie znaleziono kontenerów
        # → Próbuj innej strategii lub innej strony
        pass
    elif result["quality"]["extraction_rate"] < 0.3:
        # Problem: kontenery OK, ale ekstrakcja pól słaba
        # → Dodaj custom patterns dla tej strony
        pass
```

## Następne Kroki

1. **Przetestuj na Ceneo:**
```bash
CURLLM_USE_SEMANTIC_QUERY=true curllm --stealth "https://ceneo.pl/..." -d "Find products under 150zł"
```

2. **Porównaj logi:**
   - Stary: `products_count: 0` (brak info)
   - Nowy: Full execution trace + quality metrics

3. **Iteruj na podstawie feedback:**
   - Jeśli `containers_found: 0` → problem z selektorami
   - Jeśli `extraction_rate: 0.1` → problem z field extraction
   - Jeśli `completeness: 0.5` → brakuje niektórych pól

4. **Rozszerz:**
   - Dodaj więcej atomic functions
   - Dodaj adaptive retry logic
   - Dodaj site-specific optimizations
