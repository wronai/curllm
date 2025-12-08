"""
Form Fill module - DEPRECATED: Use curllm_core.form_fill package instead.

This module is kept for backward compatibility.
New code should use:
    from curllm_core.form_fill import deterministic_form_fill, parse_form_pairs
"""

# Re-export from new package for backward compatibility
from curllm_core.form_fill import (
    parse_form_pairs,
    robust_fill_field as _robust_fill_field_new,
    deterministic_form_fill,
)

# Keep old function signatures for compatibility
async def _robust_fill_field(page, selector: str, value: str) -> bool:
    """Robust field filling with multiple fallbacks and event triggering."""
    try:
        # Attempt 1: page.fill (native Playwright)
        try:
            await page.fill(selector, value, timeout=3000)
            # Trigger events on the field
            await page.evaluate(
                """(sel) => {
                  const el = document.querySelector(sel);
                  if (el) {
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    el.blur();
                  }
                }""", selector
            )
            return True
        except Exception:
            pass
        # Attempt 2: page.type (slower but more reliable for some fields)
        try:
            await page.evaluate(f"(sel) => {{ const el = document.querySelector(sel); if (el) el.value = ''; }}", selector)
            await page.type(selector, value, delay=20, timeout=3000)
            await page.evaluate(
                """(sel) => {
                  const el = document.querySelector(sel);
                  if (el) {
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    el.blur();
                  }
                }""", selector
            )
            return True
        except Exception:
            pass
        # Attempt 3: Direct DOM setValue via evaluate
        try:
            await page.evaluate(
                """(args) => {
                  const el = document.querySelector(args.sel);
                  if (el) {
                    el.value = args.val;
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    el.blur();
                  }
                }""", {"sel": selector, "val": value}
            )
            return True
        except Exception:
            pass
        return False
    except Exception:
        return False


