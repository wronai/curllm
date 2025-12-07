# Plan Refaktoryzacji i Przypadków Testowych

*Ostatnia aktualizacja: 2025-12-07*

## 📊 Obecny Stan Systemu

```
Komponenty:
├── DSL Executor          ✅ Zintegrowany
├── Knowledge Base        ✅ SQLite działa
├── DOM Toolkit           ✅ Pure JS queries
├── Result Validator      ✅ Deterministyczny + LLM
├── Strategy Files        ✅ Format YAML
├── Specs Extraction      ✅ specs_table, dl_pairs
└── Metrics Collector     ✅ JSONL tracking
```

### Metryki Bazowe (do zmierzenia)

| Metryka | Cel | Obecny | Status |
|---------|-----|--------|--------|
| Czas ekstrakcji (avg) | < 5s | ~8s | 🔴 |
| LLM calls per extraction | 1-3 | 3-5 | 🟡 |
| Success rate (ceneo.pl) | > 90% | ~85% | 🟡 |
| Success rate (allegro.pl) | > 85% | ? | 🔴 |
| Success rate (forms) | > 95% | ~90% | 🟡 |
| Success rate (specs) | > 80% | ~75% | 🟡 |
| Knowledge Base reuse rate | > 70% | ~40% | 🔴 |

---

## 🎯 Cele Refaktoryzacji (zaktualizowane)

### 1. **Niezawodność Sieci** 🔴 WYSOKI PRIORYTET
*Źródło: TODO/curllm-wskazowki-dla-llm.md §2.1*

- [ ] Retry logic przy timeoutach (tenacity)
- [ ] Rate limiting per domena
- [ ] Graceful degradation przy błędach

### 2. **Wydajność** 🔴 WYSOKI PRIORYTET
*Źródło: TODO/curllm-wskazowki-dla-llm.md §2.2, §2.3*

- [ ] Równoległe przetwarzanie URL (asyncio Semaphore)
- [ ] Cache selektorów CSS w Knowledge Base
- [ ] Preload strategii dla znanych domen

### 3. **Dokładność Ekstrakcji** 🟡 ŚREDNI PRIORYTET

- [ ] Lepsza detekcja cen (w tym obrazkowych)
- [ ] Poprawne wykrywanie nazw produktów
- [ ] Obsługa dynamicznie ładowanych treści
- [ ] Fix parsowania specs (key/value)

### 4. **Redukcja Wywołań LLM** 🟡 ŚREDNI PRIORYTET

- [ ] Więcej logiki w Pure JS
- [ ] Lepsze cache'owanie strategii
- [ ] Fallback do deterministycznych algorytmów
- [ ] Skip validation dla specs data

### 5. **Rozszerzenie Wsparcia** 🟢 NISKI PRIORYTET

- [ ] E-commerce (ceneo, allegro, amazon, ebay)
- [ ] Ogłoszenia (olx, gumtree)
- [ ] Formularze kontaktowe
- [ ] Specyfikacje techniczne produktów

### 6. **Infrastruktura** 🟢 NISKI PRIORYTET
*Źródło: TODO/curllm-wskazowki-dla-llm.md §2.5-2.8*

- [ ] Proxy rotation
- [ ] Webhook notifications
- [ ] Scheduled jobs (cron)
- [ ] Diff detection dla zmian

---

## 🔧 Nowe Moduły do Implementacji

### A. Retry Logic (`curllm_core/retry.py`)

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def navigate_with_retry(page, url):
    await page.goto(url, timeout=30000)
```

### B. Rate Limiter (`curllm_core/rate_limiter.py`)

```python
class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.rpm = requests_per_minute
        self.domain_timestamps = defaultdict(list)
    
    async def wait_if_needed(self, domain: str):
        # ... throttle per domain
```

### C. Parallel Processor (`curllm_core/parallel.py`)

```python
async def process_urls_parallel(urls: list, max_concurrent: int = 5):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_single(url):
        async with semaphore:
            return await extract(url)
    
    return await asyncio.gather(*[process_single(u) for u in urls])
