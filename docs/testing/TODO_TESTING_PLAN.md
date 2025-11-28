# 📋 Plan Rozwoju i Testowania Systemu Dynamicznej Detekcji

## 🎯 Cel Główny
Stworzenie środowiska testowego z zapisanymi stronami HTML do testowania i udoskonalania systemu ekstrakcji danych lokalnie, bez potrzeby łączenia się z internetem.

---

## 📦 FAZA 1: Środowisko Testowe (Test Environment)

### 1.1 Struktura Katalogów
```
curllm/
├── tests/
│   ├── fixtures/
│   │   ├── html_samples/          # Zapisane strony HTML
│   │   │   ├── polskikoszyk/
│   │   │   │   ├── homepage.html
│   │   │   │   ├── category_seafood.html
│   │   │   │   └── metadata.json
│   │   │   ├── lidl/
│   │   │   │   ├── fruits_vegetables.html
│   │   │   │   └── metadata.json
│   │   │   ├── gral/
│   │   │   │   ├── landing_page.html
│   │   │   │   └── metadata.json
│   │   │   ├── balta/
│   │   │   │   ├── products.html
│   │   │   │   └── metadata.json
│   │   │   └── komputronik/
│   │   │       ├── laptops.html
│   │   │       └── metadata.json
│   │   ├── expected_results/      # Oczekiwane wyniki
│   │   │   ├── polskikoszyk_under_100g.json
│   │   │   ├── lidl_under_500g.json
│   │   │   └── ...
│   │   └── test_scenarios.json    # Scenariusze testowe
│   ├── test_dynamic_detector.py   # Testy detektora
│   ├── test_multi_criteria.py     # Testy filtrowania
│   └── test_integration.py        # Testy integracyjne
```

### 1.2 Skrypt do Pobierania Stron (scraper.py)
**Zadanie:** Stworzyć skrypt do zapisywania stron HTML
```bash
python tests/scraper.py --url https://polskikoszyk.pl/ --output tests/fixtures/html_samples/polskikoszyk/homepage.html
```

**Funkcjonalności:**
- [ ] Pobieranie pełnego HTML ze wszystkimi zasobami inline
- [ ] Zapisywanie metadanych (URL, data pobrania, rozmiar)
- [ ] Zachowanie struktury DOM bez zewnętrznych zasobów
- [ ] Zapisywanie cookies i session info (opcjonalnie)

### 1.3 Format Metadanych (metadata.json)
```json
{
  "url": "https://polskikoszyk.pl/",
  "captured_at": "2025-11-26T08:57:00Z",
  "page_type": "product_listing",
  "total_products": 142,
  "has_prices": true,
  "has_weights": true,
  "expected_containers": [
    {
      "selector": "product-tile.product-tile",
      "count": 142,
      "correct": true
    }
  ],
  "known_issues": [
    "Carousel wrapper: div.splide__track (wrong container)"
  ]
}
```

---

## 🧪 FAZA 2: Test Cases i Scenariusze

### 2.1 Kategorie Testów

#### A. Container Detection Tests
- [ ] **Landing Pages** (np. gral.pl)
  - Oczekiwany wynik: 0 produktów, LLM reject wszystkich kandydatów
- [ ] **Product Listings** (np. polskikoszyk.pl)
  - Oczekiwany wynik: Wybór product-tile, odrzucenie splide__track
- [ ] **Carousel Wrappers** 
  - Test: System musi odrzucić carousel wrapper, wybrać faktyczne produkty
- [ ] **Navigation Elements**
  - Test: LLM musi rozpoznać i odrzucić elementy nawigacyjne
- [ ] **Sidebar Widgets**
  - Test: Rozróżnienie między sidebar a główną listą produktów

#### B. Multi-Criteria Filter Tests
- [ ] **Price Filtering**
  - "Find products under 950zł"
  - Test parsowania, ekstrakcji ceny, filtrowania
- [ ] **Weight Filtering**
  - "Find products under 100g"
  - Test ekstrakcji wagi z nazwy produktu
- [ ] **Volume Filtering**
  - "Find products under 1l"
  - Test ekstrakcji objętości
- [ ] **Multi-Criteria**
  - "Under 50zł AND under 500g"
  - Test kombinacji kryteriów
- [ ] **Semantic Filtering**
  - "Find organic products"
  - Test LLM semantic validation

#### C. Edge Cases
- [ ] **Empty Pages** - Brak produktów
- [ ] **Single Product** - Strona pojedynczego produktu
- [ ] **Invalid HTML** - Zepsuta struktura
- [ ] **JavaScript-Heavy** - SPA bez SSR
- [ ] **TailwindCSS Classes** - Długie nazwy klas (bug Komputronik)

