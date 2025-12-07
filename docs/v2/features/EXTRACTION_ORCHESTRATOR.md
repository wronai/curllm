# 🎭 Transparent LLM-based Extraction Orchestrator

## Koncepcja

Podobnie jak **Form Orchestrator**, **Extraction Orchestrator** zastępuje sztywne algorytmy inteligentnym planowaniem LLM. Zamiast ślepo wywoływać `products.heuristics` na każdej stronie, **LLM planuje strategię ekstrakcji** i **nawiguje do właściwych stron**.

## Problem

**Przed Orchestrator:**
```
User: "Extract products under 150zł from ceneo.pl"
System: 
  1. Otwiera ceneo.pl (strona główna z kategoriami)
  2. Wywołuje products.heuristics
  3. ❌ Zwraca 0 produktów (bo to kategorie, nie produkty!)
```

**Po Orchestrator:**
```
User: "Extract products under 150zł from ceneo.pl"
LLM (Phase 1 - Detection): "To zadanie ekstrakcji produktów z limitem cenowym 150zł"
LLM (Phase 2 - Strategy): "Strona główna nie ma produktów. Nawiguję do kategorii 'Urządzenia sprzątające' (tanie produkty), scrolluję, potem wywołuję products.heuristics"
LLM (Phase 3 - Navigation): Nawiguje do https://www.ceneo.pl/Urzadzenia_sprzatajace
LLM (Phase 4 - Extraction): Wywołuje products.heuristics na stronie kategorii
LLM (Phase 5 - Validation): ✅ Znalazło 15 produktów, jakość dobra, zwracam wynik
```

## 5 Faz Orkiestracji

### Phase 1: Detection
LLM analizuje instrukcję i określa:
- Typ ekstrakcji (products, links, articles, tables, text)
- Kryteria filtrowania (price_limit, keywords, category)

**Przykład:**
```json
{
  "extraction_type": "products",
  "criteria": {
    "price_limit": 150,
    "keywords": [],
    "category": ""
  },
  "reasoning": "Ekstrakcja produktów z limitem cenowym 150zł"
}
```

### Phase 2: Strategy
LLM planuje strategię:
- Czy można ekstrahować bezpośrednio? Czy trzeba nawigować?
- Jakie akcje nawigacji (click na kategorię, scroll, search)?
- Które narzędzie ekstrakcji użyć?

**Kluczowa innowacja:** LLM dostaje **konkretne linki** ze strony, nie wymyśla generycznych selectorów!

**Przykład:**
```json
{
  "requires_navigation": true,
  "navigation_actions": [
    {
      "type": "click",
      "href": "https://www.ceneo.pl/Elektronika",
      "reason": "Navigate to electronics category (likely has cheap products)"
    },
    {
      "type": "scroll",
      "times": 3,
      "reason": "Load more products"
    }
  ],
  "extraction_tool": "products.heuristics",
  "tool_args": {"threshold": 150},
  "reasoning": "Homepage shows categories, not products. Navigate to category first."
}
```

### Phase 3: Navigation
Wykonuje zaplanowane akcje nawigacji:
- `type: "click"` z `href` → `page.goto(href)`
- `type: "click"` z `selector` → `page.click(selector)`
- `type: "scroll"` → scroll down N razy

### Phase 4: Extraction
Wywołuje wybrane narzędzie ekstrakcji:
- `products.heuristics` - ekstrakcja produktów z heurystyką
- `extract.links` - ekstrakcja linków
- `articles.extract` - ekstrakcja artykułów

### Phase 5: Validation
LLM waliduje wyniki:
- Czy dane pasują do instrukcji?
- Czy jakość jest akceptowalna?
- Czy zatwierdzić czy powtórzyć?

**Przykład:**
```json
{
  "approved": true,
  "quality_score": 0.9,
  "issues": [],
  "reasoning": "Znaleziono 15 produktów poniżej 150zł, wszystkie mają nazwy, ceny i URL"
}
```

## Quick Start

### 1. Włącz Orchestrator

```bash
echo "CURLLM_EXTRACTION_ORCHESTRATOR=true" >> .env
```

### 2. Restart Serwisów

```bash
./curllm --stop-services
./curllm --start-services
```

### 3. Test

```bash
./curllm https://ceneo.pl -d "Find all products under 150zł and extract names, prices and urls"
```

### 4. Sprawdź Logi

```bash
tail -500 $(ls -t logs/*.md | head -1) | grep -E "(PHASE|🎯 DECISION)"
```

Powinieneś zobaczyć:
```
━━━ PHASE 1: Detection ━━━
   🎯 DECISION (Detection):
━━━ PHASE 2: Strategy ━━━
   🎯 DECISION (Strategy):
━━━ PHASE 3: Navigation ━━━
   🎯 DECISION (Navigation):
━━━ PHASE 4: Extraction ━━━
   🎯 DECISION (Extraction):
━━━ PHASE 5: Validation ━━━
   🎯 DECISION (Validation):
✅ Orchestration Complete
```

## Konfiguracja

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `CURLLM_EXTRACTION_ORCHESTRATOR` | `false` | Włącz orkiestrator ekstrakcji |
| `CURLLM_EXTRACTION_ORCHESTRATOR_TIMEOUT` | `120` | Timeout w sekundach |

## Tryb Hybrydowy (Rekomendowany!)

Orkiestrator **automatycznie** przełącza się na fallback jeśli zawiedzie:

```
🎭 Extraction Orchestrator enabled
━━━ PHASE 1: Detection ━━━ ✅
━━━ PHASE 2: Strategy ━━━ ✅
━━━ PHASE 3: Navigation ━━━ ❌ ERR_TIMEOUT
⚠️  Orchestrator failed, falling back to standard planner
🔧 Using standard LLM planner
✅ Task completed via fallback
```

