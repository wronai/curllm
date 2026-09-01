"""Audio CAPTCHA solver."""
from __future__ import annotations

import asyncio
import base64
import time
from typing import Optional

import requests
from playwright.async_api import Page

try:
    from .captcha_support import AUDIO_SUPPORT, AudioSegment, sr
    from .captcha_types import CaptchaConfig, logger
except ImportError:
    from captcha_support import AUDIO_SUPPORT, AudioSegment, sr
    from captcha_types import CaptchaConfig, logger


class AudioCaptchaSolver:
    """Solver for audio CAPTCHAs."""

    def __init__(self, config: CaptchaConfig):
        self.config = config
        self.recognizer = sr.Recognizer() if AUDIO_SUPPORT else None

    async def solve(self, page: Page) -> Optional[str]:
        """Solve audio CAPTCHA. Returns transcribed text or None."""
        if not AUDIO_SUPPORT:
            logger.error("Audio support not available (install speech_recognition and pydub)")
            return None

        try:
            await self._click_audio_button(page)
            audio_element = await page.wait_for_selector("audio", timeout=5000)
            if not audio_element:
                logger.error("No audio element found")
                return None

            audio_src = await audio_element.get_attribute("src")
            if not audio_src:
                logger.error("No audio source found")
                return None

            audio_data = self._load_audio_bytes(audio_src)
            audio_path = self.config.screenshot_dir / f"captcha_audio_{int(time.time())}.mp3"
            with open(audio_path, "wb") as handle:
                handle.write(audio_data)

            wav_path = audio_path.with_suffix(".wav")
            AudioSegment.from_file(audio_path).export(wav_path, format="wav")
            return self._transcribe_wav(wav_path)
        except Exception as exc:
            logger.error("Error solving audio CAPTCHA: %s", exc)
            return None

    async def _click_audio_button(self, page: Page) -> None:
        audio_button_selectors = [
            '[title*="audio"]',
            '[aria-label*="audio"]',
            'button:has-text("Audio")',
            '[class*="audio-button"]',
        ]
        for selector in audio_button_selectors:
            try:
                button = await page.wait_for_selector(selector, timeout=2000)
                if button:
                    await button.click()
                    await asyncio.sleep(2)
                    return
            except Exception:
                continue

    def _load_audio_bytes(self, audio_src: str) -> bytes:
        if audio_src.startswith("data:"):
            return base64.b64decode(audio_src.split(",", 1)[1])
        return requests.get(audio_src, timeout=30).content

    def _transcribe_wav(self, wav_path) -> Optional[str]:
        with sr.AudioFile(str(wav_path)) as source:
            audio_data = self.recognizer.record(source)
            try:
                text = self.recognizer.recognize_google(audio_data, language="pl-PL")
                logger.info("Google recognized: %s", text)
                return text
            except Exception:
                pass
            try:
                text = self.recognizer.recognize_sphinx(audio_data)
                logger.info("Sphinx recognized: %s", text)
                return text
            except Exception:
                return None
