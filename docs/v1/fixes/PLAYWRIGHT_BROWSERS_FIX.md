# Playwright Browsers Installation Fix

## 🐛 Problem

```bash
$ curllm --visual "https://example.com"

Error: BrowserType.launch: Executable doesn't exist at 
/home/user/.cache/ms-playwright/chromium_headless_shell-1194/chrome-linux/headless_shell

╔════════════════════════════════════════════════════════════╗
║ Looks like Playwright was just installed or updated.       ║
║ Please run the following command to download new browsers: ║
║                                                            ║
║     playwright install                                     ║
╚════════════════════════════════════════════════════════════╝
```

### Root Cause

**`make stop && make clean && make start` nie instalowało przeglądarek!**

```bash
make clean:
  ✅ Czyści Python cache
  ✅ Reinstaluje pakiet (pip install -e .)
  ❌ NIE uruchamia playwright install  # <-- PROBLEM!
```

**Dlaczego?**
- `make clean` wywołuje `reinstall` który tylko robi `pip install -e .`
- `pip install playwright` instaluje **pakiet Python**, ale NIE **przeglądarki**
- Przeglądarki wymagają osobnego `playwright install`

---

## ✅ Rozwiązanie

### Quick Fix (Manual)

```bash
# Zainstaluj przeglądarki ręcznie
playwright install
```

Lub tylko Chromium:
```bash
playwright install chromium
```

### Permanent Fix (Automatyczny)

**Zaktualizowaliśmy Makefile:**

```makefile
# Nowy target
install-browsers:
	@echo "🌐 Installing Playwright browsers..."
	@python -m playwright install chromium
	@echo "✅ Playwright browsers ready!"

# Automatycznie wywołuje install-browsers
start: clean-cache reinstall install-browsers
	@bash scripts/start.sh
```

**Teraz `make start` automatycznie:**
1. ✅ Czyści cache
2. ✅ Reinstaluje pakiet
3. ✅ **Instaluje przeglądarki** (NOWE!)
4. ✅ Startuje serwer

---

## 🚀 Użycie

### Opcja 1: Automatyczna (Recommended)

```bash
# Wszystko w jednym
make stop && make start
```

**Efekt:**
```
🧹 Cleaning cache...
✅ Cache cleaned!
🔄 Reinstalling curllm...
✅ Package reinstalled!
🌐 Installing Playwright browsers...
✅ Playwright browsers ready!
Starting services...
```

### Opcja 2: Tylko Przeglądarki

```bash
# Jeśli tylko przeglądarki brakują
make install-browsers
```

### Opcja 3: Pełna Reinstalacja

```bash
# Od początku
make install
```

---

## 📊 Porównanie

### PRZED (Broken)

```bash
$ make clean && make start
🧹 Cleaning...
🔄 Reinstalling package...
Starting services...

$ curllm --visual "https://example.com"
❌ Error: Executable doesn't exist  # FAIL!
```

**Problem:** Przeglądarki nie zainstalowane.

### PO (Fixed)

```bash
$ make clean && make start
🧹 Cleaning...
🔄 Reinstalling package...
🌐 Installing Playwright browsers...  # <-- NOWE!
✅ Playwright browsers ready!
Starting services...

$ curllm --visual "https://example.com"
✅ SUCCESS  # Działa!
```

---

## 🔍 Szczegóły Techniczne

### Co Robi `playwright install`?

```bash
playwright install chromium
```

**Pobiera:**
- Chromium browser (~200MB)
- Headless shell
- System dependencies (Linux)

**Lokalizacja:**
- Linux: `~/.cache/ms-playwright/`
- macOS: `~/Library/Caches/ms-playwright/`
- Windows: `%USERPROFILE%\AppData\Local\ms-playwright\`

### Dlaczego Osobno od Pakietu?

**Pakiet Python (`pip install playwright`):**
- Instaluje Python bindings
- API do sterowania przeglądarką
- ~5MB

**Przeglądarki (`playwright install`):**
- Faktyczne binarne pliki przeglądarek
- ~200MB+ na przeglądarkę
- Różne wersje dla różnych OS

**Są osobne aby:**
- Nie powiększać pakietu Python
- Umożliwić wybór przeglądarek
- Optymalizować rozmiar instalacji

---

## 🧪 Testowanie

### Sprawdź Zainstalowane Przeglądarki

```bash
# Lista zainstalowanych
playwright install --help

# Lub sprawdź folder
ls -lh ~/.cache/ms-playwright/
```

Powinno być:
```
chromium_headless_shell-1194/
  chrome-linux/
    headless_shell  # <-- Ten plik musi istnieć!
```

### Test Działania

```bash
# Prosty test
curllm --visual --stealth "https://example.com" -d "extract title"
```

**Oczekiwany output:**
```
✅ SUCCESS
Title: "Example Domain"
```

**Jeśli błąd:**
```
❌ Error: Executable doesn't exist
```
→ Uruchom `make install-browsers`

---

## 💡 FAQ

### Q: Czy `make start` zawsze instaluje przeglądarki?

**A:** Tak, ale tylko jeśli nie są już obecne. `playwright install` sprawdza czy są i pobiera tylko jeśli brakują.

### Q: Które przeglądarki są instalowane?

**A:** Tylko Chromium (najlżejsza opcja, ~200MB). Możesz zainstalować więcej:

```bash
playwright install firefox webkit  # Dodatkowe przeglądarki
```

### Q: Co jeśli mam mało miejsca?

**A:** Chromium jest obowiązkowy dla curllm. Jeśli brak miejsca:

```bash
# Usuń stare wersje
rm -rf ~/.cache/ms-playwright/chromium*-old*

# Lub wszystkie i reinstaluj
rm -rf ~/.cache/ms-playwright/
make install-browsers
```

### Q: Czy mogę używać systemowej przeglądarki?

**A:** Nie, Playwright wymaga własnych wersji przeglądarek z specjalnymi API.

---

## 📚 Related Docs

- **Makefile:** Wszystkie dostępne targets
- **install.sh:** Pełny proces instalacji (zawiera `playwright install`)
- **README.md:** Główna dokumentacja

---

## 🎯 Summary

### Problem
```
make clean && make start → NIE instalował przeglądarek
```

### Rozwiązanie
```
Dodano install-browsers do Makefile
start: clean-cache reinstall install-browsers
```

### Rezultat
```
make start → Automatycznie instaluje wszystko ✅
```

**Status: FIXED** ✅

---

## 🚀 Next Steps

Po zainstalowaniu przeglądarek:

1. ✅ Test transparent orchestrator:
   ```bash
   curllm --visual --stealth "https://www.prototypowanie.pl/" \
     -d '{"instruction":"Fill form...", "params":{"llm_transparent_orchestrator": true}}'
   ```

2. ✅ Sprawdź logi:
   ```bash
   tail -f logs/run-*.md
   ```

3. ✅ Sprawdź screenshoty:
   ```bash
   ls -lht screenshots/
   ```

**Gotowe!** 🎉
