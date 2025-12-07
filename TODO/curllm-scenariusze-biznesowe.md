# curllm - Scenariusze Biznesowe i Use Cases

## Wprowadzenie

Artykuł przedstawia praktyczne zastosowania **curllm** w różnych scenariuszach biznesowych wraz z gotowymi do użycia komendami.

---

## 1. E-commerce: Monitoring cen konkurencji

### Scenariusz

Sklep internetowy chce śledzić ceny produktów u konkurencji.

### Implementacja

```bash
#!/bin/bash
# price_monitor.sh

DATE=$(date +%Y-%m-%d)
PRODUCTS_DIR="./price_data"
mkdir -p "$PRODUCTS_DIR"

# Ceneo - laptopy
curllm --stealth "https://www.ceneo.pl/Laptopy" \
  -d "extract all products with name, price, and link" \
  --csv -o "$PRODUCTS_DIR/ceneo_laptopy_${DATE}.csv"

# Skapiec - laptopy  
curllm --stealth "https://www.skapiec.pl/cat/1/komputery-laptopy.html" \
  -d "extract all products with name, price, and link" \
  --csv -o "$PRODUCTS_DIR/skapiec_laptopy_${DATE}.csv"

# Morele
curllm --stealth "https://www.morele.net/kategoria/laptopy-31/" \
  -d "extract all products with name, price, and link" \
  --csv -o "$PRODUCTS_DIR/morele_laptopy_${DATE}.csv"

echo "Monitoring zakończony: $DATE"
```

### Cron job (codzienny o 6:00)

```bash
0 6 * * * /path/to/price_monitor.sh >> /var/log/price_monitor.log 2>&1
```

---

## 2. Lead Generation: Ekstrakcja kontaktów

### Scenariusz

Firma B2B zbiera dane kontaktowe z katalogów branżowych.

### Implementacja

```bash
#!/bin/bash
# lead_generation.sh

OUTPUT_DIR="./leads"
mkdir -p "$OUTPUT_DIR"

# Lista URL katalogów branżowych
URLS=(
  "https://panoramafirm.pl/it-i-telekomunikacja"
  "https://pkt.pl/firmy/informatyka"
)

for url in "${URLS[@]}"; do
  FILENAME=$(echo "$url" | md5sum | cut -d' ' -f1)
  
  curllm --stealth "$url" \
    -d "extract all company contacts: name, email, phone, address, website" \
    --csv -o "$OUTPUT_DIR/${FILENAME}.csv"
  
  # Pauza między requestami
  sleep 5
done

# Połącz wszystkie pliki
cat "$OUTPUT_DIR"/*.csv | sort -u > "$OUTPUT_DIR/all_leads.csv"
```

---

## 3. SEO: Analiza konkurencji

### Scenariusz

Agencja SEO analizuje strukturę linków konkurencyjnych stron.

### Implementacja

```bash
#!/bin/bash
# seo_analysis.sh

COMPETITOR="https://konkurent.pl"
OUTPUT="seo_report_$(date +%Y%m%d).json"

# Ekstrakcja wszystkich linków wewnętrznych
curllm "$COMPETITOR" \
  -d "extract all internal links with anchor text" \
  -o links_internal.json

# Ekstrakcja meta tagów
curllm "$COMPETITOR" \
  -d "extract page title, meta description, h1, h2 headings" \
  -o meta_tags.json

# Ekstrakcja linków wychodzących
curllm "$COMPETITOR" \
  -d "extract all external links (links to other domains)" \
  -o links_external.json
```

---

## 4. HR: Automatyczne aplikowanie

### Scenariusz

Rekruter automatyzuje wysyłanie formularzy kontaktowych do kandydatów.

### Implementacja

```bash
#!/bin/bash
# hr_outreach.sh

# Plik CSV z danymi: name,email,position
INPUT_FILE="candidates.csv"

while IFS=, read -r name email position; do
  # Pomiń nagłówek
  [ "$name" == "name" ] && continue
  
  MESSAGE="Dzień dobry $name, mamy dla Pana/Pani ciekawą ofertę na stanowisko $position."
  
  curllm --stealth "https://company.pl/contact" \
    -d "Fill contact form: name=$name, email=$email, subject=Oferta pracy, message=$MESSAGE"
  
  echo "Wysłano do: $name ($email)"
  sleep 10  # Pauza między wysyłkami
done < "$INPUT_FILE"
```

---

## 5. Content Marketing: Zbieranie inspiracji

### Scenariusz

Content manager zbiera nagłówki artykułów z branżowych portali.

### Implementacja

```bash
#!/bin/bash
# content_ideas.sh

PORTALS=(
  "https://techcrunch.com"
  "https://www.theverge.com"
  "https://arstechnica.com"
)

for portal in "${PORTALS[@]}"; do
  NAME=$(echo "$portal" | sed 's/https:\/\///' | sed 's/www\.//' | cut -d'.' -f1)
  
  curllm "$portal" \
    -d "extract all article headlines with their URLs" \
    --csv -o "headlines_${NAME}.csv"
done
```

