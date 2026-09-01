"""Advanced CAPTCHA Solver for curllm — compatibility facade.

Handles sliding puzzles, image recognition, and audio CAPTCHAs.
Implementation is split across captcha_*.py modules (STARTER-004).
"""
from __future__ import annotations

import asyncio

try:
    from .audio_solver import AudioCaptchaSolver
    from .captcha_orchestrator import CaptchaSolver
    from .captcha_types import CaptchaConfig, CaptchaType, logger
    from .captcha_support import AUDIO_SUPPORT, OCR_SUPPORT, TWOCAPTCHA_SUPPORT
    from .curllm_extension import CurllmCaptchaExtension
    from .sliding_solver import SlidingPuzzleSolver
except ImportError:  # flat import when captcha/ is on sys.path
    from audio_solver import AudioCaptchaSolver
    from captcha_orchestrator import CaptchaSolver
    from captcha_types import CaptchaConfig, CaptchaType, logger
    from captcha_support import AUDIO_SUPPORT, OCR_SUPPORT, TWOCAPTCHA_SUPPORT
    from curllm_extension import CurllmCaptchaExtension
    from sliding_solver import SlidingPuzzleSolver

__all__ = [
    "AUDIO_SUPPORT",
    "OCR_SUPPORT",
    "TWOCAPTCHA_SUPPORT",
    "AudioCaptchaSolver",
    "CaptchaConfig",
    "CaptchaSolver",
    "CaptchaType",
    "CurllmCaptchaExtension",
    "SlidingPuzzleSolver",
    "logger",
    "main",
]


async def main() -> None:
    """Example of using the CAPTCHA solver with Playwright."""
    from playwright.async_api import async_playwright

    config = CaptchaConfig(
        use_2captcha=False,
        api_key_2captcha="YOUR_2CAPTCHA_API_KEY",
        debug_mode=True,
    )
    solver = CaptchaSolver(config)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=site-per-process",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """
        )
        page = await context.new_page()
        await page.goto("https://allegro.pl")
        await asyncio.sleep(2)

        if await solver.solve(page):
            logger.info("Successfully passed CAPTCHA!")
            await asyncio.sleep(5)
        else:
            logger.error("Failed to solve CAPTCHA")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
