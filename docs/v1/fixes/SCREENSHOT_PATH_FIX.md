# 🔧 Naprawa: Debug Screenshots Zapisywane w Folderze Domeny

## ❌ **Problem**

**Screenshot debugowania** `debug_before_submit_*.png` był zapisywany **poza** folderem domeny:

```
❌ PRZED:
screenshots/
├── debug_before_submit_17640519233515382.png  ← Poza folderem domeny!
└── www.prototypowanie.pl/
    ├── step_0_1764050920.008828.png
    ├── step_1_1764050923.234567.png
    └── ... (inne screenshoty)
```

**Powinno być:**

```
✅ PO:
screenshots/
└── www.prototypowanie.pl/
    ├── step_0_1764050920.008828.png
    ├── step_1_1764050923.234567.png
    ├── debug_before_submit_17640519233515382.png  ← W folderze domeny!
    └── ... (inne screenshoty)
```

---

## 🔍 **Analiza Przyczyny**

### **Problem w `form_fill.py`**

**Przed naprawą:**
```python
# curllm_core/form_fill.py linia 342
screenshot_path = f"screenshots/debug_before_submit_{timestamp}.png"
await page.screenshot(path=screenshot_path)
```

**Hardcoded path** bez użycia `domain_dir`!

---

### **Prawidłowy Pattern w Innych Miejscach**

**W `task_runner.py`, `shortcuts.py`, `navigation.py`:**
```python
shot_path = await executor._take_screenshot(page, 0, target_dir=domain_dir)
# ↑ Używają domain_dir!
```

---

## ✅ **Rozwiązanie**

### **1. Dodano parametr `domain_dir` do `deterministic_form_fill`**

**Plik:** `curllm_core/form_fill.py` (linia 83)

**Przed:**
```python
async def deterministic_form_fill(instruction: str, page, run_logger=None):
```

**Po:**
```python
async def deterministic_form_fill(instruction: str, page, run_logger=None, domain_dir: Optional[str] = None):
```

---

### **2. Użyto `domain_dir` przy zapisie screenshot**

**Plik:** `curllm_core/form_fill.py` (linie 343-346)

**Przed:**
```python
screenshot_path = f"screenshots/debug_before_submit_{timestamp}.png"
await page.screenshot(path=screenshot_path)
```

**Po:**
```python
# Save in domain folder if provided, otherwise root screenshots/
if domain_dir:
    screenshot_path = f"{domain_dir}/debug_before_submit_{timestamp}.png"
else:
    screenshot_path = f"screenshots/debug_before_submit_{timestamp}.png"
await page.screenshot(path=screenshot_path)
```

**Logika:**
- Jeśli `domain_dir` jest dostępny → zapisz w folderze domeny
- Jeśli brak → fallback do root `screenshots/` (jak było)

---

### **3. Zaktualizowano wywołania w `executor.py`**

**Plik:** `curllm_core/executor.py` (linia 549)

**Przed:**
```python
async def _deterministic_form_fill(self, instruction, page, run_logger):
    return await _deterministic_form_fill_func(instruction, page, run_logger)
```

**Po:**
```python
async def _deterministic_form_fill(self, instruction, page, run_logger, domain_dir=None):
    return await _deterministic_form_fill_func(instruction, page, run_logger, domain_dir)
```

---

### **4. Zaktualizowano wywołania w `task_runner.py`**

**3 miejsca gdzie `_deterministic_form_fill` jest wywoływane:**

**Miejsce 1:** Linia 35 (early form fill)
```python
det_form = await executor._deterministic_form_fill(instruction, page, run_logger, domain_dir)
```

**Miejsce 2:** Linia 476 (form.fill tool)
```python
det = await executor._deterministic_form_fill(instruction, page, run_logger, domain_dir)
```

**Miejsce 3:** Linia 704 (finalize fallback)
```python
det2 = await executor._deterministic_form_fill(instruction, page, run_logger, domain_dir)
```

**Plus:** Dodano `domain_dir` do sygnatury `_finalize_fallback` (linia 699)
```python
async def _finalize_fallback(executor, instruction, url, page, run_logger, result, domain_dir=None):
```

I przekazano w wywołaniu (linia 909)
```python
await _finalize_fallback(executor, instruction, url, page, run_logger, result, domain_dir)
```

---

### **5. Zaktualizowano wywołanie w `shortcuts.py`**

**Plik:** `curllm_core/shortcuts.py` (linia 16)

**Przed:**
```python
det_form = await executor._deterministic_form_fill(instruction, page, run_logger)
```

**Po:**
```python
det_form = await executor._deterministic_form_fill(instruction, page, run_logger, domain_dir)
```

---

## 📊 **Pliki Zmienione**

| Plik | Linie | Zmiany |
|------|-------|--------|
| `form_fill.py` | 83, 343-346 | Dodano `domain_dir` param + użycie w path |
| `executor.py` | 549, 558 | Dodano `domain_dir` param + przekazanie |
| `task_runner.py` | 35, 476, 699, 704, 909 | Przekazywanie `domain_dir` (5 miejsc) |
| `shortcuts.py` | 16 | Przekazywanie `domain_dir` |

**Razem:** 4 pliki, 10 zmian

---

## 🧪 **Test Po Naprawie**

### **Przed:**
```bash
curllm --visual --stealth "https://www.prototypowanie.pl/kontakt/" \
  -d '{"instruction":"Fill form: name=John, email=john@example.com"}' -v
```

**Struktura:**
```
screenshots/
├── debug_before_submit_17640519233515382.png  ❌ Poza!
└── www.prototypowanie.pl/
    └── step_0_*.png
```

---

### **Po:**
```bash
curllm --visual --stealth "https://www.prototypowanie.pl/kontakt/" \
  -d '{"instruction":"Fill form: name=John, email=john@example.com"}' -v
```

**Struktura:**
```
screenshots/
└── www.prototypowanie.pl/
    ├── step_0_*.png
    └── debug_before_submit_*.png  ✅ W folderze domeny!
```

---

## 🎯 **Korzyści**

### **1. Organizacja**
- Wszystkie screenshoty z danego runu w jednym folderze
- Łatwiejsze debugowanie (wszystko w jednym miejscu)

### **2. Czysty Root**
- Brak luźnych plików w `screenshots/`
- Wszystko zorganizowane per domena

### **3. Spójność**
- Wszystkie screenshoty używają tego samego wzorca
- `domain_dir` jest konsekwentnie używany wszędzie

---

## 📝 **Podsumowanie**

### ❌ **Problem:**
- Debug screenshots zapisywane poza folderem domeny
- Hardcoded path bez `domain_dir`

### ✅ **Rozwiązanie:**
- Dodano parametr `domain_dir` do `deterministic_form_fill`
- Użyto `domain_dir` w path screenshot
- Zaktualizowano wszystkie wywołania (4 pliki, 10 miejsc)

### 🚀 **Rezultat:**
- ✅ Debug screenshots w folderze domeny
- ✅ Wszystkie screenshoty w jednym miejscu
- ✅ Spójna organizacja plików

---

**Data naprawy:** 2025-11-25T07:30:00  
**Severity:** LOW (organizacyjne, nie funkcjonalne)  
**Impact:** Screenshots są teraz lepiej zorganizowane  
**Status:** ✅ NAPRAWIONE - Serwis zrestartowany
