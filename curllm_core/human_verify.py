#!/usr/bin/env python3
import re
from typing import Optional

from .logger import RunLogger

PATTERNS = [
    "potwierdź, że jesteś człowiekiem",
    "potwierdz, że jesteś człowiekiem",
    "potwierdzam",
    "jestem człowiekiem",
    "jestem czlowiekiem",
    "przejdź dalej",
    "przejdz dalej",
    "kontynuuj",
    "confirm you are human",
    "verify you are human",
]


def looks_like_human_verify_text(txt: str) -> bool:
    t = (txt or "").lower()
    return any(p in t for p in PATTERNS)


async def handle_human_verification(page, run_logger: Optional[RunLogger] = None) -> bool:
    try:
        txt = await page.evaluate("() => (document.body && document.body.innerText) || ''")
    except Exception:
        txt = ""
    if not looks_like_human_verify_text(txt):
        try:
            has_btn = await page.evaluate(
                "() => !!Array.from(document.querySelectorAll('button, a, [role=button]')).find(el => (el.innerText||'').toLowerCase().includes('potwierdzam'))"
            )
        except Exception:
            has_btn = False
        if not has_btn:
            return False
    clicked = False
    try:
        btn = page.get_by_role(
            "button",
            name=re.compile("potwierdzam|potwierdź|confirm|kontynuuj|przej(d|dz)\\s+dalej|jestem", re.I),
        )
        if await btn.count() > 0:
            await btn.first.click(timeout=1500)
            clicked = True
    except Exception:
        pass
    if not clicked:
        for sel in [
            'button:has-text("Potwierdzam")',
            'button:has-text("Potwierdź")',
            'button:has-text("Kontynuuj")',
            'button:has-text("Jestem człowiekiem")',
            'button:has-text("Jestem czlowiekiem")',
            'button:has-text("Przejdź dalej")',
            'button:has-text("Przejdz dalej")',
            'button[aria-label*="potwierd" i]',
            '[role="button"]:has-text("Potwierdzam")',
            '[role="button"]:has-text("Kontynuuj")',
            '[role="button"]:has-text("Jestem człowiekiem")',
        ]:
            try:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    await loc.first.click(timeout=1500)
                    clicked = True
                    break
            except Exception:
                continue
    if not clicked:
        try:
            await page.evaluate(
                """
                () => {
                  const el = Array.from(document.querySelectorAll('button, a, [role=button]'))
                    .find(e => {
                      const t=(e.innerText||'').toLowerCase();
                      return t.includes('potwierdzam') || t.includes('potwierdź') || t.includes('kontynuuj') || t.includes('jestem cz') || t.includes('przejdź dalej') || t.includes('przejdz dalej');
                    });
                  if (el) el.click();
                }
                """
            )
            clicked = True
        except Exception:
            pass
    if clicked:
        if run_logger:
            run_logger.log_text("Clicked human verification button (Potwierdzam)")
        try:
            await page.wait_for_load_state("networkidle")
        except Exception:
            try:
                await page.wait_for_timeout(800)
            except Exception:
                pass
    return clicked
