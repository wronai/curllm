# curllm - Praktyczne Przykłady Wykorzystania

## Wprowadzenie

**curllm** to narzędzie CLI łączące automatyzację przeglądarki z lokalnymi LLM (Ollama). Wszystko działa lokalnie, bez wysyłania danych do chmury. Ten artykuł zawiera działające komendy bash pokazujące pełne możliwości narzędzia.

---

## 1. Ekstrakcja Danych

### 1.1 Wyciąganie linków ze strony

```bash
# Podstawowa ekstrakcja wszystkich linków
curllm "https://news.ycombinator.com" -d "extract all links"

# Z zapisem do JSON
curllm "https://news.ycombinator.com" -d "extract all links" -o links.json

# Z zapisem do CSV
curllm "https://news.ycombinator.com" -d "extract all links" --csv -o links.csv
```

### 1.2 Ekstrakcja adresów email

```bash
# Wyciągnięcie wszystkich emaili ze strony kontaktowej
curllm "https://example.com/contact" -d "extract all email addresses"

# Z trybem stealth (omijanie detekcji botów)
curllm --stealth "https://example.com/contact" -d "extract all email addresses"
```

### 1.3 Ekstrakcja produktów z e-commerce

```bash
# Wszystkie produkty ze strony sklepu
curllm --stealth "https://www.ceneo.pl/Telefony_komorkowe" -d "extract all products with names and prices"

# Produkty poniżej określonej ceny
curllm --stealth "https://www.ceneo.pl/Telefony_komorkowe" -d "Find all products under 500zł"

# Eksport do różnych formatów
curllm --stealth "https://www.ceneo.pl/Laptopy" -d "extract all products" --csv -o produkty.csv
curllm --stealth "https://www.ceneo.pl/Laptopy" -d "extract all products" --html -o produkty.html
curllm --stealth "https://www.ceneo.pl/Laptopy" -d "extract all products" --xls -o produkty.xlsx
```

### 1.4 Ekstrakcja tabel i danych strukturalnych

```bash
# Wyciągnięcie tabeli ze strony
curllm "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)" \
  -d "extract the main population table with country names and populations"

# Ekstrakcja danych giełdowych
curllm --stealth "https://stooq.pl/q/?s=wig20" -d "extract stock data with symbols and prices"
```

---

## 2. Automatyzacja Formularzy

### 2.1 Wypełnianie formularza kontaktowego

```bash
# Podstawowe wypełnienie formularza
curllm --visual --stealth "https://example.com/contact" \
  -d "Fill form: name=Jan Kowalski, email=jan@example.com, message=Proszę o kontakt"

# Z podglądem w przeglądarce (tryb visual)
curllm --visual "https://example.com/contact" \
  -d "Fill contact form with: first_name=Anna, last_name=Nowak, email=anna@test.pl, phone=123456789"
```

### 2.2 Logowanie do aplikacji

```bash
# Logowanie do WordPress
curllm --visual "https://mysite.com/wp-admin" \
  -d '{"instruction":"Login", "credentials":{"user":"admin", "pass":"haslo123"}}'

# Logowanie z zapisem screenshota
curllm --visual "https://app.example.com/login" \
  -d "Login with username=testuser and password=testpass, then take screenshot"
```

### 2.3 Wypełnianie formularzy rejestracyjnych

```bash
curllm --visual --stealth "https://example.com/register" \
  -d "Register new account: username=newuser123, email=new@example.com, password=SecurePass123!, confirm_password=SecurePass123!"
```

---

## 3. Screenshoty i Wizualizacja

### 3.1 Robienie screenshotów

```bash
# Podstawowy screenshot
curllm "https://example.com" -d "screenshot"

# Screenshot konkretnej sekcji
curllm "https://example.com" -d "screenshot the header section"

# Screenshot z pełnym załadowaniem strony
curllm --visual "https://example.com" -d "wait for page load and take full page screenshot"
```

### 3.2 Tryb wizualny do debugowania

```bash
# Obserwacja działań przeglądarki w czasie rzeczywistym
curllm --visual "https://example.com" -d "extract all links" 

# Z opóźnieniem dla lepszej obserwacji
curllm --visual --stealth "https://shop.example.com" -d "scroll down and extract all products"
```

---

## 4. Zapytania BQL (Browser Query Language)

### 4.1 Strukturalne zapytania o dane

```bash
# Ekstrakcja tytułu i linków z HackerNews
curllm --bql -d 'query {
  page(url: "https://news.ycombinator.com") {
    title
    links: select(css: "a.titlelink") { 
      text 
      url: attr(name: "href") 
    }
  }
}'
```

### 4.2 Złożone ekstrakcje z BQL

```bash
# Ekstrakcja produktów z selektorami CSS
curllm --bql -d 'query {
  page(url: "https://www.ceneo.pl/Smartfony") {
    products: select(css: ".product-card") {
      name: select(css: ".product-name") { text }
      price: select(css: ".price") { text }
      rating: select(css: ".rating") { text }
    }
  }
}'
```

