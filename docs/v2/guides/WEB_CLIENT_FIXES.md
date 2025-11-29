# curllm Web Client - Poprawki i Ulepszenia

## 🔧 Naprawione problemy

### 1. Błąd 404 API - NAPRAWIONE ✅

**Problem:**
- Klient webowy pokazywał błąd 404 przy wykonywaniu zadań
- Wyniki były puste `[]` mimo że zadanie się wykonało

**Przyczyna:**
- Klient webowy wysyłał parametr `instruction` zamiast `data`
- API server (`curllm_server.py`) oczekuje parametru `data`
- Endpoint był `/execute` zamiast `/api/execute`

**Rozwiązanie:**
```python
# curllm_web.py - PRZED
payload = {
    'url': url,
    'instruction': instruction,  # ❌ Zły parametr
    ...
}
async with session.post(f'{api_host}/execute', ...)  # ❌ Zły endpoint

# curllm_web.py - PO
payload = {
    'url': url,
    'data': instruction,  # ✅ Poprawny parametr
    'use_bql': options.get('use_bql', False),  # ✅ Dodany parametr
    ...
}
async with session.post(f'{api_host}/api/execute', ...)  # ✅ Poprawny endpoint
```

### 2. Brak wyników w interfejsie - NAPRAWIONE ✅

**Problem:**
- Dane były w logu ale nie wyświetlały się w interfejsie
- `result` było `undefined` lub `null`

**Rozwiązanie:**
- Zaktualizowano funkcję `displayResults()` w JavaScript
- Dodano obsługę wszystkich pól zwracanych przez API:
  - `result` - właściwe dane wynikowe
  - `success` - status sukcesu
  - `reason` - przyczyna sukcesu/błędu
  - `steps_taken` - liczba wykonanych kroków
  - `run_log` - ścieżka do logu
  - `screenshots` - lista screenshotów
  - `evaluation` - metadata ewaluacji

### 3. Mało promptów - ROZSZERZONE ✅

**Przed:** 7 promptów
**Po:** 19 promptów

**Nowe prompty:**
1. Produkty poniżej 100zł
2. Najnowsze wiadomości
3. Wyciągnij linki
4. Wyciągnij obrazy
5. Wyciągnij tabele
6. Wykryj formularze
7. Wypełnij formularz kontaktowy
8. Szukaj na stronie
9. Porównaj ceny
10. Wyciągnij opinie
11. Nawiguj i wyciągnij
12. Zaloguj i wyciągnij

### 4. Słabe komunikaty błędów - ULEPSZONE ✅

**Przed:**
```
API error: 404
<!doctype html>
<html lang=en>
...
```

**Po:**
```
Nie można połączyć z API serwrem na http://localhost:8000

💡 Pomoc: Uruchom serwer API w osobnym terminalu: python curllm_server.py

📋 Szczegóły techniczne (zwijane)
```

### 5. Brak wsparcia dla podkatalogów w screenshots - NAPRAWIONE ✅

**Problem:**
- Screenshoty w podkatalogach (np. `screenshots/ceneo.pl/step_0.png`) nie były dostępne
- Routing Flask nie obsługiwał ścieżek z `/`

**Rozwiązanie:**
```python
@app.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    """Serve screenshot files from subdirectories"""
    screenshots_dir = Path('./screenshots')
    file_path = screenshots_dir / filename
    
    # Security check
    try:
        file_path.resolve().relative_to(screenshots_dir.resolve())
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 403
    
    if file_path.exists() and file_path.is_file():
        return send_from_directory(screenshots_dir, filename)
    return jsonify({'error': 'Screenshot not found'}), 404
```

## 🚀 Nowe funkcje

### 1. Skrypt automatycznego startu

**Plik:** `start-web-full.sh`

```bash
./start-web-full.sh
```

**Co robi:**
- ✅ Sprawdza czy Ollama działa
- ✅ Uruchamia serwer API w tle
- ✅ Uruchamia klienta webowego
- ✅ Pokazuje linki i statusy
- ✅ Zatrzymuje wszystko po Ctrl+C

### 2. Lepsze wyświetlanie wyników

**Nowe elementy:**
- 📊 Liczba elementów/pól w wynikach
- 📝 Liczba wykonanych kroków
- 🔗 Przycisk do otwarcia logu z obrazami
- 🖼️ Galeria screenshotów (grid 2 kolumny)
- 📈 Zwijane szczegóły ewaluacji
- ⚠️ Ostrzeżenie gdy brak danych

### 3. Rozszerzona obsługa błędów

