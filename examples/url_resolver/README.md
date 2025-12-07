# 🔍 URL Resolver - Przykłady użycia

Komponent automatycznie znajduje odpowiednie podstrony na podstawie intencji użytkownika.

## Testowane sklepy/serwisy

| Serwis | URL | Scenariusze |
|--------|-----|-------------|
| Morele.net | morele.net | produkty, koszyk, kontakt, logowanie |
| X-kom | x-kom.pl | produkty, koszyk, blog, rejestracja |
| Allegro | allegro.pl | produkty, koszyk, FAQ, kariera |
| MediaExpert | mediaexpert.pl | produkty, dostawa, konto |
| Euro RTV AGD | euro.com.pl | produkty, gwarancja |
| Ceneo | ceneo.pl | produkty, FAQ, rejestracja |
| Empik | empik.com | produkty, regulamin, logowanie |
| Komputronik | komputronik.pl | produkty, kontakt |

## Przykłady

### 1. `example_find_products.py` - Szukanie produktów
```python
# User: "Znajdź pamięci RAM DDR5 32GB"
# URL: https://www.morele.net (strona główna)
# → Resolver używa wyszukiwarki → morele.net/search?q=RAM+DDR5
```

### 2. `example_find_contact.py` - Formularze kontaktowe
```python
# User: "Wypełnij formularz kontaktowy"
# URL: https://allegro.pl
# → Resolver szuka linku "Kontakt" → allegro.pl/pomoc/kontakt
```

### 3. `example_find_info.py` - Informacje (FAQ, zwroty, dostawa)
```python
# User: "Jaka jest polityka zwrotów?"
# URL: https://www.x-kom.pl
# → Resolver szuka linku "Zwroty" → x-kom.pl/zwroty-i-reklamacje
```

### 4. `example_shopping_flow.py` - Flow zakupowy
```python
# User: "Przejdź do koszyka"
# URL: https://www.morele.net/laptopy
# → Resolver szuka ikony koszyka → morele.net/koszyk
```

### 5. `example_auto_detect.py` - Automatyczne wykrywanie celu
```python
# Resolver SAM wykrywa intencję z naturalnego języka
# User: "Mam pytanie do obsługi - gdzie FAQ?"
# → Wykrywa: FIND_FAQ → nawiguje do centrum pomocy
```

## Uruchomienie

```bash
cd examples/url_resolver

# Pojedynczy przykład
python example_find_products.py

# Interaktywne menu
python run_all.py
```

## Jak URL Resolver rozwiązuje problemy

### Problem: User podał stronę główną sklepu
```
Przed: https://morele.net
Po:    https://morele.net/pamieci-ram-ddr5-42/?q=32GB

Strategia:
1. Sprawdź czy strona główna ma produkty → NIE
2. Znajdź search box → TAK
3. Wpisz "RAM DDR5 32GB" → Enter
4. Zwróć URL wyników
```

### Problem: User chce kontakt ale jest na stronie produktu
```
Przed: https://x-kom.pl/p/123456-laptop.html
Po:    https://x-kom.pl/kontakt

Strategia:
1. Wykryj cel: FIND_CONTACT_FORM
2. Szukaj linków: a[href*="kontakt"], a[href*="contact"]
3. Szukaj tekstu: "Kontakt", "Napisz do nas"
4. Nawiguj do znalezionego linku
```

### Problem: User pyta o zwroty
```
Przed: https://allegro.pl/kategoria/elektronika
Po:    https://allegro.pl/pomoc/zwroty

Strategia:
1. Wykryj cel: FIND_RETURNS (słowo "zwrot" w instrukcji)
2. Szukaj linków w stopce/menu
3. Nawiguj do polityki zwrotów
```
