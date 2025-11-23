#!/usr/bin/env python3
import asyncio
from typing import Optional

class CaptchaSolver:
    """CAPTCHA solving integration"""
    def __init__(self):
        import os
        self.use_2captcha = os.getenv("CAPTCHA_API_KEY") is not None
        self.api_key = os.getenv("CAPTCHA_API_KEY", "")

    async def solve(self, image_path: str) -> Optional[str]:
        if not self.use_2captcha:
            return await self._solve_local(image_path)
        return await self._solve_2captcha(image_path)

    async def _solve_local(self, image_path: str) -> Optional[str]:
        try:
            from PIL import Image  # lazy import
            import pytesseract  # lazy import
            img = Image.open(image_path).convert('L')
            img = img.point(lambda p: p > 128 and 255)
            text = pytesseract.image_to_string(img, config='--psm 8')
            return text.strip()
        except Exception:
            return None

    async def _solve_2captcha(self, image_path: str) -> Optional[str]:
        import aiohttp  # lazy import
        async with aiohttp.ClientSession() as session:
            with open(image_path, 'rb') as f:
                data = {'key': self.api_key, 'method': 'post'}
                files = {'file': f}
                async with session.post('http://2captcha.com/in.php', data=data, files=files) as resp:
                    result = await resp.text()
                    if 'OK' in result:
                        captcha_id = result.split('|')[1]
                        await asyncio.sleep(20)
                        async with session.get(f'http://2captcha.com/res.php?key={self.api_key}&action=get&id={captcha_id}') as resp2:
                            result2 = await resp2.text()
                            if 'OK' in result2:
                                return result2.split('|')[1]
        return None
