# Jak zalogować się i tworzyć artykuły na WordPress w jednej sesji (bez proxy)

- **Bez proxy**: pomiń pole `proxy` w żądaniu.
- **Jedna sesja**: używaj tego samego `session_id` w kolejnych wywołaniach. Sesja i cookies zapisują się automatycznie do `./workspace/sessions/<session_id>.json`.

## Krok 0: Sprawdź serwer
```bash
curl -s http://localhost:8000/health
```
Jeśli używasz innego portu, podmień `8000`.

## Krok 1: Pierwsze logowanie + utworzenie posta
- Upewnij się, że nagłówek jest poprawny: `Content-Type: application/json`
- Użyj swojego `session_id` np. `wp-mysession`
```bash
curl -s -X POST 'http://localhost:8000/api/execute' \
  -H 'Content-Type: application/json' \
  -d '{
    "wordpress_config": {
      "url": "https://example.wordpress.com",
      "username": "admin",
      "password": "secret123",
      "action": "create_post",
      "title": "Nowy artykuł",
      "content": "# Tytuł\n\nTreść w markdown...",
      "status": "publish",
      "categories": ["Technologia"],
      "tags": ["AI","Automation"]
    },
    "session_id": "wp-mysession",
    "headers": {"Accept-Language": "pl-PL,pl;q=0.9"}
  }'
```
- Wynik zwróci `post_url` po sukcesie.
- Po tej operacji sesja (cookies) jest zapisana i gotowa do ponownego użycia.

## Krok 2: Kolejne posty w tej samej sesji (bez podawania hasła)
- Powtarzaj żądanie z tym samym `session_id`, bez `username`/`password`.
```bash
curl -s -X POST 'http://localhost:8000/api/execute' \
  -H 'Content-Type: application/json' \
  -d '{
    "wordpress_config": {
      "url": "https://example.wordpress.com",
      "action": "create_post",
      "title": "Kolejny artykuł",
      "content": "Treść...",
      "status": "draft",
      "categories": ["Nowości"],
      "tags": ["curllm"]
    },
    "session_id": "wp-mysession",
    "headers": {"Accept-Language": "pl-PL,pl;q=0.9"}
  }'
```

## Batch (wiele plików .md naraz)
- Przygotuj katalog `./articles` z plikami `.md`. Opcjonalny FrontMatter:
  ```
  ---
  title: Status projektu curllm
  status: publish
  categories: Development, AI
  tags: automation, browser, llm
  ---
  ```
- Uruchom:
```bash
python wordpress_batch.py ./articles
```
- Zmienne środowiskowe:
  - `WP_URL`, `WP_USER`, `WP_PASS` (pierwszy login)
  - Opcjonalnie `PROXY_URL` (tu nie używasz, więc pomiń)

## Wskazówki
- Jeśli WordPress używa antybota/2FA/CAPTCHA, możesz dodać `"captcha_solver": true` w żądaniu. Bez proxy to nadal działa.
- Dla polskich layoutów dodawaj `headers.Accept-Language` jak w przykładzie.
- Jeśli dostaniesz 415, sprawdź dokładnie literę w `Content-Type` (bez literówek) i poprawność JSON.

# Status
- Podałem gotowe komendy do zalogowania i tworzenia wielu postów w jednej sesji bez proxy, oraz wariant batch. Możesz od razu wkleić i uruchomić.