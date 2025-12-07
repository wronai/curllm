# Status Projektu: curllm

## Przegląd

| Kategoria | Wartość |
|-----------|---------|
| **Nazwa** | curllm |
| **Wersja** | 1.0.32 |
| **Licencja** | Apache 2.0 |
| **Repozytorium** | github.com/wronai/curllm |
| **PyPI** | pypi.org/project/curllm |
| **Status** | Aktywny rozwój |

---

## Opis projektu

**curllm** (curl + LLM) to narzędzie CLI łączące automatyzację przeglądarki z lokalnymi modelami językowymi. Umożliwia inteligentną ekstrakcję danych, wypełnianie formularzy i automatyzację zadań webowych - wszystko działające lokalnie z pełną prywatnością.

---

## Kluczowe funkcjonalności

### Zaimplementowane ✅

- **Ekstrakcja danych** - LLM-guided DOM analysis bez hardkodowanych selektorów
- **Wypełnianie formularzy** - automatyczne mapowanie pól
- **Stealth Mode** - omijanie detekcji botów
- **Tryb wizualny** - podgląd działań przeglądarki w czasie rzeczywistym
- **BQL (Browser Query Language)** - strukturalne zapytania
- **Eksport** - JSON, CSV, HTML, XLS
- **Web Interface** - GUI na localhost:5000
- **Multi-provider LLM** - Ollama, OpenAI, Anthropic, Google Gemini
- **DSL System** - automatyczne uczenie się strategii ekstrakcji
- **Knowledge Base** - SQLite do śledzenia skuteczności algorytmów

### W planach 🔄

- Równoległe przetwarzanie wielu URL
- Integracja z Google Sheets
- Wbudowany scheduler (cron)
- Webhook notifications
- Proxy rotation

---

## Architektura systemu

```
┌─────────────────────────────────────────────────────┐
│                    curllm CLI                       │
├─────────────────────────────────────────────────────┤
│  DSL Executor → Knowledge Base → Strategy YAML     │
├─────────────────────────────────────────────────────┤
│           DOM Toolkit (Pure JavaScript)            │
│  Structure Analyzer | Patterns | Selectors | Prices│
├─────────────────────────────────────────────────────┤
│     Playwright Browser Engine (Chromium+Stealth)   │
├─────────────────────────────────────────────────────┤
│    Ollama / LiteLLM (Qwen, Llama, Mistral, GPT)   │
└─────────────────────────────────────────────────────┘
```

---

## Wymagania systemowe

| Komponent | Minimum | Rekomendowane |
|-----------|---------|---------------|
| Python | 3.10+ | 3.11+ |
| GPU VRAM | 6GB | 8GB+ (RTX 3060/4060) |
| RAM | 8GB | 16GB |
| Ollama | Wymagane | - |

---

## Struktura kodu

### Główne moduły

| Moduł | Plików | Opis |
|-------|--------|------|
| `curllm_core/` | 80+ | Rdzeń aplikacji |
| `curllm_core/dom_toolkit/` | 12 | Narzędzia DOM (JS) |
| `curllm_core/dsl/` | 5 | System DSL i strategie |
| `curllm_core/orchestrators/` | 8 | Orkiestratory zadań |
| `curllm_core/streamware/` | 20+ | Pipeline'y przetwarzania |
| `curllm_core/tools/` | 15 | Narzędzia ekstrakcji |

### Kluczowe pliki

- `curllm_core/extraction_orchestrator.py` - główna logika ekstrakcji
- `curllm_core/llm.py` - integracja z modelami LLM
- `curllm_core/stealth.py` - anti-detection
- `curllm_core/form_fill.py` - automatyzacja formularzy
- `curllm_core/bql.py` - Browser Query Language

---

## Dokumentacja

| Typ | Lokalizacja |
|-----|-------------|
| Główna | `docs/v2/README.md` |
| Architektura | `docs/v2/architecture/` |
| API | `docs/v2/api/` |
| Przykłady | `examples/` |
| Guides | `docs/v2/guides/` |

---

## Testy

### Pokrycie testami

| Kategoria | Status |
|-----------|--------|
| Unit tests | ✅ Obecne |
| Integration tests | ✅ Obecne |
| E2E tests | ✅ Obecne |
| Linux distro tests | ✅ Ubuntu, Debian, Fedora |

### Uruchamianie testów

```bash
make test              # Wszystkie testy
pytest tests/          # Pytest
./tests/e2e.sh        # End-to-end
```

---

## Ostatnie zmiany

- Dodano system DSL dla strategii ekstrakcji
- Ulepszone DOM Toolkit z analizą statystyczną
- Nowy hierarchical planner v2
- Wsparcie dla wielu providerów LLM przez LiteLLM
- Streamware - nowy system pipeline'ów

---

## Zależności zewnętrzne

- **Playwright** - automatyzacja przeglądarki
- **Ollama** - lokalne LLM
- **LiteLLM** - multi-provider LLM
- **Flask** - web interface

---

## Kontakt i kontrybucja

- **GitHub Issues**: Zgłaszanie błędów i propozycji
- **Pull Requests**: Wkład w rozwój projektu
- **Dokumentacja**: Pomoc w rozbudowie docs

---

*Status na: grudzień 2025*
