# curllm Web Client

Nowoczesny interfejs webowy dla curllm - automatyzacji przeglądarki z lokalnym LLM.

## Funkcje

- 🌐 **Wklejanie URL** - Łatwe wprowadzanie adresów stron do przetworzenia
- 📝 **Wybór promptów** - Lista gotowych promptów z możliwością edycji
- 💾 **Zarządzanie promptami** - Dodawanie, edycja i usuwanie własnych promptów (zapisywane w JSON)
- 📤 **Upload plików** - Wsparcie dla CSV, XLS, XLSX, JSON, TXT, HTML
- 📊 **Podgląd wyników** - Wyświetlanie wyników w przejrzystej formie
- 📋 **Przeglądarka logów** - Markdown z osadzonymi obrazami (screenshots)
- ⚙️ **Opcje zaawansowane** - Tryb wizualny, stealth, rozwiązywanie CAPTCHA
- 🎨 **Nowoczesny UI** - Responsywny interfejs z Tailwind CSS

## Instalacja

1. Zainstaluj curllm (jeśli jeszcze nie masz):
```bash
pip install -e .
```

2. Zarządzanie serwerem webowym:

```bash
# Uruchom serwer
curllm-web start

# Sprawdź status
curllm-web status

# Zatrzymaj serwer
curllm-web stop

# Zrestartuj serwer
curllm-web restart

# Zobacz pomoc
curllm-web --help
```

3. Otwórz przeglądarkę na: http://localhost:5000

## Konfiguracja

Możesz skonfigurować klienta webowego przez zmienne środowiskowe:

```bash
# Port serwera webowego (domyślnie 5000)
export CURLLM_WEB_PORT=5000

# Host serwera webowego (domyślnie 0.0.0.0)
export CURLLM_WEB_HOST=0.0.0.0

# Adres API curllm (domyślnie http://localhost:8000)
export CURLLM_API_HOST=http://localhost:8000

# Tryb debug (domyślnie false)
export CURLLM_DEBUG=true
```

## Użycie

### 1. Wykonywanie zadań

1. Wklej URL strony w pole "URL strony"
2. Wybierz gotowy prompt z listy lub wpisz własny
3. Dostosuj opcje (tryb wizualny, stealth, CAPTCHA)
4. Wybierz format eksportu (JSON, CSV, HTML, XML)
5. Kliknij "Wykonaj zadanie"

### 2. Przesyłanie plików

- Kliknij "Wybierz plik" i wybierz plik CSV, XLS, JSON itp.
- Kliknij ikonę upload
- Plik zostanie zapisany w katalogu `uploads/`

### 3. Przeglądanie logów

- Przejdź do zakładki "Logi"
- Kliknij na wybrany log z listy
- Log zostanie wyświetlony w formacie Markdown z osadzonymi obrazami

### 4. Zarządzanie promptami

- Przejdź do zakładki "Prompty"
- Edytuj istniejące prompty lub dodaj nowe
- Kliknij ikonę dyskietki aby zapisać zmiany
- Prompty są zapisywane w pliku `web_prompts.json`

## Domyślne prompty

Klient webowy zawiera następujące gotowe prompty:

- **Wyciągnij wszystkie dane** - Ekstraktuje linki, emaile, telefony, produkty
- **Wyciągnij produkty** - Ekstraktuje produkty z nazwami, cenami i opisami
- **Wyciągnij artykuły** - Ekstraktuje artykuły z tytułami, autorami i datami
- **Wyciągnij kontakty** - Ekstraktuje informacje kontaktowe
- **Wypełnij formularz** - Wypełnia formularz danymi
- **Zrób screenshot** - Robi zrzut ekranu strony
- **Własny prompt** - Pusty prompt do własnych instrukcji

## Struktura plików

```
curllm/
├── curllm_web.py           # Główna aplikacja Flask
├── templates/
│   └── index.html          # Interfejs webowy
├── static/
│   └── js/
│       └── app.js          # Logika JavaScript
├── web_prompts.json        # Zapisane prompty (tworzone automatycznie)
├── uploads/                # Przesłane pliki
└── logs/                   # Logi wykonania (run-*.md)
```

## API Endpoints

### GET /
Główna strona aplikacji

### GET /api/prompts
Pobiera listę wszystkich promptów

### POST /api/prompts
Dodaje nowy prompt

### PUT /api/prompts/<id>
Aktualizuje istniejący prompt

### DELETE /api/prompts/<id>
Usuwa prompt

### POST /api/execute
Wykonuje zadanie curllm
```json
{
  "url": "https://example.com",
  "instruction": "Extract all products",
  "options": {
    "visual_mode": false,
    "stealth_mode": false,
    "captcha_solver": false,
    "export_format": "json"
  }
}
```

### POST /api/upload
Przesyła plik

### GET /api/logs
Pobiera listę logów

### GET /api/logs/<filename>
Pobiera zawartość konkretnego logu

### GET /health
Status serwera

## Wymagania

- Python 3.10+
- Flask
- Flask-CORS
- aiohttp
- Wszystkie zależności curllm

## Troubleshooting

### Serwer nie startuje
- Sprawdź czy port 5000 nie jest zajęty
- Sprawdź czy curllm API działa na porcie 8000
- Sprawdź logi w konsoli

### Logi nie wyświetlają obrazów
- Sprawdź czy katalog `screenshots/` istnieje
- Sprawdź ścieżki w plikach logów
- Upewnij się że obrazy są w formacie PNG

### Prompty nie zapisują się
- Sprawdź uprawnienia do zapisu w katalogu projektu
- Sprawdź czy plik `web_prompts.json` nie jest tylko do odczytu

## Rozwój

Aby rozwijać klienta webowego:

1. Edytuj `curllm_web.py` dla logiki backendu
2. Edytuj `templates/index.html` dla interfejsu
3. Edytuj `static/js/app.js` dla logiki frontendu
4. Przeładuj stronę w przeglądarce

## Licencja

Apache-2.0 - Zobacz plik LICENSE w głównym katalogu projektu.
