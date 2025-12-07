# 📝 Bulk Form Filler - curllm

Masowe wypełnianie formularzy kontaktowych na wielu stronach jednocześnie.

## ✨ Funkcje

- **Multi-URL form filling** - Wypełnianie formularzy na wielu stronach jednocześnie
- **Automatyczne mapowanie pól** - LLM dopasowuje dane do pól formularza
- **Wykrywanie pól** - Automatyczne wykrywanie struktury formularza
- **RODO/Privacy** - Automatyczne zaznaczanie zgód
- **Streaming logs** - Logi w czasie rzeczywistym
- **Docker support** - Gotowe do uruchomienia

## 🚀 Szybki start

### Docker

```bash
cd forms/
docker compose up --build
# Otwórz: http://localhost:8081
```

### Lokalnie

```bash
python forms/app.py
# Otwórz: http://localhost:8081
```

## 📖 Jak używać

### Interfejs webowy

1. Otwórz `http://localhost:8081`
2. Wklej URL-e stron z formularzami (jeden na linię)
3. Wypełnij dane osobowe i treść wiadomości
4. Opcjonalnie dodaj instrukcje dla AI
5. Kliknij "Wypełnij formularze"

### API

```bash
# Wypełnij pojedynczy formularz
curl -X POST http://localhost:8081/api/fill \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/contact",
    "data": {
      "name": "Jan Kowalski",
      "email": "jan@example.com",
      "message": "Treść wiadomości..."
    },
    "submit": true
  }'

# Wykryj pola formularza
curl -X POST http://localhost:8081/api/detect \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/contact"}'

# Bulk fill (streaming)
curl -X POST http://localhost:8081/api/bulk/stream \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://site1.com/contact", "https://site2.com/kontakt"],
    "data": {"name": "Jan", "email": "jan@ex.com", "message": "Cześć!"},
    "submit": true
  }'
```

## 🎯 Przypadki użycia

### 1. Wysyłanie ofert do wielu firm
```
URLs: Lista stron kontaktowych firm
Dane: Imię, email firmowy, treść oferty
Instrukcja: "Wypełnij jako zapytanie ofertowe B2B"
```

### 2. Newsletter signup
```
URLs: Lista stron z formularzami newsletter
Dane: Email
Instrukcja: "Znajdź pole email i zapisz do newsletter"
```

### 3. Zapytania o cenę/dostępność
```
URLs: Sklepy internetowe z formularzami kontaktowymi
Dane: Imię, email, "Proszę o informację o dostępności produktu X"
```

## 🔧 Konfiguracja

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `PORT` | `8081` | Port serwera |
| `MAX_CONCURRENT_FORMS` | `3` | Równoległe formularze |
| `FORM_TIMEOUT` | `60` | Timeout (sekundy) |
| `LLM_PROVIDER` | (auto) | Provider LLM |

## ⚠️ Uwagi

- Używaj odpowiedzialnie - nie spamuj
- Niektóre strony mogą blokować automatyczne wypełnianie
- Upewnij się, że masz zgodę na kontakt z odbiorcami

## 📝 Licencja

MIT License
