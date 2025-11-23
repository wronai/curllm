#!/usr/bin/env python3
from typing import List

async def auto_scroll(page, steps: int = 3, delay_ms: int = 500):
    for _ in range(steps):
        try:
            await page.evaluate("window.scrollBy(0, window.innerHeight);")
            await page.wait_for_timeout(delay_ms)
        except Exception:
            break

async def accept_cookies(page):
    try:
        # Try by accessible name
        names: List[str] = [
            "Akceptuj", "Zgadzam się", "Accept", "I agree"
        ]
        for name in names:
            try:
                btn = page.get_by_role("button", name=name)
                if await btn.count() > 0:
                    await btn.first.click(timeout=1000)
                    return
            except Exception:
                pass
        # Try common CSS selectors
        selectors: List[str] = [
            'button:has-text("Akceptuj")',
            'button:has-text("Zgadzam się")',
            'button:has-text("Accept")',
            'button:has-text("I agree")',
            'button[aria-label*="accept" i]',
            '#onetrust-accept-btn-handler',
            '.cookie-accept', '.cookie-approve', '.cookies-accept',
            'button[mode="primary"]',
        ]
        for sel in selectors:
            try:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    await loc.first.click(timeout=1000)
                    return
            except Exception:
                pass
    except Exception:
        pass

async def is_block_page(page) -> bool:
    try:
        txt = await page.evaluate("() => (document.body && document.body.innerText || '').slice(0, 4000).toLowerCase()")
        markers = [
            "you have been blocked",
            "access denied",
            "robot",
            "are you human",
            "verify you are human",
            "potwierdź, że jesteś człowiekiem",
            "potwierdz, że jesteś człowiekiem",
            "potwierdzam",
        ]
        return any(m in txt for m in markers)
    except Exception:
        return False
