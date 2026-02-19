Create a new Python package directory 'curllm_core' and split curllm_server.py into reusable modules: config, logger, llm, vision, captcha, stealth, browserless, executor, server.
Update curllm_server.py to be a thin shim that runs the server from the new package.
Update pyproject.toml to include the new package.
Update examples.py to import the executor from the new package.
Add simple unit tests (Flask health endpoint and BQL parsing path). I'll create the new module files in parallel, then update existing files and add tests.


zaktualizuj changelog 
dodaj więcej testów
na bazie wskazówek z webtest/README.md stwórz nowy projekt webtest, uruchom, prztestuj z docker



Czy curllm_server.py jest jeszce potrzebne skoro mamy curllm_core/*.py ?

Odchudzić curllm_server.py do cienkiej powłoki (usunąć zdublowaną logikę, pozostawić tylko delegowanie).
Przenieść bql_parser.py do pakietu (np. curllm_core/bql.py) i dodać testy jego parsowania.
Testy E2E: dodać lekkie testy integracyjne z mockiem przeglądarki.
CI: dodać workflow (GitHub Actions) do uruchamiania make test.

 całkowicie „odchudz” curllm_server.py (usunął zdublowaną logikę) oraz przeniósł bql_parser.py do pakietu z testami



curllm --visual -H "Accept-Language: pl-PL,pl;q=0.9" "https://allegro.com" -d '{
  "instruction":"Find all products under 150 and extract names, prices and urls",
  "params": {
    "include_dom_html": true,
    "no_click": true,
    "scroll_load": true,
    "action_timeout_ms": 120000,
    "use_external_slider_solver": true
  }
}'

curllm --visual -H "Accept-Language: pl-PL,pl;q=0.9" "https://ceneo.pl" -d '{
  "instruction":"Find all products under 150zł and extract names, prices and urls",
  "params": {
    "include_dom_html": true,
    "no_click": true,
    "scroll_load": true,
    "action_timeout_ms": 120000,
    "use_external_slider_solver": true
  }
}'


logs/run-20251124-074608.md
logs/run-20251124-075525.md

Czy aktualny projekt pozwala na automatycznewypełnianie i wysyłanie formularzy na wordpress z wykyrwaniem captcha ?
użyj pliku i wdróż w projekcie captcha/playwright_bql_framework.py
Użyj i dodaj przykłady użycia na różnych przykładowych stronach
Uruchom pip install playwright i playwright install przed uruchomieniem.
Podmień call_llm_placeholder na swoją integrację z LLM (OpenAI/Ollama/local) — framework oczekuje, że LLM zwróci JSON array BQL actions.
Jeśli chcesz, mogę: dodać async-version, Selenium-version, albo zintegrować konkretny LLM (np. przykład z OpenAI / Ollama).





chciałbym użyć curllm lokalnie do testowania obecności stron www
w interncie poprzez uruchamianie codzinnie o okreslonej godzinie i wysyałnie email z załcznikiem screenshot jesli coś jest nie tak na hoscie
Stworz przyklad uzycia curllm w taki sposob, aby w pliku url.csv były linia po linii kolejne domeny do testowania, stworz taki przykladowy z 4 url
a nastepnie zrob kolejne krok i aby niezaleznie od distro linuxa skrypt shell zainstalowal w cron zadanie uruchamiane co 3 godziny
skrypt powinien miec tez komende z mozliwoscia usuniecia tego zadania cron 




jeśli sa błędy w monitorowaniu to pokaż więcej danych o domenie, np jakie są dnsy
i dokąd kieruje ta domena, gdzie jest błąd?



Dodaj możliwość odnoszenia sie w zapytaniu LLM, do wczesniejszyc zapytan i danych
ktore zostaly wskazane, aby byly brane pod uwage w query LLM
np. wez po d uwage ostatnie wyniki i porownaj po wynoaniu czy nastapila zmiana w wynikach

podaj przyklady, w kontekscie wynikow url , np pokaz tylko rozne wyniki, czyli jesli beda nowe
wiersze - dane json to je wyseitlaj a nie wszystkie

np dla takich zapytan, dodaj odpowiednie parametry, aby to dziallo z wieloma query, np gdy beda robione cyklicznie co godzine
curllm --visual -H "Accept-Language: pl-PL,pl;q=0.9" "https://oferteo.pl/zlecenia-it" -d '{
  "instruction":"Save all offers and extract titles and urls"  
}'
{"result":{"emails":[],"links":[{"href":"https://www.oferteo.pl/","text":""},{"href":"https://www.oferteo.pl/firmy-budowlane","text":"Firmy budowlane"},{"href":"https://www.oferteo.pl/firmy-budujace-domy","text":"Budowa dom\u00f3w"},{"href":"https://www.oferteo.pl/fotowoltaika","text":"Fotowoltaika"},{"href":"https://www.oferteo.pl/pompy-ciepla","text":"Pompy ciep\u0142a"},{"href":"https://www.oferteo.pl/ukladanie-kostki-brukowej","text":"Uk\u0142adanie kostki brukowej"},{"href":"https://www.oferteo.pl/elewacje","text":"Elewacje"},{"href":"https://www.oferteo.pl/remonty","text":"Remonty"},{"href":"https://www.oferteo.pl/remonty-mieszkan","text":"Remonty mieszka\u0144"},{"href":"https://www.oferteo.pl/elektrycy","text":"Elektryk"},{"href":"https://www.oferteo.pl/malarze","text":"Malarz"},{"href":"https://www.oferteo.pl/glazurnik","text":"Glazurnik"},{"href":"https://www.oferteo.pl/klimatyzacja","text":"Klimatyzacja"},{"href":"https://www.oferteo.pl/okna-pcv","text":"Okna PCV"},{"href":"https://www.oferteo.pl/biuro-rachunkowe","text":"Biuro rachunkowe"},{"href":"https://www.oferteo.pl/kredyt-hipoteczny","text":"Kredyt hipoteczny"},{"href":"https://www.oferteo.pl/leasing-samochodu","text":"Leasing samochodu"},{"href":"https://www.oferteo.pl/ubezpieczenie-na-zycie","text":"Ubezpieczenie na \u017cycie"},{"href":"https://www.oferteo.pl/adwokaci","text":"Adwokat"},{"href":"https://www.oferteo.pl/firmy","text":"Firmy"},{"href":"https://www.oferteo.pl/zlecenia","text":"Zlecenia"},{"href":"https://www.oferteo.pl/porady","text":"Porady"},{"href":"https://www.oferteo.pl/rejestracja/wybierz-klientow?cats=494&loc=&src=rfpList","text":"Do\u0142\u0105cz do firm"},{"href":"https://www.oferteo.pl/logowanie","text":"Zaloguj si\u0119"},{"href":"https://www.oferteo.pl/","text":""},{"href":"https://www.oferteo.pl/","text":"Oferteo"},{"href":"https://www.oferteo.pl/zlecenia","text":"Zlecenia"},{"href":"https://www.oferteo.pl/zlecenia-na-bazy-danych","text":"Zlecenia na bazy danych"},{"href":"https://www.oferteo.pl/zlecenia-dla-dostawcow-internetu","text":"Zlecenia dla dostawc\u00f3w Internetu"},{"href":"https://www.oferteo.pl/zlecenia-na-druk-3d","text":"Zlecenia na druk 3d"},{"href":"https://www.oferteo.pl/zlecenia-dla-grafikow-komputerowych","text":"Zlecenia dla grafik\u00f3w komputerowych"},{"href":"https://www.oferteo.pl/instalacja-konfiguracja","text":"Zlecenia na konfiguracj\u0119 komputer\u00f3w i sieci"},{"href":"https://www.oferteo.pl/integracja-systemow-it","text":"Zlecenia na integracj\u0119 system\u00f3w IT"},{"href":"https://www.oferteo.pl/odzyskiwanie-danych","text":"Zlecenia na odzyskiwanie danych"},{"href":"https://www.oferteo.pl/outsourcing-it","text":"Zlecenia na outsourcing IT"},{"href":"https://www.oferteo.pl/zlecenia-dla-serwisow-komputerowych","text":"Zlecenia dla serwis\u00f3w komputerowych"},{"href":"https://www.oferteo.pl/zlecenia-dla-programistow","text":"Zlecenia dla programist\u00f3w"},{"href":"https://www.oferteo.pl/projektowanie-cad-cam-cae","text":"Zlecenia na projektowanie CAD, CAM, CAE"},{"href":"https://www.oferteo.pl/zlecenia-na-sieci-komputerowe","text":"Zlecenia na sieci komputerowe"},{"href":"https://www.oferteo.pl/rfp/16834324_Potrzebna-naprawa-komputera-bledy-systemu-Zamosc.html","text":"Potrzebna naprawa komputera, b\u0142\u0119dy systemu"},{"href":"https://www.oferteo.pl/rfp/16834324_Potrzebna-naprawa-komputera-bledy-systemu-Zamosc.html?doUncover=true","text":"Z\u0142\u00f3\u017c ofert\u0119"},{"href":"https://www.oferteo.pl/rfp/16834320_Zlecenia-na-programowanie-od-nowa-aplikacji-mobilnej-Boleslawiec.html","text":"Zlecenia na programowanie od nowa aplikacji mobilnej"},{"href":"https://www.oferteo.pl/rfp/16834320_Zlecenia-na-programowanie-od-nowa-aplikacji-mobilnej-Boleslawiec.html?doUncover=true","text":"Z\u0142\u00f3\u017c ofert\u0119"},{"href":"https://www.oferteo.pl/rfp/16834300_Zapotrzebowanie-na-rozwoj-wsparcie-i-utrzymanie-aplikacji-Boleslawiec.html","text":"Zapotrzebowanie na rozw\u00f3j, wsparcie i utrzymanie aplikacji"},{"href":"https://www.oferteo.pl/rfp/16834300_Zapotrzebowanie-na-rozwoj-wsparcie-i-utrzymanie-aplikacji-Boleslawiec.html?doUncover=true","text":"Z\u0142\u00f3\u017c ofert\u0119"},{"href":"https://www.oferteo.pl/rfp/16833668_Zlece-naprawe-sprzetu-komputerowego-Leszno.html","text":"Zlec\u0119 napraw\u0119 sprz\u0119tu komputerowego"},{"href":"https://www.oferteo.pl/rfp/16833668_Zlece-naprawe-sprzetu-komputerowego-Leszno.html?doUncover=true","text":"Z\u0142\u00f3\u017c ofert\u0119"},{"href":"https://www.oferteo.pl/rfp/16833446_Zapytanie-o-konfiguracje-sieci-Rawicz.html","text":"Zapytanie o konfiguracj\u0119 sieci"},{"href":"https://www.oferteo.pl/rfp/16833446_Zapytanie-o-konfiguracje-sieci-Rawicz.html?doUncover=true","text":"Z\u0142\u00f3\u017c ofert\u0119"},{"href":"https://www.oferteo.pl/firma-it","text":"Firma IT"}],"phones":["20251124\n5","20251123\n1","20251122\n2","20082025","20251124\n6","20251124\n4","20251124\n3","20251124\n14","20251124\n1","8992693475"],"title":"Zlecenia IT, 2025","url":"https://www.oferteo.pl/zlecenia-it"},"run_log":"logs/run-20251124-140341.md","screenshots":[],"steps_taken":0,"success":true,"timestamp":"2025-11-24T14:03:46.757951"}
(venv) (base) tom@nvidia:~/github/wronai/curllm$ 

curllm --stop-services
curllm --install
python3 -m playwright install chromium
curllm --start-services

curllm --stop-services
curllm --start-services

dodaj obsluge 
curllm --status-services


curllm --visual --stealth --session kontakt \
  --model gemma3:12b \
  "https://www.prototypowanie.pl/kontakt/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, subject=Test, message=Hello ...",
    "params":{
      "include_dom_html":true,
      "fastpath":false,
      "scroll_load":true,
      "dom_max_chars":60000,
      "stall_limit":11,
      "action_timeout_ms":22000,
      "wait_after_nav_ms":3000,
      "wait_after_click_ms":1800
    }
  }' \
  -v


curllm --visual --stealth --session kontakt \
  --model llama3.2-vision:11b \
  "https://www.prototypowanie.pl/kontakt/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, subject=Test, message=Hello ...",
    "params":{
      "include_dom_html":true,
      "fastpath":false,
      "scroll_load":true,
      "dom_max_chars":60000,
      "stall_limit":11,
      "action_timeout_ms":22000,
      "wait_after_nav_ms":3000,
      "wait_after_click_ms":1800
    }
  }' \
  -v


curllm --visual --stealth --session kontakt \
--model qwen2.5:14b \
"https://www.prototypowanie.pl/kontakt/" \
-d '{
  "instruction":"Fill contact form: name=John Doe, email=john@example.com, subject=Test, message=Hello ...",
  "params":{
    "include_dom_html":true,
    "fastpath":false,
    "dom_max_chars":30000
  }
}' \
-v


curllm --visual --stealth --session kontakt \
  "https://www.prototypowanie.pl/kontakt/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, phone=+48123456789, subject=Test, message=Hello i need quota for my MVP project",
    "params":{"hierarchical_planner":true}
  }' \
  -v



curllm --visual --stealth --session kontakt \
  "https://www.prototypowanie.pl/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, phone=+48123456789, subject=Test, message=Hello i need quota for my MVP project",
    "params":{"hierarchical_planner":true}
  }' \
  -v



$ make stop
Stopping curllm services...
Stopped curllm API server
Services stopped
make[1]: Entering directory '/home/tom/github/wronai/curllm'
🧹 Cleaning Python cache...
✅ Cache cleaned!
make[1]: Leaving directory '/home/tom/github/wronai/curllm'

Sprawdz dlaczego nie jest wysyłana wiadomość, czy wszystkie pola są poprawnie wypełniane?

 logs/run-20251125-085745.md

Czy workflow jest inteligentny i czy sprawdza liste pól i sprawdza ktore są aktualnie wypełnione?
Czy jest autodiagnostyka i autowalidacja pol formularza, aby przesłać do LLM stan aktualny tego co dzieje sie w formularzu w drzewie DOM, 

Dlaczego przy wysyłaniu requestow do LLM są wysyłane wszystkie dane dotyczące drzewa DOM, czemu nie jest wysyłana tylko część odpowiedzialana za formualrz jeśli tak jest zdefiniowane zapytanie, aby wysyłać dane przez forumarz?



# Automatyczne (z vision model)
curllm --visual --stealth \
  --model llava:13b \
  "https://example.com/contact" \
  -d '{"instruction":"Fill form: name=John, email=john@example.com"}'

# Ręczna konfiguracja
export CURLLM_VISION_FORM_ANALYSIS=true
export CURLLM_VISION_MODEL=llava:13b
export CURLLM_VISION_CONFIDENCE_THRESHOLD=0.8

curllm --visual "https://example.com/contact" \
  -d '{"instruction":"..."}'


# Domyślnie włączone
curllm --model qwen2.5:14b "https://www.prototypowanie.pl/kontakt/" \
  -d '{"instruction":"Fill contact form: name=John, email=john@example.com,  subject=Test, message=Hello i need quota for my MVP project"}'

## 2025-11-24: Hierarchical Planner - optymalizacja komunikacji z LLM

### Problem
- Wysyłano **53KB DOM** w jednym request do LLM
- Timeout **204s** na model gemma3:12b
- LLM musiał przeanalizować wszystkie dane naraz

### Rozwiązanie: 3-poziomowy hierarchical planner (interaktywny)

```
POZIOM 1 (STRATEGIC): ~2KB zarys
├─ Pytanie: "Co jest na stronie? Jakich szczegółów potrzebujesz?"
├─ Dane: 2-level outline (form_outline bez fields)
└─ LLM decyduje:
    ├─ decision: "use_form"
    └─ need_details: ["forms[0].fields"] | null

POZIOM 2 (TACTICAL): ~5KB (tylko jeśli LLM poprosił)  
├─ Pytanie: "Jakie narzędzie wywołać?"
├─ Dane: DOKŁADNIE to co LLM poprosił w need_details
└─ Decyzja: tool_name="form.fill", args={...}

POZIOM 3 (EXECUTION): 0 KB (direct)
└─ Wykonanie: form.fill(name="John Doe", email="john@example.com")

OPCJA SKRÓCONA: Jeśli LLM w Level 1 ustawi need_details=null
└─ Pomija Level 2, parsuje argumenty bezpośrednio z instrukcji
```

### Korzyści
- ✅ **Redukcja danych**: 53KB → 2KB + 5KB = **~87% mniej**
- ✅ **Szybsze requesty**: 2-3 małe requesty zamiast 1 dużego
- ✅ **Interaktywność**: **LLM SAM decyduje** jakich szczegółów potrzebuje (`need_details`)
- ✅ **Inteligentne pomijanie**: Jeśli LLM ma dość info z Level 1, pomija Level 2 całkowicie
- ✅ **2-poziomowy zarys JSON**: W Level 1 wysyłany jest zarys bez szczegółów (np. bez `fields`), tylko `form_outline` z licznikami typu pól
- ✅ **Automatyczny fallback**: Jeśli nie dotyczy formularzy, użyj standardowego plannera

### Implementacja
1. **`hierarchical_planner.py`** - nowy moduł z 3-poziomową logiką **INTERAKTYWNĄ**
   - `should_use_hierarchical_planner()` - sprawdza rozmiar `page_context` vs `CURLLM_HIERARCHICAL_PLANNER_CHARS`
   - `extract_strategic_context()` - tworzy 2-poziomowy zarys JSON bez `fields`
   - `extract_requested_details()` - **pobiera TYLKO to co LLM poprosił** w `need_details`
   - `generate_strategic_prompt()` - LLM zwraca `{decision, need_details, reason}`
   - `hierarchical_plan()` - obsługuje 3 scenariusze:
     * LLM poprosi o szczegóły → Level 2 z requested details
     * LLM nie poprosi (need_details=null) → **pomija Level 2**, parsuje bezpośrednio
     * Nie dotyczy formularzy → fallback na standardowy planner
2. **`task_runner.py`** - integracja w `_planner_cycle()`
3. **`runtime.py`** - parametr `CURLLM_HIERARCHICAL_PLANNER=true`
4. **`config.py`** - parametr `CURLLM_HIERARCHICAL_PLANNER_CHARS=25000`
5. **`.env`** - włączony domyślnie dla zadań "fill form" lub gdy context > 25KB

### Użycie
```bash
# Domyślnie włączone
curllm --model qwen2.5:14b "https://example.com/contact" \
  -d '{"instruction":"Fill contact form: name=John, email=john@example.com"}'

# Wyłączenie (użyj standardowego plannera)
curllm -d '{"instruction":"...", "params":{"hierarchical_planner":false}}'

# Zmiana progu automatycznej optymalizacji (domyślnie 25KB)
export CURLLM_HIERARCHICAL_PLANNER_CHARS=30000
```

### Automatyczna optymalizacja
- Jeśli `page_context` > 25KB (domyślnie): **automatycznie** używa hierarchical planner
- Level 1 dostaje **2-poziomowy zarys** bez szczegółów:
  ```json
  {
    "forms": [{
      "id": "forminator-module-5635",
      "field_count": 5,
      "field_types": {"text": 2, "email": 1, "textarea": 1}
    }]
  }
  ```
  Zamiast pełnego DOM z listą `fields: [...]`

## 2025-11-24: Refaktoryzacja wypełniania formularzy

### Problem
Formularz nie był wypełniany zgodnie z instrukcją - używano wartości testowych z LLM zamiast tych z instrukcji.
- Wartości z `args` (wygenerowane przez LLM) nadpisywały wartości z instrukcji
- Pole email nie było wypełniane poprawnie (proste `page.fill` rzucało wyjątek)
- Brak priorytetyzacji `input[type="email"]` dla pola email
- Detekacja błędu email była globalna, nie bezpośrednio na polu

### Zmiany (2025-11-24)
1. **form_fill.py**:
   - Zmiana priorytetu: instrukcja > window.__curllm_canonical (teraz parsowanie z instrukcji nadpisuje args)
   - Dodano `_robust_fill_field()` z 3 fallbackami: page.fill -> page.type -> page.evaluate
   - Bezpośrednie wywołanie zdarzeń input/change/blur na każdym polu po wypełnieniu
   - Priorytetyzacja `input[type="email"]` (score 14) w findField dla emaila
   - Detekacja błędu invalid_email bezpośrednio na polu (aria-invalid, forminator-error)

2. **task_runner.py**:
   - Scalanie wartości: najpierw args z LLM, potem nadpisanie wartościami z instrukcji (parse_form_pairs)
   - Wartości z instrukcji mają najwyższy priorytet przed ustawieniem window.__curllm_canonical

### Weryfikacja
- Import modułów: OK
- Testy: `tests/test_health.py`, `tests/test_executor_bql.py` przechodzą


## 2025-11-26: Plan Testowania i Udoskonalania Systemu Dynamicznej Detekcji

### Nowy plik: TODO_TESTING_PLAN.md
Szczegółowy plan stworzenia środowiska testowego do offline testing systemu ekstrakcji danych.

### Główne cele:
1. **Środowisko testowe** - Zapisane strony HTML do testowania lokalnie
2. **Test Framework** - Automatyczne testy bez łączenia z internetem  
3. **Metryki i benchmarki** - Pomiar accuracy, performance
4. **Udoskonalenia** - Iteracyjne ulepszanie na bazie wyników testów
5. **CI/CD** - Automatyczne testy na każdym commit

### Status systemu dynamicznej detekcji (po naprawach):
- ✅ Bug #1: Logger methods fixed (log_substep → log_text)
- ✅ Bug #2: JavaScript syntax fixed (IIFE wrapper)
- ✅ Bug #3: LLM method fixed (generate → ainvoke)
- ✅ Bug #4: LLM rejection logic fixed (respects valid_count=0)
- ✅ System operational end-to-end
- ⚠️ Minor: Multi-criteria filter 'price_unit' bug (non-blocking)

### Priorytetowe zadania:
1. Stworzyć scraper.py do pobierania HTML
2. Pobrać 10 stron testowych (polskikoszyk, lidl, gral, balta, etc.)
3. Zaimplementować OfflineTestRunner
4. Napisać 20+ test scenarios
5. Setup CI/CD z GitHub Actions

Zobacz: TODO_TESTING_PLAN.md dla pełnego planu wykonania.














































podlinkuj wszystkie dokumentacje, aby zawieraloy odniesniea w menu do innnych i do plikow w kodzie w examples, itd
dodaj więcej przykładów w examples/ wedle struktury examples/[nazwa projektu]/README.md
i examples/[nazwa projektu]/[nazwa przykładu].[rozszerzenie]


przenies dokumentacje do folderu docs/*
poukładaj w folderach i zrob foldery docs/v1  i docs/v2 aby rozdzielić stare wersje, ktore nie są aktualne na ten aktualny stan projektu pi przenieść do v1

Sparwdz czy dokumentacja v2 jest zgodna z aktuazlnym stanem i posegreguj pliki z ./*.md (poza readme, changelog i todo) do odpowiednich podfolderow w docs/*

Dodatkowo zaktualizuj examples, aby uzywały krótkiego zapisu curllm, aby pokazać możliwości, jeśli coś wyamga dodatkowego kodu python, to stwoórż nowy components/*

zadbaj o to by użycie curllm nie wymagało od operatora dodatkowych instalacji, aby to działo się podczas używania sq

wykrywaj providerów i zrób automatyczne podpinanie wedle


 wprowadź poprawki do przykładów i architektury, oraz przy obsłudze róznych providerów LLM
Here you can use any provider that Litellm library supports, for instance: ollama/qwen2
            # provider="ollama/qwen2", api_token="no-token", 
            llm_config = LLMConfig(provider="openai/gpt-4o", api_token=os.getenv('OPENAI_API_KEY')), 
            schema=OpenAIModelFee.schema(),
            extraction_type="schema",
            instruction="""From the crawled content, extract all mentioned model names along with their fees for input and output tokens. 
            Do not miss any models in the entire content. One extracted model JSON format should look like this: 
            {"model_name": "GPT-4", "input_fee": "US$10.00 / 1M tokens", "output_fee": "US$30.00 / 1M tokens"}."""
        ),            


LLMConfig is useful to pass LLM provider config to strategies and functions that rely on LLMs to do extraction, filtering, schema generation etc. Currently it can be used in the following -
LLMExtractionStrategy
LLMContentFilter
JsonCssExtractionStrategy.generate_schema
JsonXPathExtractionStrategy.generate_schema
3.1 Parameters
ParameterType / DefaultWhat It Does
provider
"ollama/llama3","groq/llama3-70b-8192","groq/llama3-8b-8192", "openai/gpt-4o-mini" ,"openai/gpt-4o","openai/o1-mini","openai/o1-preview","openai/o3-mini","openai/o3-mini-high","anthropic/claude-3-haiku-20240307","anthropic/claude-3-opus-20240229","anthropic/claude-3-sonnet-20240229","anthropic/claude-3-5-sonnet-20240620","gemini/gemini-pro","gemini/gemini-1.5-pro","gemini/gemini-2.0-flash","gemini/gemini-2.0-flash-exp","gemini/gemini-2.0-flash-lite-preview-02-05","deepseek/deepseek-chat"
(default: "openai/gpt-4o-mini")
Which LLM provider to use.
api_token
1.Optional. When not provided explicitly, api_token will be read from environment variables based on provider. For example: If a gemini model is passed as provider then,"GEMINI_API_KEY" will be read from environment variables
2. API token of LLM provider
eg: api_token = "gsk_1ClHGGJ7Lpn4WGybR7vNWGdyb3FY7zXEw3SCiy0BAVM9lL8CQv"
3. Environment variable - use with prefix "env:"
eg:api_token = "env: GROQ_API_KEY"
API token to use for the given provider
base_url
Optional. Custom API endpoint
If your provider has a custom endpoint
3.2 Example Usage
llm_config = LLMConfig(provider="openai/gpt-4o-mini", api_token=os.getenv("OPENAI_API_KEY"))



na koniec, gdy już mamy zwrocony JSON rezultat LLM powinien ocenić czy odpowiadaja instrukcji z polecenia i dać odpowiedź lub poprawić JSON jeśłi to kwestia formatowania, wykorzytsaj gotowe bilbioteki, które mogą tutaj się przydać, użyj DSL-który jest wykorzystywany w wypełnianiu formularzy również podczas ekstrakcji, aby sprawdzić jak przebiega orchestracja, czy działanie jest deterministyczne, jakie błedy są popełniane za pomocą decyzji z uzyciem jeyka opisowego DSL

Wyciągnij wnioski i zaplanuj refaktoryzacje aby w oparciu o ten system mozliwe było
wyodrebnianie danych i wypełnianie formularzy na dowolnej stronie www przy uzyciu 
wielu algorytmów, które już są gotowe jako projekty OSS, użyj ich i stworz baze wiedzy dla LLM,
ktore lepiej działają na danej stronie internetowej w celu późniejszego uzycia w pierwszej kolejnosci tych metod , technik i algorytmów, które lepiej sie sprawdzały ostatnim razem, a jesli do aktualnego zadania sie nie nadaja, to zoptymalizowac i zapisac DSL razem z calym URL, tak aby mozna bylo łatwo mapować na to co uzytkownik wpisuje w linii komend i szybko wykorzystac juz raz opracowany sposob działania poprzez zapisywanie ich jako jezyka DSL w pliku dsl/*.dsl



https://www.soselectronic.com/pl-pl/products/sensirion/sdp810-500pa-2-232928
curllm --visual --stealth "https://www.soselectronic.com/pl-pl/products/sensirion/sdp810-500pa-2-232928" -d "wyświetl wszystkie dane techniczne produktu"


kontynuuj
przeanalizuj wskazówki z folderu TODO/README.md i przejrzyj pliki
zaadoptuj do naszego systemu, jeśli te wskazówki mają w tym systemie zastosowanie
wyypracuj nowy plan refaktoringu na bazie docs/REFACTORING_PLAN.md

Jak użytkownik może oceniać rezultaty i np napisać wskazówkę do poprawy systemu, aby przy kolejnym request były brane pod uwage
wady wczesniejszej ekstrakcji danych lub wypełninia formularza aby LLM był w stanie zzadoptować algorytmy i wskazówki w nowym request
Wdroz odpowiednie funkcje w komendach oraz w systemie, aby LLM był bardziej adaptacyjny tworzac generyczne małe zatomizowane funkcje samodzielnie
w folderze functions/*.{py,js}





kontynuuj , zatomizuj funkcje w functions , aby jedna funkcja była w jednym pliku, wszędzie tam, gdzie 
jest używane regular ekspression i inne metody filktrowania wyodrebniaj jako funkcje, z mozliwoscia adaptacji,
gdzie będzie możliwość w razie braku rezultatów zmiany tego regular expression przez LLM, 
jesli w trakcie orchestracji ta funkcja nie zadziała poprawnie, atk aby LLM w oparciu 
o kontekst stworzył poprawną funkcje regex



 napraw:

nie obsługuje poprawnie --yaml
 curllm --stealth "https://www.soselectronic.com/pl-pl/products/sensirion/sdp810-500pa-2-232928" -d "wyświetl parametry techniczne" --yaml -o products.yaml

nie obsluguje poprawnie html
products.html
products.yaml
products.csv

sparwdz poozstałe formaty przenalizuj jakie mozna jeszcze dodac, np xml



chciałbym też móc wykonywać szersze kontekstowo zadnia, 
takie ktore np porównują zebrane dane pomiedzy stronami, wyciąga wnioski pomiędzy np różnicami w cenie i opisami produktów
chciałbym np zrobić porównywarke cen produktów za pomocą curllm w folderze pricing/ gdzie będzie z uzyciem docker zaimplementowana
funkcjonalnosc porownywarki, ktora będzie miała liste url i jedno zapytanie dla wielu url jednoczesnie
stworz odpowiedni plik README.md w folderze pricing/ z opisem jak uzywac
Wyniki powinny byc w przegladarce jako usluga z uzyciem python, gdzie po wpisaniu prompt i podaniu kilku url, gdzie ma byc uruchomiony ten prompt
otrzymam kilka wynikow w postaci tabel html i powinna być też drugi prompt dotyczący wszystkich wynikow jako drugi etap
w wyniku czego powinna byc mozliwosc zobaczenia porownania cen z roznych sklepow internetowych i np napisania porownaj parametry i ceny produktow ze wszystkich sklepow


Stwórz nowy komponent dla curllm, który będzie odpowiedzialny za walidację i poprawę adresów url
Chciałbym aby w sytuacji gdy podano nieprawidłowy url została przeprowadzona 
analiza strony www w celu znalezienia w kategoria lub poprzez okno search strony www 
odpowiedniego zakresu danych, które aktualnie jest sprecyzowane w prompt, a które nie zostało odnalezione
np wpisuję adres url do sklepu z zapytaniem  odnosnie konkretnej grupy produktów, ale 
sklep zawiera dużo różnych produktów i np na stronie, która została podana nie ma tych produktów
chciałbym aby ten component był w stanie odnależć na podstawie wyszukiwania lub sitemap odpowiedniej kategorii
lub wyszukał jesli jest dostepne ten produkt czy fraze, o którą pytał user


curllm --stealth "https://fatpc.pl/pl/c/DDR5/1169" -d "Find all products with prices under 500PLN"


curllm "Wejdź na prototypowanie.pl i wyślij wiadomość przez formularz z zapytaniem o dostępność usługi prototypowania 3d z adresem email info@softreck.com i nazwiskiem Sapletta"



wykonaj make test i napraw błędy

skorzystaj z migration_plan.md aby upewnić się w jakim kierunku przeprowadzana jest refakoryzacja 
stwórz dokumentacje  dla refaktoryzacji, która będzie  realizowała automatyczną, dynamiczną detekcje url w danej domenie do podstron
i dla poszukiwania odpowiedniego selectora z wykorzystaniem LLM z użyciem: 
curllm_core/llm_dsl/
├── selector_generator.py   # LLMSelectorGenerator - dynamiczne selektory
├── element_finder.py       # LLMElementFinder - elementy po PURPOSE
└── ...

curllm_core/form_fill/js_scripts.py
└── generate_field_concepts_with_llm()  # LLM generuje keywords
└── find_form_fields_with_llm()         # Main entry point


┌─────────────────────────────────────────────────────────────────┐
│                    PRZED → PO                                    │
├─────────────────────────────────────────────────────────────────┤
│ PRZED: if data_key in ['phone', 'tel']:                         │
│ PO:    if data_key in phone_concepts:                           │
│                                                                  │
│ PRZED: PLATFORM_SELECTORS = {'email': '#email'}                 │
│ PO:    ELEMENT_PURPOSES = {'email': 'email input field'}        │
│        + _find_auth_element() with LLM                          │
│                                                                  │
│ PRZED: findField(['email', 'mail'], ...)  // hardcoded JS       │
│ PO:    concepts = await generate_field_concepts_with_llm(page)  │
│        result = await page.evaluate(PARAMETRIZED_JS, concepts)  │
└─────────────────────────────────────────────────────────────────┘


currllm nie powinien używać hardkodowanych selectorów, url, etykiet oraz innych hardkodowanych zmiennych, tylko funkcje, algorytmy ,
statystyki i LLM w celu realziacji zadań, stwórz skrypt, który stworzy listę plików do refaktoryzacji
sprawdzi pliki, czy nie ma tam hardkodowanych regexów czy selectorów i użyj już istniejących funkcji
lub stwórz nowe dla poszukiwnaia odpowiedniego selectora z LLM-em, 
który jest odpowiedzialny za inteligentne i generyczne zawsze działajace 
wyszukiwanie odpowiednich danych z użyciem kontekstu
np. używaj zatomizowanych algorytmow, statystyk, heurystyk oraz zapytan LLM, 
aby w sposob dynamiczny i generyczny pozyskać odpowiednie url 
w oparciu o dane z aktualnego kontekstu z drzewa DOM, sitemap itd
javascript
findField(['email', 'mail', 'adres'], 'email', form)
To NIE jest hardkodowany selektor - to dynamiczne wyszukiwanie, ale 
tego typu funkcje powinien realizować LLM, powinien poprzez język DSL
generować odpowiednie zapytania do zatomizowanych wyspecjalizowanych funkcji, 
to nie powinno być keyword sensetive hardkoded filtering
Stwórz nową architekturę opartą na LLM + DSL

python ./scripts/find_hardcoded.py 
hardcoded_report.json
przejdź do refaktoryzacji konkretnego pliku używając nowego llm_dsl
Użytkownik: "Znajdź formularz kontaktowy"
              ↓
    ┌─────────────────────────────────────────────────────────┐
    │              LLM-DSL Architecture                        │
    ├─────────────────────────────────────────────────────────┤
    │  1. LLM Analysis (highest priority)                      │
    │     - Analizuje wszystkie linki/elementy na stronie      │
    │     - Wybiera najlepszy na podstawie semantyki           │
    │                                                          │
    │  2. Statistical Analysis (fallback)                      │
    │     - Word overlap scoring                               │
    │     - Location-based scoring                             │
    │                                                          │
    │  3. Keyword Fallback (legacy)                            │
    │     - Zachowane dla kompatybilności                      │
    │     - Będzie stopniowo usuwane                          │
    └─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│                    LLM-DSL SELECTOR GENERATION                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User: "Znajdź checkbox do zgody RODO"                              │
│                          ↓                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  1. LLMSelectorGenerator.generate_consent_selector()        │    │
│  │     - Pobiera wszystkie checkboxy z etykietami              │    │
│  │     - Wysyła do LLM z promptem                              │    │
│  │     - LLM analizuje semantycznie i zwraca selector          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                          ↓                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  2. Statistical Fallback (jeśli LLM niedostępny)            │    │
│  │     - Scoring bazujący na słowach w etykietach              │    │
│  │     - NIE hardkodowane if/elif - dynamiczny scoring         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                          ↓                                           │
│  Result: GeneratedSelector(selector="...", confidence=0.9)          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

Chce żeby LLM generował selektory dynamicznie, a nie używał pre-definiowanych list.

┌────────────────────────────────────────────────────────────────────────┐
│                    CURLLM LLM-DSL ARCHITECTURE                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐   │
│  │ LLMSelectorGen   │    │ LLMElementFinder │    │ generate_field  │   │
│  │ .generate_*()    │    │ .find_element()  │    │ _concepts()     │   │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬────────┘   │
│           │                       │                       │             │
│           └───────────────────────┼───────────────────────┘             │
│                                   ↓                                     │
│                    ┌──────────────────────────────┐                     │
│                    │   LLM Prompt Generation      │                     │
│                    │   - Page context             │                     │
│                    │   - Purpose description      │                     │
│                    │   - Element analysis         │                     │
│                    └──────────────────────────────┘                     │
│                                   ↓                                     │
│                    ┌──────────────────────────────┐                     │
│                    │   Generated Selectors        │                     │
│                    │   - Confidence score         │                     │
│                    │   - Reasoning                │                     │
│                    └──────────────────────────────┘                     │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  find_url_for_goal()                             │
├─────────────────────────────────────────────────┤
│  1. _find_url_with_llm()     ← LLM semantic     │
│  2. dom_helpers.find_link()  ← Statistical      │
│  3. _legacy_find_url()       ← Pattern fallback │
└─────────────────────────────────────────────────┘

# 1. Generate selector with LLM
generator = LLMSelectorGenerator(llm=my_llm)
result = await generator.generate_consent_selector(page)

# 2. Find element by purpose
finder = LLMElementFinder(llm=my_llm, page=page)
result = await finder.find_element("email input field")

# 3. Find form fields
selectors = await find_form_fields_with_llm(page, llm=my_llm)
await page.fill(selectors['email'], "test@example.com")

# 4. Semantic concepts (fallback)
phone_concepts = {'phone', 'tel', 'telefon', 'mobile'}
if data_key in phone_concepts:



Stosuj poprawe ale tylko z DSL LLM bez hardkodowanych selektorów, tylko generowanych w oparciu o LLM

