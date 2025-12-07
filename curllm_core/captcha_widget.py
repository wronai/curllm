#!/usr/bin/env python3
import asyncio
from typing import Optional

from .logger import RunLogger

async def handle_captcha_image(page, screenshot_path: str, solver, run_logger: Optional[RunLogger] = None) -> bool:
    """Solve simple image captcha via provided solver and fill common input.
    Returns True if something was filled.
    """
    if not solver:
        return False
    try:
        solution = await solver.solve(screenshot_path)
    except Exception:
        solution = None
    if not solution:
        return False
    try:
        await page.fill('input[name*="captcha"]', solution)
        if run_logger:
            run_logger.log_text("Filled CAPTCHA input with solved text")
        return True
    except Exception:
        return False

async def handle_widget_captcha(page, current_url: Optional[str], solver, run_logger: Optional[RunLogger] = None) -> bool:
    """Detect widget CAPTCHA (reCAPTCHA/hCaptcha/Turnstile) and solve via 2captcha using solver.solve_sitekey.
    Returns True if token injected.
    """
    # If no sitekey solver is available, skip
    if not solver or not getattr(solver, 'solve_sitekey', None):
        return False
    try:
        info = await page.evaluate(
            r"""
            () => {
              const q = (sel) => document.querySelector(sel);
              const byAttr = document.querySelector('[data-sitekey]');
              const recaptchaEl = q('.g-recaptcha[data-sitekey], [class*="recaptcha"][data-sitekey]') || (byAttr && /recaptcha/i.test(byAttr.className) ? byAttr : null);
              const hcaptchaEl = q('.h-captcha[data-sitekey]') || (byAttr && /hcaptcha/i.test(byAttr.className) ? byAttr : null);
              const turnstileEl = q('.cf-turnstile[data-sitekey]') || (byAttr && /turnstile/i.test(byAttr.className) ? byAttr : null);
              const getKey = (el) => el && (el.getAttribute('data-sitekey') || el.dataset.sitekey);
              if (recaptchaEl) return {type: 'recaptcha', sitekey: getKey(recaptchaEl)};
              if (hcaptchaEl) return {type: 'hcaptcha', sitekey: getKey(hcaptchaEl)};
              if (turnstileEl) return {type: 'turnstile', sitekey: getKey(turnstileEl)};
              // script-based guess
              const scripts = Array.from(document.scripts).map(s => s.src||'');
              if (scripts.some(s => /recaptcha\.google\.com|google\.com\/recaptcha/i.test(s))) return {type: 'recaptcha', sitekey: (q('[data-sitekey]')||{}).dataset?.sitekey || null};
              if (scripts.some(s => /hcaptcha\.com/i.test(s))) return {type: 'hcaptcha', sitekey: (q('[data-sitekey]')||{}).dataset?.sitekey || null};
              if (scripts.some(s => /challenges\.cloudflare\.com|turnstile/i.test(s))) return {type: 'turnstile', sitekey: (q('[data-sitekey]')||{}).dataset?.sitekey || null};
              return null;
            }
            """
        )
    except Exception:
        info = None
    if not info or not isinstance(info, dict) or not info.get('sitekey') or not info.get('type'):
        return False
    wtype = str(info.get('type'))
    sitekey = str(info.get('sitekey'))
    token = await solver.solve_sitekey(wtype, sitekey, current_url or '')
    if not token:
        return False
    # Inject token
    try:
        await page.evaluate(
            """
            (token) => {
              const ensure = (name) => {
                let el = document.querySelector('input[name="'+name+'"]');
                if (!el) { el = document.createElement('input'); el.type='hidden'; el.name=name; document.body.appendChild(el); }
                el.value = token;
              };
              ['g-recaptcha-response','h-recaptcha-response','hcaptcha-response','cf-turnstile-response'].forEach(ensure);
              ['g-recaptcha-response','h-recaptcha-response','hcaptcha-response','cf-turnstile-response'].forEach(n => {
                const el = document.querySelector('input[name="'+n+'"]');
                if (el) {
                  el.dispatchEvent(new Event('change', {bubbles: true}));
                  el.dispatchEvent(new Event('input', {bubbles: true}));
                }
              });
            }
            """,
            token,
        )
        if run_logger:
            run_logger.log_text(f"Widget CAPTCHA solved and token injected ({wtype})")
        try:
            await page.wait_for_timeout(1000)
        except Exception:
            pass
        return True
    except Exception:
        return False
