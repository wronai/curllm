"""
Captcha Detection - Detect CAPTCHA presence and type on page

No hardcoded selectors for specific sites - uses dynamic pattern detection.
"""

from enum import Enum
from typing import Dict, Any, Optional


class CaptchaType(Enum):
    """Supported CAPTCHA types"""
    NONE = "none"
    RECAPTCHA = "recaptcha"
    HCAPTCHA = "hcaptcha"
    TURNSTILE = "turnstile"
    IMAGE = "image"
    SLIDER = "slider"
    UNKNOWN = "unknown"


async def detect_captcha(page) -> Dict[str, Any]:
    """
    Detect CAPTCHA presence and type on page.
    
    Uses dynamic pattern detection - no hardcoded selectors.
    
    Args:
        page: Playwright page
        
    Returns:
        {
            found: bool,
            type: CaptchaType,
            sitekey: str|None,
            selector: str|None,
            details: {...}
        }
    """
    result = {
        "found": False,
        "type": CaptchaType.NONE,
        "sitekey": None,
        "selector": None,
        "details": {}
    }
    
    try:
        # Dynamic detection via JavaScript
        detection = await page.evaluate("""
        () => {
            const result = {
                found: false,
                type: 'none',
                sitekey: null,
                selector: null,
                details: {}
            };
            
            // Check for sitekey attribute (common for widget CAPTCHAs)
            const sitekeyEl = document.querySelector('[data-sitekey]');
            if (sitekeyEl) {
                result.found = true;
                result.sitekey = sitekeyEl.getAttribute('data-sitekey');
                
                // Determine type by class/attributes
                const classes = (sitekeyEl.className || '').toLowerCase();
                const id = (sitekeyEl.id || '').toLowerCase();
                
                if (classes.includes('g-recaptcha') || classes.includes('recaptcha')) {
                    result.type = 'recaptcha';
                } else if (classes.includes('h-captcha') || classes.includes('hcaptcha')) {
                    result.type = 'hcaptcha';
                } else if (classes.includes('cf-turnstile') || classes.includes('turnstile')) {
                    result.type = 'turnstile';
                } else {
                    result.type = 'unknown';
                }
                
                result.selector = sitekeyEl.id ? '#' + sitekeyEl.id : null;
            }
            
            // Check for iframe-based CAPTCHAs
            if (!result.found) {
                const iframes = document.querySelectorAll('iframe');
                for (const iframe of iframes) {
                    const src = (iframe.src || '').toLowerCase();
                    const title = (iframe.title || '').toLowerCase();
                    const name = (iframe.name || '').toLowerCase();
                    
                    if (src.includes('recaptcha') || src.includes('google.com/recaptcha')) {
                        result.found = true;
                        result.type = 'recaptcha';
                        break;
                    } else if (src.includes('hcaptcha') || src.includes('newassets.hcaptcha.com') || 
                               title.includes('hcaptcha') || name.includes('hcaptcha')) {
                        result.found = true;
                        result.type = 'hcaptcha';
                        break;
                    } else if (src.includes('turnstile') || src.includes('cloudflare')) {
                        result.found = true;
                        result.type = 'turnstile';
                        break;
                    }
                }
            }
            
            // Check for hCaptcha widget containers (often have h-captcha class)
            if (!result.found) {
                const hcaptchaWidget = document.querySelector('.h-captcha, [data-hcaptcha-widget-id], div[data-hcaptcha]');
                if (hcaptchaWidget) {
                    result.found = true;
                    result.type = 'hcaptcha';
                    result.sitekey = hcaptchaWidget.getAttribute('data-sitekey');
                }
            }
            
            // Check for hidden captcha response fields (indicates captcha is present)
            if (!result.found) {
                const responseFields = document.querySelectorAll(
                    '[name="h-captcha-response"], [name="g-recaptcha-response"], ' +
                    'textarea[name*="captcha-response"]'
                );
                for (const field of responseFields) {
                    const name = (field.name || '').toLowerCase();
                    if (name.includes('h-captcha')) {
                        result.found = true;
                        result.type = 'hcaptcha';
                        break;
                    } else if (name.includes('g-recaptcha') || name.includes('recaptcha')) {
                        result.found = true;
                        result.type = 'recaptcha';
                        break;
                    }
                }
            }
            
            // Check for slider CAPTCHAs
            if (!result.found) {
                const sliders = document.querySelectorAll(
                    '[class*="slider"], [class*="captcha"], [class*="verify"]'
                );
                for (const el of sliders) {
                    const hasTrack = el.querySelector('[class*="track"], [class*="bg"]');
                    const hasHandle = el.querySelector('[class*="btn"], [class*="handle"], [class*="drag"]');
                    if (hasTrack && hasHandle) {
                        result.found = true;
                        result.type = 'slider';
                        result.details = {
                            track: hasTrack ? true : false,
                            handle: hasHandle ? true : false
                        };
                        break;
                    }
                }
            }
            
            // Check for image-based CAPTCHAs
            if (!result.found) {
                const captchaImages = document.querySelectorAll(
                    'img[src*="captcha"], img[alt*="captcha"], [class*="captcha"] img'
                );
                if (captchaImages.length > 0) {
                    result.found = true;
                    result.type = 'image';
                    result.details = {
                        image_count: captchaImages.length
                    };
                }
            }
            
            return result;
        }
        """)
        
        result["found"] = detection.get("found", False)
        result["type"] = CaptchaType(detection.get("type", "none"))
        result["sitekey"] = detection.get("sitekey")
        result["selector"] = detection.get("selector")
        result["details"] = detection.get("details", {})
        
    except Exception as e:
        result["details"]["error"] = str(e)
    
    return result
