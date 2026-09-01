"""Main CAPTCHA orchestrator."""
from __future__ import annotations

import asyncio
from typing import Optional

from playwright.async_api import Page

try:
    from .audio_solver import AudioCaptchaSolver
    from .captcha_support import TWOCAPTCHA_SUPPORT, TwoCaptcha
    from .captcha_types import CaptchaConfig, CaptchaType, logger
    from .sliding_solver import SlidingPuzzleSolver
except ImportError:
    from audio_solver import AudioCaptchaSolver
    from captcha_support import TWOCAPTCHA_SUPPORT, TwoCaptcha
    from captcha_types import CaptchaConfig, CaptchaType, logger
    from sliding_solver import SlidingPuzzleSolver


class CaptchaSolver:
    """Main CAPTCHA solver that orchestrates different solving methods."""

    def __init__(self, config: Optional[CaptchaConfig] = None):
        self.config = config or CaptchaConfig()
        self.sliding_solver = SlidingPuzzleSolver(self.config)
        self.audio_solver = AudioCaptchaSolver(self.config)

    async def detect_captcha_type(self, page: Page) -> Optional[CaptchaType]:
        """Detect what type of CAPTCHA is present on the page."""
        if await self._has_selector(page, 'text="Przesuń w prawo"'):
            return CaptchaType.SLIDING_PUZZLE
        if await self._has_selector(page, '[class*="slide-puzzle"]'):
            return CaptchaType.SLIDING_PUZZLE
        if await self._has_selector(page, 'canvas[class*="captcha"]'):
            return CaptchaType.SLIDING_PUZZLE
        if await self._has_selector(page, 'iframe[src*="recaptcha"]'):
            return CaptchaType.RECAPTCHA_V2
        if await self._has_selector(page, 'iframe[src*="hcaptcha"]'):
            return CaptchaType.HCAPTCHA
        if await self._has_selector(page, 'audio[src*="captcha"]'):
            return CaptchaType.AUDIO
        return None

    async def _has_selector(self, page: Page, selector: str) -> bool:
        try:
            element = await page.wait_for_selector(selector, timeout=1000)
            return element is not None
        except Exception:
            return False

    async def solve(self, page: Page, captcha_type: Optional[CaptchaType] = None) -> bool:
        """Solve CAPTCHA, auto-detecting type when omitted."""
        captcha_type = captcha_type or await self.detect_captcha_type(page)
        if not captcha_type:
            logger.warning("Could not detect CAPTCHA type")
            return False

        logger.info("Detected CAPTCHA type: %s", captcha_type.value)
        for attempt in range(self.config.max_retries):
            logger.info("Attempt %s/%s", attempt + 1, self.config.max_retries)
            success = await self._solve_once(page, captcha_type)
            if success:
                logger.info("CAPTCHA solved successfully!")
                return True
            await asyncio.sleep(2)

        logger.error("Failed to solve CAPTCHA after %s attempts", self.config.max_retries)
        return False

    async def _solve_once(self, page: Page, captcha_type: CaptchaType) -> bool:
        if captcha_type == CaptchaType.SLIDING_PUZZLE:
            captcha_frame = next(
                (frame for frame in page.frames if "captcha" in frame.url.lower()),
                None,
            )
            return await self.sliding_solver.solve(page, frame=captcha_frame)

        if captcha_type == CaptchaType.AUDIO:
            return await self._solve_audio(page)

        if captcha_type in {CaptchaType.RECAPTCHA_V2, CaptchaType.HCAPTCHA}:
            if self.config.use_2captcha:
                return await self.solve_with_service(page, captcha_type)
            logger.warning("%s requires 2captcha service", captcha_type.value)
        return False

    async def _solve_audio(self, page: Page) -> bool:
        solution = await self.audio_solver.solve(page)
        if not solution:
            return False
        input_field = await page.wait_for_selector('input[type="text"]', timeout=5000)
        if not input_field:
            return False
        await input_field.fill(solution)
        submit = await page.wait_for_selector('button[type="submit"]', timeout=2000)
        if not submit:
            return False
        await submit.click()
        return True

    async def solve_with_service(self, page: Page, captcha_type: CaptchaType) -> bool:
        """Use 2captcha or similar service for complex CAPTCHAs."""
        if not TWOCAPTCHA_SUPPORT or not self.config.api_key_2captcha:
            return False

        try:
            solver = TwoCaptcha(self.config.api_key_2captcha)
            if captcha_type != CaptchaType.RECAPTCHA_V2:
                return False

            site_key = await page.evaluate(
                """
                () => {
                    const element = document.querySelector('[data-sitekey]');
                    return element ? element.getAttribute('data-sitekey') : null;
                }
                """
            )
            if not site_key:
                return False

            result = solver.recaptcha(sitekey=site_key, url=page.url)
            if result and "code" in result:
                await page.evaluate(
                    """
                    (token) => {
                        document.querySelector('#g-recaptcha-response').innerHTML = token;
                        if (typeof ___grecaptcha_cfg !== 'undefined') {
                            Object.entries(___grecaptcha_cfg.clients).forEach(([key, client]) => {
                                if (client.callback) {
                                    client.callback(token);
                                }
                            });
                        }
                    }
                    """,
                    result["code"],
                )
                return True
        except Exception as exc:
            logger.error("Service solving failed: %s", exc)
        return False