```

### D. Proxy Manager (`curllm_core/proxy_manager.py`)

```python
class ProxyManager:
    def __init__(self, proxies: List[str]):
        self.proxy_cycle = cycle(proxies)
        self.failed_proxies = set()
    
    def get_next_proxy(self) -> Optional[str]:
        # ... rotate through working proxies
```

---

## 🧪 Przypadki Testowe

### A. Testy Jednostkowe (Pure JS - bez przeglądarki)

```python
# tests/test_dom_toolkit_unit.py

class TestDOMAnalyzers:
    """Test DOM analyzers with mock page."""
    
    def test_price_pattern_detection(self):
        """Test różnych formatów cen."""
        prices = [
            ("1 234,56 zł", 1234.56),
            ("PLN 999.99", 999.99),
            ("od 500 zł", 500.0),
            ("1234.56€", 1234.56),
            ("$99.99", 99.99),
        ]
        # Verify regex patterns work
        
    def test_product_link_patterns(self):
        """Test wykrywania linków produktowych."""
        urls = [
            ("/179521263", True),      # ceneo numeric
            ("/offers/123/456", True), # ceneo offers
            ("/product-name_123.html", True),  # gral.pl
            ("/category/shoes", False),  # category
            ("/kontakt", False),  # contact
        ]
        
    def test_selector_stability(self):
        """Test stabilności generowanych selektorów."""
        # Selektory nie powinny zawierać dynamicznych ID
        
    def test_container_scoring(self):
        """Test scoringu kontenerów."""
        # Kontenery z cenami powinny mieć wyższy score
```

### B. Testy Integracyjne (z Playwright)

```python
# tests/integration/test_extraction_sites.py

