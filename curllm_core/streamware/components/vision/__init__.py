"""
Vision Component - Visual analysis using CV and LLM.

Features:
- Image-based CAPTCHA detection
- Form field analysis
- Honeypot detection
- Visual element detection
"""

from .analyzer import VisionAnalyzer, analyze_image

# Re-export from main module to avoid duplication
from curllm_core.vision_form_analysis import (
    analyze_form_fields_vision,
)

__all__ = [
    'VisionAnalyzer',
    'analyze_image',
    'analyze_form_fields_vision',
]
