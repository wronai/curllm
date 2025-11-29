# Fix: WPForms Split Name Fields

## Problem - softreck.com/contact/

### Screenshot pokazał:
- ❌ **Name First:** PUSTE
- ❌ **Name Last:** PUSTE  
- ❌ **E-mail:** "John Doe" (błędna wartość!)
- ⚠️ **Błąd walidacji:** "Please enter a valid email address."

### Co się stało?

```
Instrukcja: name=John Doe, email=john@example.com
```

**System wykrył:**
```
Found selectors: ['name', 'message', 'consent', 'submit']
⚠️  Fields in instruction but NOT in form: {'email', 'phone'}
```

**Rezultat:**
- Wypełnił `name` wartością "John Doe" ✅
- Ale NIE wykrył pola `email` ❌
- Pole email pozostało puste lub dostało błędną wartość

---

## Struktura WPForms

WPForms używa **split name fields** - oddzielne pola dla First i Last:

```html
<!-- Name Field - SPLIT -->
<div class="wpforms-field-name">
  <input id="wpforms-260-field_0" 
         name="wpforms[fields][0][first]"  ← First Name
         class="wpforms-field-name-first">
  <label>First</label>
  
  <input id="wpforms-260-field_0-last" 
         name="wpforms[fields][0][last]"   ← Last Name
         class="wpforms-field-name-last">
  <label>Last</label>
</div>

<!-- Email Field -->
<input id="wpforms-260-field_1" 
       type="email" 
       name="wpforms[fields][1]">

<!-- Message Field -->
<textarea id="wpforms-260-field_2" 
          name="wpforms[fields][2]">
</textarea>
```

**Problem:**
1. System szukał pojedynczego pola "name"
2. Znalazł jedno z pól (prawdopodobnie first)
3. Wypełnił je całą wartością "John Doe"
4. Pole Last pozostało puste
5. Pole email nie zostało wykryte (brak słowa "email" w ID/name)

---

## Rozwiązanie

### 1. **Wykrywanie Split Name Fields**

JavaScript teraz:
1. Szuka pól "first" i "last"
2. Jeśli oba znalezione → oznacza jako split name field
3. Ustawia flagę `_split_name: true`

```javascript
// NAME FIELD: Check for split fields (First + Last) first
const firstNameEl = findField(['first','firstname','first name','imi','imię'], 'input', targetForm);
const lastNameEl = findField(['last','lastname','last name','nazwisko','nazw'], 'input', targetForm);

if (firstNameEl && lastNameEl && !marked.has(firstNameEl) && !marked.has(lastNameEl)) {
  // Split name field detected
  res.name_first = mark(firstNameEl, 'name_first');
  res.name_last = mark(lastNameEl, 'name_last');
  res._split_name = true;  // Flag for Python to split name
} else {
  // Single name field (standard)
  const nameEl = findField(['name','fullname','full name'], 'input', targetForm);
  if (nameEl && !marked.has(nameEl)) res.name = mark(nameEl, 'name');
}
```

### 2. **Dzielenie Nazwy w Python**

Python automatycznie dzieli "John Doe":

```python
# Handle SPLIT NAME FIELDS (First + Last)
if selectors.get("_split_name") and canonical.get("name"):
    full_name = canonical["name"].strip()
    # Split on first space: "John Doe" -> "John", "Doe"
    parts = full_name.split(None, 1)  # Split on whitespace, max 1 split
    first_name = parts[0] if len(parts) > 0 else ""
    last_name = parts[1] if len(parts) > 1 else ""
    
    if run_logger:
        run_logger.log_text(f"   🔀 Split name detected: '{full_name}' → First: '{first_name}', Last: '{last_name}'")
    
    # Fill first name
    if selectors.get("name_first") and first_name:
        await _robust_fill_field(page, selectors["name_first"], first_name)
    
    # Fill last name
    if selectors.get("name_last") and last_name:
        await _robust_fill_field(page, selectors["name_last"], last_name)
```

### 3. **Poprawione Wykrywanie Email**

Email teraz wykrywany przez:
- Keywords: `['email','e-mail','mail','adres']`
- **Type attribute:** `input[type="email"]` ← Kluczowe dla WPForms!
- Label text matching

