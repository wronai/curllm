# Refaktoryzacja Complete - Architektura Modułowa Streamware

## Podsumowanie

Projekt CurLLM został zrefaktoryzowany z wykorzystaniem nowej modułowej architektury Streamware inspirowanej Apache Camel. System umożliwia tworzenie kompozytowych pipeline'ów automatyzacji webowej poprzez:

1. **Komponenty URI-based** - Routing oparty na schematach URI
2. **Composable Pipelines** - Łączenie komponentów operatorem pipe (`|`)
3. **YAML Flows** - Deklaratywne definicje pipeline'ów
4. **CLI Tools** - Narzędzia wiersza poleceń

## Struktura Projektu

### Nowa Architektura

```
curllm_core/
├── streamware/              # Nowa architektura komponentowa
│   ├── __init__.py
│   ├── core.py             # Klasy bazowe komponentów
│   ├── uri.py              # Parser URI
│   ├── exceptions.py       # Wyjątki
│   ├── registry.py         # Rejestr komponentów
│   ├── flow.py             # Flow builder
│   ├── patterns.py         # Wzorce (split, join, multicast)
│   ├── helpers.py          # Narzędzia pomocnicze
│   ├── yaml_runner.py      # Runner YAML flows
│   └── components/         # Wbudowane komponenty
│       ├── curllm.py       # Komponenty CurLLM
│       ├── web.py          # Komponenty HTTP/Web
│       ├── file.py         # Komponenty File I/O
│       └── transform.py    # Komponenty transformacji
│
└── cli/
    └── flow.py             # CLI dla YAML flows
```

### Pliki YAML Flows

```
flows/
├── README.md                          # Dokumentacja flows
├── example_browse.yaml                # Proste przeglądanie
├── example_extraction.yaml            # Ekstrakcja danych
├── example_form_fill.yaml             # Wypełnianie formularzy
├── example_scraping_pipeline.yaml     # Kompletny pipeline
├── example_bql.yaml                   # Zapytania BQL
├── example_multi_site.yaml            # Multi-site scraping
├── example_http_pipeline.yaml         # Integracja API
└── example_screenshot.yaml            # Screenshots
```

### Dokumentacja

```
docs/
└── STREAMWARE.md          # Pełna dokumentacja architektury

YAML_FLOWS.md              # Przewodnik YAML flows
REFACTORING_COMPLETE.md    # Ten plik
STREAMWARE_ARCHITECTURE.md # Szczegóły architektury
```

### Przykłady

```
examples/
├── streamware_examples.py  # 15 przykładów Streamware
├── streamware_quickstart.py # Quick start
└── examples_streamware.py  # Zrefaktoryzowane przykłady
```

## Kluczowe Funkcjonalności

### 1. Komponenty URI-based

**Przed (Legacy):**
```python
executor = CurllmExecutor()
result = executor.execute({
    "url": "https://example.com",
    "data": "Get all links",
    "params": {"stealth_mode": True}
})
```

**Po (Streamware):**
```python
from curllm_core.streamware import flow

result = flow("curllm://extract?url=https://example.com&instruction=Get all links&stealth=true").run()
```

### 2. Composable Pipelines

```python
result = (
    flow("curllm://browse?url=https://example.com&stealth=true")
    | "curllm://extract?instruction=Get product prices"
    | "transform://csv"
    | "file://write?path=products.csv"
).run()
```

### 3. YAML Flows

**Plik: `my_flow.yaml`**
```yaml
name: "Product Scraping"
description: "Extract products and save to CSV"

diagnostics: true

input:
  data:
    url: "https://shop.example.com"

steps:
  - component: "curllm://browse"
    params:
      url: "${url}"
      stealth: true
      
  - component: "curllm://extract"
    params:
      instruction: "Get all products with name and price"
      
  - component: "transform://csv"
  
  - component: "file://write"
    params:
      path: "/tmp/products.csv"
```

**Uruchomienie:**
```bash
curllm-flow run my_flow.yaml
```

### 4. Advanced Patterns

**Split/Join:**
```python
from curllm_core.streamware import split, join

result = (
    flow("http://api.example.com/items")
    | split("$.items[*]")
    | "curllm://extract?instruction=Get details"
    | join()
    | "file://write?path=results.json"
).run()
```

**Multicast:**
```python
from curllm_core.streamware import multicast

flow("curllm://extract?url=...")
    | multicast([
        "file://write?path=backup.json",
        "transform://csv",
        "http://webhook.site?method=post"
    ])
```

