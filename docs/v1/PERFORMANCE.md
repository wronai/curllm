# Performance Optimization Tips

## Make Commands - Fast vs Full Reinstall

### Problem
Poprzednio `make start` używał `pip install -e . --force-reinstall --no-cache-dir`, co:
- Pobierało WSZYSTKIE zależności z internetu (ignorując cache)
- Trwało kilka minut
- Było całkowicie niepotrzebne przy zwykłym developmencie

### Rozwiązanie

#### `make reinstall` (SZYBKIE - ~4s)
```bash
make reinstall
```
- Aktualizuje tylko symlinka do lokalnego projektu
- Używa cache pip dla zależności
- **Zalecane dla codziennej pracy**
- Czas: ~4 sekundy

#### `make reinstall-full` (WOLNE - ~2-5min)
```bash
make reinstall-full
```
- Pełna reinstalacja wszystkich zależności
- Pobiera z internetu (ignoruje cache)
- **Użyj tylko gdy:**
  - Zmieniłeś wersje zależności w `pyproject.toml`
  - Masz problemy z uszkodzonym cache
  - Po aktualizacji systemu/Python

### Porównanie

| Komenda | Czas | Kiedy użyć |
|---------|------|------------|
| `make start` | ~5-7s | Normalne uruchomienie |
| `make reinstall` | ~4s | Po zmianach w kodzie |
| `make reinstall-full` | ~2-5min | Po zmianach w dependencies |

### Co robi `pip install -e .`?

**Editable install** (`-e`):
- Tworzy symlink do lokalnego projektu
- Zmiany w kodzie widoczne natychmiast
- Nie kopiuje plików
- Nie pobiera zależności jeśli już są zainstalowane

**Flags które SPOWOLNIAJĄ:**
- `--force-reinstall` - wymusza reinstalację WSZYSTKICH pakietów
- `--no-cache-dir` - pomija cache pip (pobiera z internetu)

### Workflow developerski

```bash
# 1. Pierwsza instalacja (raz)
make install

# 2. Start development
make start                     # ~5-7s

# 3. Zmiany w kodzie Python
# -> kod automatycznie widoczny (editable mode)
# -> restart API: make restart  # ~5-7s

# 4. Zmiany w pyproject.toml (dependencies)
make reinstall-full           # ~2-5min
make start

# 5. Problemy z cache?
make clean-cache
make reinstall-full
make start
```

## Inne optymalizacje

### Playwright Browsers
Browsers są cache'owane. Instalują się tylko raz:
```bash
make install-browsers  # Tylko przy pierwszej instalacji lub aktualizacji
```

### Python Cache
Automatyczne czyszczenie przy `make stop`:
```bash
make stop
# Automatycznie czyści __pycache__, *.pyc, etc.
```

### API Restart bez full reinstall
```bash
# Szybki restart (bez reinstall)
./curllm --stop
./curllm --start

# Lub
make restart  # automatycznie robi clean-cache + reinstall + start
```

### LLM Models
Modele Ollama są cache'owane lokalnie. Pobierają się tylko raz:
```bash
ollama pull qwen2.5:14b  # Raz
# Potem zawsze dostępny offline
```

## Troubleshooting

### Problem: "ModuleNotFoundError" po zmianach
**Rozwiązanie:**
```bash
make reinstall  # Szybkie - tylko 4s
```

### Problem: Zależności się nie aktualizują
**Rozwiązanie:**
```bash
make reinstall-full  # Pełna reinstalacja
```

### Problem: Stare pliki .pyc
**Rozwiązanie:**
```bash
make clean-cache
make restart
```

### Problem: Playwright nie działa
**Rozwiązanie:**
```bash
make install-browsers
```

## Benchmarks

### Before optimization (stary sposób):
```
make start:
  - clean-cache: 1s
  - reinstall (--force-reinstall --no-cache-dir): 180-300s
  - install-browsers: 5s
  Total: ~3-5 minut
```

### After optimization (nowy sposób):
```
make start:
  - clean-cache: 1s
  - reinstall (tylko editable): 4s
  - install-browsers (cached): 1s
  Total: ~6 sekund
```

**Przyspieszenie: 30-50x szybciej!** 🚀

## Best Practices

1. **Używaj `make start` zamiast ręcznego pip install**
   - Automatycznie robi clean-cache
   - Szybszy reinstall
   - Instaluje browsers jeśli potrzeba

2. **Nie używaj `make reinstall-full` bez powodu**
   - Tylko przy zmianach w dependencies
   - Tylko przy problemach z cache

3. **Przy problemach z kodem:**
   ```bash
   make clean-cache
   make restart  # Nie reinstall-full!
   ```

4. **Przy problemach z dependencies:**
   ```bash
   make clean-cache
   make reinstall-full
   make start
   ```

5. **Git pull + aktualizacja:**
   ```bash
   git pull
   make restart  # Wystarczy restart, nie reinstall-full
   ```
