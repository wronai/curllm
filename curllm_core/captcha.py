#!/usr/bin/env python3
"""
DEPRECATED: Use curllm_core.streamware.components.captcha instead.

This file is kept for backward compatibility.
"""
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

    async def solve_sitekey(self, widget_type: str, sitekey: str, page_url: str) -> Optional[str]:
        """Solve widget-based CAPTCHA via 2captcha using sitekey and pageurl.
        widget_type: 'recaptcha' | 'hcaptcha' | 'turnstile'
        Returns solution token or None.
        """
        if not self.use_2captcha or not self.api_key:
            return None
        import aiohttp  # lazy import
        method_map = {
            'recaptcha': 'userrecaptcha',
            'hcaptcha': 'hcaptcha',
            'turnstile': 'turnstile',
        }
        method = method_map.get(widget_type)
        if not method:
            return None
        data = {
            'key': self.api_key,
            'method': method,
            # 2captcha expects 'googlekey' for recaptcha and sitekey for others
            'googlekey' if widget_type == 'recaptcha' else 'sitekey': sitekey,
            'pageurl': page_url,
            'json': 1,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post('http://2captcha.com/in.php', data=data) as resp:
                up = await resp.json(content_type=None)
            if not isinstance(up, dict) or up.get('status') != 1:
                return None
            captcha_id = up.get('request')
            # Poll for result
            for _ in range(24):  # ~ 2 min max
                await asyncio.sleep(5)
                async with session.get('http://2captcha.com/res.php', params={
                    'key': self.api_key,
                    'action': 'get',
                    'id': captcha_id,
                    'json': 1,
                }) as r2:
                    rs = await r2.json(content_type=None)
                if isinstance(rs, dict) and rs.get('status') == 1:
                    return rs.get('request')
                # continue polling if 'CAPCHA_NOT_READY'
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