---

## 6. Real Estate: Monitoring ofert

### Scenariusz

Inwestor nieruchomości monitoruje nowe oferty w określonych lokalizacjach.

### Implementacja

```bash
#!/bin/bash
# real_estate_monitor.sh

LOCATIONS=("warszawa" "krakow" "wroclaw")
DATE=$(date +%Y%m%d)

for city in "${LOCATIONS[@]}"; do
  curllm --stealth "https://www.otodom.pl/pl/oferty/sprzedaz/mieszkanie/${city}" \
    -d "extract all listings: title, price, area in m2, rooms, location, link" \
    --csv -o "otodom_${city}_${DATE}.csv"
  
  sleep 3
done
```

---

## 7. Research: Zbieranie danych naukowych

### Scenariusz

Badacz zbiera dane z publicznych rejestrów i baz.

### Implementacja

```bash
# Ekstrakcja danych z KRS (przykład)
curllm "https://ekrs.ms.gov.pl/web/wyszukiwarka-krs/strona-glowna/index.html" \
  -d "search for company: ACME and extract: NIP, REGON, address, board members"

# Ekstrakcja publikacji naukowych
curllm "https://scholar.google.com/scholar?q=machine+learning+2024" \
  -d "extract all papers: title, authors, year, citations count, link"
```

---

## 8. Quality Assurance: Testowanie formularzy

### Scenariusz

QA team automatyzuje testy formularzy na stronie.

### Implementacja

```bash
#!/bin/bash
# qa_form_tests.sh

BASE_URL="https://staging.company.com"

# Test 1: Formularz kontaktowy - poprawne dane
curllm --visual "$BASE_URL/contact" \
  -d "Fill form: name=Test User, email=test@example.com, message=Test message" \
  2>&1 | tee "test_contact_valid.log"

# Test 2: Formularz kontaktowy - niepoprawny email
curllm --visual "$BASE_URL/contact" \
  -d "Fill form: name=Test User, email=invalid-email, message=Test" \
  2>&1 | tee "test_contact_invalid_email.log"

# Test 3: Formularz rejestracji
curllm --visual "$BASE_URL/register" \
  -d "Fill registration: username=testuser123, email=test@test.pl, password=Test123!, confirm=Test123!" \
  2>&1 | tee "test_registration.log"
```

---

## 9. Finance: Zbieranie kursów walut

### Scenariusz

Firma importowa codziennie zbiera kursy walut.

### Implementacja

```bash
#!/bin/bash
# currency_monitor.sh

DATE=$(date +%Y-%m-%d)

# NBP
curllm "https://www.nbp.pl/home.aspx?f=/kursy/kursya.html" \
  -d "extract exchange rates table: currency code, currency name, rate" \
  --csv -o "nbp_rates_${DATE}.csv"

# Kantor
curllm --stealth "https://www.cinkciarz.pl/kursy-walut" \
  -d "extract all currency rates: currency, buy rate, sell rate" \
  --csv -o "cinkciarz_rates_${DATE}.csv"
```

---

## 10. Social Media: Monitoring wzmianek

### Scenariusz

PR team monitoruje wzmianki o marce.

### Implementacja

```bash
#!/bin/bash
# brand_monitoring.sh

BRAND="MojaMarka"
DATE=$(date +%Y%m%d)

# Hacker News
curllm "https://hn.algolia.com/?q=${BRAND}" \
  -d "extract all results: title, url, points, comments" \
  -o "hn_${BRAND}_${DATE}.json"

# Reddit (wyniki wyszukiwania Google)
curllm "https://www.google.com/search?q=site:reddit.com+${BRAND}" \
  -d "extract all search results: title, url, snippet" \
  -o "reddit_${BRAND}_${DATE}.json"
```

---

## Dobre praktyki

### Rate Limiting

```bash
# Dodaj opóźnienia między requestami
for url in "${URLS[@]}"; do
  curllm --stealth "$url" -d "extract data"
  sleep $((RANDOM % 5 + 3))  # 3-7 sekund losowo
done
```

### Logowanie błędów

```bash
curllm --stealth "$URL" -d "task" 2>&1 | tee -a extraction.log
```

### Walidacja wyników

```bash
# Sprawdź czy plik nie jest pusty
if [ -s "output.csv" ]; then
  echo "Sukces"
else
  echo "Błąd: pusty wynik"
fi
```

### Backup danych

```bash
# Backup przed nadpisaniem
cp "data.csv" "data_backup_$(date +%Y%m%d_%H%M%S).csv"
```

---

*Artykuł przedstawia przykładowe scenariusze. Zawsze przestrzegaj regulaminów serwisów i prawa.*
