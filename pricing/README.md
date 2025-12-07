# 🏷️ Price Comparator - curllm

Porównywarka cen produktów z wielu sklepów internetowych. Używa `curllm` do ekstrakcji danych i LLM do analizy porównawczej.

## ✨ Funkcje

- **Multi-URL extraction** - Pobieranie danych produktowych z wielu sklepów jednocześnie
- **Dwuetapowe przetwarzanie**:
  1. **Ekstrakcja** - Jeden prompt aplikowany do każdego URL
  2. **Analiza porównawcza** - Drugi prompt analizuje wszystkie zebrane dane
- **Interfejs webowy** - Nowoczesny UI do wprowadzania URL-i i promptów
- **Wyniki w tabelach HTML** - Czytelne porównanie produktów
- **Wskazanie najlepszej oferty** - Automatyczne wykrywanie najlepszej ceny
- **Docker support** - Gotowe do uruchomienia w kontenerze

## 🚀 Szybki start

### Opcja 1: Docker (zalecana)

```bash
cd pricing/

# Uruchom z Docker Compose
docker compose up --build

# Otwórz w przeglądarce
# http://localhost:8080
```

### Opcja 2: Bezpośrednie uruchomienie

```bash
# Zainstaluj zależności (z głównego katalogu projektu)
pip install -r requirements.txt
pip install -r pricing/requirements.txt

# Zainstaluj Playwright
playwright install chromium

# Uruchom serwis
python pricing/app.py

# Otwórz: http://localhost:8080
```

## 📖 Jak używać

### Interfejs webowy

1. Otwórz `http://localhost:8080`
2. Dodaj URL-e produktów do porównania (każdy URL to osobna strona produktu)
3. Wpisz **prompt ekstrakcji** - co wyciągnąć z każdej strony
4. Wpisz **prompt porównawczy** - jak porównać wszystkie wyniki
5. Kliknij "Porównaj produkty"

### Przykład promptów

**Prompt ekstrakcji:**
```
Wyciągnij z tej strony produktowej:
- Nazwa produktu
- Cena (z walutą)
- Specyfikacje techniczne
- Dostępność
- Oceny użytkowników
```

**Prompt porównawczy:**
```
Porównaj wszystkie produkty. Przeanalizuj:
1. Różnice w cenach między sklepami
2. Porównaj specyfikacje techniczne
3. Wskaż najlepszą ofertę cenową
4. Wskaż najlepszy produkt pod względem parametrów
5. Daj końcową rekomendację zakupową
```

### API

Możesz też używać API bezpośrednio:

```bash
# Pełne porównanie
curl -X POST http://localhost:8080/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://allegro.pl/oferta/produkt-1",
      "https://sklep.pl/produkt-2",
      "https://morele.net/produkt-3"
    ],
    "extraction_prompt": "Wyciągnij nazwę, cenę i specyfikacje produktu",
    "comparison_prompt": "Porównaj ceny i wskaż najlepszą ofertę",
    "stealth": true
  }'

# Pojedyncza ekstrakcja
curl -X POST http://localhost:8080/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://allegro.pl/oferta/produkt",
    "prompt": "Wyciągnij dane produktu",
    "stealth": true
  }'
```

## 🔧 Konfiguracja

### Zmienne środowiskowe

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `PORT` | `8080` | Port serwera HTTP |
| `DEBUG` | `false` | Tryb debugowania |
| `MAX_CONCURRENT_URLS` | `5` | Maksymalna liczba równoległych ekstrakcji |
| `EXTRACTION_TIMEOUT` | `120` | Timeout ekstrakcji (sekundy) |
| `LLM_PROVIDER` | (auto) | Provider LLM (`openai/gpt-4o-mini`, `anthropic/claude-3-haiku`, etc.) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL do lokalnego Ollama |
| `LLM_MODEL` | `llama3.2` | Model Ollama |
| `OPENAI_API_KEY` | - | Klucz API OpenAI |
| `ANTHROPIC_API_KEY` | - | Klucz API Anthropic |

### Plik .env

```bash
# Przykładowy .env
PORT=8080
DEBUG=false
MAX_CONCURRENT_URLS=5

# Dla OpenAI
LLM_PROVIDER=openai/gpt-4o-mini
OPENAI_API_KEY=sk-...

# Lub dla lokalnego Ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2
```

## 🐳 Docker

### Uruchomienie z Ollama (lokalne LLM)

