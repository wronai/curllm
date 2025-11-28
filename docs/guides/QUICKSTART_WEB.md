# curllm Web Client - Quick Start Guide

## Szybki start w 3 krokach

### 1. Instalacja

```bash
# Zainstaluj curllm (jeśli jeszcze nie masz)
pip install -e .

# Uruchom setup (jeśli pierwszy raz)
curllm-setup
```

### 2. Uruchom serwer API

W pierwszym terminalu:

```bash
# Uruchom serwer curllm API
python curllm_server.py
```

Serwer powinien wystartować na `http://localhost:8000`

### 3. Uruchom klienta webowego

**Nowa wersja z zarządzaniem procesem:**

```bash
# Uruchom w tle
curllm-web start

# Sprawdź status
curllm-web status

# Zatrzymaj
curllm-web stop

# Zrestartuj
curllm-web restart
```

**Lub tradycyjnie (w konsoli):**

```bash
curllm-web
```

Otwórz przeglądarkę na: **http://localhost:5000**

## Pierwsze kroki

### Przykład 1: Wyciągnij produkty ze strony

1. W polu "URL strony" wklej: `https://www.ceneo.pl`
2. Z listy promptów wybierz: **"Wyciągnij produkty"**
3. Kliknij **"Wykonaj zadanie"**
4. Poczekaj na wyniki (pojawią się po prawej stronie)
5. Przejdź do zakładki **"Logi"** aby zobaczyć szczegóły z obrazami

### Przykład 2: Własny prompt

1. Wklej URL: `https://news.ycombinator.com`
2. Wybierz z listy: **"Własny prompt"**
3. W polu tekstowym wpisz: `Extract first 10 article titles and URLs`
4. Zaznacz opcję **"Tryb wizualny"** dla lepszej analizy
5. Kliknij **"Wykonaj zadanie"**

### Przykład 3: Zarządzanie promptami

1. Przejdź do zakładki **"Prompty"**
2. Kliknij **"Dodaj nowy"**
3. Wpisz nazwę: `Mój własny prompt`
4. W polu tekstowym wpisz swoją instrukcję
5. Kliknij ikonę dyskietki 💾 aby zapisać
6. Teraz możesz używać tego promptu w zakładce "Wykonaj"

### Przykład 4: Upload pliku

1. W zakładce "Wykonaj" znajdź sekcję **"Prześlij plik"**
2. Kliknij **"Wybierz plik"** i wybierz CSV/JSON/XLS
3. Kliknij ikonę upload ☁️
4. Plik zostanie zapisany w katalogu `uploads/`

## Opcje zaawansowane

### Tryb wizualny
- Włącz dla stron wymagających analizy obrazów
- Automatycznie robi screenshoty
- Używa vision model do analizy

### Tryb stealth
- Włącz dla stron z detekcją botów
- Symuluje prawdziwego użytkownika
- Randomizuje zachowanie przeglądarki

### Rozwiązywanie CAPTCHA
- Włącz jeśli strona ma CAPTCHA
- Automatycznie wykrywa i rozwiązuje
- Wspiera różne typy CAPTCHA

## Przeglądanie logów

Każde wykonanie zadania tworzy plik logu w formacie Markdown:

1. Przejdź do zakładki **"Logi"**
2. Kliknij na wybrany log z listy
3. Log wyświetli się po prawej z:
   - Szczegółami konfiguracji
   - Krokami wykonania
   - Osadzonymi screenshotami
   - Wynikami w JSON

## Konfiguracja

### Zmienne środowiskowe

Utwórz plik `.env` lub ustaw zmienne:

```bash
# Port klienta webowego (domyślnie 5000)
CURLLM_WEB_PORT=5000

# Host klienta webowego (domyślnie 0.0.0.0)
CURLLM_WEB_HOST=0.0.0.0

# Adres API curllm (domyślnie http://localhost:8000)
CURLLM_API_HOST=http://localhost:8000

# Model LLM (domyślnie qwen2.5:7b)
CURLLM_MODEL=qwen2.5:14b

# Debug mode
CURLLM_DEBUG=true
```

### Dostosowanie promptów

Prompty są zapisywane w pliku `web_prompts.json`:

```json
[
  {
    "id": "custom_1",
    "name": "Mój prompt",
    "prompt": "Extract all data from the page"
  }
]
```

Możesz edytować ten plik bezpośrednio lub przez interfejs webowy.

## Troubleshooting

### Serwer nie startuje

**Problem:** `Address already in use`

**Rozwiązanie:**
```bash
# Zmień port
export CURLLM_WEB_PORT=5001
curllm-web
```

### API nie odpowiada

**Problem:** `API error: Connection refused` lub `Nie można połączyć z API serwrem`

**Rozwiązanie:**

**Łatwy sposób - użyj skryptu:**
```bash
./start-web-full.sh
```
Ten skrypt automatycznie uruchamia oba serwery.

**Ręczny sposób - dwa terminale:**

Terminal 1 - Serwer API:
```bash
python curllm_server.py
```

Terminal 2 - Klient webowy:
```bash
curllm-web
```

Następnie otwórz http://localhost:5000

### Obrazy w logach nie wyświetlają się

**Problem:** Screenshoty pokazują 404

**Rozwiązanie:**
1. Sprawdź czy katalog `screenshots/` istnieje
2. Sprawdź uprawnienia do odczytu
3. Zrestartuj serwer webowy

### Prompty nie zapisują się

**Problem:** `Failed to save prompt`

**Rozwiązanie:**
1. Sprawdź uprawnienia do zapisu w katalogu projektu
2. Sprawdź czy plik `web_prompts.json` nie jest tylko do odczytu
3. Sprawdź logi serwera w konsoli

## Wsparcie

- 📚 [Pełna dokumentacja](WEB_CLIENT_README.md)
- 🐛 [Zgłoś błąd](https://github.com/wronai/curllm/issues)
- 💬 [Dyskusje](https://github.com/wronai/curllm/discussions)

## Następne kroki

1. Przeczytaj [pełną dokumentację](WEB_CLIENT_README.md)
2. Zobacz [przykłady użycia](docs/EXAMPLES.md)
3. Poznaj [API Reference](docs/API.md)
4. Dołącz do społeczności na GitHub
