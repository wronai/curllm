# Form Filling

**[📚 Documentation Index](INDEX.md)** | **[⬅️ Back to Main README](../README.md)**

---

## Overview

Automated form filling with intelligent value prioritization, error detection, and automatic remediation.

---

## Quick Start

```bash
# Basic form filling
curllm "https://example.com/contact" \
  -d '{"instruction":"Fill contact form: name=John Doe, email=john@example.com, message=Hello"}'

# With visual mode and session
curllm --visual --session myform \
  "https://example.com/contact" \
  -d '{"instruction":"Fill form: name=John, email=john@example.com"}'
```

---

## Value Prioritization

### Priority Order (Highest to Lowest)

1. **📝 Instruction values** (from `-d` JSON)
2. **🤖 LLM-generated args** (from planner)
3. **🔧 Canonical fallbacks** (defaults)

### Example

```bash
# Instruction
"Fill contact form: name=John Doe, email=john@example.com"

# LLM generates (lower priority)
{"name": "Test User", "email": "test@example.com"}

# Result: Instruction wins!
Final values: {"name": "John Doe", "email": "john@example.com"}
```

---

## Supported Field Types

### Standard Fields

| Field | Keyword Patterns | Required |
|-------|------------------|----------|
| **name** | name, imię, nazwisko, full name, fullname | Optional |
| **email** | email, e-mail, mail, adres e-mail | Usually required |
| **subject** | subject, temat | Optional |
| **phone** | phone, telefon, tel | Optional |
| **message** | message, wiadomość, treść, content, komentarz | Usually required |

### Auto-Detection

System automatically detects fields by:
1. `name` attribute
2. `id` attribute
3. `placeholder` text
4. `aria-label` attribute
5. Associated `<label>` text
6. Input `type` (e.g., `type="email"`)

---

## Robust Filling Strategy

### Multi-Method Approach

For each field, system tries (in order):

```python
1. page.fill(selector, value)           # Playwright default
2. page.type(selector, value)           # Character-by-character
3. page.evaluate(setValue via JS)       # Direct DOM manipulation
4. Dispatch events: input, change, blur # Trigger validation
```

### Event Dispatching

```javascript
// Automatically triggered after filling
element.dispatchEvent(new Event('input', {bubbles: true}));
element.dispatchEvent(new Event('change', {bubbles: true}));
element.blur();
```

This ensures framework validation (React, Vue, Angular) triggers properly.

---

## Error Detection & Remediation

### Automatic Error Detection

System detects errors by checking for:

```javascript
// Invalid email
document.querySelector('input[type="email"][aria-invalid="true"]')
document.querySelector('.wpcf7-not-valid[name*="email"]')
document.querySelector('.forminator-error-message')
/nie jest prawidłowy adres e-mail|invalid email/i.test(bodyText)

// Missing required field
document.querySelector('.wpcf7-not-valid')
document.querySelector('.forminator-error-message')
/wymagane|required|to pole jest wymagane/i.test(bodyText)

// Consent required
document.querySelector('input[type="checkbox"][required]')
/zgod|akcept|privacy|regulamin/i.test(bodyText)
```

### Automatic Remediation

**1. Invalid Email Fallback**

```python
# Original
email = "john@example.com"  # Validation fails

# Fallback: use site's domain
email = "john@prototypowanie.pl"  # ✅ Passes validation
```

**2. Consent Checkbox**

```python
# If consent required
consent_checkbox = page.locator('input[type="checkbox"][required]')
consent_checkbox.check()  # Automatically checks
```

**3. Retry Logic**

```python
# Up to 2 attempts
for attempt in range(2):
    submit()
    if success_detected():
        break
    if invalid_email():
        apply_email_fallback()
    if consent_required():
        check_consent()
```

---

## Success Detection

### Auto-Detection Patterns

System recognizes success by:

**Text patterns:**
```regex
/(dziękujemy|dziekujemy|wiadomość została|wiadomosc zostala|
  wiadomość wysłana|wiadomosc wyslana|message sent|
  thank you|success)/i
```

**DOM selectors:**
```css
.wpcf7-mail-sent-ok
.wpcf7-response-output
.elementor-message-success
.elementor-alert.elementor-alert-success
```

---

## Configuration

### Environment Variables

```bash
# Fastpath: Skip LLM, use deterministic filling
CURLLM_FASTPATH=true

# Use hierarchical planner for forms
CURLLM_HIERARCHICAL_PLANNER=true

# Action timeout (ms)
CURLLM_ACTION_TIMEOUT_MS=25000

# Wait after submit (ms)
CURLLM_WAIT_AFTER_CLICK_MS=1800
```

### Per-Request Options

```bash
curllm -d '{
  "instruction": "Fill form...",
  "params": {
    "fastpath": true,          # Skip LLM planning
    "action_timeout_ms": 30000 # Custom timeout
  }
}'
```

---

## Examples

### Basic Contact Form

