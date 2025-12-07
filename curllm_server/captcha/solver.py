"""CAPTCHA Solver - Integration for solving CAPTCHAs"""

import asyncio
import os
from typing import Optional

import aiohttp
from PIL import Image


class CaptchaSolver:
    """CAPTCHA solving integration"""
    
    def __init__(self):
        self.use_2captcha = os.getenv("CAPTCHA_API_KEY") is not None
        self.api_key = os.getenv("CAPTCHA_API_KEY", "")
    
    async def solve(self, image_path: str) -> Optional[str]:
        """Solve CAPTCHA from image"""
        if not self.use_2captcha:
            # Try local OCR first
            return await self._solve_local(image_path)
        
        # Use 2captcha service
        return await self._solve_2captcha(image_path)
    
    async def _solve_local(self, image_path: str) -> Optional[str]:
        """Local CAPTCHA solving using OCR"""
        try:
            import pytesseract
            
            # Preprocess image
            img = Image.open(image_path)
            img = img.convert('L')  # Grayscale
            
            # Apply filters to improve OCR
            img = img.point(lambda p: p > 128 and 255)
            
            # OCR
            text = pytesseract.image_to_string(img, config='--psm 8')
            return text.strip()
        except Exception:
            return None
    
    async def _solve_2captcha(self, image_path: str) -> Optional[str]:
        """Solve using 2captcha API"""
        async with aiohttp.ClientSession() as session:
            # Upload image
            with open(image_path, 'rb') as f:
                data = {
                    'key': self.api_key,
                    'method': 'post'
                }
                files = {'file': f}
                
                async with session.post(
                    'http://2captcha.com/in.php',
                    data=data,
                    files=files
                ) as resp:
                    result = await resp.text()
                    if 'OK' in result:
                        captcha_id = result.split('|')[1]
                        
                        # Poll for result
                        await asyncio.sleep(20)
                        
                        async with session.get(
                            f'http://2captcha.com/res.php?key={self.api_key}&action=get&id={captcha_id}'
                        ) as resp2:
                            result = await resp2.text()
                            if 'OK' in result:
                                return result.split('|')[1]
        return None
