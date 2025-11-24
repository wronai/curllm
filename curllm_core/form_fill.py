import json
import re
from typing import Any, Dict, Optional


def parse_form_pairs(instruction: str | None) -> Dict[str, str]:
    pairs: Dict[str, str] = {}
    text = instruction or ""
    # If JSON-like wrapper is used, parse to get inner instruction
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and isinstance(obj.get("instruction"), str):
            text = obj.get("instruction") or text
    except Exception:
        pass
    # Extract key=value pairs separated by commas/semicolons/newlines
    for m in re.finditer(r"([A-Za-ząćęłńóśźż\- ]+)\s*=\s*([^,;\n]+)", text, flags=re.IGNORECASE):
        k = (m.group(1) or "").strip().lower()
        v = (m.group(2) or "").strip()
        if k and v:
            pairs[k] = v
    return pairs


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


async def deterministic_form_fill(instruction: str, page, run_logger=None) -> Optional[Dict[str, Any]]:
    try:
        # Priority: instruction > window.__curllm_canonical
        # First, get values from window.__curllm_canonical (from tool args)
        canonical: Dict[str, str] = {}
        try:
            cc = await page.evaluate("() => (window.__curllm_canonical||null)")
            if isinstance(cc, dict):
                for k in ["name","email","subject","phone","message"]:
                    v = cc.get(k)
                    if isinstance(v, str) and v.strip():
                        canonical[k] = v.strip()
        except Exception:
            pass
        
        # Then parse instruction and OVERWRITE canonical (instruction has priority)
        raw_pairs = parse_form_pairs(instruction)
        for k, v in raw_pairs.items():
            lk = k.lower()
            if any(x in lk for x in ["email", "e-mail", "mail"]):
                canonical["email"] = v
            elif any(x in lk for x in ["name", "imi", "nazw", "full name", "fullname", "first name", "last name"]):
                canonical["name"] = v
            elif any(x in lk for x in ["message", "wiadomo", "treść", "tresc", "content", "komentarz"]):
                canonical["message"] = v
            elif any(x in lk for x in ["subject", "temat"]):
                canonical["subject"] = v
            elif any(x in lk for x in ["phone", "telefon", "tel"]):
                canonical["phone"] = v

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
              const findField = (keywords, prefer) => {
                const C = [];
                const by = (sel, s) => { try { document.querySelectorAll(sel).forEach(el => add(C, el, s)); } catch(e){} };
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
                      add(C, el, 13);
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
              
              // Find and mark REQUIRED fields first (with fallback)
              const nameEl = findField(['name','fullname','full name','imi','imię','nazw'], 'input');
              if (nameEl) res.name = mark(nameEl, 'name');
              const emailEl = findField(['email','e-mail','mail','adres'], 'email');
              if (emailEl && !marked.has(emailEl)) res.email = mark(emailEl, 'email');
              const msgEl = findField(['message','wiadomo','treść','tresc','content','komentarz'], 'textarea');
              if (msgEl && !marked.has(msgEl)) res.message = mark(msgEl, 'message');
              
              // Find OPTIONAL fields (NO fallback - only if exact match)
              // For subject: only mark if found by keyword, NOT by fallback
              const subjCandidates = [];
              ['subject','temat'].forEach(k => {
                try {
                  document.querySelectorAll(`input[name*="${k}"], input[id*="${k}"], input[placeholder*="${k}"]`).forEach(el => {
                    if (el && el.offsetParent !== null && !marked.has(el)) subjCandidates.push(el);
                  });
                } catch(e){}
              });
              if (subjCandidates.length > 0) {
                res.subject = mark(subjCandidates[0], 'subject');
              }
              
              // phone optional (with keyword match only)
              const phoneEl = findField(['phone','telefon','tel'], 'input');
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
                    cb = lb.querySelector('input[type="checkbox"]');
                  }
                  if (cb && cb.type === 'checkbox' && visible(cb)) {
                    consent = cb;
                    consentScore = matchCount;
                  }
                }
              });
              
              // If not found by label, try checkbox attributes (name, id, aria-label)
              if (!consent) {
                Array.from(document.querySelectorAll('input[type="checkbox"]')).forEach(cb => {
                  if (!visible(cb)) return;
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
              
              // Fallback: required checkbox
              if (!consent) {
                const reqCheckbox = document.querySelector('input[type="checkbox"][required]');
                if (reqCheckbox && visible(reqCheckbox)) {
                  consent = reqCheckbox;
                }
              }
              
              if (consent && visible(consent)) {
                res.consent = mark(consent, 'consent');
              }
              // submit button
              const subs = Array.from(document.querySelectorAll('button, input[type="submit"], .wpcf7-submit'))
                .filter(el => visible(el) && ((el.getAttribute('type')||'').toLowerCase()==='submit' || /(wyślij|wyslij|wyślij wiadomość|send message|send|submit)/i.test((el.innerText||el.value||'').toLowerCase())));
              if (subs.length) res.submit = mark(subs[0], 'submit');
              return res;
            }
            """
        )
        if not isinstance(selectors, dict):
            selectors = {}
        
        # DEBUG: Log what we're about to fill
        if run_logger:
            run_logger.log_text("🔍 Form fill debug:")
            run_logger.log_text(f"   Canonical values: {canonical}")
            run_logger.log_text(f"   Found selectors: {list(selectors.keys())}")
            for key, selector in selectors.items():
                run_logger.log_text(f"   {key} → {selector}")
            
            # Warn about fields in instruction but not in form
            instruction_fields = set(canonical.keys())
            form_fields = set(selectors.keys())
            missing_fields = instruction_fields - form_fields
            if missing_fields:
                run_logger.log_text(f"   ⚠️  Fields in instruction but NOT in form: {missing_fields}")
                run_logger.log_text(f"      These will be SKIPPED (not filled)")
        
        filled: Dict[str, Any] = {"filled": {}, "submitted": False}
        # Fill fields using robust filling
        if canonical.get("name") and selectors.get("name"):
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
                            screenshot_path = f"screenshots/debug_before_submit_{timestamp}.png"
                            await page.screenshot(path=screenshot_path)
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
                    ok = await page.evaluate(
                        """
                        () => {
                          const t = (document.body.innerText||'').toLowerCase();
                          if (/(dziękujemy|dziekujemy|wiadomość została|wiadomosc zostala|wiadomość wysłana|wiadomosc wyslana|message sent|thank you|success)/i.test(t)) return true;
                          if (document.querySelector('.wpcf7-mail-sent-ok, .wpcf7-response-output, .elementor-message-success, .elementor-alert.elementor-alert-success')) return true;
                          return false;
                        }
                        """
                    )
                    if bool(ok):
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
        return filled
    except Exception as e:
        if run_logger:
            run_logger.log_kv("deterministic_form_fill_error", str(e))
        return None
