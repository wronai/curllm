# Analiza Problemu: Formularze Nie Są Wysyłane

## 🔍 Główne Problemy Znalezione

### **Problem 1: Hierarchical Planner Pada z NoneType Error**

**Log:**
```
📋 Level 2 (Tactical): 1,427 chars context
   Form 'forminator-module-5635': 14 fields
Hierarchical planner failed: 'NoneType' object has no attribute 'lower', falling back to standard
```

**Przyczyna:**
- Kod: `field.get("name", "").lower()`
- Jeśli `field.get("name")` zwraca `None`, to `.lower()` pada
- Powinno być: `(field.get("name") or "").lower()`

**Status:** ✅ NAPRAWIONE w hierarchical_planner.py

---

### **Problem 2: LLM Zwraca Błędny Format Akcji**

**Log:**
```json
{
  "type": "fill",  // ❌ BŁĄD! Powinno być "tool"
  "name": "John Doe",
  "email": "test@example.com",
  ...
}
```

**Powinno być:**
```json
{
  "type": "tool",
  "tool_name": "form.fill",
  "args": {
    "name": "John Doe",
    "email": "test@example.com",
    ...
  }
}
```

**Przyczyna:**
- LLM NIE rozumie że `form.fill` to NARZĘDZIE (tool)
- LLM myśli że "fill" to typ akcji (jak "click", "scroll")
- Prompt nie jest wystarczająco jasny

**Status:** ⚠️ DO NAPRAWY

---

### **Problem 3: LLM Nie Wywołuje form.fill**

**Przebieg w logach:**
1. Step 1: Hierarchical planner pada → fallback do standard
2. Step 2-5: LLM zwraca `{"type": "fill", ...}` 
3. System wykonuje `action_type: fill` (nie form.fill!)
4. Brak wywołania deterministic_form_fill
5. Brak wysłania formularza

**Status:** ⚠️ DO NAPRAWY

---

## 🔧 Co Trzeba Naprawić

### **1. Naprawić Prompt dla LLM (llm_planner.py)**

**Przed:**
```
Available tools you MAY call by returning type='tool':
- form.fill(args: {...}): returns {form_fill: {submitted: boolean}}
```

**Po:**
```
CRITICAL: To fill forms, you MUST use the form.fill TOOL!

DO NOT use type="fill" - this is wrong!
ALWAYS use:
{
  "type": "tool",
  "tool_name": "form.fill",
  "args": {
    "name": "...",
    "email": "...",
    ...
  },
  "reason": "..."
}
```

---

### **2. Wykrywać i Naprawiać Błędny Format**

Dodać fallback w task_runner.py:

```python
# Jeśli LLM zwrócił type="fill" zamiast type="tool" + tool_name="form.fill"
if action.get("type") == "fill" and "tool_name" not in action:
    # Konwertuj na prawidłowy format
    action = {
        "type": "tool",
        "tool_name": "form.fill",
        "args": {k: v for k, v in action.items() if k not in ["type", "reason"]},
        "reason": action.get("reason", "Form filling (auto-corrected)")
    }
```

---

### **3. Dodać Walidację Hierarchical Planner**

Jeśli hierarchical planner pada, loguj DLACZEGO:

```python
except Exception as e:
    run_logger.log_text(f"❌ Hierarchical planner failed: {e}")
    run_logger.log_text(f"   Traceback: {traceback.format_exc()}")
```

---

## 📊 Dlaczego Emaile Nie Są Wysyłane?

### **Flow Obecnie:**

```
1. Hierarchical planner → PADA (NoneType)
2. Fallback do standard planner
3. LLM zwraca: {"type": "fill", "name": "...", "email": "..."}
4. System wykonuje: action_type = "fill"
5. NIE wywołuje form.fill tool!
6. NIE wypełnia formularza!
7. NIE wysyła emaila!
```

### **Flow Po Naprawie:**

```
1. Hierarchical planner → OK (naprawiony NoneType)
2. LLM zwraca: {"type": "tool", "tool_name": "form.fill", "args": {...}}
3. System wywołuje: deterministic_form_fill(args)
4. Wypełnia formularz ✅
5. Wysyła formularz ✅
6. Email wysłany! ✅
```

---

## 🎯 Priorytet Napraw

1. ✅ **Naprawić NoneType w hierarchical_planner** - GOTOWE
2. 🔴 **Wzmocnić prompt aby LLM zwracał type="tool"** - KRYTYCZNE
3. 🟠 **Dodać fallback dla błędnego formatu** - WAŻNE
4. 🟡 **Dodać debug logging dla hierarchical planner** - POMOCNE

---

## 📝 Testy Po Naprawie

```bash
# Test 1: Hierarchical planner powinien działać
curllm --visual --stealth \
  --model qwen2.5:14b \
  "https://www.prototypowanie.pl/kontakt/" \
  -d '{"instruction":"Fill contact form: name=John Doe, email=john@example.com, phone=+48123456789, message=Hello", "params":{"hierarchical_planner":true}}' \
  -v

# Oczekiwane w logach:
# ✓ Hierarchical planner (bez pada)
# ✓ {"type": "tool", "tool_name": "form.fill", ...}
# ✓ 🔍 Form fill debug: Canonical values: {...}
# ✓ Form submitted successfully

# Test 2: Standard planner z poprawnym formatem
curllm --visual --stealth \
  --model qwen2.5:14b \
  "https://httpbin.org/forms/post" \
  -d '{"instruction":"Fill form: custname=John, custemail=john@example.com"}' \
  -v

# Oczekiwane:
# ✓ {"type": "tool", "tool_name": "form.fill", ...}
# ✓ Form submitted
```