```bash
# Uruchom z profilem ollama
docker compose --profile with-ollama up --build

# Pobierz model (w osobnym terminalu)
docker exec ollama ollama pull llama3.2
```

### Uruchomienie z zewnętrznym LLM

```bash
# Utwórz .env z kluczami API
echo "OPENAI_API_KEY=sk-your-key" > .env
echo "LLM_PROVIDER=openai/gpt-4o-mini" >> .env

# Uruchom
docker compose up --build
```

### Budowanie obrazu

```bash
# Z poziomu głównego katalogu projektu
docker build -f pricing/Dockerfile -t curllm-price-comparator .
```

## 📊 Format odpowiedzi API

```json
{
  "success": true,
  "extraction_results": [
    {
      "url": "https://sklep1.pl/produkt",
      "store_name": "sklep1.pl",
      "success": true,
      "data": {
        "name": "Produkt A",
        "price": "1299 zł",
        "specs": {...}
      },
      "timestamp": "2024-01-15T12:00:00"
    },
    {
      "url": "https://sklep2.pl/produkt",
      "store_name": "sklep2.pl",
      "success": true,
      "data": {...}
    }
  ],
  "comparison": {
    "analysis": "Analiza porównawcza produktów...",
    "summary_table": [
      {
        "store": "sklep1.pl",
        "product_name": "Produkt A",
        "price": "1299",
        "currency": "zł",
        "availability": "Dostępny",
        "rating": "4.5/5",
        "key_features": ["cecha1", "cecha2"]
      }
    ],
    "best_price": {
      "store": "sklep2.pl",
      "price": "1199 zł",
      "url": "https://sklep2.pl/produkt"
    },
    "warnings": []
  },
  "timestamp": "2024-01-15T12:05:00"
}
```

## 🎯 Przypadki użycia

### 1. Porównanie cen elektroniki

```
URLs:
- https://allegro.pl/oferta/iphone-15-128gb
- https://mediaexpert.pl/iphone-15-128gb
- https://rtveuroagd.pl/iphone-15-128gb

Prompt ekstrakcji:
"Wyciągnij: nazwa modelu, cena, pojemność, kolory, gwarancja, dostawa"

Prompt porównawczy:
"Porównaj ceny i warunki zakupu (dostawa, gwarancja) dla iPhone 15 128GB"
```

### 2. Porównanie parametrów laptopów

```
URLs:
- https://x-kom.pl/laptop-dell-xps-15
- https://morele.net/laptop-macbook-pro-14
- https://komputronik.pl/laptop-lenovo-thinkpad

Prompt ekstrakcji:
"Wyciągnij: procesor, RAM, dysk, ekran, bateria, waga, cena"

Prompt porównawczy:
"Porównaj parametry techniczne laptopów. Który oferuje najlepszy stosunek wydajności do ceny? Który jest najlepszy do pracy biurowej, a który do programowania?"
```

### 3. Analiza ofert AGD

```
URLs:
- https://mediamarkt.pl/pralka-samsung
- https://neonet.pl/pralka-lg
- https://oleole.pl/pralka-bosch

Prompt ekstrakcji:
"Wyciągnij: marka, model, pojemność bębna, klasa energetyczna, zużycie wody, programy prania, cena"

Prompt porównawczy:
"Porównaj pralki pod kątem efektywności energetycznej i pojemności. Która jest najbardziej ekonomiczna w użytkowaniu?"
```

## 🔒 Bezpieczeństwo

- Serwis używa trybu stealth do omijania podstawowych blokad
- Nie przechowuje danych logowania użytkowników
- Rekomendowane uruchamianie za reverse proxy (nginx) z HTTPS w produkcji

## 🐛 Rozwiązywanie problemów

### Błąd: "Nie udało się pobrać danych"
- Sprawdź czy URL jest poprawny i dostępny
- Włącz tryb stealth
- Niektóre sklepy mogą blokować automatyczne zapytania

### Błąd: "LLM connection failed"
- Sprawdź czy Ollama działa: `curl http://localhost:11434/api/tags`
- Lub sprawdź klucze API dla zewnętrznych providerów

### Wolna ekstrakcja
- Zmniejsz `MAX_CONCURRENT_URLS` jeśli masz mało zasobów
- Użyj szybszego modelu LLM

## 📝 Licencja

MIT License - zobacz główny plik LICENSE w repozytorium.
