# Iterative Extractor - Fast Atomic DOM Queries

## Problem z Obecnym Podejściem

### ❌ Stare: Wysyłanie Całego DOM Tree do LLM
```
DOM Tree: 100KB → LLM (7-10s) → Decision
└─ Jeśli products.heuristics zwraca 0, nie wiesz dlaczego
```

**Problemy:**
- 🐌 **Wolne**: 7-12 sekund na generację (ogromny kontekst)
- 💰 **Drogie**: Duży prompt = wysokie koszty
- ❌ **Brak debugowania**: All-or-nothing, brak insight dlaczego failed
- 🔄 **Nieefektywne**: Wysyła dane które nigdy nie są użyte

## ✨ Nowe Rozwiązanie: Iterative Extractor

### 4-Step Atomic Approach

```
┌─────────────────────────────────────────────┐
│ Step 1: Quick Page Check (~100ms)           │
│ Fast JS: Has prices? Product links? Count?  │
│ Decision: Continue or skip                  │
└──────────────┬──────────────────────────────┘
               │ ✅ Product page
               v
┌─────────────────────────────────────────────┐
│ Step 2: Container Detection (~200ms)        │
│ Find pattern: .product-box? article?        │
│ Return: Best selector + count               │
└──────────────┬──────────────────────────────┘
               │ ✅ Found containers
               v
┌─────────────────────────────────────────────┐
│ Step 3: Field Location Detection (~150ms)   │
│ Analyze FIRST container: Where is name?     │
│ Where is price? Where is URL?               │
└──────────────┬──────────────────────────────┘
               │ ✅ Fields mapped
               v
┌─────────────────────────────────────────────┐
│ Step 4: Data Extraction (~300ms)            │
│ Extract using discovered strategy           │
│ Return: Clean product data                  │
└─────────────────────────────────────────────┘

Total: ~750ms (vs 7-12s!)
```

## 🚀 Przykład Użycia

### Automatyczne (Domyślne):
```bash
# Iterative Extractor jest domyślnie enabled
curllm --stealth "https://ceneo.pl/..." -d "Find products under 150zł"
```

### Programatyczne:
```python
from curllm_core.iterative_extractor import iterative_extract

result = await iterative_extract(
    instruction="Find products under 150zł",
    page=page,
    llm=llm,
    run_logger=logger
)

# Result structure:
{
    "products": [
        {"name": "...", "price": 149.99, "url": "..."},
        ...
    ],
    "count": 10,
    "reason": "Success",
    "metadata": {
        "checks_performed": [...],
        "decisions": [...],
        "extraction_strategy": {
            "container_selector": ".product-box",
            "fields": {...}
        }
    }
}
```

## 📊 Jak to Działa?

### Step 1: Quick Page Check
**Cel**: Szybko określić czy strona zawiera produkty

**JavaScript (~100ms)**:
```javascript
{
    has_prices: true,
    price_count: 45,
    has_product_links: true,
    product_link_count: 38,
    page_type: 'product_listing'
}
```

**Decyzja**: Czy kontynuować? (TAK/NIE)

### Step 2: Container Detection  
**Cel**: Znaleźć wzorzec kontenerów produktów

**JavaScript (~200ms)**:
```javascript
{
    best: {
        selector: ".product-box",
        count: 38,
        has_link: true,
        has_price: true,
        has_image: true
    }
}
```

**Decyzja**: Który selektor użyć do ekstrakcji

### Step 3: Field Location Detection
**Cel**: Zmapować gdzie w kontenerze są dane

**JavaScript (~150ms)** - Analizuje TYLKO pierwszy kontener:
```javascript
{
    fields: {
        name: {
            selector: "h3.product-name",
            sample: "Odkurzacz ABC"
        },
        price: {
            selector: "span.price",
            sample: "149.99 zł",
            value: 149.99
        },
        url: {
            selector: "a[href]",
            sample: "https://ceneo.pl/12345"
        }
    },
    completeness: 1.0  // 100% pól znaleziono
}
```