### 2.2 Test Scenarios (test_scenarios.json)
```json
{
  "scenarios": [
    {
      "id": "polskikoszyk_weight_100g",
      "name": "Polskikoszyk - Products under 100g",
      "html_fixture": "polskikoszyk/homepage.html",
      "instruction": "Find all products under 100g",
      "expected": {
        "container_selector": "product-tile.product-tile",
        "products_count": 45,
        "criteria_type": "weight",
        "criteria_value": 100,
        "criteria_unit": "g",
        "sample_product": {
          "name": "Łosoś pacyficzny delikatnie wędzony 100g",
          "weight": 100,
          "weight_unit": "g"
        }
      },
      "assertions": {
        "llm_should_reject": ["div.splide__track", "li.splide__slide"],
        "llm_should_approve": ["product-tile.product-tile"],
        "all_products_match_criteria": true
      }
    },
    {
      "id": "gral_landing_page",
      "name": "Gral.pl - Landing page (no products)",
      "html_fixture": "gral/landing_page.html",
      "instruction": "Find all products under 950zł",
      "expected": {
        "container_selector": null,
        "products_count": 0,
        "llm_rejection_reason": "Navigation elements only, no product containers"
      },
      "assertions": {
        "llm_should_reject": ["ALL"],
        "final_products_count": 0
      }
    }
  ]
}
```

---

## 🔧 FAZA 3: Framework Testowy

### 3.1 Test Runner (test_runner.py)
**Zadanie:** Stworzyć runner do uruchamiania testów offline

```python
# tests/test_runner.py
class OfflineTestRunner:
    """Run tests using local HTML fixtures"""
    
    async def run_scenario(self, scenario_id: str):
        # 1. Wczytaj HTML fixture
        # 2. Utwórz mock Playwright page
        # 3. Wstrzyknij HTML
        # 4. Uruchom dynamic detector + multi-criteria filter
        # 5. Porównaj z expected results
        # 6. Zwróć raport
```

**Funkcjonalności:**
- [ ] Mock Playwright page (bez prawdziwej przeglądarki)
- [ ] Wstrzykiwanie HTML do mock page
- [ ] Uruchamianie pełnego pipeline'u ekstrakcji
- [ ] Porównywanie wyników z oczekiwaniami
- [ ] Generowanie raportów (pass/fail/warnings)
- [ ] Mierzenie czasu wykonania
- [ ] Coverage metrics dla LLM validation

### 3.2 Assertion Framework
```python
# tests/assertions.py
class ExtractionAssertions:
    def assert_container_selected(self, result, expected_selector):
        """Verify correct container was selected"""
    
    def assert_llm_rejected(self, result, selectors_to_reject):
        """Verify LLM rejected specific containers"""
    
    def assert_products_match_criteria(self, products, criteria):
        """Verify all products match filtering criteria"""
    
    def assert_field_completeness(self, result, min_completeness):
        """Verify field detection completeness"""
```

---

## 📊 FAZA 4: Metryki i Benchmarki

### 4.1 Metryki do Mierzenia
- [ ] **Container Detection Accuracy**
  - Correct container selected / Total tests
  - LLM rejection accuracy (false positives/negatives)
- [ ] **Field Detection Completeness**
  - Average completeness across all tests
- [ ] **Filter Accuracy**
  - Products matching criteria / Total products
- [ ] **Performance**
  - Avg time per extraction
  - LLM calls per extraction
  - Memory usage

### 4.2 Benchmark Suite
```bash
python tests/benchmark.py --all
```

**Output:**
```
=== BENCHMARK RESULTS ===
Container Detection:
  Accuracy: 95% (19/20 correct)
  LLM Rejection: 100% (all navigation elements rejected)
  
Field Detection:
  Avg Completeness: 87%
  100% completeness: 15/20 tests
  
Multi-Criteria Filtering:
  Weight filter accuracy: 100%
  Price filter accuracy: 100%
  Semantic filter accuracy: 85%
  
Performance:
  Avg extraction time: 2.3s
  Avg LLM calls: 4.2 per extraction
```

---

## 🚀 FAZA 5: Udoskonalenia Systemu

### 5.1 Obszary do Poprawy (Based on Tests)

#### A. Dynamic Container Detector
- [ ] **Problem:** LLM zbyt konserwatywny (odrzuca .widget z produktami)
  - **Rozwiązanie:** Dostroić prompt LLM, dodać więcej kontekstu
- [ ] **Problem:** Statistical analysis nie znajduje optimal depth
  - **Rozwiązanie:** Ulepszyć algorytm depth analysis
- [ ] **Problem:** Candidate generation pomija dobre kontenery
  - **Rozwiązanie:** Rozszerzyć zakres głębokości, dodać heurystyki

#### B. Multi-Criteria Filter
- [ ] **Bug:** `'price_unit'` KeyError
  - **Fix:** Obsługa brakujących pól w extracted data
- [ ] **Improvement:** Lepsza ekstrakcja wagi z tekstu
  - Pattern matching dla "100g", "0.5kg", "500 gram"
