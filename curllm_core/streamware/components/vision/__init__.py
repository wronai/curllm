"""
Vision Component - Visual analysis using CV and LLM.

Features:
- Image-based CAPTCHA detection
- Form field analysis
- Honeypot detection
- Visual element detection
"""

from .analyzer import VisionAnalyzer, analyze_image
from .form_analysis import analyze_form_fields_vision, VisionFormAnalyzer

__all__ = [
    'VisionAnalyzer',
    'analyze_image',
    'analyze_form_fields_vision',
    'VisionFormAnalyzer'
]
