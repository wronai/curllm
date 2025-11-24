#!/usr/bin/env python3
import random
from typing import Any, Dict

async def execute_action(page, action: Dict, runtime: Dict[str, Any]):
    action_type = action.get("type")
    if action_type == "click":
        sel = action.get("selector")
        if not sel:
            return
        timeout = int(action.get("timeoutMs") or runtime.get("action_timeout_ms") or 8000)
        # Optional pre-scroll to reveal element
        if runtime.get("smart_click"):
            try:
                await _auto_scroll(page, steps=2, delay_ms=300)
            except Exception:
                pass
        loc = page.locator(str(sel))
        try:
            if await loc.count() == 0 and runtime.get("smart_click"):
                # Try a deeper scroll to lazy-load
                await _auto_scroll(page, steps=4, delay_ms=500)
            await loc.first.wait_for(state="visible", timeout=timeout)
            await loc.first.click(timeout=timeout)
        except Exception:
            # Fallback: try evaluate click
            try:
                await page.evaluate(
                    "(s) => { const el=document.querySelector(s); if(el) el.click(); }",
                    sel,
                )
            except Exception:
                pass
        # Post-click wait
        try:
            await page.wait_for_timeout(int(runtime.get("wait_after_click_ms") or 800))
        except Exception:
            pass
    elif action_type == "fill":
        timeout = int(action.get("timeoutMs") or runtime.get("action_timeout_ms") or 8000)
        sel = action.get("selector")
        val = action.get("value", "")
        if not sel:
            return
        try:
            await page.locator(str(sel)).first.wait_for(state="visible", timeout=timeout)
        except Exception:
            pass
        # If this looks like an email field, avoid filling invalid values like "Test"
        try:
            is_email = await page.evaluate(
                "(s) => { const el=document.querySelector(s); if(!el) return false; if (el.matches('[data-curllm-target=\\"email\\"]')) return true; const t=(el.getAttribute('type')||'').toLowerCase(); const name=(el.getAttribute('name')||'').toLowerCase(); const pid=(el.id||'').toLowerCase(); const ph=(el.getAttribute('placeholder')||'').toLowerCase(); const aria=(el.getAttribute('aria-label')||'').toLowerCase(); return t==='email' || [name,pid,ph,aria].some(x=>x.includes('email')||x.includes('e-mail')||x.includes('mail')); }",
                sel,
            )
        except Exception:
            is_email = False
        if is_email:
            try:
                canon = await page.evaluate("() => window.__curllm_canonical || null")
            except Exception:
                canon = None
            try:
                sval = str(val)
                if (not isinstance(val, str)) or ("@" not in sval):
                    if isinstance(canon, dict) and isinstance(canon.get("email"), str) and "@" in canon.get("email", ""):
                        val = canon["email"]
            except Exception:
                pass
        await page.fill(str(sel), str(val))
        # Fire input/blur to trigger client-side validation when present
        try:
            await page.evaluate(
                "(s) => { const el=document.querySelector(s); if(!el) return; try{ el.dispatchEvent(new Event('input', {bubbles:true})); }catch(e){} try{ el.blur(); }catch(e){} }",
                sel,
            )
        except Exception:
            pass
        await page.wait_for_timeout(150 + int(random.random()*350))
    elif action_type == "scroll":
        dy = 300 + int(random.random()*700)
        try:
            await page.mouse.wheel(0, dy)
        except Exception:
            await page.evaluate(f"window.scrollBy(0, {dy})")
        await page.wait_for_timeout(500 + int(random.random()*800))
    elif action_type == "wait":
        await page.wait_for_timeout(800 + int(random.random()*1200))

async def _auto_scroll(page, steps: int = 3, delay_ms: int = 500):
    for _ in range(steps):
        try:
            await page.evaluate("window.scrollBy(0, window.innerHeight);")
            await page.wait_for_timeout(delay_ms)
        except Exception:
            break
