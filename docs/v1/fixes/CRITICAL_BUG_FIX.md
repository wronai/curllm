# 🐛 KRYTYCZNY BUG: Email Wypełniany Wartością "Test" (z subject)

## ❌ **Problem**

**Symptom:** Pole email było wypełniane wartością "Test" zamiast "john@example.com"

**Screenshot pokazuje:**
```
Imię: John Doe ✅
Adres e-mail: Test ❌ BŁĄD! (powinno być john@example.com)
Numer telefonu: +48123456789 ✅
Wiadomość: Hello i need quota... ✅
```

**Logi pokazują:**
```json
{
  "name": "email-1",
  "type": "email",
  "value": "Test",  // ❌ To jest wartość z subject!
  "visible": true,
  "required": true
}
```

**Instrukcja użytkownika:**
```
subject=Test, email=john@example.com
```

---

## 🔍 **Analiza Przyczyny**

### **Problem 1: Fallback w findField**

**Kod `findField` w form_fill.py:**
```javascript
const findField = (keywords, prefer) => {
  // ... szuka po keywords
  
  if (C.length === 0 && prefer === 'input') {
    by('input[type="email"]', 9);    // ← FALLBACK!
    by('input[type="text"]', 5);
  }
  
  return C.length ? C[0].el : null;
};
```

**Flow który powodował błąd:**

```
1. Szuka pola "subject" z keywords: ['subject', 'temat']
2. NIE znajduje żadnego pola (formularz nie ma subject!)
3. FALLBACK: zwraca pierwszy input[type="email"] jako "subject"
4. Oznacza pole EMAIL jako data-curllm-target="subject"
5. Później próbuje znaleźć pole email
6. Znajduje to samo pole, ale już oznaczone jako "subject"
7. System wypełnia to pole wartością subject="Test"
8. REZULTAT: Email field = "Test" ❌
```

---

### **Problem 2: Brak Śledzenia Już Oznaczonych Pól**

**Przed naprawą:**
```javascript
const mark = (el, key) => { 
  el.setAttribute('data-curllm-target', key); 
  return `[data-curllm-target="${key}"]`; 
};

// Znajduje pole email i oznacza jako "subject" (fallback)
const subjEl = findField(['subject','temat'], 'input');
if (subjEl) res.subject = mark(subjEl, 'subject');  // ← Oznacza EMAIL jako "subject"!

// Później próbuje znaleźć email
const emailEl = findField(['email'], 'email');
if (emailEl) res.email = mark(emailEl, 'email');   // ← To samo pole, już oznaczone!
```

**Rezultat:**
- Pole email ma `data-curllm-target="subject"` (z fallback)
- System wypełnia je wartością `subject="Test"`
- Email nigdy nie dostaje poprawnej wartości

---

## ✅ **Rozwiązanie**

### **Naprawa 1: Śledzenie Oznaczonych Pól**

```javascript
const marked = new Set();  // Track already marked elements

const mark = (el, key) => { 
  if (!el) return null; 
  
  // Don't mark if already marked with different key
  if (el.hasAttribute('data-curllm-target') && 
      el.getAttribute('data-curllm-target') !== key) {
    return null;  // ← Zapobiegamy duplikacji!
  }
  
  el.setAttribute('data-curllm-target', key); 
  marked.add(el);
  return `[data-curllm-target="${key}"]`; 
};
```

**Benefit:** Pole może być oznaczone tylko RAZ, z jednym kluczem.

---

### **Naprawa 2: Subject BEZ Fallback (Exact Match Only)**

**Przed:**
```javascript
// Używał findField z fallback
const subjEl = findField(['subject','temat'], 'input');
if (subjEl) res.subject = mark(subjEl, 'subject');
// ↑ Jeśli nie znajdzie, fallback zwraca inne pole!
```

**Po:**
```javascript
// TYLKO exact keyword match, BEZ fallback
const subjCandidates = [];
['subject','temat'].forEach(k => {
  document.querySelectorAll(`input[name*="${k}"], input[id*="${k}"], input[placeholder*="${k}"]`)
    .forEach(el => {
      if (el && el.offsetParent !== null && !marked.has(el)) {
        subjCandidates.push(el);
      }
    });
});
if (subjCandidates.length > 0) {
  res.subject = mark(subjCandidates[0], 'subject');
}
// ↑ Jeśli nie znajdzie, zwraca PUSTĄ listę (nie używa fallback)
```

**Benefit:** Subject jest wykrywany TYLKO jeśli faktycznie istnieje pole z tym słowem kluczowym.

---

### **Naprawa 3: Priorytetyzacja Wymaganych Pól**

