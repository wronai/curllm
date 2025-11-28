"""
Captcha Component - Detection and solving of CAPTCHAs

Supports:
- Checkbox CAPTCHAs (hCaptcha, reCAPTCHA v2)
- Image selection CAPTCHAs
- Slider CAPTCHAs
- Text/image CAPTCHAs

Solving methods:
- vision_solve: Local visual LLM (llava, minicpm-v) - no API key needed
- solve: External API (2captcha) - requires CAPTCHA_API_KEY
"""

from .detect import detect_captcha, CaptchaType
from .solve import solve_captcha, CaptchaSolver
from .vision_solve import solve_captcha_visual

__all__ = [
    'detect_captcha',
    'solve_captcha',
    'solve_captcha_visual',
    'CaptchaType',
    'CaptchaSolver'
]
