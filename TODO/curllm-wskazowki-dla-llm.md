# Wskazówki dla LLM: Ulepszanie curllm

## Cel dokumentu

Ten dokument zawiera wytyczne dla asystentów AI pracujących nad rozwojem i ulepszaniem projektu **curllm**. Opisuje priorytetowe obszary, wzorce kodu i najlepsze praktyki.

---

## 1. Mapa projektu - gdzie co znaleźć

### Rdzeń ekstrakcji danych

```
curllm_core/
├── extraction_orchestrator.py  # Główna logika - ZACZNIJ TUTAJ
├── extraction.py               # Niskopoziomowa ekstrakcja
├── iterative_extractor.py      # Iteracyjne podejście
├── product_extract.py          # Specjalizowana ekstrakcja produktów
└── universal_field_extractor.py # Uniwersalny ekstraktor pól
```

### System DSL i uczenie się

```
curllm_core/dsl/
├── executor.py      # Wykonywanie strategii
├── knowledge_base.py # SQLite baza skuteczności
├── parser.py        # Parsowanie YAML strategii
└── validator.py     # Walidacja wyników

dsl/
├── *.yaml           # Zapisane strategie per domena
└── knowledge.db     # Baza wiedzy
```

### DOM Toolkit (bez LLM)

```
curllm_core/dom_toolkit/
├── analyzers/
│   ├── structure.py  # Analiza struktury DOM
│   ├── patterns.py   # Wykrywanie wzorców
│   ├── selectors.py  # Generowanie selektorów
│   └── prices.py     # Detekcja cen
├── statistics/
│   ├── clustering.py # Grupowanie elementów
│   ├── frequency.py  # Analiza częstotliwości
│   └── scoring.py    # Ocena trafności
└── orchestrator/
    └── task_router.py # Routing zadań
```

### Integracja LLM

```
curllm_core/
├── llm.py                    # Główna integracja
├── llm_config.py             # Konfiguracja modeli
├── llm_factory.py            # Factory pattern
├── llm_guided_extractor.py   # LLM-guided ekstrakcja
├── llm_form_orchestrator.py  # LLM dla formularzy
├── llm_planner.py            # Planowanie zadań
└── llm_heuristics.py         # Heurystyki
```

---

## 2. Priorytetowe obszary do ulepszenia

### 🔴 Wysoki priorytet

#### 2.1 Obsługa błędów sieciowych

**Problem**: Brak retry logic przy timeoutach i błędach połączenia.

**Lokalizacja**: `curllm_core/navigation.py`, `curllm_core/browser_setup.py`

**Sugestia implementacji**:

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def navigate_with_retry(page, url):
    await page.goto(url, timeout=30000)
```

#### 2.2 Równoległe przetwarzanie URL

**Problem**: Sekwencyjne przetwarzanie wielu URL jest wolne.

**Lokalizacja**: Nowy moduł `curllm_core/parallel.py`

**Sugestia**:

```python
import asyncio
from playwright.async_api import async_playwright

async def process_urls_parallel(urls: list, max_concurrent: int = 5):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_single(url):
        async with semaphore:
            # ekstrakcja
            pass
    
    tasks = [process_single(url) for url in urls]
    return await asyncio.gather(*tasks)
```

#### 2.3 Cache selektorów CSS

**Problem**: Te same selektory są odkrywane wielokrotnie dla tej samej domeny.

**Lokalizacja**: `curllm_core/dsl/knowledge_base.py`

**Rozszerzenie**:

```python
class KnowledgeBase:
    def cache_selector(self, domain: str, task_type: str, selector: str, success_rate: float):
        """Zapisz skuteczny selektor dla domeny"""
        
    def get_cached_selector(self, domain: str, task_type: str) -> Optional[str]:
        """Pobierz najlepszy selektor dla domeny"""
```

### 🟡 Średni priorytet

#### 2.4 Rate limiting

**Lokalizacja**: `curllm_core/navigation.py`

```python
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.rpm = requests_per_minute
        self.domain_timestamps = defaultdict(list)
    
    async def wait_if_needed(self, domain: str):
        now = time.time()
        minute_ago = now - 60
        
        # Wyczyść stare timestampy
        self.domain_timestamps[domain] = [
            ts for ts in self.domain_timestamps[domain] 
            if ts > minute_ago
        ]
        
        if len(self.domain_timestamps[domain]) >= self.rpm:
            wait_time = self.domain_timestamps[domain][0] - minute_ago
            await asyncio.sleep(wait_time)
        
        self.domain_timestamps[domain].append(now)
```

#### 2.5 Proxy rotation

**Lokalizacja**: Nowy `curllm_core/proxy_manager.py`

```python
from itertools import cycle
from typing import List, Optional