**Decyzja**: Czy mamy wystarczająco danych? (completeness >= 0.5)

### Step 4: Data Extraction
**Cel**: Wyciągnij dane używając odkrytej strategii

**JavaScript (~300ms)** - Używa strategii z Step 3:
```javascript
// For each container:
containers.forEach(container => {
    const name = container.querySelector("h3.product-name").innerText;
    const price = parseFloat(container.querySelector("span.price").innerText);
    const url = container.querySelector("a[href]").href;
    
    products.push({name, price, url});
});
```

## 🔍 Pełne Logowanie

Każdy krok loguje szczegóły:

```
🔄 ═══ ITERATIVE EXTRACTOR ═══

🔍 Step 1: Quick Page Check
Running fast indicators check...
{
  "has_prices": true,
  "price_count": 45,
  "has_product_links": true,
  "product_link_count": 38,
  "page_type": "product_listing"
}

🔍 Step 2: Container Structure Detection
Looking for product_listing containers...
{
  "found": true,
  "best": {
    "selector": ".product-box",
    "count": 38,
    "has_link": true,
    "has_price": true
  }
}

🔍 Step 3: Field Location Detection
Analyzing fields in .product-box...
{
  "found": true,
  "fields": {
    "name": {"selector": "h3.product-name", "sample": "Odkurzacz ABC"},
    "price": {"selector": "span.price", "value": 149.99},
    "url": {"selector": "a[href]", "sample": "https://ceneo.pl/12345"}
  },
  "completeness": 1.0
}

🔍 Step 4: Data Extraction
Extracting up to 50 items using strategy...
{
  "count": 38,
  "sample": [
    {"name": "Odkurzacz ABC", "price": 149.99, "url": "..."},
    {"name": "Mop XYZ", "price": 139.00, "url": "..."},
    {"name": "Robot DEF", "price": 145.50, "url": "..."}
  ]
}

✅ Iterative Extractor succeeded - found 38 items
```

## 📈 Porównanie Performance

| Metryka | Stare (Full DOM) | Nowe (Iterative) | Improvement |
|---------|------------------|------------------|-------------|
| **Czas**| 7-12s | 0.5-1s | **10-20x** ⚡ |
| **Prompt size** | 100KB | 1-2KB | **50-100x** 📉 |
| **Debugowanie** | ❌ Brak | ✅ Pełne | **∞** 🔍 |
| **Early exit** | ❌ Nie | ✅ Tak | **Smart** 🧠 |
| **LLM calls** | 1 duże | 0 (pure JS!) | **0 cost** 💰 |

**Kluczowa różnica**: Iterative Extractor używa **czystego JavaScript** - LLM NIE jest używany!

## ⚙️ Konfiguracja

### Environment Variables:

```bash
# Enable/disable
CURLLM_ITERATIVE_EXTRACTOR=true  # Default: true

# Max items to extract
CURLLM_ITERATIVE_EXTRACTOR_MAX_ITEMS=50  # Default: 50
```

### W .env:
```bash
# Fast atomic extraction (domyślnie włączone)
CURLLM_ITERATIVE_EXTRACTOR=true
CURLLM_ITERATIVE_EXTRACTOR_MAX_ITEMS=50
```

## 🎯 Kiedy Używać?

### ✅ Idealne dla:
- **E-commerce**: Ceneo, Allegro, Amazon
- **Product listings**: Listy produktów z cenami
- **Structured data**: Powtarzalne wzorce
- **Fast extraction**: Gdy liczy się prędkość

### ⚠️ Nie idealne dla:
- **Complex layouts**: Bardzo nietypowe struktury
- **Dynamic rendering**: Heavy JavaScript apps (ale może działać z wait)
- **Custom widgets**: Niestandarowe komponenty