async def deterministic_form_fill(instruction: str, page, run_logger=None, domain_dir: Optional[str] = None, llm=None) -> Optional[Dict[str, Any]]:
    """
    Fill form using LLM-driven field detection.
    
    Architecture:
    1. LLM generates field concepts dynamically (if available)
    2. Field concepts are passed to JavaScript for DOM matching
    3. Fallback to default concepts if LLM unavailable
    """
    try:
        # Priority: instruction > window.__curllm_canonical
        # First, get values from window.__curllm_canonical (from tool args)
        canonical: Dict[str, str] = {}
        try:
            cc = await page.evaluate("() => (window.__curllm_canonical||null)")
            if isinstance(cc, dict):
                # Use dynamic field detection from known canonical fields
                for k, v in cc.items():
                    if isinstance(v, str) and v.strip():
                        canonical[k] = v.strip()
        except Exception:
            pass
        
        # Generate field concepts with LLM (or use defaults)
        try:
            from curllm_core.form_fill.js_scripts import generate_field_concepts_with_llm, get_default_field_concepts
            if llm:
                field_concepts = await generate_field_concepts_with_llm(page, llm)
                if run_logger:
                    run_logger.log_text("🤖 Using LLM-generated field concepts")
            else:
                field_concepts = get_default_field_concepts()
        except Exception:
            # Fallback to inline defaults
            field_concepts = {
                "email": ["email", "e-mail", "mail", "correo", "poczta"],
                "name": ["name", "imi", "nazw", "full name", "fullname", "first name", "last name", "nombre"],
                "message": ["message", "wiadomo", "treść", "tresc", "content", "komentarz", "mensaje"],
                "subject": ["subject", "temat", "asunto", "topic"],
                "phone": ["phone", "telefon", "tel", "mobile", "celular", "komórka"],
            }
        
        # Then parse instruction and OVERWRITE canonical (instruction has priority)
        raw_pairs = parse_form_pairs(instruction)
        for k, v in raw_pairs.items():
            lk = k.lower()
            # Use semantic matching to determine field type
            matched_field = None
            for field, concepts in field_concepts.items():
                if any(x in lk for x in concepts):
                    matched_field = field
                    break
            if matched_field:
                canonical[matched_field] = v

        # Mark target fields in DOM and obtain stable selectors
        selectors = await page.evaluate(
            r"""
            () => {
              const visible = (el) => {
                if (!el) return false;
                const r = el.getBoundingClientRect();
                return r && r.width > 1 && r.height > 1 && !el.disabled && el.offsetParent !== null;
              };
              const intoView = (el) => { try { el.scrollIntoView({behavior:'auto', block:'center'}); } catch(e){} };
              const add = (arr, el, score) => { if (el && visible(el)) { intoView(el); arr.push({el, score}); } };
              
              // Get the parent form for an element
              const getForm = (el) => {
                if (!el) return null;
                return el.closest('form');
              };
              
              const findField = (keywords, prefer, targetForm) => {
                const C = [];
                const by = (sel, s) => { 
                  try { 
                    document.querySelectorAll(sel).forEach(el => {
                      // Only include if in target form (or no form restriction)
                      if (!targetForm || getForm(el) === targetForm) {
                        add(C, el, s);
                      }
                    });
                  } catch(e){} 
                };
                keywords.forEach(k => {
                  by(`input[name*="${k}"]`, 12);
                  by(`input[id*="${k}"]`, 11);
                  by(`input[placeholder*="${k}"]`, 10);
                  by(`input[aria-label*="${k}"]`, 10);
                  by(`textarea[name*="${k}"]`, 12);
                  by(`textarea[id*="${k}"]`, 11);
                  by(`textarea[placeholder*="${k}"]`, 10);
                  by(`textarea[aria-label*="${k}"]`, 10);
                });
                // label association
                Array.from(document.querySelectorAll('label')).forEach(lb => {
                  const t = (lb.innerText||'').toLowerCase();
                  keywords.forEach(k => {
                    if (t.includes(k)) {
                      const forId = lb.getAttribute('for');
                      let el = null;
                      if (forId) el = document.getElementById(forId);
                      if (!el) el = lb.querySelector('input,textarea');
                      // Check form membership
                      if (el && (!targetForm || getForm(el) === targetForm)) {
                        add(C, el, 13);
                      }
                    }
                  });
                });
                if (C.length === 0 && prefer === 'input') {
                  by('input[type="email"]', 9);
                  by('input[type="text"]', 5);
                }
                // For email field, prioritize input[type="email"] even if keywords matched
                if (prefer === 'email') {
                  by('input[type="email"]', 14);
                }
                C.sort((a,b)=>b.score-a.score);
                return C.length ? C[0].el : null;
              };
              
              // STEP 1: Find all forms and score them by field matches
              const forms = Array.from(document.querySelectorAll('form'));
              let bestForm = null;
              let bestScore = 0;
              
              forms.forEach(form => {
                let score = 0;
                // Check for key fields in this form
                const nameEl = findField(['name','fullname','full name','imi','imię','nazw'], 'input', form);
                if (nameEl) score += 3;
                const emailEl = findField(['email','e-mail','mail','adres'], 'email', form);
                if (emailEl) score += 3;
                const msgEl = findField(['message','wiadomo','treść','tresc','content','komentarz'], 'textarea', form);
                if (msgEl) score += 2;
                const phoneEl = findField(['phone','telefon','tel'], 'input', form);
                if (phoneEl) score += 1;
                
                if (score > bestScore) {
                  bestScore = score;
                  bestForm = form;
                }
              });
              
              // If no form found with fields, try without form restriction
              const targetForm = bestForm;
              
              const res = {};
              const marked = new Set();  // Track which elements are already marked
              const mark = (el, key) => { 
                if (!el) return null; 
                // Don't mark if already marked with different key
                if (el.hasAttribute('data-curllm-target') && el.getAttribute('data-curllm-target') !== key) {
                  return null;
                }
                el.setAttribute('data-curllm-target', key); 
                marked.add(el);
                return `[data-curllm-target="${key}"]`; 
              };
              
              // STEP 2: Find and mark fields within the best form
              
              // EMAIL FIELD FIRST (highest priority - type="email" is most reliable)
              // This prevents email fields from being misidentified as name fields
              const emailEl = findField(['email','e-mail','mail','adres'], 'email', targetForm);
              if (emailEl && !marked.has(emailEl)) {
                res.email = mark(emailEl, 'email');
                res._debug_email = { id: emailEl.id, name: emailEl.name, type: emailEl.type };
              }
              
              // MESSAGE FIELD (second priority - textarea is distinctive)
              let msgEl = findField(['message','wiadomo','treść','tresc','content','komentarz','zapytanie','opis','description'], 'textarea', targetForm);
              
              // FALLBACK: If no message field found by keywords, use ANY visible textarea in form
              if (!msgEl && targetForm) {
                const fallbackTextareas = targetForm.querySelectorAll('textarea');
                for (const ta of fallbackTextareas) {
                  if (visible(ta) && !marked.has(ta)) {
                    msgEl = ta;
                    break;
                  }
                }
              }
              
              if (msgEl && !marked.has(msgEl)) {
                res.message = mark(msgEl, 'message');
                res._debug_message = { id: msgEl.id, name: msgEl.name, type: msgEl.tagName, fallback: !msgEl.name?.match(/message|wiadomo|treść|opis/i) };
              }
              
              // NAME FIELD: Check for split fields (First + Last) only after email/message marked
              const firstNameEl = findField(['first','firstname','first name','imi','imię'], 'input', targetForm);
              const lastNameEl = findField(['last','lastname','last name','nazwisko','nazw'], 'input', targetForm);
              
              if (firstNameEl && lastNameEl && !marked.has(firstNameEl) && !marked.has(lastNameEl)) {
                // Split name field detected
                res.name_first = mark(firstNameEl, 'name_first');
                res.name_last = mark(lastNameEl, 'name_last');
                res._split_name = true;  // Flag for Python to split name
              } else {
                // Single name field
                const nameEl = findField(['name','fullname','full name','imi','imię','nazw'], 'input', targetForm);
                if (nameEl && !marked.has(nameEl)) res.name = mark(nameEl, 'name');
              }
              
              // Find OPTIONAL fields (NO fallback - only if exact match)
              // For subject: only mark if found by keyword, NOT by fallback
              const subjCandidates = [];
              ['subject','temat'].forEach(k => {
                try {
                  document.querySelectorAll(`input[name*="${k}"], input[id*="${k}"], input[placeholder*="${k}"]`).forEach(el => {
                    if (el && el.offsetParent !== null && !marked.has(el) && (!targetForm || getForm(el) === targetForm)) {
                      subjCandidates.push(el);
                    }
                  });
                } catch(e){}
              });
              if (subjCandidates.length > 0) {
                res.subject = mark(subjCandidates[0], 'subject');
              }
              
              // phone optional (with keyword match only)
              const phoneEl = findField(['phone','telefon','tel'], 'input', targetForm);
              if (phoneEl && !marked.has(phoneEl)) res.phone = mark(phoneEl, 'phone');
              // consent checkbox (GDPR/RODO) - enhanced detection
              const consentKeywords = ['zgod', 'akcept', 'regulamin', 'polityk', 'rodo', 'privacy', 'consent', 'agree', 'terms', 'warunki', 'akceptuj', 'potwierdzam'];
              let consent = null;
              let consentScore = 0;
              
              // Try label-associated checkboxes first
              Array.from(document.querySelectorAll('label')).forEach(lb => {
                const t = (lb.innerText||'').toLowerCase();
                const matchCount = consentKeywords.filter(k => t.includes(k)).length;
                if (matchCount > consentScore) {
                  const forId = lb.getAttribute('for');
                  let cb = null;
                  if (forId) {
                    cb = document.getElementById(forId);
                  } else {
                    // Try inside label
                    cb = lb.querySelector('input[type="checkbox"]');
                    // Try previous sibling
                    if (!cb && lb.previousElementSibling && lb.previousElementSibling.tagName === 'INPUT' && lb.previousElementSibling.type === 'checkbox') {
                      cb = lb.previousElementSibling;
                    }
                    // Try next sibling
                    if (!cb && lb.nextElementSibling && lb.nextElementSibling.tagName === 'INPUT' && lb.nextElementSibling.type === 'checkbox') {
                      cb = lb.nextElementSibling;
                    }
                    // Try parent's previous sibling (common pattern: <div><input></div><div><label></div>)
                    if (!cb && lb.parentElement && lb.parentElement.previousElementSibling) {
                      const prevInput = lb.parentElement.previousElementSibling.querySelector('input[type="checkbox"]');
                      if (prevInput) cb = prevInput;
                    }
                  }
                  if (cb && cb.type === 'checkbox' && visible(cb) && (!targetForm || getForm(cb) === targetForm)) {
                    consent = cb;
                    consentScore = matchCount;
                  }
                }
              });
              
              // If not found by label, try checkbox attributes (name, id, aria-label)
              if (!consent) {
                Array.from(document.querySelectorAll('input[type="checkbox"]')).forEach(cb => {
                  if (!visible(cb) || (targetForm && getForm(cb) !== targetForm)) return;
                  const name = (cb.getAttribute('name')||'').toLowerCase();
                  const id = (cb.getAttribute('id')||'').toLowerCase();
                  const ariaLabel = (cb.getAttribute('aria-label')||'').toLowerCase();
                  const combined = name + ' ' + id + ' ' + ariaLabel;
                  const matchCount = consentKeywords.filter(k => combined.includes(k)).length;
                  if (matchCount > consentScore) {
                    consent = cb;
                    consentScore = matchCount;
                  }
                });
              }
              
              // Fallback 1: required checkbox
              if (!consent && targetForm) {
                const reqCheckbox = targetForm.querySelector('input[type="checkbox"][required]');
                if (reqCheckbox && visible(reqCheckbox)) {
                  consent = reqCheckbox;
                }
              }
              
              // Fallback 2: if form has only ONE checkbox, use it (likely consent)
              if (!consent && targetForm) {
                const allCheckboxes = Array.from(targetForm.querySelectorAll('input[type="checkbox"]')).filter(cb => visible(cb));
                if (allCheckboxes.length === 1) {
                  consent = allCheckboxes[0];
                }
              }
              
              // Fallback 3: if still no consent and no target form, try any checkbox with consent keywords
              if (!consent && !targetForm) {
                const allCheckboxes = Array.from(document.querySelectorAll('input[type="checkbox"]')).filter(cb => visible(cb));
                if (allCheckboxes.length === 1) {
                  consent = allCheckboxes[0];
                }
              }
              
              if (consent && visible(consent)) {
                res.consent = mark(consent, 'consent');
              }
              
              // DEBUG: Report checkbox detection details
              const debugInfo = {
                targetFormId: targetForm ? (targetForm.id || targetForm.className || 'unnamed') : 'none',
                allCheckboxes: Array.from(document.querySelectorAll('input[type="checkbox"]')).length,
                visibleCheckboxes: Array.from(document.querySelectorAll('input[type="checkbox"]')).filter(cb => visible(cb)).length,
                inFormCheckboxes: targetForm ? Array.from(targetForm.querySelectorAll('input[type="checkbox"]')).filter(cb => visible(cb)).length : 0,
                consentFound: !!consent,
                consentScore: consentScore
              };
              res._debug_consent = debugInfo;
              
              // submit button - prioritize button in target form
              let subs = [];
              if (targetForm) {
                subs = Array.from(targetForm.querySelectorAll('button, input[type="submit"], .wpcf7-submit'));
              } else {
                subs = Array.from(document.querySelectorAll('button, input[type="submit"], .wpcf7-submit'));
              }
              subs = subs.filter(el => visible(el) && ((el.getAttribute('type')||'').toLowerCase()==='submit' || /(wyślij|wyslij|wyślij wiadomość|send message|send|submit)/i.test((el.innerText||el.value||'').toLowerCase())));
              if (subs.length) res.submit = mark(subs[0], 'submit');
              
              // Add debug info about which form was selected
              if (targetForm) {
                res._formId = targetForm.id || targetForm.getAttribute('class') || 'unnamed-form';
              }
              return res;
            }
            """
        )
        if not isinstance(selectors, dict):
            selectors = {}
        
        # DEBUG: Log what we're about to fill
        if run_logger:
            run_logger.log_text("🔍 Form fill debug:")
            
            # Show which form was selected (if any)
            if selectors.get("_formId"):
                run_logger.log_text(f"   🎯 Selected form: {selectors['_formId']}")
            
            # Show consent checkbox debug info
            if selectors.get("_debug_consent"):
                debug_consent = selectors["_debug_consent"]
                run_logger.log_text(f"   📋 Checkbox detection:")
                run_logger.log_text(f"      - All checkboxes: {debug_consent.get('allCheckboxes', 0)}")
                run_logger.log_text(f"      - Visible checkboxes: {debug_consent.get('visibleCheckboxes', 0)}")
                run_logger.log_text(f"      - In target form: {debug_consent.get('inFormCheckboxes', 0)}")
                run_logger.log_text(f"      - Consent found: {debug_consent.get('consentFound', False)}")
                run_logger.log_text(f"      - Consent score: {debug_consent.get('consentScore', 0)}")
            
            run_logger.log_text(f"   Canonical values: {canonical}")
            
            # Debug: Show email and message field detection
            if selectors.get("_debug_email"):
                run_logger.log_text(f"   🔍 Email field detected: {selectors['_debug_email']}")
            if selectors.get("_debug_message"):
                run_logger.log_text(f"   🔍 Message field detected: {selectors['_debug_message']}")
            
            # Filter out internal keys like _formId
            display_selectors = {k: v for k, v in selectors.items() if not k.startswith('_')}
            run_logger.log_text(f"   Found selectors: {list(display_selectors.keys())}")
            for key, selector in display_selectors.items():
                run_logger.log_text(f"   {key} → {selector}")
            
            # Warn about fields in instruction but not in form
            instruction_fields = set(canonical.keys())
            form_fields = set(display_selectors.keys())
            missing_fields = instruction_fields - form_fields
            if missing_fields:
                run_logger.log_text(f"   ⚠️  Fields in instruction but NOT in form: {missing_fields}")
                run_logger.log_text(f"      These will be SKIPPED (not filled)")
        
        filled: Dict[str, Any] = {"filled": {}, "submitted": False}
        
        # Handle SPLIT NAME FIELDS (First + Last)
        if selectors.get("_split_name") and canonical.get("name"):
            full_name = canonical["name"].strip()
            # Split on first space: "John Doe" -> "John", "Doe"
            parts = full_name.split(None, 1)  # Split on whitespace, max 1 split
            first_name = parts[0] if len(parts) > 0 else ""
            last_name = parts[1] if len(parts) > 1 else ""
            
            if run_logger:
                run_logger.log_text(f"   🔀 Split name detected: '{full_name}' → First: '{first_name}', Last: '{last_name}'")
            
            if selectors.get("name_first") and first_name:
                if run_logger:
                    run_logger.log_text(f"   ▶️  Filling name (first): '{first_name}' → {selectors['name_first']}")
                if await _robust_fill_field(page, str(selectors["name_first"]), first_name):
                    filled["filled"]["name_first"] = True
            
            if selectors.get("name_last") and last_name:
                if run_logger:
                    run_logger.log_text(f"   ▶️  Filling name (last): '{last_name}' → {selectors['name_last']}")
                if await _robust_fill_field(page, str(selectors["name_last"]), last_name):
                    filled["filled"]["name_last"] = True
        # Standard single name field
        elif canonical.get("name") and selectors.get("name"):
            if run_logger:
                run_logger.log_text(f"   ▶️  Filling name: '{canonical['name']}' → {selectors['name']}")
            if await _robust_fill_field(page, str(selectors["name"]), canonical["name"]):
                filled["filled"]["name"] = True
        if canonical.get("email") and selectors.get("email"):
            if run_logger:
                run_logger.log_text(f"   ▶️  Filling email: '{canonical['email']}' → {selectors['email']}")
            if await _robust_fill_field(page, str(selectors["email"]), canonical["email"]):
                filled["filled"]["email"] = True
        if canonical.get("subject") and selectors.get("subject"):
            if run_logger:
                run_logger.log_text(f"   ▶️  Filling subject: '{canonical['subject']}' → {selectors['subject']}")
            if await _robust_fill_field(page, str(selectors["subject"]), canonical["subject"]):
                filled["filled"]["subject"] = True
        if canonical.get("phone") and selectors.get("phone"):
            if run_logger:
                run_logger.log_text(f"   ▶️  Filling phone: '{canonical['phone']}' → {selectors['phone']}")
            if await _robust_fill_field(page, str(selectors["phone"]), canonical["phone"]):
                filled["filled"]["phone"] = True
        if canonical.get("message") and selectors.get("message"):
            if run_logger:
                run_logger.log_text(f"   ▶️  Filling message: '{canonical['message'][:50]}...' → {selectors['message']}")
            if await _robust_fill_field(page, str(selectors["message"]), canonical["message"]):
                filled["filled"]["message"] = True
        # Consent checkbox if present
        if selectors.get("consent"):
            try:
                await page.check(str(selectors["consent"]))
                filled["filled"]["consent"] = True
            except Exception:
                try:
                    await page.click(str(selectors["consent"]))
                    filled["filled"]["consent"] = True
                except Exception:
                    pass
        
        # AUTO-VALIDATION: Verify fields were actually filled
        if run_logger:
            run_logger.log_text("🔍 Auto-validation: Checking field values in DOM...")
        
        validation_results = await page.evaluate(
            """
            () => {
              const results = {};
              const check = (key) => {
                const el = document.querySelector(`[data-curllm-target="${key}"]`);
                if (!el) return { found: false };
                const value = el.value || '';
                const checked = el.type === 'checkbox' ? el.checked : null;
                const required = el.required || el.getAttribute('aria-required') === 'true' || el.getAttribute('data-required') === 'true';
                return { 
                  found: true, 
                  value: value,
                  checked: checked,
                  isEmpty: value.trim() === '' && checked === null,
                  isChecked: checked === true,
                  required: required
                };
              };
              results.name = check('name');
              results.name_first = check('name_first');
              results.name_last = check('name_last');
              results.email = check('email');
              results.subject = check('subject');
              results.phone = check('phone');
              results.message = check('message');
              results.consent = check('consent');
              return results;
            }
            """
        )
        
        if run_logger and isinstance(validation_results, dict):
            # Generate table for validation results
            headers = ["Field", "Value", "Status"]
            rows = []
            for field, result in validation_results.items():
                if result.get("found"):
                    req_marker = " [REQ]" if result.get("required") else ""
                    if result.get("checked") is not None:
                        status = ("✅ CHECKED" if result.get("isChecked") else "❌ UNCHECKED") + req_marker
                        rows.append([field, "(checkbox)", status])
                    elif result.get("isEmpty"):
                        status = "❌ EMPTY" + req_marker
                        rows.append([field, "", status])
                    else:
                        value_preview = str(result.get("value", ""))[:25]
                        status = "✅ FILLED" + req_marker
                        rows.append([field, value_preview, status])
            if rows:
                run_logger.log_table(headers, rows, "🔍 Auto-validation Results")
        
        # PRE-SUBMISSION DIAGNOSIS: Check for potential blocking issues
        if run_logger:
            run_logger.log_text("🔬 Pre-submission diagnosis:")
        
        pre_submit_diagnosis = await page.evaluate(
            """
            () => {
              const issues = [];
              const warnings = [];
              
              // Check all required fields in the form
              const targetForm = document.querySelector('[data-curllm-target="submit"]')?.closest('form');
              if (targetForm) {
                // Required checkboxes
                const requiredCheckboxes = targetForm.querySelectorAll('input[type="checkbox"][required], input[type="checkbox"][aria-required="true"]');
                requiredCheckboxes.forEach(cb => {
                  if (!cb.checked) {
                    const label = cb.labels?.[0]?.innerText || cb.id || 'unnamed checkbox';
                    issues.push({
                      type: 'required_checkbox_unchecked',
                      field: label.substring(0, 100),
                      element: cb.id || cb.name || 'unknown'
                    });
                  }
                });
                
                // Required inputs not filled
                const requiredInputs = targetForm.querySelectorAll('input[required], textarea[required], input[aria-required="true"], textarea[aria-required="true"]');
                requiredInputs.forEach(inp => {
                  if (inp.type !== 'checkbox' && !inp.value?.trim()) {
                    const label = inp.labels?.[0]?.innerText || inp.placeholder || inp.id || inp.name || 'unnamed field';
                    issues.push({
                      type: 'required_field_empty',
                      field: label.substring(0, 100),
                      element: inp.id || inp.name || 'unknown'
                    });
                  }
                });
                
                // Check for visible validation errors already present
                const errorSelectors = ['.error', '.invalid', '.forminator-error-message', '.wpcf7-not-valid-tip', '[aria-invalid="true"]'];
                errorSelectors.forEach(sel => {
                  const errors = targetForm.querySelectorAll(sel);
                  errors.forEach(err => {
                    if (err.offsetParent !== null) {
                      warnings.push({
                        type: 'existing_validation_error',
                        message: err.innerText?.substring(0, 100) || 'validation error present'
                      });
                    }
                  });
                });
              }
              
              return { issues, warnings, hasBlockingIssues: issues.length > 0 };
            }
            """
        )
        
        if run_logger and isinstance(pre_submit_diagnosis, dict):
            issues = pre_submit_diagnosis.get("issues", [])
            warnings = pre_submit_diagnosis.get("warnings", [])
            
            if issues:
                run_logger.log_text(f"   ⚠️  Found {len(issues)} blocking issue(s):")
                for issue in issues[:5]:  # Show max 5
                    issue_type = issue.get("type", "unknown")
                    field = issue.get("field", "unknown")
                    run_logger.log_text(f"      - {issue_type}: {field}")
            
            if warnings:
                run_logger.log_text(f"   ⚠️  Found {len(warnings)} warning(s):")
                for warning in warnings[:3]:  # Show max 3
                    msg = warning.get("message", "unknown")
                    run_logger.log_text(f"      - {msg}")
            
            if not issues and not warnings:
                run_logger.log_text("   ✅ No blocking issues detected")
        
        # AUTO-FIX: Try to fix blocking issues before submission
        if isinstance(pre_submit_diagnosis, dict) and pre_submit_diagnosis.get("hasBlockingIssues"):
            if run_logger:
                run_logger.log_text("🔧 Auto-fix: Attempting to resolve blocking issues...")
            
            fix_results = await page.evaluate(
                """
                () => {
                  const fixed = [];
                  const targetForm = document.querySelector('[data-curllm-target="submit"]')?.closest('form');
                  if (!targetForm) return { fixed, success: false };
                  
                  // Fix 1: Check all unchecked required checkboxes
                  const requiredCheckboxes = targetForm.querySelectorAll('input[type="checkbox"][required], input[type="checkbox"][aria-required="true"]');
                  requiredCheckboxes.forEach(cb => {
                    if (!cb.checked && cb.offsetParent !== null) {
                      try {
                        cb.click();
                        fixed.push({ type: 'checkbox_checked', element: cb.id || cb.name || 'unnamed' });
                      } catch(e) {
                        // Try clicking parent label
                        try {
                          const label = cb.labels?.[0] || cb.closest('label');
                          if (label) {
                            label.click();
                            fixed.push({ type: 'checkbox_checked_via_label', element: cb.id || cb.name || 'unnamed' });
                          }
                        } catch(e2) {}
                      }
                    }
                  });
                  
                  return { fixed, success: fixed.length > 0 };
                }
                """
            )
            
            if run_logger and isinstance(fix_results, dict):
                fixed = fix_results.get("fixed", [])
                if fixed:
                    run_logger.log_text(f"   ✅ Fixed {len(fixed)} issue(s):")
                    for fix in fixed:
                        run_logger.log_text(f"      - {fix.get('type')}: {fix.get('element')}")
                else:
                    run_logger.log_text("   ⚠️  Could not auto-fix any issues")
        
        # Attempt submit with basic validation-aware remediation
        if selectors.get("submit"):
            try:
                try:
                    await page.evaluate(
                        """
                        () => {
                          const qs = '[data-curllm-target="name"], [data-curllm-target="email"], [data-curllm-target="subject"], [data-curllm-target="phone"], [data-curllm-target="message"]';
                          document.querySelectorAll(qs).forEach(el => {
                            try { el.dispatchEvent(new Event('input', {bubbles:true})); } catch(e){}
                            try { el.blur(); } catch(e){}
                          });
                        }
                        """
                    )
                except Exception:
                    pass
                attempts = 0
                diag_last: Dict[str, Any] | None = None
                while attempts < 2:
                    attempts += 1
                    
                    # DEBUG: Take screenshot before submit to see validation errors
                    if run_logger and attempts == 1:
                        try:
                            import time
                            timestamp = str(time.time()).replace('.', '')
                            # Save in domain folder if provided, otherwise root screenshots/
                            if domain_dir:
                                screenshot_path = f"{domain_dir}/debug_before_submit_{timestamp}.png"
                            else:
                                screenshot_path = f"screenshots/debug_before_submit_{timestamp}.png"
                            await page.screenshot(path=screenshot_path)
                            # Log as markdown image for proper rendering
                            try:
                                run_logger.log_image(screenshot_path, alt=f"Screenshot before submit (attempt {attempts})")
                            except Exception:
                                run_logger.log_text(f"📸 Screenshot before submit (attempt {attempts}): {screenshot_path}")
                        except Exception as e:
                            if run_logger:
                                run_logger.log_text(f"   ⚠️  Could not take screenshot: {e}")
                    
                    try:
                        await page.click(str(selectors["submit"]))
                    except Exception:
                        pass
                    try:
                        await page.wait_for_selector('.wpcf7-response-output, .elementor-message-success, .elementor-alert.elementor-alert-success', timeout=5000)
                    except Exception:
                        pass
                    try:
                        await page.wait_for_load_state("networkidle")
                    except Exception:
                        pass
                    
                    # POST-SUBMISSION DIAGNOSIS: Detailed check of what happened after submit
                    post_submit_result = await page.evaluate(
                        """
                        () => {
                          const result = { success: false, errors: [], warnings: [], successIndicators: [] };
                          const t = (document.body.innerText||'').toLowerCase();
                          
                          // Check for success indicators
                          if (/(dziękujemy|dziekujemy|wiadomość została|wiadomosc zostala|wiadomość wysłana|wiadomosc wyslana|message sent|thank you|success)/i.test(t)) {
                            result.successIndicators.push('success_text_found');
                          }
                          if (document.querySelector('.wpcf7-mail-sent-ok, .wpcf7-response-output, .elementor-message-success, .elementor-alert.elementor-alert-success')) {
                            result.successIndicators.push('success_element_found');
                          }
                          
                          if (result.successIndicators.length > 0) {
                            result.success = true;
                            return result;
                          }
                          
                          // Check for specific error types
                          const targetForm = document.querySelector('[data-curllm-target="submit"]')?.closest('form');
                          if (targetForm) {
                            // Error 1: Required checkbox not checked
                            const errorCheckboxes = targetForm.querySelectorAll('input[type="checkbox"][required]:not(:checked), input[type="checkbox"][aria-required="true"]:not(:checked)');
                            errorCheckboxes.forEach(cb => {
                              const label = cb.labels?.[0]?.innerText || cb.id || 'checkbox';
                              result.errors.push({
                                type: 'required_checkbox_unchecked',
                                field: label.substring(0, 100)
                              });
                            });
                            
                            // Error 2: Required fields empty
                            const emptyRequired = targetForm.querySelectorAll('input[required]:not([type="checkbox"]), textarea[required]');
                            emptyRequired.forEach(inp => {
                              if (!inp.value?.trim()) {
                                const label = inp.labels?.[0]?.innerText || inp.placeholder || inp.id || 'field';
                                result.errors.push({
                                  type: 'required_field_empty',
                                  field: label.substring(0, 100)
                                });
                              }
                            });
                            
                            // Error 3: Visible validation errors
                            const errorMessages = targetForm.querySelectorAll('.forminator-error-message, .wpcf7-not-valid-tip, .error-message, [role="alert"]');
                            errorMessages.forEach(msg => {
                              if (msg.offsetParent !== null && msg.innerText?.trim()) {
                                result.errors.push({
                                  type: 'validation_error',
                                  message: msg.innerText.substring(0, 150)
                                });
                              }
                            });
                            
                            // Error 4: Fields marked as invalid
                            const invalidFields = targetForm.querySelectorAll('[aria-invalid="true"], .invalid, .wpcf7-not-valid, .forminator-error');
                            invalidFields.forEach(field => {
                              if (field.offsetParent !== null) {
                                const label = field.labels?.[0]?.innerText || field.placeholder || field.name || field.id || 'field';
                                result.errors.push({
                                  type: 'invalid_field',
                                  field: label.substring(0, 100)
                                });
                              }
                            });
                          }
                          
                          return result;
                        }
                        """
                    )
                    
                    # Log post-submission diagnosis
                    if run_logger and isinstance(post_submit_result, dict) and attempts == 1:
                        run_logger.log_text("🔬 Post-submission diagnosis:")
                        if post_submit_result.get("success"):
                            run_logger.log_text(f"   ✅ SUCCESS - Found {len(post_submit_result.get('successIndicators', []))} success indicator(s)")
                        else:
                            errors = post_submit_result.get("errors", [])
                            if errors:
                                run_logger.log_text(f"   ❌ Found {len(errors)} error(s) blocking submission:")
                                for error in errors[:5]:  # Show max 5
                                    error_type = error.get("type", "unknown")
                                    field = error.get("field") or error.get("message", "unknown")
                                    run_logger.log_text(f"      - {error_type}: {field}")
                            else:
                                run_logger.log_text("   ⚠️  Submission status unclear - no success or error indicators found")
                    
                    ok = bool(post_submit_result.get("success")) if isinstance(post_submit_result, dict) else False
                    if ok:
                        filled["submitted"] = True
                        break
                    try:
                        diag_last = await page.evaluate(
                            """
                            () => {
                              const txt = (document.body.innerText||'').toLowerCase();
                              // Check for invalid email directly on email field
                              const emailField = document.querySelector('[data-curllm-target="email"]');
                              let invalidEmail = false;
                              if (emailField) {
                                invalidEmail = emailField.getAttribute('aria-invalid') === 'true'
                                  || emailField.classList.contains('wpcf7-not-valid')
                                  || emailField.classList.contains('forminator-error')
                                  || (emailField.nextElementSibling && emailField.nextElementSibling.classList.contains('forminator-error-message'))
                                  || (emailField.parentElement && emailField.parentElement.querySelector('.forminator-error-message'));
                              }
                              if (!invalidEmail) {
                                invalidEmail = /(nie jest prawidłowy adres e-mail|nieprawidłowy email|błędny email|invalid email)/i.test(txt);
                              }
                              const consentRequired = (!!document.querySelector('input[type="checkbox"][required], input[type="checkbox"].wpcf7-not-valid'))
                                && /(zgod|akcept|privacy|regulamin)/i.test(txt);
                              const requiredMissing = /(wymagane|required|to pole jest wymagane)/i.test(txt)
                                || !!document.querySelector('.wpcf7-not-valid, .forminator-error-message, .elementor-field-required');
                              return {invalid_email: !!invalidEmail, consent_required: !!consentRequired, required_missing: !!requiredMissing};
                            }
                            """
                        )
                    except Exception:
                        diag_last = None
                    if isinstance(diag_last, dict):
                        if diag_last.get("invalid_email") and selectors.get("email"):
                            # Try multiple email formats if validation fails
                            try:
                                host = await page.evaluate("() => (location.hostname||'')")
                            except Exception:
                                host = ""
                            try:
                                dom = host.lstrip('www.') if isinstance(host, str) else ""
                            except Exception:
                                dom = ""
                            
                            # Build fallback email list (try generic addresses first)
                            fallback_emails = []
                            if dom:
                                fallback_emails.append(f"kontakt@{dom}")  # Generic contact
                                fallback_emails.append(f"info@{dom}")     # Generic info
                                fallback_emails.append(f"test@{dom}")     # Test account
                            
                            # Add original local part as last resort
                            try:
                                local = (canonical.get("email") or "user").split("@")[0] or "user"
                                if dom:
                                    fallback_emails.append(f"{local}@{dom}")
                            except Exception:
                                pass
                            
                            # Try each fallback email
                            email_accepted = False
                            for fallback_email in fallback_emails:
                                if run_logger:
                                    run_logger.log_text(f"⚠️  Attempting email fallback: {fallback_email}")
                                
                                if await _robust_fill_field(page, str(selectors["email"]), fallback_email):
                                    canonical["email"] = fallback_email
                                    filled["filled"]["email"] = True
                                    
                                    # Wait and check if still invalid
                                    try:
                                        await page.wait_for_timeout(500)
                                    except:
                                        pass
                                    
                                    # Re-check validation
                                    try:
                                        still_invalid = await page.evaluate(
                                            """
                                            () => {
                                              const emailField = document.querySelector('[data-curllm-target="email"]');
                                              if (!emailField) return false;
                                              return emailField.getAttribute('aria-invalid') === 'true'
                                                || emailField.classList.contains('wpcf7-not-valid')
                                                || emailField.classList.contains('forminator-error');
                                            }
                                            """
                                        )
                                        if not still_invalid:
                                            email_accepted = True
                                            if run_logger:
                                                run_logger.log_text(f"   ✅ Email fallback accepted: {fallback_email}")
                                            break
                                        else:
                                            if run_logger:
                                                run_logger.log_text(f"   ❌ Email fallback rejected: {fallback_email}")
                                    except:
                                        # Assume accepted if can't check
                                        email_accepted = True
                                        if run_logger:
                                            run_logger.log_text(f"   ✓ Email fallback applied: {fallback_email}")
                                        break
                            
                            if not email_accepted and run_logger:
                                run_logger.log_text(f"   ⚠️  All email fallbacks rejected")
                        if diag_last.get("consent_required") and selectors.get("consent"):
                            try:
                                await page.check(str(selectors["consent"]))
                            except Exception:
                                try:
                                    await page.click(str(selectors["consent"]))
                                except Exception:
                                    pass
                        # one more small wait before next attempt
                        try:
                            await page.wait_for_timeout(500)
                        except Exception:
                            pass
                if not filled.get("submitted") and diag_last is not None:
                    filled["errors"] = diag_last
            except Exception:
                pass
        filled["selectors"] = selectors
        filled["values"] = canonical
        
        # LOG FINAL FORM SUMMARY TABLE
        if run_logger:
            headers = ["Field", "Provided Value", "Selector", "Filled"]
            rows = []
            display_selectors = {k: v for k, v in selectors.items() if not k.startswith('_')}
            all_fields = set(canonical.keys()) | set(display_selectors.keys())
            
            for field in sorted(all_fields):
                value = canonical.get(field, "")
                selector = display_selectors.get(field, "")
                was_filled = filled.get("filled", {}).get(field, False)
                
                display_value = str(value)[:25] + ("..." if len(str(value)) > 25 else "") if value else "-"
                display_selector = str(selector)[:35] + ("..." if len(str(selector)) > 35 else "") if selector else "-"
                filled_status = "✅" if was_filled else ("⏭️" if not value else "❌")
                
                rows.append([field, display_value, display_selector, filled_status])
            
            if rows:
                run_logger.log_table(headers, rows, "📋 Form Fill Summary")
            
            # Final result line
            submitted = filled.get("submitted", False)
            result_emoji = "✅" if submitted else "❌"
            run_logger.log_text(f"**Form Result:** {result_emoji} {'SUBMITTED' if submitted else 'NOT SUBMITTED'}")
            if filled.get("errors"):
                run_logger.log_text(f"**Errors:** {filled['errors']}")
        
        return filled
    except Exception as e:
        if run_logger:
            run_logger.log_kv("deterministic_form_fill_error", str(e))
        return None