**Typy błędów:**
1. **Connection Error** - API server nie działa
2. **Timeout Error** - Zadanie trwa zbyt długo (>5 min)
3. **API Error** - Błąd HTTP (404, 500, etc.)
4. **Generic Error** - Inne błędy

**Dla każdego błędu:**
- 🔴 Czytelny komunikat
- 💡 Sekcja "Pomoc" z instrukcjami
- 📋 Zwijane szczegóły techniczne

## 📝 Zmiany w plikach

### Zmodyfikowane pliki:

1. **curllm_web.py**
   - Poprawiono endpoint API: `/api/execute`
   - Zmieniono parametr: `instruction` → `data`
   - Dodano `use_bql` parametr
   - Ulepszona obsługa błędów z timeoutami
   - Dodano routing dla podkatalogów w screenshots

2. **static/js/app.js**
   - Całkowicie przepisano `displayResults()`
   - Dodano wyświetlanie wszystkich pól API
   - Dodano liczniki i statystyki
   - Dodano galeria screenshotów
   - Poprawiono komunikaty błędów z pomocą

3. **templates/index.html**
   - Bez zmian (interfejs był OK)

### Nowe pliki:

1. **start-web-full.sh**
   - Skrypt uruchamiający oba serwery
   - Automatyczna konfiguracja
   - Cleanup po zakończeniu

2. **WEB_CLIENT_FIXES.md** (ten plik)
   - Dokumentacja wszystkich poprawek

3. **web_prompts.json** (zaktualizowany)
   - 19 promptów zamiast 7

## 🧪 Testowanie

### Test 1: Podstawowe wywołanie

```bash
# Terminal 1
python curllm_server.py

# Terminal 2
curllm-web

# Terminal 3
curl -X POST http://localhost:5000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.ceneo.pl", "instruction": "Extract all products"}'
```

### Test 2: Przez interfejs

1. Otwórz http://localhost:5000
2. Wklej URL: `https://www.ceneo.pl`
3. Wybierz prompt: "Wyciągnij produkty"
4. Kliknij "Wykonaj zadanie"
5. Sprawdź czy wyniki się wyświetlają

### Test 3: Screenshoty

1. Włącz "Tryb wizualny"
2. Wykonaj zadanie
3. Sprawdź czy screenshoty wyświetlają się
4. Przejdź do zakładki "Logi"
5. Sprawdź czy obrazy są w logach

## 📊 Porównanie przed/po

| Funkcja | Przed | Po |
|---------|-------|-----|
| Prompty | 7 | 19 ✅ |
| Wyniki wyświetlane | ❌ Puste | ✅ Pełne |
| Komunikaty błędów | ❌ HTML 404 | ✅ Pomocne |
| Screenshoty | ❌ 404 dla podkat. | ✅ Działają |
| Start aplikacji | 2 terminale | 1 skrypt ✅ |
| Logi z obrazami | ❌ Nie działa | ✅ Działa |

## 🎯 Jak używać teraz

### Najprostszy sposób:

```bash
./start-web-full.sh
```

Następnie otwórz: http://localhost:5000

### Co zobaczysz:

1. **Zakładka "Wykonaj"**
   - 19 gotowych promptów do wyboru
   - Edytowalne pole tekstowe
   - Opcje: visual, stealth, CAPTCHA
   - Upload plików

2. **Zakładka "Logi"**
   - Lista wszystkich logów
   - Podgląd Markdown z obrazami
   - Osadzone screenshoty

3. **Zakładka "Prompty"**
   - Wszystkie 19 promptów
   - Edycja nazw i treści
   - Dodawanie nowych
   - Usuwanie

## ✅ Status

Wszystkie problemy zostały naprawione! 🎉

- ✅ API zwraca wyniki
- ✅ Wyniki wyświetlają się poprawnie
- ✅ 19 promptów gotowych do użycia
- ✅ Obrazy działają w logach
- ✅ Komunikaty błędów są pomocne
- ✅ Prosty start jednym skryptem

## 🔜 Możliwe przyszłe ulepszenia

1. **Export wyników**
   - Przycisk "Pobierz JSON"
   - Przycisk "Pobierz CSV"
   - Przycisk "Skopiuj do schowka"

2. **Historia wykonań**
   - Lista ostatnich 10 zadań
   - Ponowne wykonanie
   - Porównanie wyników

3. **Edytor promptów WYSIWYG**
   - Podgląd na żywo
   - Szablon zmiennych
   - Walidacja składni

4. **WebSocket real-time**
   - Live logi podczas wykonania
   - Progress bar
   - Streaming wyników

5. **Multi-tab execution**
   - Równoległe wykonania
   - Queue manager
   - Batch processing