## Zalety vs. Standardowy Planner

| Funkcja | Standardowy Planner | Extraction Orchestrator |
|---------|---------------------|------------------------|
| Strategia nawigacji | ❌ Losowe klikanie | ✅ LLM planuje całą ścieżkę |
| Wybór kategorii | ❌ Pierwsza znaleziona | ✅ LLM wybiera najbardziej odpowiednią |
| Reasoning | ❌ Brak | ✅ LLM wyjaśnia DLACZEGO |
| Walidacja wyników | ❌ Brak | ✅ LLM sprawdza jakość |
| Fallback | ✅ Automatyczny | ✅ Automatyczny |
| Transparentność | ⭐⭐ | ⭐⭐⭐⭐⭐ |

## Architektura

```
User Request
     ↓
┌─────────────────────────────────────┐
│  Extraction Orchestrator (LLM)      │
├─────────────────────────────────────┤
│  Phase 1: Detection                 │  ← Wykrywa typ ekstrakcji
│  Phase 2: Strategy                  │  ← Planuje nawigację + ekstrakcję
│  Phase 3: Navigation                │  ← Wykonuje nawigację
│  Phase 4: Extraction                │  ← Wywołuje narzędzie
│  Phase 5: Validation                │  ← Waliduje wyniki
└─────────────────────────────────────┘
     ↓ (jeśli sukces)
   Result
     ↓ (jeśli fail)
┌─────────────────────────────────────┐
│  Standard LLM Planner (Fallback)    │
└─────────────────────────────────────┘
```

## Przykłady Użycia

### Ceneo.pl - Produkty

```bash
./curllm curllm --stealth https://ceneo.pl -d "Find all products under 150zł and extract names, prices and urls"
```

**Orkiestrator:**
1. Wykrywa ekstrakcję produktów z limitem 150zł
2. Planuje nawigację do kategorii z tanimi produktami
3. Nawiguje → Scrolluje → Ekstrahuje
4. Waliduje i zwraca wyniki

### Allegro.pl - Aukcje

```bash
./curllm curllm --stealth https://allegro.pl -d "Extract all auctions ending today with price below 100zł"
```

**Orkiestrator:**
1. Wykrywa ekstrakcję aukcji z kryterium czasu + ceny
2. Planuje wyszukiwanie lub nawigację do filtrów
3. Nawiguje + Filtruje + Ekstrahuje
4. Zwraca wyniki

### News Site - Artykuły

```bash
./curllm https://wyborcza.pl -d "Extract all article titles and links from politics section"
```

**Orkiestrator:**
1. Wykrywa ekstrakcję artykułów z sekcji "politics"
2. Planuje nawigację do sekcji polityka
3. Nawiguje + Ekstrahuje
4. Zwraca artykuły

## Debugging

### Sprawdź czy orkiestrator się uruchomił

```bash
grep "🎭 Extraction Orchestrator" $(ls -t logs/*.md | head -1)
```

### Sprawdź wszystkie fazy

```bash
grep -E "(PHASE|🎯 DECISION)" $(ls -t logs/*.md | head -1)
```

### Sprawdź błędy

```bash
grep "❌ ERROR" $(ls -t logs/*.md | head -1)
```

### Sprawdź czy był fallback

```bash
grep "falling back to standard planner" $(ls -t logs/*.md | head -1)
```

## Porównanie z Form Orchestrator

| Aspekt | Form Orchestrator | Extraction Orchestrator |
|--------|-------------------|------------------------|
| Cel | Wypełnianie formularzy | Ekstrakcja danych |
| Fazy | 5 (Field Mapping → Validation) | 5 (Detection → Validation) |
| Nawigacja | Rzadko potrzebna | Często kluczowa |
| Narzędzia | form.fill, field.detect | products.heuristics, extract.links |
| Fallback | Deterministyczny | Standardowy planner |
| Transparentność | ✅ Pełna | ✅ Pełna |

## Limitacje

1. **Timeout** - Długie LLM prompty mogą przekroczyć 120s
2. **Kodowanie URL** - Polskie znaki wymagają specjalnego encodingu
3. **Dynamiczne strony** - JavaScript heavy sites mogą wymagać dodatkowych wait
4. **Captcha** - Orkiestrator nie omija captcha (użyj `--captcha-solver`)

## Roadmap

- [ ] Multi-page extraction (paginacja automatyczna)
- [ ] Smart retry logic (jeśli extraction zwraca 0, spróbuj innej kategorii)
- [ ] Adaptive thresholds (jeśli 0 produktów <150zł, spróbuj <200zł)
- [ ] Integration with BQL (Browser Query Language)

## Dokumentacja Techniczna

- **Kod:** `curllm_core/extraction_orchestrator.py`
- **Config:** `curllm_core/config.py` (linie 44-46)
- **Integration:** `curllm_core/task_runner.py` (linie 975-1006)
- **Prompts:** `extraction_orchestrator.py` metody `_build_*_prompt()`

## Podsumowanie

✅ **5-fazowa orkiestracja** podobna do Form Orchestrator  
✅ **LLM planuje strategię** zamiast sztywnych algorytmów  
✅ **Konkretne linki** w promptach (nie generyczne selektory)  
✅ **Automatyczny fallback** do standardowego plannera  
✅ **Pełna transparentność** - każda decyzja jest logowana  
✅ **Hybrydowy tryb** - best of both worlds  

**Użyj orkiestratora dla complex extraction tasks z nawigacją!**
