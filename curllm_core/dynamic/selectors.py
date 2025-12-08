"""
Dynamic Selector Detection - Find elements without hardcoded selectors

Uses LLM + heuristics + statistics to find elements dynamically.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FoundElement:
    """Result of dynamic element detection"""
    selector: str
    element_type: str
    confidence: float
    method: str  # llm, heuristic, statistical
    attributes: Dict[str, Any] = None


async def find_form_fields(page, form_purpose: str = None, llm=None) -> List[FoundElement]:
    """
    Dynamically find form fields on page.
    
    Instead of hardcoded selectors like 'input[name="email"]',
    uses LLM + heuristics to detect fields.
    
    Args:
        page: Playwright page
        form_purpose: Optional hint like "contact", "login", "signup"
        llm: Optional LLM for intelligent detection
        
    Returns:
        List of found form fields with their selectors
    """
    from curllm_core.element_finder import LLMElementFinder
    
    fields = []
    
    # Use LLM for intelligent detection if available
    if llm:
        finder = LLMElementFinder(llm=llm, page=page)
        
        # Ask LLM to find form fields
        field_types = ['email', 'name', 'phone', 'message', 'password']
        for field_type in field_types:
            try:
                match = await finder.find_element(
                    f"find {field_type} input field",
                    element_type="input"
                )
                if match and match.confidence > 0.5:
                    fields.append(FoundElement(
                        selector=match.selector,
                        element_type=field_type,
                        confidence=match.confidence,
                        method='llm',
                    ))
            except Exception as e:
                logger.debug(f"LLM field detection failed for {field_type}: {e}")
    
    # Fallback: heuristic detection
    if not fields:
        fields = await _heuristic_find_fields(page)
    
    return fields


async def _heuristic_find_fields(page) -> List[FoundElement]:
    """Heuristic fallback for field detection"""
    fields = []
    
    # Get all visible inputs
    inputs = await page.evaluate("""() => {
        const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
        return Array.from(inputs).map(el => ({
            tagName: el.tagName.toLowerCase(),
            type: el.type || 'text',
            name: el.name,
            id: el.id,
            placeholder: el.placeholder,
            ariaLabel: el.getAttribute('aria-label'),
            labels: Array.from(el.labels || []).map(l => l.textContent.trim()),
            visible: el.offsetParent !== null,
        })).filter(i => i.visible);
    }""")
    
    # Score each input based on attributes
    for inp in inputs:
        field_type = _detect_field_type(inp)
        selector = _build_selector(inp)
        
        if field_type and selector:
            fields.append(FoundElement(
                selector=selector,
                element_type=field_type,
                confidence=0.7,
                method='heuristic',
                attributes=inp,
            ))
    
    return fields


def _detect_field_type(inp: Dict) -> Optional[str]:
    """Detect field type from attributes using heuristics"""
    # Combine all text attributes
    text = ' '.join([
        inp.get('name', ''),
        inp.get('id', ''),
        inp.get('placeholder', ''),
        inp.get('ariaLabel', ''),
        ' '.join(inp.get('labels', [])),
    ]).lower()
    
    # Common patterns (not hardcoded selectors, just semantic hints)
    patterns = {
        'email': ['email', 'e-mail', 'mail', 'correo'],
        'name': ['name', 'imię', 'nazwisko', 'nombre', 'first', 'last'],
        'phone': ['phone', 'telefon', 'tel', 'mobile', 'komórka'],
        'message': ['message', 'wiadomość', 'comment', 'komentarz', 'treść'],
        'password': ['password', 'hasło', 'pass', 'pwd'],
        'address': ['address', 'adres', 'street', 'ulica'],
        'city': ['city', 'miasto', 'town'],
        'zip': ['zip', 'postal', 'kod', 'pocztowy'],
    }
    
    for field_type, keywords in patterns.items():
        if any(kw in text for kw in keywords):
            return field_type
    
    # Fallback to input type
    if inp.get('type') == 'email':
        return 'email'
    if inp.get('type') == 'tel':
        return 'phone'
    if inp.get('type') == 'password':
        return 'password'
    if inp.get('tagName') == 'textarea':
        return 'message'
    
    return None


def _build_selector(inp: Dict) -> Optional[str]:
    """Build a selector for the input dynamically"""
    # Prefer ID
    if inp.get('id'):
        return f"#{inp['id']}"
    
    # Then name
    if inp.get('name'):
        tag = inp.get('tagName', 'input')
        return f"{tag}[name=\"{inp['name']}\"]"
    
    # Then aria-label
    if inp.get('ariaLabel'):
        tag = inp.get('tagName', 'input')
        return f"{tag}[aria-label=\"{inp['ariaLabel']}\"]"
    
    return None


async def find_submit_button(page, form_context: str = None, llm=None) -> Optional[FoundElement]:
    """
    Find submit button dynamically without hardcoded selectors.
    
    Args:
        page: Playwright page
        form_context: Context hint like "contact form", "login"
        llm: Optional LLM
        
    Returns:
        Found submit button or None
    """
    from curllm_core.element_finder import LLMElementFinder
    
    # Try LLM first
    if llm:
        finder = LLMElementFinder(llm=llm, page=page)
        try:
            match = await finder.find_element(
                f"find submit button for {form_context or 'form'}",
                element_type="button"
            )
            if match and match.confidence > 0.6:
                return FoundElement(
                    selector=match.selector,
                    element_type='submit',
                    confidence=match.confidence,
                    method='llm',
                )
        except Exception as e:
            logger.debug(f"LLM submit detection failed: {e}")
    
    # Heuristic fallback
    buttons = await page.evaluate("""() => {
        const btns = document.querySelectorAll('button, input[type="submit"], [role="button"]');
        return Array.from(btns).map(el => ({
            tagName: el.tagName.toLowerCase(),
            type: el.type,
            text: el.textContent.trim().toLowerCase(),
            value: el.value,
            visible: el.offsetParent !== null,
            selector: el.id ? '#' + el.id : null,
        })).filter(b => b.visible);
    }""")
    
    # Score buttons
    submit_keywords = ['submit', 'send', 'wyślij', 'zapisz', 'ok', 'confirm', 'register', 'login']
    
    best = None
    best_score = 0
    
    for btn in buttons:
        score = 0
        text = btn.get('text', '') + ' ' + (btn.get('value') or '')
        
        if btn.get('type') == 'submit':
            score += 3
        
        for kw in submit_keywords:
            if kw in text.lower():
                score += 2
                break
        
        if score > best_score:
            best_score = score
            best = btn
    
    if best:
        selector = best.get('selector')
        if not selector:
            # Build selector from context
            selector = f"button:has-text('{best['text'][:30]}')"
        
        return FoundElement(
            selector=selector,
            element_type='submit',
            confidence=min(best_score / 5, 1.0),
            method='heuristic',
        )
    
    return None


async def find_input_by_purpose(page, purpose: str, llm=None) -> Optional[FoundElement]:
    """
    Find input field by its semantic purpose.
    
    Args:
        page: Playwright page
        purpose: What the field is for (e.g., "email address", "user name")
        llm: Optional LLM
        
    Returns:
        Found input element
    """
    from curllm_core.element_finder import LLMElementFinder
    
    if llm:
        finder = LLMElementFinder(llm=llm, page=page)
        match = await finder.find_element(
            f"find input for {purpose}",
            element_type="input"
        )
        if match:
            return FoundElement(
                selector=match.selector,
                element_type=purpose,
                confidence=match.confidence,
                method='llm',
            )
    
    # Fallback to heuristic search
    fields = await find_form_fields(page)
    for field in fields:
        if purpose.lower() in field.element_type.lower():
            return field
    
    return None


async def find_clickable_by_intent(page, intent: str, llm=None) -> Optional[FoundElement]:
    """
    Find clickable element (button, link) by user intent.
    
    Args:
        page: Playwright page
        intent: What user wants to do (e.g., "close modal", "accept cookies")
        llm: Optional LLM
        
    Returns:
        Found clickable element
    """
    from curllm_core.element_finder import LLMElementFinder
    
    if llm:
        finder = LLMElementFinder(llm=llm, page=page)
        match = await finder.find_element(intent, element_type="button")
        if match and match.confidence > 0.5:
            return FoundElement(
                selector=match.selector,
                element_type='clickable',
                confidence=match.confidence,
                method='llm',
            )
    
    # Heuristic: search by text content
    intent_keywords = intent.lower().split()
    
    element = await page.evaluate("""(keywords) => {
        const elements = document.querySelectorAll('button, a, [role="button"], [onclick]');
        for (const el of elements) {
            const text = el.textContent.toLowerCase();
            if (keywords.some(kw => text.includes(kw))) {
                return {
                    id: el.id,
                    text: el.textContent.trim().substring(0, 50),
                };
            }
        }
        return null;
    }""", intent_keywords)
    
    if element:
        selector = f"#{element['id']}" if element.get('id') else f":has-text('{element['text']}')"
        return FoundElement(
            selector=selector,
            element_type='clickable',
            confidence=0.6,
            method='heuristic',
        )
    
    return None


async def find_container_by_content(
    page, 
    content_description: str, 
    llm=None
) -> Optional[FoundElement]:
    """
    Find container element based on its content description.
    
    Args:
        page: Playwright page
        content_description: What the container holds (e.g., "product list", "search results")
        llm: Optional LLM
        
    Returns:
        Found container element
    """
    from curllm_core.detection import DynamicPatternDetector
    
    # Use dynamic pattern detection
    detector = DynamicPatternDetector()
    
    # Get page DOM
    html = await page.content()
    
    # Detect patterns
    result = await detector.detect_patterns(html, content_description)
    
    if result and result.get('container_selector'):
        return FoundElement(
            selector=result['container_selector'],
            element_type='container',
            confidence=result.get('confidence', 0.7),
            method='statistical',
            attributes=result,
        )
    
    return None
