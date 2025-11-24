# curllm Website Monitoring

Prosty monitoring stron www oparty o curllm. Dla każdej domeny robi zrzut ekranu, wykrywa typowe problemy heurystycznie (np. error/timeout/captcha w tytule) i w razie wykrycia wysyła jeden zbiorczy e‑mail z załączonymi screenshotami.

[Pełne przykłady użycia znajdziesz w EXAMPLES.md](./EXAMPLES.md)

- Harmonogram przez cron (domyślnie co 3 godziny).
- Konfiguracja przez plik `.env`.
- Lista stron w `url.csv` (jedna domena/URL na linię).

## Wymagania

- curllm (patrz: rootowy README projektu)
- jq (parser JSON)
- Python 3.11+
- (opcjonalnie) SMTP do wysyłki maili

Linki:
- curllm: ./../README.md
- Proxies (opcjonalnie): ./../docs/REMOTE_PROXY_TUTORIAL.md
- Monitoring examples: ./EXAMPLES.md

## Szybki start

1) Skonfiguruj `.env`:
```bash
cd monitoring
cp .env.example .env
$EDITOR .env  # ustaw MAIL_TO i SMTP_* jeśli chcesz e-mail
```

2) Uzupełnij listę stron w `url.csv` (po jednej na linię; komentarze dozwolone po #):
```text
https://example.com
https://ceneo.pl
https://allegro.pl
https://softreck.com
```

3) Uruchom jednorazowo (test):
```bash
make setup
make run
```

4) Zainstaluj w cron (co 3 godziny):
```bash
make install-3h
# lub codziennie o 06:00
make install-06
# lub własny expr (CRON_EXPR z .env) / make install
```

5) Podgląd logów:
```bash
make logs
```

## Pliki

- `url.csv` — lista domen/URL (jedna na linię; komentarze po #). 
- `.env.example` — wzór konfiguracji, skopiuj do `.env`.
- `website_monitor.sh` — skrypt monitorujący i zarządzający cronem.
- `send_email.py` — wysyłka maili z załącznikami (SMTP przez `.env`).
- `Makefile` — ułatwia użycie (setup/run/install/remove/logs).

## Konfiguracja (.env)

Najważniejsze zmienne:
- `MAIL_TO` — odbiorca raportów (wymagane do wysyłki maili)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_SSL`, `MAIL_FROM` — SMTP
- `ISSUE_PATTERNS` — regex wykrywający problemy (domyślne: błędy HTTP/timeout/captcha)
- `CSV_FILE` — opcjonalna ścieżka do innego pliku CSV z listą URL
- `CURLLM_ARGS` — dodatkowe argumenty do `curllm` (np. `--stealth --headless`)
- `CRON_EXPR` — harmonogram crona (np. `0 6 * * *`)
- `CURLLM_BIN`, `JQ_BIN` — ścieżki do binarek (opcjonalnie)

## Jak to działa

- Skrypt uruchamia `curllm` dla każdego URL z poleceniem `screenshot`.
- Odczytuje JSON wynikowy (pola `success`, `result.title`, `screenshots`).
- Jeśli tytuł zawiera frazy z `ISSUE_PATTERNS` albo `success != true` — uznaje stronę za problematyczną.
- Wysyła jeden zbiorczy mail z listą problemów i dołącza ostatnie screenshoty.

## Przykłady

- Dodatkowe argumenty dla `curllm` (z `.env`):
```bash
CURLLM_ARGS="--stealth --headless"
```

- Własny harmonogram crona (z `.env`):
```bash
CRON_EXPR="0 6 * * *"  # codziennie 06:00
```

- Własny plik URL:
```bash
CSV_FILE="/path/to/my_urls.csv"
```

## Odinstalowanie/cleanup

- Usuń zadanie crona i zatrzymaj użycie:
```bash
make remove
```

## Wskazówki

- Jeśli często napotykasz CAPTCHA/403, użyj proxy (rotate:registry/rotate:public) — zobacz ./../docs/REMOTE_PROXY_TUTORIAL.md i ustaw `CURLLM_ARGS`.
- Jeśli nie masz SMTP, raport zostanie wypisany na stderr (bez wysyłki e-mail). 
- Upewnij się, że `jq` i `curllm` są dostępne w PATH (patrz `make setup`).