- [ ] **Improvement:** Semantic filtering z LLM
  - "organic", "gluten-free", "vegan"

#### C. LLM Validation
- [ ] **Prompt Engineering:** Lepsze prompty dla container validation
- [ ] **Few-shot Examples:** Dodać przykłady do promptów
- [ ] **Confidence Calibration:** Kalibracja threshold dla confidence
- [ ] **Error Analysis:** Analiza błędów LLM (false positives/negatives)

### 5.2 Nowe Funkcjonalności
- [ ] **Adaptive Depth Range:** Dynamiczne dostosowanie zakresu głębokości
- [ ] **Pattern Learning:** Uczenie się z udanych ekstrakcji
- [ ] **Container Caching:** Cache dla już rozpoznanych kontenerów
- [ ] **Multi-LLM Ensemble:** Użycie wielu modeli LLM i voting

---

## 🎯 FAZA 6: CI/CD Integration

### 6.1 Automated Testing
```yaml
# .github/workflows/test-dynamic-extraction.yml
name: Test Dynamic Extraction

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -e .
      - name: Run offline tests
        run: python -m pytest tests/ --html-fixtures
      - name: Generate coverage report
        run: python tests/coverage_report.py
```

### 6.2 Regression Testing
- [ ] Auto-run tests on every commit
- [ ] Compare results with baseline
- [ ] Alert on accuracy degradation
- [ ] Track metrics over time

---

## 📝 PLAN WYKONANIA (Execution Plan)

### Sprint 1 (Tydzień 1-2): Infrastruktura
- [ ] Stworzyć strukturę katalogów `tests/fixtures/`
- [ ] Napisać `scraper.py` do pobierania stron
- [ ] Pobrać 5-10 stron testowych (polskikoszyk, lidl, gral, balta, komputronik)
- [ ] Stworzyć `metadata.json` dla każdej strony
- [ ] Zdefiniować `test_scenarios.json`

### Sprint 2 (Tydzień 3-4): Test Framework
- [ ] Zaimplementować `OfflineTestRunner`
- [ ] Stworzyć mock Playwright page
- [ ] Napisać assertion framework
- [ ] Zaimplementować 5 podstawowych testów
- [ ] Uruchomić pierwszy test suite

### Sprint 3 (Tydzień 5-6): Test Coverage
- [ ] Dodać 20+ test scenarios
- [ ] Pokryć wszystkie edge cases
- [ ] Zaimplementować benchmark suite
- [ ] Zmierzyć baseline metrics
- [ ] Dokumentacja testów

### Sprint 4 (Tydzień 7-8): Improvements
- [ ] Naprawić znalezione bugi
- [ ] Udoskonalić LLM prompts
- [ ] Poprawić statistical analysis
- [ ] Optymalizacja performance
- [ ] Re-run benchmarks, porównać wyniki

### Sprint 5 (Tydzień 9-10): CI/CD
- [ ] Setup GitHub Actions
- [ ] Automated test runs
- [ ] Regression tracking
- [ ] Documentation updates
- [ ] Release v2.0

---

## 📚 Dodatkowe Zadania

### Documentation
- [ ] `TESTING.md` - Jak uruchamiać testy
- [ ] `BENCHMARKS.md` - Wyniki benchmarków
- [ ] `CONTRIBUTING.md` - Jak dodawać nowe test cases

### Tools
- [ ] `html_diff.py` - Porównywanie zmian w HTML między wersjami
- [ ] `container_visualizer.py` - Wizualizacja wykrytych kontenerów
- [ ] `llm_debug.py` - Debug LLM decisions

### Advanced
- [ ] Multi-site pattern analysis
- [ ] Automated pattern discovery
- [ ] Transfer learning z innych stron
- [ ] A/B testing dla różnych strategii

---

## ✅ Success Criteria

### Minimum Viable Testing (MVT)
- ✅ 10+ test scenarios
- ✅ 90%+ accuracy on known sites
- ✅ All tests run offline
- ✅ Tests run in <30s

### Production Ready
- ✅ 50+ test scenarios
- ✅ 95%+ accuracy
- ✅ Full CI/CD integration
- ✅ Regression tracking
- ✅ Performance benchmarks

---

## 🎉 Expected Outcomes

Po realizacji planu system będzie:
1. **Testowalny offline** - Bez potrzeby internetu
2. **Udokumentowany** - Wszystkie test cases opisane
3. **Zautomatyzowany** - CI/CD z auto-testami
4. **Ulepsony** - Wyższa accuracy dzięki testom
5. **Monitorowany** - Metryki i tracking regresji
6. **Skalowany** - Łatwo dodawać nowe test cases

**Cel:** Pewność, że system działa poprawnie na różnych stronach, z możliwością szybkiego testowania i iteracji bez dostępu do internetu.
