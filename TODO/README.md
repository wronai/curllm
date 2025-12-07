# Articles - curllm Documentation

Repozytorium artykułów o projekcie **curllm** przeznaczonych do publikacji na WordPress.

## Struktura

```
articles/
├── README.md                          # Ten plik
├── curllm-praktyczne-przyklady.md     # Działające komendy bash
├── curllm-status-projektu.md          # Status i przegląd projektu
├── curllm-wskazowki-dla-llm.md        # Wytyczne dla AI developerów
└── curllm-scenariusze-biznesowe.md    # Use cases i automatyzacje
```

## Artykuły

| Plik | Opis | Docelowa publiczność |
|------|------|---------------------|
| `curllm-praktyczne-przyklady.md` | Kompletny przewodnik z działającymi komendami | Developerzy, Power Users |
| `curllm-status-projektu.md` | Przegląd projektu, architektura, komponenty | Managerowie, Kontrybutorzy |
| `curllm-wskazowki-dla-llm.md` | Mapa kodu, priorytety rozwoju, wzorce | AI Asystenci, Core Devs |
| `curllm-scenariusze-biznesowe.md` | Biznesowe use cases ze skryptami | Business Users, Automation |

## Użycie

### Import do WordPress

1. Skopiuj zawartość pliku `.md`
2. W WordPress utwórz nowy post
3. Przełącz na edytor Markdown lub użyj bloku "Classic"
4. Wklej zawartość
5. Dostosuj formatowanie jeśli potrzeba

### Konwersja do HTML

```bash
# Użyj pandoc do konwersji
pandoc curllm-praktyczne-przyklady.md -o curllm-praktyczne-przyklady.html

# Lub z custom CSS
pandoc curllm-praktyczne-przyklady.md -c style.css -o output.html
```

## Aktualizacje

Artykuły powinny być aktualizowane przy:

- Nowych wersjach curllm
- Dodaniu nowych funkcjonalności
- Zmianach w API
- Nowych przypadkach użycia

## Licencja

Zawartość objęta licencją Apache 2.0, zgodnie z głównym projektem curllm.
