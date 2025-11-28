"""
Captcha Component - CAPTCHA detection and solving

Atomic operations:
- detect: Detect CAPTCHA type on page
- solve: Solve CAPTCHA (local OCR or 2captcha)
- inject_solution: Inject solution token into page
"""

from .detect import detect_captcha, CaptchaType
from .solve import CaptchaSolver, solve_captcha

__all__ = [
    'detect_captcha',
    'CaptchaType',
    'CaptchaSolver',
    'solve_captcha'
]
