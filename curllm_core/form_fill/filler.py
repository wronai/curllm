"""Main form filling logic - deterministic_form_fill function"""

from typing import Any, Dict, Optional

from curllm_core.form_fill.parser import parse_form_pairs
from curllm_core.form_fill.field_filler import robust_fill_field, check_checkbox
from curllm_core.form_fill.js_scripts import (
    FIND_FORM_FIELDS_JS,
    VALIDATE_FIELDS_JS,
    POST_SUBMIT_CHECK_JS,
    TRIGGER_EVENTS_JS,
    AUTO_FIX_JS,
)


async def deterministic_form_fill(
    instruction: str, 
    page, 
    run_logger=None, 
    domain_dir: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Fill a form deterministically based on instruction and DOM analysis.
    
    Args:
        instruction: Form fill instruction with field values (e.g., "email=test@example.com")
        page: Playwright page object
        run_logger: Optional logger for debugging
        domain_dir: Optional directory for screenshots
        
    Returns:
        Dict with filled fields, submitted status, and errors
    """
    try:
        # Get canonical values from window and instruction
        canonical = await _get_canonical_values(page, instruction)
        
        # Find and mark form fields in DOM
        selectors = await page.evaluate(FIND_FORM_FIELDS_JS)
        if not isinstance(selectors, dict):
            selectors = {}
        
        # Log debug info
        if run_logger:
            _log_form_debug(run_logger, selectors, canonical)
        
        filled: Dict[str, Any] = {"filled": {}, "submitted": False}
        
        # Fill all fields
        await _fill_all_fields(page, selectors, canonical, filled, run_logger)
        
        # Check consent checkbox
        if selectors.get("consent"):
            if await check_checkbox(page, str(selectors["consent"])):
                filled["filled"]["consent"] = True
        
        # Auto-validation
        if run_logger:
            await _log_validation(page, run_logger)
        
        # Pre-submission diagnosis
        pre_submit_diagnosis = await _pre_submit_diagnosis(page, run_logger)
        
        # Auto-fix blocking issues
        if isinstance(pre_submit_diagnosis, dict) and pre_submit_diagnosis.get("hasBlockingIssues"):
            await _auto_fix_issues(page, run_logger)
        
        # Submit form
        if selectors.get("submit"):
            await _submit_form(page, selectors, canonical, filled, run_logger, domain_dir)
        
        filled["selectors"] = selectors
        filled["values"] = canonical
        
        # Log final summary
        if run_logger:
            _log_final_summary(run_logger, selectors, canonical, filled)
        
        return filled
    except Exception as e:
        if run_logger:
            run_logger.log_kv("deterministic_form_fill_error", str(e))
        return None


async def _get_canonical_values(page, instruction: str) -> Dict[str, str]:
    """Get canonical field values from window.__curllm_canonical and instruction."""
    canonical: Dict[str, str] = {}
    
    # First, get values from window.__curllm_canonical (from tool args)
    try:
        cc = await page.evaluate("() => (window.__curllm_canonical||null)")
        if isinstance(cc, dict):
            for k in ["name", "email", "subject", "phone", "message"]:
                v = cc.get(k)
                if isinstance(v, str) and v.strip():
                    canonical[k] = v.strip()
    except Exception:
        pass
    
    # Semantic concept groups (language-agnostic)
    # LLM would determine these dynamically in production
    field_concepts = {
        "email": {"email", "e-mail", "mail", "correo", "poczta"},
        "name": {"name", "imi", "nazw", "full name", "fullname", "nombre"},
        "message": {"message", "wiadomo", "treść", "tresc", "content", "komentarz"},
        "subject": {"subject", "temat", "asunto", "topic"},
        "phone": {"phone", "telefon", "tel", "mobile", "komórka"},
    }
    
    # Then parse instruction and OVERWRITE canonical (instruction has priority)
    raw_pairs = parse_form_pairs(instruction)
    for k, v in raw_pairs.items():
        lk = k.lower()
        # Match using semantic concept groups
        matched = False
        for field_type, concepts in field_concepts.items():
            if any(x in lk for x in concepts):
                canonical[field_type] = v
                matched = True
                break
    
    return canonical


async def _fill_all_fields(
    page, 
    selectors: Dict, 
    canonical: Dict, 
    filled: Dict, 
    run_logger
) -> None:
    """Fill all detected form fields."""
    # Handle SPLIT NAME FIELDS (First + Last)
    if selectors.get("_split_name") and canonical.get("name"):
        full_name = canonical["name"].strip()
        parts = full_name.split(None, 1)
        first_name = parts[0] if len(parts) > 0 else ""
        last_name = parts[1] if len(parts) > 1 else ""
        
        if run_logger:
            run_logger.log_text(f"   🔀 Split name: '{full_name}' → First: '{first_name}', Last: '{last_name}'")
        
        if selectors.get("name_first") and first_name:
            if await robust_fill_field(page, str(selectors["name_first"]), first_name):
                filled["filled"]["name_first"] = True
        
        if selectors.get("name_last") and last_name:
            if await robust_fill_field(page, str(selectors["name_last"]), last_name):
                filled["filled"]["name_last"] = True
    
    # Standard single name field
    elif canonical.get("name") and selectors.get("name"):
        if run_logger:
            run_logger.log_text(f"   ▶️  Filling name: '{canonical['name']}'")
        if await robust_fill_field(page, str(selectors["name"]), canonical["name"]):
            filled["filled"]["name"] = True
    
    # Email
    if canonical.get("email") and selectors.get("email"):
        if run_logger:
            run_logger.log_text(f"   ▶️  Filling email: '{canonical['email']}'")
        if await robust_fill_field(page, str(selectors["email"]), canonical["email"]):
            filled["filled"]["email"] = True
    
    # Subject
    if canonical.get("subject") and selectors.get("subject"):
        if run_logger:
            run_logger.log_text(f"   ▶️  Filling subject: '{canonical['subject']}'")
        if await robust_fill_field(page, str(selectors["subject"]), canonical["subject"]):
            filled["filled"]["subject"] = True
    
    # Phone
    if canonical.get("phone") and selectors.get("phone"):
        if run_logger:
            run_logger.log_text(f"   ▶️  Filling phone: '{canonical['phone']}'")
        if await robust_fill_field(page, str(selectors["phone"]), canonical["phone"]):
            filled["filled"]["phone"] = True
    
    # Message
    if canonical.get("message") and selectors.get("message"):
        msg_preview = canonical["message"][:50] + "..." if len(canonical["message"]) > 50 else canonical["message"]
        if run_logger:
            run_logger.log_text(f"   ▶️  Filling message: '{msg_preview}'")
        if await robust_fill_field(page, str(selectors["message"]), canonical["message"]):
            filled["filled"]["message"] = True


async def _log_validation(page, run_logger) -> None:
    """Log auto-validation results."""
    run_logger.log_text("🔍 Auto-validation: Checking field values in DOM...")
    
    validation_results = await page.evaluate(VALIDATE_FIELDS_JS)
    
    if isinstance(validation_results, dict):
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


async def _pre_submit_diagnosis(page, run_logger) -> Dict:
    """Check for potential blocking issues before submission."""
    if run_logger:
        run_logger.log_text("🔬 Pre-submission diagnosis:")
    
    diagnosis = await page.evaluate("""
        () => {
          const issues = [];
          const warnings = [];
          const targetForm = document.querySelector('[data-curllm-target="submit"]')?.closest('form');
          if (targetForm) {
            const requiredCheckboxes = targetForm.querySelectorAll('input[type="checkbox"][required]:not(:checked)');
            requiredCheckboxes.forEach(cb => {
              const label = cb.labels?.[0]?.innerText || cb.id || 'checkbox';
              issues.push({ type: 'required_checkbox_unchecked', field: label.substring(0, 100) });
            });
            
            const requiredInputs = targetForm.querySelectorAll('input[required]:not([type="checkbox"]), textarea[required]');
            requiredInputs.forEach(inp => {
              if (!inp.value?.trim()) {
                const label = inp.labels?.[0]?.innerText || inp.placeholder || inp.id || 'field';
                issues.push({ type: 'required_field_empty', field: label.substring(0, 100) });
              }
            });
          }
          return { issues, warnings, hasBlockingIssues: issues.length > 0 };
        }
    """)
    
    if run_logger and isinstance(diagnosis, dict):
        issues = diagnosis.get("issues", [])
        if issues:
            run_logger.log_text(f"   ⚠️  Found {len(issues)} blocking issue(s)")
            for issue in issues[:5]:
                run_logger.log_text(f"      - {issue.get('type')}: {issue.get('field')}")
        else:
            run_logger.log_text("   ✅ No blocking issues detected")
    
    return diagnosis


async def _auto_fix_issues(page, run_logger) -> None:
    """Try to fix blocking issues automatically."""
    if run_logger:
        run_logger.log_text("🔧 Auto-fix: Attempting to resolve blocking issues...")
    
    fix_results = await page.evaluate(AUTO_FIX_JS)
    
    if run_logger and isinstance(fix_results, dict):
        fixed = fix_results.get("fixed", [])
        if fixed:
            run_logger.log_text(f"   ✅ Fixed {len(fixed)} issue(s)")
        else:
            run_logger.log_text("   ⚠️  Could not auto-fix any issues")


async def _submit_form(
    page, 
    selectors: Dict, 
    canonical: Dict, 
    filled: Dict, 
    run_logger, 
    domain_dir: Optional[str]
) -> None:
    """Submit the form and handle validation errors."""
    try:
        # Trigger events on all fields first
        try:
            await page.evaluate(TRIGGER_EVENTS_JS)
        except Exception:
            pass
        
        attempts = 0
        while attempts < 2:
            attempts += 1
            
            # Take screenshot before submit
            if run_logger and attempts == 1:
                await _take_debug_screenshot(page, run_logger, domain_dir, "before_submit")
            
            # Click submit
            try:
                await page.click(str(selectors["submit"]))
            except Exception:
                pass
            
            # Wait for response
            try:
                await page.wait_for_selector('.wpcf7-response-output, .elementor-message-success', timeout=5000)
            except Exception:
                pass
            try:
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
            
            # Check submission result
            post_result = await page.evaluate(POST_SUBMIT_CHECK_JS)
            
            if run_logger and isinstance(post_result, dict) and attempts == 1:
                _log_post_submit(run_logger, post_result)
            
            ok = bool(post_result.get("success")) if isinstance(post_result, dict) else False
            if ok:
                filled["submitted"] = True
                break
            
            # Try email fallback if validation failed
            diag = await _get_validation_diagnosis(page)
            if isinstance(diag, dict) and diag.get("invalid_email") and selectors.get("email"):
                await _try_email_fallbacks(page, selectors, canonical, filled, run_logger)
            
            if isinstance(diag, dict) and diag.get("consent_required") and selectors.get("consent"):
                await check_checkbox(page, str(selectors["consent"]))
            
            try:
                await page.wait_for_timeout(500)
            except Exception:
                pass
        
        if not filled.get("submitted"):
            diag = await _get_validation_diagnosis(page)
            if diag is not None:
                filled["errors"] = diag
    except Exception:
        pass


async def _take_debug_screenshot(page, run_logger, domain_dir: Optional[str], name: str) -> None:
    """Take a debug screenshot."""
    try:
        import time
        timestamp = str(time.time()).replace('.', '')
        if domain_dir:
            screenshot_path = f"{domain_dir}/debug_{name}_{timestamp}.png"
        else:
            screenshot_path = f"screenshots/debug_{name}_{timestamp}.png"
        await page.screenshot(path=screenshot_path)
        try:
            run_logger.log_image(screenshot_path, alt=f"Screenshot: {name}")
        except Exception:
            run_logger.log_text(f"📸 Screenshot: {screenshot_path}")
    except Exception as e:
        run_logger.log_text(f"   ⚠️  Could not take screenshot: {e}")


async def _get_validation_diagnosis(page) -> Optional[Dict]:
    """Get validation diagnosis after submission attempt."""
    try:
        return await page.evaluate("""
            () => {
              const txt = (document.body.innerText||'').toLowerCase();
              const emailField = document.querySelector('[data-curllm-target="email"]');
              let invalidEmail = false;
              if (emailField) {
                invalidEmail = emailField.getAttribute('aria-invalid') === 'true'
                  || emailField.classList.contains('wpcf7-not-valid')
                  || emailField.classList.contains('forminator-error');
              }
              if (!invalidEmail) {
                invalidEmail = /(nie jest prawidłowy adres e-mail|nieprawidłowy email|invalid email)/i.test(txt);
              }
              const consentRequired = (!!document.querySelector('input[type="checkbox"][required]'))
                && /(zgod|akcept|privacy|regulamin)/i.test(txt);
              const requiredMissing = /(wymagane|required|to pole jest wymagane)/i.test(txt);
              return {invalid_email: !!invalidEmail, consent_required: !!consentRequired, required_missing: !!requiredMissing};
            }
        """)
    except Exception:
        return None


async def _try_email_fallbacks(
    page, 
    selectors: Dict, 
    canonical: Dict, 
    filled: Dict, 
    run_logger
) -> None:
    """Try fallback email addresses if validation fails."""
    try:
        host = await page.evaluate("() => (location.hostname||'')")
    except Exception:
        host = ""
    
    dom = host.lstrip('www.') if isinstance(host, str) else ""
    
    fallback_emails = []
    if dom:
        fallback_emails.append(f"kontakt@{dom}")
        fallback_emails.append(f"info@{dom}")
        fallback_emails.append(f"test@{dom}")
    
    for fallback_email in fallback_emails:
        if run_logger:
            run_logger.log_text(f"⚠️  Attempting email fallback: {fallback_email}")
        
        if await robust_fill_field(page, str(selectors["email"]), fallback_email):
            canonical["email"] = fallback_email
            filled["filled"]["email"] = True
            
            try:
                await page.wait_for_timeout(500)
            except Exception:
                pass
            
            # Check if still invalid
            try:
                still_invalid = await page.evaluate("""
                    () => {
                      const emailField = document.querySelector('[data-curllm-target="email"]');
                      if (!emailField) return false;
                      return emailField.getAttribute('aria-invalid') === 'true'
                        || emailField.classList.contains('wpcf7-not-valid');
                    }
                """)
                if not still_invalid:
                    if run_logger:
                        run_logger.log_text(f"   ✅ Email fallback accepted: {fallback_email}")
                    break
            except Exception:
                break


def _log_form_debug(run_logger, selectors: Dict, canonical: Dict) -> None:
    """Log form detection debug info."""
    run_logger.log_text("🔍 Form fill debug:")
    
    if selectors.get("_formId"):
        run_logger.log_text(f"   🎯 Selected form: {selectors['_formId']}")
    
    if selectors.get("_debug_consent"):
        debug_consent = selectors["_debug_consent"]
        run_logger.log_text(f"   📋 Checkbox detection:")
        run_logger.log_text(f"      - Visible checkboxes: {debug_consent.get('visibleCheckboxes', 0)}")
        run_logger.log_text(f"      - Consent found: {debug_consent.get('consentFound', False)}")
    
    run_logger.log_text(f"   Canonical values: {canonical}")
    
    display_selectors = {k: v for k, v in selectors.items() if not k.startswith('_')}
    run_logger.log_text(f"   Found selectors: {list(display_selectors.keys())}")


def _log_post_submit(run_logger, post_result: Dict) -> None:
    """Log post-submission diagnosis."""
    run_logger.log_text("🔬 Post-submission diagnosis:")
    if post_result.get("success"):
        run_logger.log_text(f"   ✅ SUCCESS - Found {len(post_result.get('successIndicators', []))} success indicator(s)")
    else:
        errors = post_result.get("errors", [])
        if errors:
            run_logger.log_text(f"   ❌ Found {len(errors)} error(s) blocking submission:")
            for error in errors[:5]:
                run_logger.log_text(f"      - {error.get('type')}: {error.get('field', error.get('message', 'unknown'))}")
        else:
            run_logger.log_text("   ⚠️  Submission status unclear")


def _log_final_summary(run_logger, selectors: Dict, canonical: Dict, filled: Dict) -> None:
    """Log final form fill summary."""
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
    
    submitted = filled.get("submitted", False)
    result_emoji = "✅" if submitted else "❌"
    run_logger.log_text(f"**Form Result:** {result_emoji} {'SUBMITTED' if submitted else 'NOT SUBMITTED'}")
    if filled.get("errors"):
        run_logger.log_text(f"**Errors:** {filled['errors']}")
