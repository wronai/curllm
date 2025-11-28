# System Autodiagnozy Formularzy

## Przegląd

System automatycznie **diagnozuje i naprawia** problemy z wypełnianiem formularzy w 3 etapach:

```
1. PRE-SUBMISSION → 2. AUTO-FIX → 3. POST-SUBMISSION
```

---

## 1. 🔍 PRE-SUBMISSION DIAGNOSIS (Przed Wysłaniem)

**Kiedy:** Zaraz po wypełnieniu pól, PRZED kliknięciem Submit

**Co sprawdza:**

### A. Autowalidacja Wypełnionych Pól
```
🔍 Auto-validation: Checking field values in DOM...
   name: ✅ 'John Doe' [REQUIRED]
   email: ✅ 'john@example.com' [REQUIRED]
   phone: ✅ '+48123456789'
   message: ✅ 'Hello test'
   consent: ❌ UNCHECKED [REQUIRED]  ← Problem wykryty!
```

**Pokazuje:**
- ✅ Czy wartości trafiły do DOM
- ❌ Które pola są puste
- `[REQUIRED]` - które pola są wymagane

### B. Diagnoza Blokujących Problemów
```
🔬 Pre-submission diagnosis:
   ⚠️  Found 1 blocking issue(s):
      - required_checkbox_unchecked: Tak, zgadzam się z polityką prywatności
```

**Wykrywa:**
1. **Required checkboxes unchecked** - wymagane checkboxy nie zaznaczone
2. **Required fields empty** - wymagane pola puste
3. **Existing validation errors** - błędy walidacji już widoczne w DOM

---

## 2. 🔧 AUTO-FIX (Automatyczna Naprawa)

**Kiedy:** Zaraz po wykryciu problemów, PRZED wysłaniem

**Co naprawia:**

```
🔧 Auto-fix: Attempting to resolve blocking issues...
   ✅ Fixed 1 issue(s):
      - checkbox_checked_via_label: consent-1
```

**Mechanizmy naprawy:**
1. **Kliknięcie checkboxa** - `checkbox.click()`
2. **Kliknięcie labela** - jeśli checkbox nie reaguje
3. **Usunięcie CSS** - jeśli element jest ukryty (przyszła funkcja)

**Strategia:**
- Najpierw próbuje bezpośrednio
- Jeśli nie działa, próbuje przez parent element
- Raportuje co się udało naprawić

---

## 3. 🔬 POST-SUBMISSION DIAGNOSIS (Po Wysłaniu)

**Kiedy:** Zaraz PO kliknięciu Submit

**Co sprawdza:**

### A. Sukces
```
🔬 Post-submission diagnosis:
   ✅ SUCCESS - Found 2 success indicator(s)
```

**Indicators sukcesu:**
- Tekst: "Dziękujemy", "Message sent", "Thank you"
- Elementy: `.wpcf7-mail-sent-ok`, `.elementor-message-success`

### B. Błędy
```
🔬 Post-submission diagnosis:
   ❌ Found 3 error(s) blocking submission:
      - required_checkbox_unchecked: Zgoda na przetwarzanie danych
      - validation_error: To pole jest wymagane. Proszę je zaznaczyć.
      - invalid_field: email-1
```

**Wykrywa:**
1. **Required checkbox unchecked** - checkbox wciąż nie zaznaczony
2. **Required field empty** - pole wciąż puste
3. **Validation errors** - komunikaty błędów w DOM
4. **Invalid fields** - pola oznaczone jako `aria-invalid="true"`

---

## Przykład Pełnego Flow

### Scenariusz: Formularz z wymaganym checkboxem zgody

```
KROK 1: Wypełnianie pól
   ✅ name: 'John Doe' [REQUIRED]
   ✅ email: 'john@example.com' [REQUIRED]
   ❌ consent: UNCHECKED [REQUIRED]

KROK 2: Pre-submission diagnosis
   ⚠️  Found 1 blocking issue:
      - required_checkbox_unchecked: Zgoda na przetwarzanie

KROK 3: Auto-fix
   🔧 Attempting to resolve...
   ✅ Fixed 1 issue:
      - checkbox_checked_via_label: consent-1

KROK 4: Submit attempt
   [Click submit button]

KROK 5: Post-submission diagnosis
   ✅ SUCCESS - Found 1 success indicator
   
WYNIK: ✅ Form submitted successfully
```

