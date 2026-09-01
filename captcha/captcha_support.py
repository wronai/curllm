"""Optional dependency probes for captcha solvers."""
from __future__ import annotations

try:
    import speech_recognition as sr
    from pydub import AudioSegment

    AUDIO_SUPPORT = True
except ImportError:
    sr = None  # type: ignore[assignment]
    AudioSegment = None  # type: ignore[assignment,misc]
    AUDIO_SUPPORT = False

try:
    import pytesseract
    import easyocr

    OCR_SUPPORT = True
except ImportError:
    pytesseract = None  # type: ignore[assignment]
    easyocr = None  # type: ignore[assignment]
    OCR_SUPPORT = False

try:
    from twocaptcha import TwoCaptcha

    TWOCAPTCHA_SUPPORT = True
except ImportError:
    TwoCaptcha = None  # type: ignore[assignment,misc]
    TWOCAPTCHA_SUPPORT = False
