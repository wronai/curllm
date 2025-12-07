# 🚀 Ulepszenia curllm dla zastosowań multi-URL

Lista ulepszeń zidentyfikowanych podczas tworzenia `pricing/` i `forms/`.

## 1. Infrastruktura Multi-URL

### 1.1 Batch Executor
```python
# Propozycja: Natywny BatchExecutor w curllm_core
class BatchExecutor:
    async def execute_batch(
        self,
        urls: List[str],
        instruction: str,
        concurrency: int = 5,
        on_progress: Callable = None,  # callback dla logów
    ) -> List[BatchResult]
```

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🔴 Wysoki

### 1.2 Streaming Results API
- Natywne wsparcie dla SSE/WebSocket w `curllm_server.py`
- Callback `on_step` dla postępu ekstrakcji
- Event-driven architecture dla długich operacji

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🔴 Wysoki

### 1.3 Queue System
- Redis/SQLite queue dla dużych batch jobs
- Retry logic z exponential backoff
- Dead letter queue dla failed URLs

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🟡 Średni

---

## 2. Porównywanie i Agregacja Danych

### 2.1 Result Merger
```python
# Automatyczne łączenie wyników z wielu źródeł
class ResultMerger:
    def merge(
        self,
        results: List[ExtractionResult],
        merge_strategy: str = "union",  # union, intersection, diff
        key_fields: List[str] = None,
    ) -> MergedResult
```

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🟡 Średni

### 2.2 Schema Normalizer
- Automatyczna normalizacja różnych formatów danych
- Mapowanie pól między sklepami (np. "cena" vs "price" vs "Cena brutto")
- Currency/unit conversion

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🟡 Średni

### 2.3 Diff Engine
- Porównanie wyników między uruchomieniami
- Alerting na zmiany cen/dostępności
- Historical tracking

**Status:** 🟢 Częściowo zaimplementowane (`result_store.py`)  
**Priorytet:** 🟡 Średni

---

## 3. LLM Improvements

### 3.1 Two-Stage LLM Pipeline
```python
# Stage 1: Extraction per URL
# Stage 2: Aggregation/Analysis across all results
class TwoStagePipeline:
    async def run(
        self,
        urls: List[str],
        extraction_prompt: str,
        aggregation_prompt: str,
    ) -> PipelineResult
```

**Status:** ✅ Zaimplementowane w `pricing/`  
**Priorytet:** 🟢 Gotowe

### 3.2 LLM Result Validation
- Walidacja struktury JSON odpowiedzi
- Auto-retry przy niepoprawnym formacie
- Schema enforcement

**Status:** 🟢 Częściowo zaimplementowane (`result_corrector.py`)  
**Priorytet:** 🟡 Średni

### 3.3 Context Window Management
- Automatyczne truncation dla dużych kontekstów
- Chunking dla wielu URL-i
- Summary compression

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🔴 Wysoki

---

## 4. Form Handling

### 4.1 Bulk Form Filler
```python
# Wypełnianie wielu formularzy jednocześnie
class BulkFormFiller:
    async def fill_forms(
        self,
        urls: List[str],
        form_data: Dict[str, str],
        field_mapping: Dict[str, List[str]] = None,  # field -> possible selectors
    ) -> List[FormResult]
```

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🔴 Wysoki

### 4.2 Smart Field Detection
- Automatyczne wykrywanie pól formularza
- LLM-guided field matching
- Obsługa różnych typów pól (select, radio, checkbox)

**Status:** 🟢 Częściowo zaimplementowane (`form_fill.py`, `llm_field_filler.py`)  
**Priorytet:** 🟡 Średni

### 4.3 Form Templates
- Zapisywanie konfiguracji formularzy
- Re-use dla powtarzalnych zadań
- Import/export templates

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🟢 Niski

---

## 5. Monitoring i Scheduling

### 5.1 Scheduled Jobs
```python
# Cron-like scheduler dla powtarzalnych zadań
class JobScheduler:
    def schedule(
        self,
        job_id: str,
        urls: List[str],
        instruction: str,
        cron: str = "0 */6 * * *",  # co 6 godzin
        on_change: Callable = None,
    )
```

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🟡 Średni

### 5.2 Change Detection
- Webhook notifications
- Email alerts
- Slack/Discord integration

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🟡 Średni

### 5.3 Dashboard
- Web UI dla monitorowania jobs
- Wykresy historyczne
- Alerts management

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🟢 Niski

---

## 6. Performance

### 6.1 Browser Pool
- Reużywalne instancje przeglądarki
- Connection pooling
- Graceful shutdown

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🔴 Wysoki

### 6.2 Caching Layer
- Cache dla statycznych stron
- ETag/Last-Modified support
- Configurable TTL

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🟡 Średni

### 6.3 Parallel Extraction
- Configurable concurrency
- Rate limiting per domain
- Backpressure handling

**Status:** 🟢 Częściowo zaimplementowane  
**Priorytet:** 🟡 Średni

---

## 7. Error Handling

### 7.1 Smart Retry
- Domain-specific retry strategies
- Captcha detection and handling
- Proxy rotation on failure

**Status:** 🟢 Częściowo zaimplementowane  
**Priorytet:** 🟡 Średni

### 7.2 Fallback Strategies
- Alternative extraction methods
- Simplified extraction on failure
- Graceful degradation

**Status:** ⏳ Do zaimplementowania  
**Priorytet:** 🟡 Średni

---

## Priorytetyzacja dla następnych wersji

### v1.1 (Najbliższe)
1. ✅ Two-Stage Pipeline (pricing/)
2. ✅ Streaming API (pricing/)
3. 🔄 Bulk Form Filler (forms/)
4. ⏳ Browser Pool
5. ⏳ Batch Executor

### v1.2 (Następne)
1. Queue System
2. Result Merger
3. Change Detection
4. Scheduled Jobs

### v1.3 (Przyszłe)
1. Dashboard
2. Form Templates
3. Caching Layer