---

## 5. Web Interface

### 5.1 Uruchamianie interfejsu webowego

```bash
# Uruchomienie serwera web UI
curllm-web start

# Sprawdzenie statusu
curllm-web status

# Zatrzymanie serwera
curllm-web stop
```

Po uruchomieniu interfejs dostępny jest pod: `http://localhost:5000`

---

## 6. Konfiguracja i Setup

### 6.1 Pierwsza instalacja

```bash
# Instalacja z PyPI
pip install -U curllm

# Jednorazowa konfiguracja (instaluje przeglądarki Playwright)
curllm-setup

# Weryfikacja instalacji
curllm-doctor
```

### 6.2 Konfiguracja Ollama

```bash
# Instalacja Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pobranie modelu (rekomendowany: qwen2.5:7b)
ollama pull qwen2.5:7b

# Alternatywne modele
ollama pull llama3:8b
ollama pull mistral:7b
```

### 6.3 Zmienne środowiskowe (.env)

```bash
# Model LLM
export CURLLM_MODEL=qwen2.5:7b

# Host Ollama
export CURLLM_OLLAMA_HOST=http://localhost:11434

# Tryb headless (bez widocznej przeglądarki)
export CURLLM_HEADLESS=true

# Tryb stealth (anti-detection)
export CURLLM_STEALTH_MODE=false

# Locale przeglądarki
export CURLLM_LOCALE=pl-PL
```

---

## 7. Zaawansowane Scenariusze

### 7.1 Monitoring cen produktów

```bash
# Ekstrakcja cen i zapis do pliku z datą
DATE=$(date +%Y%m%d)
curllm --stealth "https://www.ceneo.pl/Laptopy" \
  -d "extract all products with prices" \
  --csv -o "ceny_laptopy_${DATE}.csv"
```

### 7.2 Scraping wielu stron

```bash
# Skrypt do scrappingu wielu URL
for url in "https://site1.com" "https://site2.com" "https://site3.com"; do
  curllm --stealth "$url" -d "extract all products" -o "$(echo $url | md5sum | cut -d' ' -f1).json"
done
```

### 7.3 Porównywanie cen między sklepami

```bash
# Ceneo
curllm --stealth "https://www.ceneo.pl/Smartfony" -d "extract products with prices" -o ceneo.json

# Skapiec
curllm --stealth "https://www.skapiec.pl/cat/1/smartfony.html" -d "extract products with prices" -o skapiec.json
```

### 7.4 Automatyczne wypełnianie wielu formularzy

```bash
# Dane kontaktów w pliku CSV, iteracja przez każdy
while IFS=, read -r name email message; do
  curllm --stealth "https://example.com/contact" \
    -d "Fill form: name=${name}, email=${email}, message=${message}"
done < contacts.csv
```

---

## 8. Diagnostyka i Debugowanie

### 8.1 Sprawdzanie stanu systemu

```bash
# Pełna diagnostyka
curllm-doctor

# Sprawdzenie czy Ollama działa
curl http://localhost:11434/api/tags
```

### 8.2 Tryb debugowania

```bash
# Uruchomienie z verbose logging
curllm --visual "https://example.com" -d "extract links" 2>&1 | tee debug.log
```

---

## Wskazówki dla LLM ulepszającego curllm

### Obszary do poprawy

1. **Obsługa błędów sieciowych** - dodać retry logic z exponential backoff
2. **Cache strategii ekstrakcji** - zapisywanie skutecznych selektorów CSS dla domen
3. **Równoległe przetwarzanie** - scraping wielu URL jednocześnie
4. **Integracja z bazami danych** - bezpośredni zapis do PostgreSQL/MongoDB
5. **Webhook notifications** - powiadomienia po zakończeniu ekstrakcji
6. **Rate limiting** - automatyczne opóźnienia między requestami
7. **Proxy rotation** - obsługa listy proxy dla unikania blokad
8. **Eksport do Google Sheets** - bezpośrednia integracja
9. **Scheduled jobs** - wbudowany cron dla regularnych ekstrakcji
10. **Diff detection** - wykrywanie zmian między ekstrakcjami

### Kluczowe pliki do analizy

- `curllm_core/extraction_orchestrator.py` - główna logika ekstrakcji
- `curllm_core/dsl/executor.py` - DSL i strategie
- `curllm_core/dom_toolkit/` - narzędzia DOM
- `curllm_core/stealth.py` - mechanizmy anti-detection
- `curllm_core/form_fill.py` - wypełnianie formularzy

### Testowanie zmian

```bash
# Uruchomienie testów
make test

# Testy integracyjne
pytest tests/integration/

# Testy e2e
./tests/e2e.sh
```

---

*Artykuł wygenerowany automatycznie na podstawie dokumentacji projektu curllm*