@pytest.fixture
async def browser_page():
    """Setup Playwright browser."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        yield page
        await browser.close()

class TestCeneoExtraction:
    """Test extraction on ceneo.pl."""
    
    URLS = [
        "https://www.ceneo.pl/Telefony_komorkowe",
        "https://www.ceneo.pl/Laptopy",
        "https://www.ceneo.pl/Telewizory",
    ]
    
    @pytest.mark.parametrize("url", URLS)
    async def test_extract_products(self, browser_page, url):
        """Test product extraction."""
        await browser_page.goto(url, wait_until="networkidle")
        
        from curllm_core.dsl import DSLExecutor
        executor = DSLExecutor(browser_page, llm_client=None)
        
        result = await executor.execute(url, "Extract products")
        
        assert result.success
        assert len(result.data) >= 5
        
        for item in result.data[:5]:
            assert "name" in item
            assert "price" in item or "url" in item
            
    async def test_price_filter(self, browser_page):
        """Test price filtering."""
        await browser_page.goto("https://www.ceneo.pl/Telefony_komorkowe")
        
        result = await executor.execute(url, "Products under 1000zł")
        
        for item in result.data:
            assert item.get("price", 0) <= 1000

class TestFormFilling:
    """Test form automation."""
    
    FORMS = [
        ("https://prototypowanie.pl/kontakt/", ["email", "message"]),
        # Add more test forms
    ]
    
    @pytest.mark.parametrize("url,fields", FORMS)
    async def test_detect_form_fields(self, browser_page, url, fields):
        """Test form field detection."""
        await browser_page.goto(url)
        
        # Verify required fields are detected
```

### C. Testy Algorytmów

```python
# tests/test_algorithm_comparison.py

class TestAlgorithmComparison:
    """Compare algorithm performance."""
    
    async def test_statistical_vs_pattern(self):
        """Compare statistical and pattern detection."""
        url = "https://example.com/products"
        
        stat_result = await run_algorithm("statistical_containers", url)
        pattern_result = await run_algorithm("pattern_detection", url)
        
        # Compare accuracy, speed, item count
        
    async def test_fallback_chain(self):
        """Test fallback algorithm chain."""
        # When primary fails, fallback should work
        
    async def test_llm_guided_accuracy(self):
        """Test LLM-guided vs pure JS accuracy."""
        # LLM should have higher accuracy but slower
```

### D. Testy Regresji

```python
# tests/regression/test_known_sites.py

KNOWN_GOOD_EXTRACTIONS = {
    "ceneo_phones": {
        "url": "https://www.ceneo.pl/Telefony_komorkowe",
        "min_items": 10,
        "required_fields": ["name", "price", "url"],
        "selector": "div.cat-prod-row",
    },
    "allegro_laptops": {
        "url": "https://allegro.pl/kategoria/laptopy",
        "min_items": 5,
        "required_fields": ["name", "url"],
    },
}

@pytest.mark.parametrize("site_id,config", KNOWN_GOOD_EXTRACTIONS.items())
async def test_regression(site_id, config):
    """Verify known extractions still work."""
    result = await extract(config["url"])
    
    assert len(result.data) >= config["min_items"]
    for item in result.data:
        for field in config["required_fields"]:
            assert field in item
```

### E. Testy Wydajności

```python
# tests/performance/test_speed.py

class TestExtractionSpeed:
    """Test extraction performance."""
    
    @pytest.mark.benchmark
    async def test_pure_js_speed(self):
        """Pure JS extraction should be < 2s."""
        start = time.time()
        result = await extract_with_js_only(url)
        elapsed = time.time() - start
        
        assert elapsed < 2.0
        
    @pytest.mark.benchmark
    async def test_llm_guided_speed(self):
        """LLM-guided should be < 10s."""
        start = time.time()
        result = await extract_with_llm(url)
        elapsed = time.time() - start
        
        assert elapsed < 10.0
```

---

## 📋 Plan Refaktoryzacji (Zaktualizowany)

### Faza 0: Stabilizacja (CURRENT - 1 dzień) ✅

```
[x] DSL System z YAML
[x] Specs extraction (specs_table, dl_pairs)
[x] Metrics collector (JSONL)
[x] Skip LLM validation dla specs
[x] Feedback system (curllm_core/feedback.py)
[x] Atomic functions framework (functions/)
[x] Function generator (LLM-powered)
[x] CLI: curllm-feedback
[ ] Fix parsowania specs key/value
[ ] Accept cookies pre-action
```

### Faza 1: Niezawodność Sieci 🔴 (2-3 dni)

*Źródło: TODO/curllm-wskazowki-dla-llm.md §2.1*

```
[x] Implementacja retry.py ✅
    - retry_network decorator
    - exponential backoff
    - custom exceptions (NetworkError, ExtractionError, RetryExhaustedError)
    - RetryContext context manager
    - navigate_with_retry helper

[x] Implementacja rate_limiter.py ✅
    - RateLimiter class
    - AdaptiveRateLimiter (auto-adjusts on 429)
    - per-domain throttling
    - configurable RPM
    - graceful waiting

[ ] Integracja z navigation.py
    - Wrap page.goto()
    - Error handling
    - Logging
```

### Faza 2: Wydajność 🔴 (3-4 dni)

*Źródło: TODO/curllm-wskazowki-dla-llm.md §2.2, §2.3*

```
[ ] Implementacja parallel.py
    - asyncio.Semaphore
    - max_concurrent config
    - progress callback

[ ] Cache selektorów w KnowledgeBase
    - cache_selector(domain, task, selector, success_rate)
    - get_cached_selector(domain, task)
    - LRU eviction

[ ] Preload strategii
    - Load all YAML on startup
    - Memory cache
    - Hot reload on file change
```

### Faza 3: Dokładność Ekstrakcji 🟡 (3-5 dni)

```
[ ] Ulepszenie specs_table
    - Lepszy scoring tabel
    - Obsługa różnych formatów
    - Test na 10 różnych stronach

[ ] Ulepszenie parsowania cen
    - Ceny obrazkowe (OCR fallback)
    - Ceny z różnych walut
    - Ceny "od X zł"

[ ] Lepsze wykrywanie nazw
    - Ignorować ceny w nazwie
    - Preferować h1-h4, a[href]
    - Limit długości

[ ] Cookies handling
    - Auto-detect cookie popups
    - Click accept before extraction
    - Store cookie state
```

### Faza 4: Knowledge Base Enhancement 🟡 (2-3 dni)

```
[ ] Error tracking per strona
    - error_type
    - algorithm_that_failed
    - context (selector, URL pattern)

[ ] Algorithm ranking per domain
    - Auto-select best
    - Fallback chain
    - Success rate decay

[ ] Export/import strategii
    - Share between instances
    - JSON format
    - Filter by success_rate
```

### Faza 5: Infrastruktura 🟢 (3-5 dni)

*Źródło: TODO/curllm-wskazowki-dla-llm.md §2.5-2.8*

```
[ ] Proxy rotation
    - proxy_manager.py
    - Cycle through proxies
    - Mark failed proxies

[ ] Diff detection
    - diff_detector.py
    - Hash-based change detection
    - DeepDiff for detailed changes

[ ] Webhook notifications
    - Send on extraction complete
    - Send on errors
    - Configurable endpoints

[ ] Scheduled jobs (opcjonalnie)
    - APScheduler integration
    - Cron expressions
    - Persistent job store
```

### Faza 6: Walidacja i Cleanup 🟢 (2 dni)

```
[ ] Result Validator improvements
    - JSON schema validation
    - Type checking
    - Duplicate detection
    - Data sanitization

[ ] Documentation
    - Update README
    - API docs
    - Add docstrings

[ ] Code cleanup
    - Remove unused code
    - Format with black
    - Sort imports with isort
```

---

## 🔧 Narzędzia do Implementacji

### 1. Test Runner Script

```bash
#!/bin/bash
# scripts/run_extraction_tests.sh

SITES=(
    "https://www.ceneo.pl/Telefony_komorkowe"
    "https://www.ceneo.pl/Laptopy"
    "https://allegro.pl/kategoria/laptopy"
)

for site in "${SITES[@]}"; do
    echo "Testing: $site"
    curllm --stealth "$site" -d "Extract 5 products" --json > "results/$(echo $site | md5sum | cut -c1-8).json"
done
```

### 2. Metrics Collector

```python
# curllm_core/metrics.py

from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class ExtractionMetrics:
    url: str
    algorithm: str
    success: bool
    items_count: int
    execution_time_ms: int
    llm_calls: int
    errors: list[str]
    timestamp: str = None
    
    def __post_init__(self):
        self.timestamp = datetime.now().isoformat()
    
    def to_json(self):
        return json.dumps(self.__dict__)

class MetricsCollector:
    def __init__(self, filepath="metrics.jsonl"):
        self.filepath = filepath
        
    def record(self, metrics: ExtractionMetrics):
        with open(self.filepath, "a") as f:
            f.write(metrics.to_json() + "\n")
    
    def analyze(self):
        # Return success rates, avg times, etc.
        pass
```

### 3. Strategy Exporter

```python
# curllm_core/dsl/exporter.py

def export_strategies_for_sharing(kb_path: str, output_dir: str):
    """Export successful strategies for sharing between instances."""
    kb = KnowledgeBase(kb_path)
    
    strategies = kb.find_all_strategies(min_success_rate=0.8)
    
    for s in strategies:
        # Remove instance-specific metadata
        s.source_file = ""
        
        parser = DSLParser()
        parser.save_strategy(s, output_dir)
```

---

## 📈 Priorytety

| Priorytet | Zadanie | Wpływ | Wysiłek |
|-----------|---------|-------|---------|
| 🔴 HIGH | Testy regresji dla ceneo/allegro | Wysoki | Niski |
| 🔴 HIGH | Metryki wydajności | Wysoki | Niski |
| 🟡 MED | Rozszerzone wzorce cen | Średni | Średni |
| 🟡 MED | Algorithm ranking | Średni | Średni |
| 🟢 LOW | Visual/OCR detection | Niski | Wysoki |
| 🟢 LOW | Export/import strategii | Niski | Niski |

---

## 📊 Oczekiwane Rezultaty

Po zakończeniu refaktoryzacji:

| Metryka | Przed | Po |
|---------|-------|-----|
| Success rate (ceneo) | ~85% | >95% |
| Success rate (allegro) | ~60% | >85% |
| Avg extraction time | ~8s | <5s |
| LLM calls per extraction | 3-5 | 1-2 |
| KB reuse rate | ~40% | >70% |

---

## 🔗 Powiązane Dokumenty

- [DSL System](docs/v2/architecture/DSL_SYSTEM.md)
- [DOM Toolkit](docs/v2/architecture/ATOMIC_QUERY_SYSTEM.md)
- [Test Suite](tests/README.md)