class ProxyManager:
    def __init__(self, proxies: List[str]):
        self.proxy_cycle = cycle(proxies)
        self.failed_proxies = set()
    
    def get_next_proxy(self) -> Optional[str]:
        for _ in range(len(self.proxies)):
            proxy = next(self.proxy_cycle)
            if proxy not in self.failed_proxies:
                return proxy
        return None
    
    def mark_failed(self, proxy: str):
        self.failed_proxies.add(proxy)
```

#### 2.6 Diff detection

**Lokalizacja**: Nowy `curllm_core/diff_detector.py`

```python
import hashlib
from deepdiff import DeepDiff

class DiffDetector:
    def __init__(self, storage_path: str = "diffs/"):
        self.storage_path = storage_path
    
    def compute_hash(self, data: dict) -> str:
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
    
    def detect_changes(self, url: str, current_data: dict) -> dict:
        previous = self.load_previous(url)
        if not previous:
            return {"status": "new", "changes": None}
        
        diff = DeepDiff(previous, current_data)
        return {"status": "changed" if diff else "unchanged", "changes": diff}
```

### 🟢 Niski priorytet (ale wartościowe)

#### 2.7 Webhook notifications

```python
import httpx

async def send_webhook(url: str, payload: dict):
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)
```

#### 2.8 Scheduled jobs

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=6)
async def daily_extraction():
    # uruchom ekstrakcję
    pass
```

---

## 3. Wzorce kodu do naśladowania

### 3.1 Struktura modułu

```python
"""
Moduł: nazwa_modulu.py
Opis: Co robi ten moduł
"""

from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class NazwaKlasy:
    """Docstring klasy"""
    
    def __init__(self, config: dict):
        self.config = config
    
    async def glowna_metoda(self, input_data: dict) -> dict:
        """
        Opis metody.
        
        Args:
            input_data: Opis argumentu
            
        Returns:
            Opis zwracanej wartości
        """
        try:
            result = await self._internal_method(input_data)
            logger.info(f"Success: {result}")
            return result
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
```

### 3.2 Obsługa błędów

```python
class ExtractionError(Exception):
    """Błąd ekstrakcji danych"""
    pass

class NetworkError(Exception):
    """Błąd sieci"""
    pass

# Użycie
try:
    data = await extract(url)
except NetworkError:
    # retry lub fallback
except ExtractionError:
    # log i kontynuuj
```

### 3.3 Konfiguracja

```python
from pydantic import BaseSettings

class ExtractorConfig(BaseSettings):
    timeout: int = 30000
    max_retries: int = 3
    stealth_mode: bool = False
    
    class Config:
        env_prefix = "CURLLM_"
```

---

## 4. Testy - co testować

### 4.1 Unit tests

```python
# tests/test_extraction.py
import pytest
from curllm_core.extraction import Extractor

def test_extract_links():
    html = "<a href='https://example.com'>Link</a>"
    result = Extractor.extract_links(html)
    assert len(result) == 1
    assert result[0]["url"] == "https://example.com"
```

### 4.2 Integration tests

```python
# tests/integration/test_ceneo.py
import pytest
from curllm_core import extract

@pytest.mark.integration
async def test_ceneo_products():
    result = await extract(
        url="https://www.ceneo.pl/Laptopy",
        task="extract products"
    )
    assert len(result["products"]) > 0
    assert all("price" in p for p in result["products"])
```

### 4.3 Test pages

Projekt zawiera testowe strony HTML w `tests/test_pages/`:

- `01_simple_form.html` - podstawowy formularz
- `02_product_list.html` - lista produktów
- `03_login_form.html` - formularz logowania
- itd.

---

## 5. Checklist przed Pull Request

- [ ] Kod jest sformatowany (black, isort)
- [ ] Testy przechodzą (`make test`)
- [ ] Dodano docstringi do nowych funkcji
- [ ] Zaktualizowano CHANGELOG
- [ ] Bez hardkodowanych wartości (użyj config)
- [ ] Obsługa błędów z logowaniem
- [ ] Kompatybilność wsteczna

---

## 6. Kontekst technologiczny

### Stack

- **Python 3.10+** - asyncio jest kluczowe
- **Playwright** - automatyzacja przeglądarki
- **Ollama** - lokalne LLM (qwen2.5:7b domyślny)
- **SQLite** - baza wiedzy
- **YAML** - konfiguracja strategii

### Filozofia projektu

1. **Privacy-first** - wszystko lokalnie
2. **LLM jako backup** - najpierw heurystyki, potem LLM
3. **Uczenie się** - zapisuj skuteczne strategie
4. **Modularność** - łatwa wymiana komponentów

---

*Dokument dla wewnętrznego użytku przez asystentów AI*