```bash
curllm "https://example.com/contact" \
  -d '{
    "instruction": "Fill contact form: name=John Doe, email=john@example.com, subject=Inquiry, message=Hello, I would like to know more about your services."
  }'
```

### With Phone Number

```bash
curllm "https://example.com/contact" \
  -d '{
    "instruction": "Fill form: name=Jane Smith, email=jane@example.com, phone=+48 123 456 789, message=Please call me back."
  }'
```

### Polish Form

```bash
curllm "https://example.pl/kontakt" \
  -d '{
    "instruction": "Wypełnij formularz: imię=Jan Kowalski, email=jan@example.com, wiadomość=Dzień dobry, proszę o kontakt."
  }'
```

### With Fastpath (No LLM)

```bash
# Fastest: Direct form fill without LLM planning
curllm "https://example.com/contact" \
  -d '{
    "instruction": "Fill contact form: name=John, email=john@example.com",
    "params": {"fastpath": true}
  }'
```

---

## Logging & Debugging

### Enable Detailed Logging

```bash
# Verbose output
curllm -v "https://example.com/contact" \
  -d '{"instruction":"Fill form..."}'

# Check logs directory
ls logs/run-*.md
```

### Log Output Example

```markdown
## Step 1

Tool call: form.fill

```json
{"name": "John Doe", "email": "john@example.com", "message": "Hello"}
```

Result:

```json
{
  "filled": {"name": true, "email": true, "message": true, "consent": true},
  "submitted": true,
  "errors": null,
  "values": {
    "name": "John Doe",
    "email": "john@prototypowanie.pl",
    "message": "Hello"
  }
}
```
```

---

## Troubleshooting

### Form Not Submitting

**Check:**
1. Required fields filled?
   - Look for `required_missing: true` in logs
2. Consent checkbox present?
   - System auto-detects, but may miss custom checkboxes
3. CAPTCHA/reCAPTCHA present?
   - Use `CURLLM_USE_EXTERNAL_SLIDER_SOLVER=true`

**Solution:**
```bash
# Enable visual mode to see what's happening
curllm --visual "https://example.com/contact" \
  -d '{"instruction":"Fill form..."}'
```

### Email Validation Failing

**Issue:** Site rejects email domain

**Solution:**
```bash
# System automatically tries site's domain as fallback
# But you can specify a known-good domain
curllm -d '{
  "instruction": "Fill form: email=test@example.com",
  "params": {"fastpath": false}
}'
```

**Log output:**
```
Attempting email fallback: john@prototypowanie.pl
✓ Email fallback successful
```

### Field Not Detected

**Issue:** Custom field not recognized

**Check logs for:**
```
"selectors": {
  "name": "[data-curllm-target=\"name\"]",
  "email": null,  ← Field not found!
  ...
}
```

**Solution:** Field uses non-standard naming

```bash
# Use BQL for custom selectors
curllm "https://example.com" \
  -q 'fill("#custom-email-field", "john@example.com")'
```

### Slow Performance

**Issue:** Each form fill takes 40-60s

**Solution:** Use [Hierarchical Planner](HIERARCHICAL_PLANNER.md)

```bash
# Auto-enabled for contexts > 25KB
export CURLLM_HIERARCHICAL_PLANNER=true
export CURLLM_HIERARCHICAL_PLANNER_CHARS=25000
```

---

## Advanced Usage

### Custom Field Mapping

Add custom field detection in `form_fill.py`:

```python
# In deterministic_form_fill()
elif any(x in lk for x in ["custom", "special"]):
    canonical["custom_field"] = v
```

### Multi-Step Forms

```bash
# Step 1: Fill first page
curllm --session multiform "https://example.com/form-step1" \
  -d '{"instruction":"Fill: name=John, email=john@example.com"}'

# Step 2: Continue on next page (session preserved)
curllm --session multiform "https://example.com/form-step2" \
  -d '{"instruction":"Fill: address=123 Main St, city=Warsaw"}'
```

### Conditional Logic

```bash
# Use BQL for complex scenarios
curllm "https://example.com/form" \
  -q 'if(exists("#newsletter-checkbox")) { check("#newsletter-checkbox") }; fill("#email", "john@example.com")'
```

---

## Integration with Hierarchical Planner

Form filling works seamlessly with [Hierarchical Planner](HIERARCHICAL_PLANNER.md):

```
📊 Level 1: LLM sees form_outline
   └─ "This is a contact form with 5 fields"

📋 Level 2: LLM receives field details
   └─ "Call form.fill with name, email, message"

✅ Level 3: deterministic_form_fill() executes
   └─ Fills fields, handles errors, submits
```

---

## Related Documentation

- [Hierarchical Planner](HIERARCHICAL_PLANNER.md) - Token optimization
- [Playwright BQL](Playwright_BQL.md) - Custom browser queries
- [Examples](EXAMPLES.md) - More use cases
- [Troubleshooting](Troubleshooting.md) - General issues

---

**[📚 Documentation Index](INDEX.md)** | **[⬆️ Back to Top](#form-filling)** | **[Main README](../README.md)**