**Conditional Routing:**
```python
from curllm_core.streamware import choose

flow("curllm://extract?url=...")
    | choose()
        .when("$.priority == 'high'", "file://write?path=high.json")
        .when("$.priority == 'low'", "file://write?path=low.json")
        .otherwise("file://write?path=default.json")
```

## Dostępne Komponenty

### CurLLM Components (`curllm://`)

- **browse** - Przeglądanie stron
- **extract** - Ekstrakcja danych z LLM
- **fill_form** - Wypełnianie formularzy
- **screenshot** - Screenshots
- **bql** - Browser Query Language
- **execute** - Bezpośrednie wywołanie executora

### HTTP/Web Components (`http://`, `https://`, `web://`)

- GET, POST, PUT, DELETE, PATCH requests
- Nagłówki, timeout, parametry

### File Components (`file://`)

- **read** - Czytanie plików
- **write** - Zapis do plików
- **append** - Dopisywanie
- **exists** - Sprawdzanie istnienia
- **delete** - Usuwanie

### Transform Components (`transform://`)

- **json** - Parse/serialize JSON
- **jsonpath** - Ekstrakcja JSONPath
- **csv** - Konwersja CSV
- **normalize** - Normalizacja danych
- **flatten** - Spłaszczanie struktur

### Pattern Components

- **split** - Podział danych
- **join** - Łączenie danych
- **multicast** - Wielokrotne przeznaczenia
- **choose** - Routing warunkowy
- **filter** - Filtrowanie

## CLI Tools

### curllm-flow

```bash
# Uruchomienie flow
curllm-flow run my_flow.yaml

# Z zmiennymi
curllm-flow run my_flow.yaml --var url=https://example.com

# Walidacja
curllm-flow validate my_flow.yaml

# Lista flows
curllm-flow list flows/

# Informacje o flow
curllm-flow info my_flow.yaml
```

## Migracja z Legacy API

### Przykład 1: Proste przeglądanie

**Przed:**
```python
executor = CurllmExecutor()
result = executor.execute({
    "url": "https://example.com",
    "data": "browse page"
})
```

**Po (Python):**
```python
from curllm_core.streamware import flow
result = flow("curllm://browse?url=https://example.com").run()
```

**Po (YAML):**
```yaml
steps:
  - component: "curllm://browse"
    params:
      url: "https://example.com"
```

### Przykład 2: Ekstrakcja danych

**Przed:**
```python
executor = CurllmExecutor()
result = executor.execute({
    "url": "https://example.com",
    "data": "Get all products",
    "params": {"hierarchical_planner": True}
})
```

**Po (Python):**
```python
result = (
    flow("curllm://extract?url=https://example.com&instruction=Get all products&planner=true")
    | "file://write?path=products.json"
).run()
```

**Po (YAML):**
```yaml
steps:
  - component: "curllm://extract"
    params:
      url: "https://example.com"
      instruction: "Get all products"
      planner: true
  - component: "file://write"
    params:
      path: "products.json"
```

## Instalacja

### Instalacja z YAML support

```bash
# Install with PyYAML dependency
pip install -e .

# Or manually add PyYAML
pip install pyyaml
```

### Weryfikacja instalacji

```bash
# Check CLI tools
curllm-flow --help

# List available components
python -c "from curllm_core.streamware import list_available_components; print(list_available_components())"

# Run quickstart
python examples/streamware_quickstart.py
```

## Testy

### Uruchomienie testów

```bash
# Testy Streamware
pytest tests/test_streamware.py -v

# Wszystkie testy
pytest tests/ -v

# Z coverage
pytest tests/ --cov=curllm_core.streamware
```

### Walidacja flows

```bash
# Validate all example flows
for flow in flows/*.yaml; do
    curllm-flow validate "$flow"
done
```

## Przykłady Użycia

### 1. Quick Start

```python
from curllm_core.streamware import flow

# Proste przeglądanie
result = flow("curllm://browse?url=https://example.com").run()

# Pipeline
result = (
    flow("curllm://extract?url=https://news.ycombinator.com&instruction=Get stories")
    | "transform://csv"
    | "file://write?path=stories.csv"
).run()
```

### 2. YAML Flow

```bash
# Run predefined flow
curllm-flow run flows/example_extraction.yaml

# With custom variables
curllm-flow run flows/example_extraction.yaml \
    --var url=https://example.com \
    --var instruction="Get all links"
```