## 🔧 Troubleshooting

### Problem: "No product containers found"
**Diagnoza**: Step 2 nie znalazł kontenerów

**Rozwiązania:**
1. Sprawdź czy strona załadowana: `await page.wait_for_timeout(3000)`
2. Sprawdź czy bot nie wykryty: Użyj stealth mode
3. Sprawdź log "Container Detection Results" - jakie candidates?

### Problem: "Insufficient field detection"
**Diagnoza**: Step 3 nie znalazł pól (completeness < 0.5)

**Rozwiązania:**
1. Sprawdź log "Field Detection Results" - które pola missing?
2. Struktura może być nietypowa - rozważ dodanie custom patterns
3. Fallback do BQL lub heuristics

### Problem: "Count: 0" mimo że found containers
**Diagnoza**: Step 4 extraction failed

**Rozwiązania:**
1. Sprawdź czy selektory prawidłowe w Step 3
2. Może być problem z parsing (np. price format)
3. Sprawdź metadata dla details

## 🚦 Priorytety Ekstrakcji

System próbuje w kolejności:

```
1. Iterative Extractor (najszybszy)  ← NOWY! 
   └─ Success? → Return
   └─ Fail? ↓

2. BQL Orchestrator (structured)
   └─ Success? → Return
   └─ Fail? ↓

3. Extraction Orchestrator (LLM-guided)
   └─ Success? → Return
   └─ Fail? ↓

4. Standard Planner (full context)
   └─ Last resort
```

## 📝 Best Practices

### 1. **Zawsze sprawdzaj logi**
```bash
# Zobacz dokładnie co się stało
cat logs/run-*.md | grep "Iterative Extractor"
```

### 2. **Monitoruj performance**
```bash
# Sprawdź czasy wykonania
grep "fn:.*_ms" logs/run-*.md
```

### 3. **Używaj metadata**
```python
result = await iterative_extract(...)
print(result["metadata"]["extraction_strategy"])
# Dowiedz się jakiej strategii użył
```

### 4. **Test na różnych stronach**
```bash
# Ceneo
curllm --stealth "https://ceneo.pl/..." -d "Find products"

# Allegro  
curllm --stealth "https://allegro.pl/..." -d "Find products"

# Custom
curllm --stealth "https://your-site.com/..." -d "Find products"
```

## 🎓 Przykłady

### Example 1: Ceneo Products
```bash
curllm --stealth "https://www.ceneo.pl/Telefony_komorkowe" -d "Find all smartphones under 2000zł"
```

**Log Output:**
```
🔄 Iterative Extractor enabled - trying atomic DOM queries
🔍 Step 1: Quick Page Check
   page_type: product_listing, price_count: 89
🔍 Step 2: Container Detection
   Found 89 containers with .product-box
🔍 Step 3: Field Detection
   completeness: 1.0 (all fields found)
🔍 Step 4: Data Extraction
   Extracted 89 products
✅ Iterative Extractor succeeded - found 89 items
```

### Example 2: Early Exit (Not a product page)
```bash
curllm --stealth "https://www.ceneo.pl/" -d "Find products"
```

**Log Output:**
```
🔄 Iterative Extractor enabled
🔍 Step 1: Quick Page Check
   page_type: other, price_count: 0
⚠️ Iterative Extractor returned no data: Page type not suitable
```

**Result**: Szybki exit bez marnowania czasu!

## 🏆 Podsumowanie

Iterative Extractor to **game changer** dla ekstrakcji produktów:

- ⚡ **10-20x szybszy** niż full DOM approach
- 💰 **0 kosztów LLM** (pure JavaScript)
- 🔍 **Pełna obserwowalność** każdego kroku
- 🧠 **Smart early exit** gdy strona niepasująca
- 📊 **Quality metrics** (completeness, field detection)

**Domyślnie włączony** - po prostu użyj curllm i ciesz się prędkością! 🚀
