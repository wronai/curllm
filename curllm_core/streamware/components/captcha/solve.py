"""
Captcha Solver - Solve detected CAPTCHAs

Supports:
- Local OCR (tesseract) for image CAPTCHAs
- 2captcha API for widget CAPTCHAs
- Slider solving (external plugin)
"""

import asyncio
import os
from typing import Dict, Any, Optional

from .detect import CaptchaType, detect_captcha


class CaptchaSolver:
    """CAPTCHA solving integration"""
    
    def __init__(self):
        self.api_key = os.getenv("CAPTCHA_API_KEY", "")
        self.use_2captcha = bool(self.api_key)
    
    async def solve(
        self,
        page,
        captcha_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Solve CAPTCHA on page.
        
        Args:
            page: Playwright page
            captcha_info: Pre-detected captcha info (optional)
            
        Returns:
            {success: bool, solution: str|None, type: str, error: str|None}
        """
        result = {"success": False, "solution": None, "type": None, "error": None}
        
        # Detect if not provided
        if not captcha_info:
            captcha_info = await detect_captcha(page)
        
        if not captcha_info.get("found"):
            result["error"] = "No CAPTCHA detected"
            return result
        
        captcha_type = captcha_info.get("type", CaptchaType.UNKNOWN)
        result["type"] = captcha_type.value if isinstance(captcha_type, CaptchaType) else str(captcha_type)
        
        # Route to appropriate solver
        if captcha_type in [CaptchaType.RECAPTCHA, CaptchaType.HCAPTCHA, CaptchaType.TURNSTILE]:
            solution = await self._solve_widget(
                widget_type=captcha_type.value,
                sitekey=captcha_info.get("sitekey"),
                page_url=page.url
            )
            if solution:
                result["success"] = True
                result["solution"] = solution
                # Inject solution
                await self._inject_solution(page, captcha_type, solution)
            else:
                result["error"] = "Widget CAPTCHA solving failed"
                
        elif captcha_type == CaptchaType.IMAGE:
            # Would need screenshot of captcha image
            result["error"] = "Image CAPTCHA requires manual screenshot"
            
        elif captcha_type == CaptchaType.SLIDER:
            # Use external slider solver
            result["error"] = "Slider CAPTCHA requires external plugin"
            
        else:
            result["error"] = f"Unsupported CAPTCHA type: {captcha_type}"
        
        return result
    
    async def _solve_widget(
        self,
        widget_type: str,
        sitekey: str,
        page_url: str
    ) -> Optional[str]:
        """Solve widget CAPTCHA via 2captcha API."""
        if not self.use_2captcha or not self.api_key:
            return None
        
        if not sitekey:
            return None
        
        try:
            import aiohttp
            
            method_map = {
                'recaptcha': 'userrecaptcha',
                'hcaptcha': 'hcaptcha',
                'turnstile': 'turnstile',
            }
            method = method_map.get(widget_type)
            if not method:
                return None
            
            # Submit CAPTCHA
            data = {
                'key': self.api_key,
                'method': method,
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
                
                # Poll for result (max ~2 min)
                for _ in range(24):
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
                
                return None
                
        except Exception:
            return None
    
    async def _inject_solution(
        self,
        page,
        captcha_type: CaptchaType,
        solution: str
    ) -> bool:
        """Inject solved CAPTCHA token into page."""
        try:
            if captcha_type == CaptchaType.RECAPTCHA:
                await page.evaluate(f"""
                    const textarea = document.querySelector('#g-recaptcha-response');
                    if (textarea) {{
                        textarea.value = '{solution}';
                        textarea.style.display = 'block';
                    }}
                """)
                return True
            
            elif captcha_type == CaptchaType.HCAPTCHA:
                await page.evaluate(f"""
                    const input = document.querySelector('[name="h-captcha-response"]');
                    if (input) input.value = '{solution}';
                """)
                return True
            
            elif captcha_type == CaptchaType.TURNSTILE:
                await page.evaluate(f"""
                    const input = document.querySelector('[name="cf-turnstile-response"]');
                    if (input) input.value = '{solution}';
                """)
                return True
            
        except Exception:
            pass
        
        return False
    
    async def solve_image(self, image_path: str) -> Optional[str]:
        """Solve image-based CAPTCHA via OCR or 2captcha."""
        if self.use_2captcha:
            return await self._solve_image_2captcha(image_path)
        return await self._solve_image_local(image_path)
    
    async def _solve_image_local(self, image_path: str) -> Optional[str]:
        """Solve image CAPTCHA with local OCR (tesseract)."""
        try:
            from PIL import Image
            import pytesseract
            
            img = Image.open(image_path).convert('L')
            img = img.point(lambda p: p > 128 and 255)
            text = pytesseract.image_to_string(img, config='--psm 8')
            return text.strip()
        except Exception:
            return None
    
    async def _solve_image_2captcha(self, image_path: str) -> Optional[str]:
        """Solve image CAPTCHA via 2captcha API."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('key', self.api_key)
                    data.add_field('method', 'post')
                    data.add_field('file', f, filename='captcha.png')
                    
                    async with session.post('http://2captcha.com/in.php', data=data) as resp:
                        result = await resp.text()
                    
                    if 'OK' not in result:
                        return None
                    
                    captcha_id = result.split('|')[1]
                    await asyncio.sleep(20)
                    
                    async with session.get(
                        f'http://2captcha.com/res.php?key={self.api_key}&action=get&id={captcha_id}'
                    ) as resp2:
                        result2 = await resp2.text()
                    
                    if 'OK' in result2:
                        return result2.split('|')[1]
                    
        except Exception:
            pass
        
        return None


async def solve_captcha(page, captcha_info: Optional[Dict] = None) -> Dict[str, Any]:
    """Convenience function to solve CAPTCHA on page."""
    solver = CaptchaSolver()
    return await solver.solve(page, captcha_info)
