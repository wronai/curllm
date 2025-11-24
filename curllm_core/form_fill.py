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


async def deterministic_form_fill(instruction: str, page, run_logger=None) -> Optional[Dict[str, Any]]:
    try:
        raw_pairs = parse_form_pairs(instruction)
        # Normalize keys to canonical fields
        canonical: Dict[str, str] = {}
        for k, v in raw_pairs.items():
            lk = k.lower()
            if any(x in lk for x in ["email", "e-mail", "mail"]):
                canonical["email"] = v
            elif any(x in lk for x in ["name", "imi", "nazw", "full name", "fullname", "first name", "last name"]):
                if "name" not in canonical:
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
                C.sort((a,b)=>b.score-a.score);
                return C.length ? C[0].el : null;
              };
              const res = {};
              const mark = (el, key) => { if (!el) return null; el.setAttribute('data-curllm-target', key); return `[data-curllm-target="${key}"]`; };
              const nameEl = findField(['name','fullname','full name','imi','imię','nazw'], 'input');
              if (nameEl) res.name = mark(nameEl, 'name');
              const emailEl = findField(['email','e-mail','mail'], 'input');
              if (emailEl) res.email = mark(emailEl, 'email');
              const msgEl = findField(['message','wiadomo','treść','tresc','content','komentarz'], 'textarea');
              if (msgEl) res.message = mark(msgEl, 'message');
              // subject optional
              const subjEl = findField(['subject','temat'], 'input');
              if (subjEl) res.subject = mark(subjEl, 'subject');
              // phone optional
              const phoneEl = findField(['phone','telefon','tel'], 'input');
              if (phoneEl) res.phone = mark(phoneEl, 'phone');
              // consent checkbox (GDPR/RODO)
              const consentKeywords = ['zgod', 'akcept', 'regulamin', 'polityk', 'rodo', 'privacy', 'consent', 'agree'];
              let consent = null;
              // label-associated checkboxes
              Array.from(document.querySelectorAll('label')).forEach(lb => {
                const t = (lb.innerText||'').toLowerCase();
                consentKeywords.forEach(k => {
                  if (!consent && t.includes(k)) {
                    const forId = lb.getAttribute('for');
                    if (forId) {
                      const cb = document.getElementById(forId);
                      if (cb && cb.type === 'checkbox') consent = cb;
                    } else {
                      const cb2 = lb.querySelector('input[type="checkbox"]');
                      if (cb2) consent = cb2;
                    }
                  }
                });
              });
              if (!consent) {
                consent = document.querySelector('input[type="checkbox"][required]') || document.querySelector('input[type="checkbox"]');
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
        filled: Dict[str, Any] = {"filled": {}, "submitted": False}
        # Fill fields
        if canonical.get("name") and selectors.get("name"):
            try:
                await page.fill(str(selectors["name"]), canonical["name"])
                filled["filled"]["name"] = True
            except Exception:
                pass
        if canonical.get("email") and selectors.get("email"):
            try:
                await page.fill(str(selectors["email"]), canonical["email"])
                filled["filled"]["email"] = True
            except Exception:
                pass
        if canonical.get("subject") and selectors.get("subject"):
            try:
                await page.fill(str(selectors["subject"]), canonical["subject"])
                filled["filled"]["subject"] = True
            except Exception:
                pass
        if canonical.get("phone") and selectors.get("phone"):
            try:
                await page.fill(str(selectors["phone"]), canonical["phone"])
                filled["filled"]["phone"] = True
            except Exception:
                pass
        if canonical.get("message") and selectors.get("message"):
            try:
                await page.fill(str(selectors["message"]), canonical["message"])
                filled["filled"]["message"] = True
            except Exception:
                pass
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
        # Attempt submit
        if selectors.get("submit"):
            try:
                await page.click(str(selectors["submit"]))
                # Wait briefly for AJAX-based responses (CF7/Elementor)
                try:
                    await page.wait_for_selector('.wpcf7-response-output, .elementor-message-success, .elementor-alert.elementor-alert-success', timeout=5000)
                except Exception:
                    pass
                try:
                    await page.wait_for_load_state("networkidle")
                except Exception:
                    pass
                # Detect success message heuristically
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
                filled["submitted"] = bool(ok)
            except Exception:
                pass
        filled["selectors"] = selectors
        filled["values"] = canonical
        return filled
    except Exception as e:
        if run_logger:
            run_logger.log_kv("deterministic_form_fill_error", str(e))
        return None
