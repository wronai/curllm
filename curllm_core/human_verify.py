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
    # 1) Try in main document
    try:
        txt = await page.evaluate("() => (document.body && document.body.innerText) || ''")
    except Exception:
        txt = ""
    main_looks = looks_like_human_verify_text(txt)
    if run_logger:
        run_logger.log_kv("human_verify_main_text_match", str(bool(main_looks)))
    clicked = False
    if main_looks:
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
    # 2) Try inside iframes if not clicked yet
    if not clicked:
        try:
            for fr in page.frames:
                if fr == page.main_frame:
                    continue
                try:
                    ftxt = await fr.evaluate("() => (document.body && document.body.innerText) || ''")
                except Exception:
                    ftxt = ""
                if run_logger and ftxt:
                    run_logger.log_kv("human_verify_frame_text_present", "True")
                if not looks_like_human_verify_text(ftxt):
                    # Skip frames with no relevant text
                    continue
                # Try role-based first
                try:
                    fbtn = fr.get_by_role("button", name=re.compile("potwierdzam|potwierdź|confirm|kontynuuj|przej(d|dz)\\s+dalej|jestem", re.I))
                    if await fbtn.count() > 0:
                        await fbtn.first.click(timeout=1500)
                        clicked = True
                        break
                except Exception:
                    pass
                # Try CSS fallbacks
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
                        floc = fr.locator(sel)
                        if await floc.count() > 0:
                            await floc.first.click(timeout=1500)
                            clicked = True
                            break
                    except Exception:
                        continue
                if clicked:
                    break
                # Last resort: evaluate in frame
                try:
                    await fr.evaluate(
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
                    break
                except Exception:
                    continue
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