### 3. Advanced Patterns

```python
from curllm_core.streamware import flow, split, join, multicast

# Multi-site scraping
urls = {"urls": ["https://site1.com", "https://site2.com"]}
result = (
    flow("transform://normalize").with_data(urls)
    | split("$.urls[*]")
    | "curllm://browse?stealth=true"
    | join()
    | "file://write?path=results.json"
).run()

# Multiple outputs
flow("curllm://extract?url=...")
    | multicast([
        "file://write?path=json_backup.json",
        "transform://csv",
        "file://write?path=csv_output.csv"
    ])
```

## Korzyści z Refaktoryzacji

### 1. Modułowość
- Komponenty są niezależne i reużywalne
- Łatwe dodawanie nowych komponentów
- Separacja odpowiedzialności

### 2. Czytelność
- Deklaratywna składnia
- Przejrzysty flow
- Samopisujący się kod

### 3. Testowalność
- Jednostkowe testy komponentów
- Mockowanie łatwe
- Izolacja logiki

### 4. Elastyczność
- YAML dla konfiguracji
- Python API dla programowania
- CLI dla automatyzacji

### 5. Rozszerzalność
- Custom componenty
- Własne patterny
- Integracje z innymi systemami

## Backward Compatibility

**Legacy API nadal działa:**

```python
# To wciąż działa
from curllm_core import CurllmExecutor

executor = CurllmExecutor()
result = executor.execute({...})
```

**Można używać obu:**

```python
# Legacy
executor = CurllmExecutor()

# Streamware
from curllm_core.streamware import flow

# Oba działają równolegle
```

## Dokumentacja

### Główne pliki dokumentacji

1. **STREAMWARE.md** - Kompletna dokumentacja architektury
2. **YAML_FLOWS.md** - Przewodnik YAML flows
3. **flows/README.md** - Dokumentacja przykładowych flows
4. **STREAMWARE_ARCHITECTURE.md** - Szczegóły implementacji

### Przykłady

1. **streamware_examples.py** - 15 przykładów Python
2. **streamware_quickstart.py** - Quick start guide
3. **examples_streamware.py** - Zrefaktoryzowane przykłady
4. **flows/*.yaml** - 8 przykładowych YAML flows

## Następne Kroki

### Dla Użytkowników

1. **Przeczytaj dokumentację**: `docs/STREAMWARE.md`
2. **Uruchom przykłady**: `python examples/streamware_quickstart.py`
3. **Wypróbuj YAML flows**: `curllm-flow list flows/`
4. **Stwórz własny flow**: Skopiuj i zmodyfikuj przykład

### Dla Deweloperów

1. **Przestudiuj kod**: `curllm_core/streamware/`
2. **Uruchom testy**: `pytest tests/test_streamware.py -v`
3. **Stwórz custom component**: Użyj `@register` decorator
4. **Rozszerz funkcjonalność**: Dodaj nowe patterny

## Statystyki Refaktoryzacji

### Nowe Pliki

- **Core Framework**: 8 plików (1,900+ linii)
- **Components**: 5 plików (1,200+ linii)
- **CLI**: 1 plik (300+ linii)
- **YAML Flows**: 8 przykładów
- **Examples**: 3 pliki (600+ linii)
- **Documentation**: 4 pliki (2,500+ linii)
- **Tests**: 1 plik (300+ linii)

**Total: ~30 nowych plików, ~7,000 linii kodu**

### Komponenty

- **14 typów komponentów** zarejestrowanych
- **5 advanced patterns** (split, join, multicast, choose, filter)
- **3 interfejsy CLI** (run, validate, list, info)
- **15 przykładów Python** + **8 przykładów YAML**

## Podsumowanie

Refaktoryzacja CurLLM do architektury Streamware zapewnia:

✅ **Modułową architekturę** - Reużywalne komponenty
✅ **Composable pipelines** - Łączenie operatorem pipe
✅ **YAML flows** - Deklaratywne definicje
✅ **CLI tools** - Narzędzia wiersza poleceń
✅ **Backward compatibility** - Legacy API działa
✅ **Pełna dokumentacja** - Przewodniki i przykłady
✅ **Testy** - Unit testy dla komponentów
✅ **Extensibility** - Łatwe rozszerzanie

Projekt jest gotowy do produkcji i dalszego rozwoju!
