"""
Dynamic Message Detection - Detect success/error messages without hardcoded selectors

Uses LLM + heuristics to detect page state messages.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DetectedMessage:
    """A detected message on the page"""
    type: str  # success, error, warning, info
    text: str
    selector: Optional[str]
    confidence: float


async def detect_success_message(page, llm=None) -> Optional[DetectedMessage]:
    """
    Detect success message on page without hardcoded selectors.
    
    Instead of looking for '.wpcf7-mail-sent-ok' or similar,
    uses semantic analysis to find success indicators.
    
    Args:
        page: Playwright page
        llm: Optional LLM for intelligent detection
        
    Returns:
        Detected success message or None
    """
    # Get page content for analysis
    content = await page.evaluate("""() => {
        // Look for elements that typically contain success messages
        const candidates = [];
        
        // Check all visible text elements
        const elements = document.querySelectorAll('*');
        for (const el of elements) {
            if (el.offsetParent === null) continue;
            
            const style = getComputedStyle(el);
            const bgColor = style.backgroundColor;
            const color = style.color;
            const text = el.textContent.trim();
            
            if (text.length < 5 || text.length > 500) continue;
            
            candidates.push({
                text: text.substring(0, 200),
                tagName: el.tagName.toLowerCase(),
                className: el.className,
                bgColor: bgColor,
                color: color,
            });
        }
        
        return candidates.slice(0, 50);
    }""")
    
    # Success indicators (semantic, not hardcoded)
    success_indicators = [
        'success', 'sukces', 'thank', 'dziękuj',
        'sent', 'wysłan', 'submitted', 'received',
        'completed', 'done', 'gotowe', 'confirm',
    ]
    
    green_colors = ['green', 'rgb(0, 128', 'rgb(34, 139', '#0f0', '#28a']
    
    for item in content:
        text_lower = item['text'].lower()
        
        # Check for success keywords
        has_keyword = any(ind in text_lower for ind in success_indicators)
        
        # Check for green color (common success indicator)
        has_green = any(
            g in (item.get('bgColor', '') + item.get('color', '')).lower()
            for g in green_colors
        )
        
        if has_keyword or has_green:
            confidence = 0.5
            if has_keyword:
                confidence += 0.3
            if has_green:
                confidence += 0.2
            
            return DetectedMessage(
                type='success',
                text=item['text'],
                selector=None,  # Dynamic detection doesn't need selector
                confidence=confidence,
            )
    
    # Try LLM if available
    if llm:
        try:
            page_text = await page.evaluate("() => document.body.innerText.substring(0, 2000)")
            prompt = f"Is there a success message on this page? Respond with YES or NO.\n\nPage text:\n{page_text}"
            response = await llm.agenerate([prompt])
            if 'yes' in response.generations[0][0].text.lower():
                return DetectedMessage(
                    type='success',
                    text='Success detected by LLM',
                    selector=None,
                    confidence=0.7,
                )
        except Exception as e:
            logger.debug(f"LLM success detection failed: {e}")
    
    return None


async def detect_error_message(page, llm=None) -> Optional[DetectedMessage]:
    """
    Detect error message on page without hardcoded selectors.
    
    Args:
        page: Playwright page
        llm: Optional LLM
        
    Returns:
        Detected error message or None
    """
    content = await page.evaluate("""() => {
        const candidates = [];
        const elements = document.querySelectorAll('*');
        
        for (const el of elements) {
            if (el.offsetParent === null) continue;
            
            const style = getComputedStyle(el);
            const text = el.textContent.trim();
            
            if (text.length < 3 || text.length > 500) continue;
            
            candidates.push({
                text: text.substring(0, 200),
                className: el.className,
                bgColor: style.backgroundColor,
                color: style.color,
            });
        }
        
        return candidates.slice(0, 50);
    }""")
    
    # Error indicators
    error_indicators = [
        'error', 'błąd', 'invalid', 'niepoprawn',
        'required', 'wymagan', 'failed', 'nie udało',
        'incorrect', 'wrong', 'nieprawidłow',
    ]
    
    red_colors = ['red', 'rgb(255, 0', 'rgb(220, 53', '#f00', '#dc3']
    
    for item in content:
        text_lower = item['text'].lower()
        
        has_keyword = any(ind in text_lower for ind in error_indicators)
        has_red = any(
            r in (item.get('bgColor', '') + item.get('color', '')).lower()
            for r in red_colors
        )
        
        if has_keyword or has_red:
            confidence = 0.5
            if has_keyword:
                confidence += 0.3
            if has_red:
                confidence += 0.2
            
            return DetectedMessage(
                type='error',
                text=item['text'],
                selector=None,
                confidence=confidence,
            )
    
    return None


async def detect_captcha(page, llm=None) -> Optional[DetectedMessage]:
    """
    Detect CAPTCHA on page without hardcoded selectors.
    
    Args:
        page: Playwright page
        llm: Optional LLM
        
    Returns:
        Detected CAPTCHA or None
    """
    # Look for CAPTCHA indicators
    has_captcha = await page.evaluate("""() => {
        const html = document.documentElement.innerHTML.toLowerCase();
        const indicators = [
            'captcha', 'recaptcha', 'hcaptcha',
            'challenge', 'robot', 'human verification',
            'weryfikacja', 'nie jestem robotem',
        ];
        
        for (const ind of indicators) {
            if (html.includes(ind)) {
                return ind;
            }
        }
        
        // Check for iframe from known CAPTCHA providers
        const iframes = document.querySelectorAll('iframe');
        for (const iframe of iframes) {
            const src = (iframe.src || '').toLowerCase();
            if (src.includes('captcha') || src.includes('challenge')) {
                return 'iframe-captcha';
            }
        }
        
        return null;
    }""")
    
    if has_captcha:
        return DetectedMessage(
            type='captcha',
            text=f'CAPTCHA detected: {has_captcha}',
            selector=None,
            confidence=0.9,
        )
    
    return None


async def detect_form_validation_error(page, llm=None) -> Optional[DetectedMessage]:
    """
    Detect form validation errors without hardcoded selectors.
    
    Args:
        page: Playwright page
        llm: Optional LLM
        
    Returns:
        Detected validation error or None
    """
    errors = await page.evaluate("""() => {
        const errors = [];
        
        // Check HTML5 validation
        const inputs = document.querySelectorAll('input, textarea, select');
        for (const inp of inputs) {
            if (!inp.validity.valid) {
                errors.push({
                    field: inp.name || inp.id || 'unknown',
                    message: inp.validationMessage,
                    type: 'html5',
                });
            }
        }
        
        // Check for visible error messages near inputs
        for (const inp of inputs) {
            const parent = inp.parentElement;
            if (!parent) continue;
            
            const errorEl = parent.querySelector('[class*="error"], [class*="invalid"]');
            if (errorEl && errorEl.offsetParent !== null) {
                errors.push({
                    field: inp.name || inp.id || 'unknown',
                    message: errorEl.textContent.trim().substring(0, 100),
                    type: 'visual',
                });
            }
        }
        
        return errors;
    }""")
    
    if errors:
        error_texts = [f"{e['field']}: {e['message']}" for e in errors[:3]]
        return DetectedMessage(
            type='validation_error',
            text='; '.join(error_texts),
            selector=None,
            confidence=0.85,
        )
    
    return None
