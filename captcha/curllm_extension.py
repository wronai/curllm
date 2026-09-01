"""curllm integration extension for automatic CAPTCHA handling."""
from __future__ import annotations

from typing import Optional

from playwright.async_api import Page

try:
    from .captcha_orchestrator import CaptchaSolver
    from .captcha_types import CaptchaConfig, logger
except ImportError:
    from captcha_orchestrator import CaptchaSolver
    from captcha_types import CaptchaConfig, logger


class CurllmCaptchaExtension:
    """Extension for curllm to handle CAPTCHAs automatically."""

    def __init__(self, api_key_2captcha: Optional[str] = None):
        config = CaptchaConfig(
            use_2captcha=bool(api_key_2captcha),
            api_key_2captcha=api_key_2captcha or "",
            debug_mode=True,
        )
        self.solver = CaptchaSolver(config)

    async def handle_page(self, page: Page) -> bool:
        """Check page for CAPTCHA and solve if found."""
        captcha_indicators = [
            'text="Potwierdź, że jesteś człowiekiem"',
            'text="I\'m not a robot"',
            '[class*="captcha"]',
            'iframe[src*="captcha"]',
            'text="Verify you are human"',
        ]
        for indicator in captcha_indicators:
            try:
                element = await page.wait_for_selector(indicator, timeout=2000)
                if element:
                    logger.info("CAPTCHA detected, attempting to solve...")
                    return await self.solver.solve(page)
            except Exception:
                continue

        logger.info("No CAPTCHA detected on page")
        return True