---

## Konfiguracja i Rozszerzenia

### Przyszłe Usprawnienia

1. **Więcej strategii auto-fix:**
   - Usuwanie `display:none` z ukrytych checkboxów
   - Wypełnianie pól wymaganych placeholder wartościami
   - Generowanie losowych emaili dla validacji

2. **Uczenie się z błędów:**
   - Zapamiętywanie które strategie działają dla których stron
   - Adaptacja do nowych typów formularzy

3. **Rozszerzona detekcja:**
   - Captcha detection
   - ReCAPTCHA handling
   - iFrame form support

4. **Smart retry:**
   - Automatyczne retry z różnymi strategiami
   - Eskalacja do bardziej agresywnych metod

---

## Logi Diagnostyczne

### Format Logów

Wszystkie 3 fazy są logowane w markdown:

```markdown
## Step 1

Tool call: form.fill

🔍 Form fill debug:
   🎯 Selected form: forminator-module-5635
   
   📋 Checkbox detection:
      - All checkboxes: 1
      - Visible checkboxes: 1
      - In target form: 1
      - Consent found: true
      
   Canonical values: {...}
   Found selectors: ['name', 'email', 'phone', 'message', 'consent', 'submit']

🔍 Auto-validation: Checking field values in DOM...
   [wyniki]

🔬 Pre-submission diagnosis:
   [diagnoza przed wysłaniem]

🔧 Auto-fix: Attempting to resolve blocking issues...
   [naprawy]

📸 Screenshot before submit (attempt 1): [path]

🔬 Post-submission diagnosis:
   [diagnoza po wysłaniu]

{"submitted": true, "errors": null}
```

---

## Zalety Systemu

### 1. **Transparentność**
- Widzisz dokładnie co system robi
- Każdy krok jest zalogowany
- Łatwo zdiagnozować problemy

### 2. **Automatyzacja**
- Nie musisz ręcznie sprawdzać pól
- Automatyczne naprawianie problemów
- Oszczędność czasu deweloperskiego

### 3. **Niezawodność**
- Wykrywa problemy przed wysłaniem
- Diagnozuje niepowodzenia po wysłaniu
- Wielokrotne próby z różnymi strategiami

### 4. **Skalowalność**
- Łatwo dodać nowe typy walidacji
- Rozszerzalne strategie naprawy
- Działa z różnymi frameworkami formularzy

---

## Korzystanie z Systemu

System jest **automatycznie włączony** dla wszystkich zadań wypełniania formularzy.

```bash
curllm --visual --stealth \
  "https://example.com/contact/" \
  -d '{
    "instruction":"Fill contact form: name=John, email=john@example.com"
  }' -v
```

Sprawdź logi aby zobaczyć:
- ✅ Co zostało wypełnione
- ⚠️ Jakie problemy wykryto
- 🔧 Co zostało naprawione
- ✅/❌ Czy wysłanie się powiodło

---

## Debug Tips

### Jeśli formularz nie wysyła się:

1. **Sprawdź Pre-submission diagnosis:**
   ```
   🔬 Pre-submission diagnosis:
      ⚠️  Found X blocking issue(s)
   ```
   To pokaże co blokuje wysłanie

2. **Sprawdź Auto-fix results:**
   ```
   🔧 Auto-fix: Attempting to resolve...
      ✅ Fixed X issue(s)
   ```
   Jeśli 0 fixed, auto-fix nie zadziałał

3. **Sprawdź Post-submission diagnosis:**
   ```
   🔬 Post-submission diagnosis:
      ❌ Found X error(s)
   ```
   To pokaże co jest nadal nie tak

4. **Screenshot przed submit:**
   ```
   📸 Screenshot before submit: screenshots/[path]
   ```
   Zobacz wizualnie stan formularza

---

## Kompatybilność

System działa z:
- ✅ **WordPress formularze:** Contact Form 7, Forminator, Elementor
- ✅ **React/Vue formularze:** z HTML5 validation
- ✅ **Vanilla HTML formularze:** z required atrybutami
- ✅ **AJAX formularze:** z success/error indicators

Testowane na:
- WordPress Forminator ✅
- Contact Form 7 ✅
- Elementor Forms ✅
- Custom HTML5 Forms ✅