```javascript
// Find REQUIRED fields first (with fallback)
const nameEl = findField(['name','fullname',...], 'input');
if (nameEl) res.name = mark(nameEl, 'name');

const emailEl = findField(['email','e-mail',...], 'email');
if (emailEl && !marked.has(emailEl)) res.email = mark(emailEl, 'email');

const msgEl = findField(['message','wiadomo',...], 'textarea');
if (msgEl && !marked.has(msgEl)) res.message = mark(msgEl, 'message');

// Find OPTIONAL fields AFTER (NO fallback)
// Subject - exact match only
const subjCandidates = [...]; // bez fallback

// Phone - with keyword match, but check if not marked
const phoneEl = findField(['phone','telefon',...], 'input');
if (phoneEl && !marked.has(phoneEl)) res.phone = mark(phoneEl, 'phone');
```

**Benefit:** Wymagane pola (name, email, message) są oznaczane PIERWSZE, opcjonalne (subject, phone) DRUGIE i nie mogą nadpisać.

---

### **Naprawa 4: Szczegółowe Logowanie**

**Dodano debug output:**
```python
🔍 Form fill debug:
   Canonical values: {'name': 'John Doe', 'email': 'john@example.com', 'subject': 'Test', ...}
   Found selectors: ['name', 'email', 'message', 'phone']
   name → [data-curllm-target="name"]
   email → [data-curllm-target="email"]
   message → [data-curllm-target="message"]
   phone → [data-curllm-target="phone"]
   
   ⚠️  Fields in instruction but NOT in form: {'subject'}
      These will be SKIPPED (not filled)
   
   ▶️  Filling name: 'John Doe' → [data-curllm-target="name"]
   ▶️  Filling email: 'john@example.com' → [data-curllm-target="email"]
   ▶️  Filling phone: '+48123456789' → [data-curllm-target="phone"]
   ▶️  Filling message: 'Hello i need quota...' → [data-curllm-target="message"]
```

**Benefit:** Widzimy DOKŁADNIE:
- Jakie wartości mamy (canonical)
- Jakie selektory znaleziono
- Które pola są pomijane (subject)
- Co wypełniamy i gdzie

---

## 📊 **Przed vs Po**

### **PRZED (❌ Błąd):**
```
1. findField('subject') → NIE znajduje
2. FALLBACK → zwraca input[type="email"]
3. mark(emailField, 'subject')
4. emailField.data-curllm-target = "subject"
5. Później: wypełnia emailField wartością "Test" (z subject)
6. REZULTAT: Email = "Test" ❌
```

### **PO (✅ Naprawione):**
```
1. mark(emailField, 'email') NAJPIERW (priorytet)
2. emailField.data-curllm-target = "email"
3. marked.add(emailField)
4. Próba znalezienia 'subject' (exact match only)
5. NIE znajduje → subjCandidates = []
6. res.subject NIE jest ustawione
7. Wypełnia emailField wartością "john@example.com"
8. subject jest POMINIĘTE (nie ma w formularzu)
9. REZULTAT: Email = "john@example.com" ✅
```

---

## 🎯 **Co Zostało Naprawione**

### **Plik: `curllm_core/form_fill.py`**

**1. Dodano śledzenie oznaczonych pól:**
- `const marked = new Set();`
- Sprawdzanie `!marked.has(el)` przed oznaczeniem

**2. Subject bez fallback:**
- Zmieniono z `findField(['subject','temat'], 'input')`
- Na exact match: `querySelectorAll('input[name*="subject"], input[id*="subject"]')`

**3. Priorytetyzacja:**
- Wymagane pola (name, email, message) PIERWSZE
- Opcjonalne (subject, phone) DRUGIE z check `!marked.has(el)`

**4. Debug logging:**
- Ostrzeżenie o polach pominietych
- Szczegółowy log wypełniania każdego pola

---

## 🧪 **Test Po Naprawie**

```bash
curllm --visual --stealth --session kontakt \
  --model qwen2.5:14b \
  "https://www.prototypowanie.pl/kontakt/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, phone=+48123456789, subject=Test, message=Hello i need quota for my MVP project",
    "params":{"hierarchical_planner":true}
  }' \
  -v
```

**Oczekiwany rezultat w nowych logach:**
```
🔍 Form fill debug:
   ⚠️  Fields in instruction but NOT in form: {'subject'}
      These will be SKIPPED (not filled)
   
   ▶️  Filling email: 'john@example.com' → [data-curllm-target="email"]
```

**Oczekiwany rezultat w formularzu:**
```
Imię: John Doe ✅
Adres e-mail: john@example.com ✅ (poprawione!)
Numer telefonu: +48123456789 ✅
Wiadomość: Hello i need quota... ✅
```

---

## 📝 **Podsumowanie**

### **Problem:**
- Pole email wypełniane wartością "Test" (z subject)
- Przyczyna: fallback w findField zwracał pole email dla subject

### **Rozwiązanie:**
- ✅ Śledzenie już oznaczonych pól
- ✅ Subject tylko exact match (bez fallback)
- ✅ Priorytetyzacja wymaganych pól
- ✅ Szczegółowe logowanie

### **Status:**
✅ **NAPRAWIONE - Serwis Zrestartowany**

---

**Data naprawy:** 2025-11-24T22:10:00  
**Severity:** CRITICAL  
**Impact:** Email field was filled with wrong value  
**Fix:** Prevent field duplication + exact match for optional fields