```javascript
const emailEl = findField(['email','e-mail','mail','adres'], 'email', targetForm);
if (emailEl && !marked.has(emailEl)) res.email = mark(emailEl, 'email');

// Inside findField:
if (prefer === 'email') {
  by('input[type="email"]', 14);  // Highest priority score!
}
```

---

## Przykładowy Log Po Naprawie

```markdown
🔍 Form fill debug:
   🎯 Selected form: wpforms-form-260
   
   Canonical values: {
     'name': 'John Doe', 
     'email': 'john@example.com', 
     'message': 'Hello test'
   }
   
   Found selectors: ['name_first', 'name_last', 'email', 'message', 'consent', 'submit']
   
   name_first → [data-curllm-target="name_first"]
   name_last → [data-curllm-target="name_last"]
   email → [data-curllm-target="email"]
   message → [data-curllm-target="message"]
   consent → [data-curllm-target="consent"]
   submit → [data-curllm-target="submit"]

🔀 Split name detected: 'John Doe' → First: 'John', Last: 'Doe'
   ▶️  Filling name (first): 'John' → [data-curllm-target="name_first"]
   ▶️  Filling name (last): 'Doe' → [data-curllm-target="name_last"]
   ▶️  Filling email: 'john@example.com' → [data-curllm-target="email"]
   ▶️  Filling message: 'Hello test' → [data-curllm-target="message"]

🔍 Auto-validation: Checking field values in DOM...
   name_first: ✅ 'John' [REQUIRED]
   name_last: ✅ 'Doe' [REQUIRED]
   email: ✅ 'john@example.com' [REQUIRED]
   message: ✅ 'Hello test' [REQUIRED]
   consent: ✅ CHECKED [REQUIRED]

🔬 Pre-submission diagnosis:
   ✅ No blocking issues detected

🔬 Post-submission diagnosis:
   ✅ SUCCESS - Found 1 success indicator(s)

✅ Form successfully submitted - auto-completing task
```

---

## Wspierane Formularze

System teraz obsługuje:

### ✅ Single Name Field
```html
<input name="name" type="text">
```

### ✅ Split Name Fields (WPForms, Gravity Forms)
```html
<input name="wpforms[fields][0][first]" class="wpforms-field-name-first">
<input name="wpforms[fields][0][last]" class="wpforms-field-name-last">
```

### ✅ Full Name Variants
```html
<input name="full_name">
<input name="fullname">
<input placeholder="Full Name">
```

### ✅ Polish Variants
```html
<input placeholder="Imię">      <!-- First -->
<input placeholder="Nazwisko">  <!-- Last -->
```

---

## Testowanie

```bash
# 1. Restart serwera
make stop && make clean && make start

# 2. Test WPForms (softreck.com)
curllm --visual --stealth --session test \
  "https://softreck.com/contact/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, message=Hello test"
  }' -v

# 3. Sprawdź logi
# Szukaj: "🔀 Split name detected"
```

### Oczekiwany Wynik:
- ✅ First Name: "John"
- ✅ Last Name: "Doe"
- ✅ Email: "john@example.com"
- ✅ Message: "Hello test"
- ✅ GDPR Consent: Checked
- ✅ Form submitted successfully

---

## Kompatybilność

| Form Builder | Split Name | Single Name | Email by Type |
|--------------|------------|-------------|---------------|
| WPForms      | ✅         | ✅          | ✅            |
| Gravity Forms| ✅         | ✅          | ✅            |
| Contact Form 7| ❌        | ✅          | ✅            |
| Forminator   | ❌         | ✅          | ✅            |
| Elementor    | ✅         | ✅          | ✅            |
| Custom HTML5 | ✅         | ✅          | ✅            |

---

## Dalsze Ulepszenia

### Planowane:
1. **Middle name support** - dla pól First, Middle, Last
2. **Title/Prefix support** - Mr./Mrs./Dr.
3. **Suffix support** - Jr./Sr./III
4. **International names** - obsługa różnych formatów
5. **Smart name parsing** - "Dr. John Doe Jr." → rozparsować wszystkie części

### Możliwe w przyszłości:
- NLP do rozpoznawania formatów nazwisk
- Uczenie maszynowe do przewidywania struktury pól
- Automatic retry z różnymi strategiami dla nieznanych formatów
