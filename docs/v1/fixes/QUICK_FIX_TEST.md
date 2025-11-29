# Quick Fix Test - Email Field Detection

## 🐛 Problem Fixed

Pole **"Kontakt e-mail"** było wypełniane **"John"** zamiast **"john@example.com"**

---

## ⚡ Quick Test (5 minut)

### 1. Restart Serwera

```bash
make stop && make clean && make start
```

⏳ Czekaj aż serwer wystartuje (~10 sekund)

### 2. Test na prototypowanie.pl

```bash
curllm --visual --stealth --session email-fix \
  "https://www.prototypowanie.pl/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, phone=+48123456789, message=Hello test"
  }' -v
```

### 3. Sprawdź Screenshot

```bash
ls -lht screenshots/www.prototypowanie.pl/ | head -2
```

Otwórz najnowszy screenshot i sprawdź:

```
✅ Kontakt e-mail: "john@example.com" (NIE "John"!)
✅ Opis oczekiwania: "Hello test"
✅ Kontakt telefoniczny: "+48123456789"
✅ GDPR: CHECKED
```

### 4. Sprawdź Logi

```bash
grep "🔍 Email field detected" logs/run-*.md | tail -1
grep "🔍 Message field detected" logs/run-*.md | tail -1
grep "Found selectors" logs/run-*.md | tail -1
```

Powinno być:

```
🔍 Email field detected: {'id': 'forminator-field-email-1_...', 'name': 'email-1', 'type': 'email'}
🔍 Message field detected: {'id': 'forminator-field-textarea-1_...', 'name': 'textarea-1', 'type': 'TEXTAREA'}
Found selectors: ['email', 'message', 'phone', 'consent', 'submit']
```

---

## ✅ Success Criteria

| Check | Expected | Command |
|-------|----------|---------|
| Email field value | "john@example.com" | Screenshot |
| Message field value | "Hello test" | Screenshot |
| Email selector found | `email` in selectors | `grep "Found selectors" logs/...` |
| Form submitted | `true` | `grep "submitted" logs/...` |

---

## ❌ If Still Broken

### Symptom 1: Email still "John"

```bash
# Check if server restarted with new code
grep "EMAIL FIELD FIRST" curllm_core/form_fill.py
# Should show the new comment
```

If not found:
```bash
git pull  # Pull latest changes
make stop && make clean && make start
```

### Symptom 2: No debug logs

```bash
# Check if _debug_email is in form_fill.py
grep "_debug_email" curllm_core/form_fill.py
```

If not found → code not updated, restart server.

### Symptom 3: Email selector not found

```bash
# Check logs for field detection order
grep -A 5 "EMAIL FIELD FIRST" logs/run-*.md
```

Should show email being checked BEFORE name.

---

## 🎯 What Changed

**Before:**
```
1. NAME → finds email-1 (wrong!)
2. EMAIL → email-1 already marked (skip)
Result: email field missing ❌
```

**After:**
```
1. EMAIL → finds email-1 (type="email", score 14) ✅
2. MESSAGE → finds textarea-1 ✅
3. NAME → finds other fields ✅
Result: all fields correct ✅
```

---

## 📚 Documentation

- **Full details:** `FIX_EMAIL_FIELD_DETECTION.md`
- **Form diagnostics:** `FORM_AUTODIAGNOSIS.md`
- **WPForms fix:** `WPFORMS_SPLIT_NAME_FIX.md`

---

## 🚀 Ready!

If all checks pass:
- ✅ Email field detection is FIXED
- ✅ Message field detection is FIXED
- ✅ Form filling works correctly

**Test other sites:**
```bash
# softreck.com (WPForms)
curllm --visual --stealth "https://softreck.com/contact/" \
  -d '{"instruction":"Fill form: name=John Doe, email=john@example.com, message=Test"}' -v

# Other forms...
```
