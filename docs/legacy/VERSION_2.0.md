# CurLLM 2.0 - Streamware Architecture

## Co Nowego w Wersji 2.0

CurLLM 2.0 wprowadza kompletną refaktoryzację architektury z wykorzystaniem wzorców z Apache Camel, tworząc modularny system komponentów do automatyzacji webowej.

### 🎯 Główne Zmiany

#### 1. **Architektura Streamware**
- Komponenty URI-based z automatycznym routingiem
- Composable pipelines z operatorem pipe (`|`)
- Reużywalne, testowalne moduły
- Extensible plugin system

#### 2. **YAML Flow System**
- Deklaratywne definicje pipeline'ów
- Wsparcie dla zmiennych i parametryzacji
- CLI tools (`curllm-flow`)
- Walidacja i debugging

#### 3. **Nowe Komponenty**
- **CurLLM**: browse, extract, fill_form, screenshot, bql
- **HTTP/Web**: GET, POST, PUT, DELETE
- **File I/O**: read, write, append
- **Transform**: JSON, JSONPath, CSV
- **Patterns**: split, join, multicast, choose, filter

#### 4. **Developer Experience**
- Intuicyjna składnia Python
- Comprehensywna dokumentacja
- 15+ przykładów Python + 8 YAML flows
- Unit testy dla komponentów

## Breaking Changes

### ❌ BRAK! - Full Backward Compatibility

Wersja 2.0 jest **w pełni kompatybilna wstecz** z 1.x:

```python
# Legacy API (1.x) - nadal działa
from curllm_core import CurllmExecutor

executor = CurllmExecutor()
result = executor.execute({
    "url": "https://example.com",
    "data": "Get data"
})

# Nowe API (2.0) - opcjonalne
from curllm_core.streamware import flow

result = flow("curllm://extract?url=https://example.com&instruction=Get data").run()
```

Możesz używać obu API jednocześnie lub migrować stopniowo.

## Migracja z 1.x do 2.0

### Opcja 1: Kontynuuj Używanie 1.x API

Wszystko działa jak wcześniej:

```python
from curllm_core import CurllmExecutor

executor = CurllmExecutor()
# ... existing code ...
```

### Opcja 2: Stopniowa Migracja

Wprowadzaj Streamware dla nowych funkcjonalności:

```python
# Stary kod - zostaw
executor = CurllmExecutor()
old_result = executor.execute({...})

# Nowy kod - używaj Streamware
from curllm_core.streamware import flow
new_result = flow("curllm://browse?url=...").run()
```

### Opcja 3: Pełna Migracja

Przepisz na Streamware dla lepszej czytelności:

**Przed (1.x):**
```python
executor = CurllmExecutor()
result = executor.execute({
    "url": "https://example.com",
    "data": "Extract products",
    "params": {
        "hierarchical_planner": True,
        "stealth_mode": True
    }
})

# Save manually
with open('/tmp/products.json', 'w') as f:
    json.dump(result, f)
```

**Po (2.0):**
```python
from curllm_core.streamware import flow

result = (
    flow("curllm://extract?url=https://example.com&instruction=Extract products&planner=true&stealth=true")
    | "file://write?path=/tmp/products.json"
).run()
```

**Lub YAML:**
```yaml
name: "Extract Products"
steps:
  - component: "curllm://extract"
    params:
      url: "https://example.com"
      instruction: "Extract products"
      planner: true
      stealth: true
  - component: "file://write"
    params:
      path: "/tmp/products.json"
```

## Nowe Możliwości

### 1. Composable Pipelines

```python
from curllm_core.streamware import flow

# Chain multiple operations
result = (
    flow("curllm://browse?url=https://shop.example.com&stealth=true")
    | "curllm://extract?instruction=Get all products"
    | "transform://jsonpath?query=$.items[*]"
    | "transform://csv"
    | "file://write?path=products.csv"
).run()
```

### 2. Advanced Patterns

```python
from curllm_core.streamware import split, join, multicast

# Batch processing
urls = {"urls": ["site1.com", "site2.com", "site3.com"]}
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
        "file://write?path=backup.json",
        "transform://csv",
        "file://write?path=output.csv"
    ])
```

### 3. YAML Workflows

```yaml
name: "Daily Scraping Job"
description: "Automated product monitoring"

diagnostics: true

input:
  data:
    url: "https://shop.example.com"
    output_dir: "/data/scraping"

steps:
  - component: "curllm://browse"
    params:
      url: "${url}"
      stealth: true
      
  - component: "curllm://extract"
    params:
      instruction: "Get all products under $100"
      planner: true
      
  - component: "transform://csv"
  
  - component: "file://write"
    params:
      path: "${output_dir}/products_$(date).csv"
```

Uruchom:
```bash
curllm-flow run daily_scraping.yaml
```

### 4. CLI Tools

```bash
# Run flows
curllm-flow run my_flow.yaml

# Validate
curllm-flow validate my_flow.yaml

# List available
curllm-flow list flows/

# Get info
curllm-flow info my_flow.yaml
```

### 5. Metrics & Monitoring

```python
from curllm_core.streamware import metrics

with metrics.track("scraping_job"):
    result = flow("curllm://extract?url=...").run()

stats = metrics.get_stats("scraping_job")
print(f"Processed: {stats['processed']}, Errors: {stats['errors']}")
```

## Instalacja

### Aktualizacja z 1.x

```bash
# Pull latest changes
git pull

# Install with YAML support
pip install -e .

# Verify
curllm-flow --help
python -c "from curllm_core import streamware; print('OK')"
```

### Nowa Instalacja

```bash
# Clone
git clone https://github.com/wronai/curllm.git
cd curllm

# Install
pip install -e .

# Setup
curllm-setup

# Test
pytest tests/test_streamware.py -v
```

## Dokumentacja

### Nowe Pliki Dokumentacji

1. **STREAMWARE_ARCHITECTURE.md** - Architektura systemu
2. **YAML_FLOWS.md** - Kompletny przewodnik YAML
3. **QUICKSTART_YAML.md** - 5-minutowy quick start
4. **docs/STREAMWARE.md** - Szczegółowa dokumentacja API
5. **flows/README.md** - Dokumentacja przykładowych flows

### Przykłady

1. **examples/streamware_examples.py** - 15 przykładów Python
2. **examples/streamware_quickstart.py** - Quick start
3. **examples_streamware.py** - Zrefaktoryzowane przykłady
4. **flows/*.yaml** - 8 przykładowych YAML flows

## Co Pozostało Bez Zmian

✅ **Core Functionality**
- CurllmExecutor API
- BQL Parser
- Hierarchical Planner
- LLM Integration
- Stealth Mode
- Captcha Solving
- Form Filling

✅ **Configuration**
- `.env` configuration
- Config module
- Logger setup

✅ **Server**
- Flask server
- API endpoints
- WebSocket support

✅ **CLI Tools (Legacy)**
- `curllm` command
- `curllm-setup`
- `curllm-doctor`
- `curllm-web`

## Nowe Zależności

```toml
dependencies = [
  # ... existing ...
  "pyyaml",  # NEW for YAML flows
]
```

## Wydajność

Streamware architecture nie wpływa negatywnie na wydajność:

- **Overhead**: < 1ms dla pipeline routing
- **Memory**: Minimal overhead dla flow builder
- **Streaming**: Efficient generator-based processing
- **Backward compat**: Zero overhead dla legacy API

## Roadmap 2.x

### 2.1 (Planowane)
- [ ] Async flow execution
- [ ] Database components (PostgreSQL, MongoDB)
- [ ] Message queue components (Kafka, RabbitMQ)
- [ ] Retry policies i circuit breakers
- [ ] Flow templates i inheritance

### 2.2 (Planowane)
- [ ] Visual flow designer (Web UI)
- [ ] Flow scheduling i cron
- [ ] Distributed execution
- [ ] Performance monitoring dashboard

### 3.0 (Przyszłość)
- [ ] Cloud-native deployment
- [ ] Kubernetes operators
- [ ] Auto-scaling
- [ ] Multi-tenant support

## Support & Community

- **Issues**: https://github.com/wronai/curllm/issues
- **Discussions**: GitHub Discussions
- **Documentation**: `docs/` directory
- **Examples**: `examples/` and `flows/`

## Changelog

### [2.0.0] - 2024-01-XX

#### Added
- ✨ Streamware component architecture
- ✨ YAML flow system with runner
- ✨ CLI tools (`curllm-flow`)
- ✨ 14 built-in components
- ✨ Advanced patterns (split, join, multicast, choose)
- ✨ Composable pipeline builder with pipe operator
- ✨ Comprehensive documentation (4 new docs)
- ✨ 23 new examples (15 Python + 8 YAML)
- ✨ Unit tests for Streamware components
- ✨ Metrics and diagnostics system

#### Changed
- 🔄 Refactored internal architecture (non-breaking)
- 📚 Updated documentation structure
- 🧪 Enhanced test coverage

#### Maintained
- ✅ Full backward compatibility with 1.x
- ✅ All existing features work unchanged
- ✅ Legacy API fully supported

## Podziękowania

Inspiracja:
- Apache Camel - Enterprise Integration Patterns
- Spring Integration - Message-driven architecture
- AWS Step Functions - State machines

## License

Apache 2.0 (bez zmian)

---

**CurLLM 2.0** - Modular, Composable, Powerful 🚀
