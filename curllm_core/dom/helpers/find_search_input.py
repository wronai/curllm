import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .element_info import ElementInfo
from .find_inputs import find_inputs

logger = logging.getLogger(__name__)

async def find_search_input(page, llm=None) -> Optional[ElementInfo]:
    """
    Find the main search input on the page.
    
    Uses LLM-first approach if LLM is available.
    """
    # 1. Try LLM-based search input finding
    if llm:
        try:
            inputs_data = await page.evaluate("""() => {
                const inputs = [];
                document.querySelectorAll('input, [contenteditable="true"]').forEach(el => {
                    if (!el.offsetParent) return;  // Skip hidden
                    const type = el.getAttribute('type') || '';
                    const name = el.getAttribute('name') || '';
                    const placeholder = el.getAttribute('placeholder') || '';
                    const ariaLabel = el.getAttribute('aria-label') || '';
                    const id = el.id || '';
                    const className = el.className || '';
                    
                    // Generate a unique selector
                    let selector = el.tagName.toLowerCase();
                    if (id) selector = `#${id}`;
                    else if (name) selector = `[name="${name}"]`;
                    else if (type === 'search') selector = 'input[type="search"]';
                    
                    inputs.push({
                        selector: selector,
                        type: type,
                        name: name,
                        placeholder: placeholder,
                        ariaLabel: ariaLabel,
                        className: className
                    });
                });
                return inputs.slice(0, 20);
            }""")
            
            if inputs_data:
                inputs_text = "\n".join([
                    f"- selector: {i['selector']}, placeholder: {i['placeholder'][:30]}, name: {i['name']}, aria: {i['ariaLabel'][:20]}"
                    for i in inputs_data[:15]
                ])
                
                prompt = f"""Find the MAIN SEARCH input field on this e-commerce page.

Inputs found:
{inputs_text}

Return ONLY the selector of the search input, or "NONE" if not found.
No explanation, just the selector."""

                response = await llm.aquery(prompt)
                response = response.strip().strip('"').strip("'")
                
                if response and response != "NONE" and not response.startswith("NONE"):
                    # Verify selector works
                    el = await page.query_selector(response)
                    if el and await el.is_visible():
                        return ElementInfo(
                            selector=response,
                            tag='input',
                            text='',
                            attributes={},
                            visible=True,
                            location='header'
                        )
        except Exception as e:
            logger.debug(f"LLM search input finding failed: {e}")
    
    # 2. Try standard approach with semantic purpose
    inputs = await find_inputs(page, purpose='search')
    if inputs:
        return inputs[0]
    
    # 3. Statistical fallback: Score inputs by semantic indicators
    # No hardcoded selectors - dynamically analyze all visible inputs
    try:
        scored_inputs = await page.evaluate("""() => {
            const inputs = [];
            document.querySelectorAll('input, [contenteditable="true"]').forEach(el => {
                if (!el.offsetParent) return;  // Skip hidden
                
                const type = (el.getAttribute('type') || 'text').toLowerCase();
                const name = (el.getAttribute('name') || '').toLowerCase();
                const placeholder = (el.getAttribute('placeholder') || '').toLowerCase();
                const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
                const id = (el.id || '').toLowerCase();
                const role = (el.closest('[role="search"]') ? 'search' : '');
                
                // Skip password, email, hidden, submit inputs
                if (['password', 'email', 'hidden', 'submit', 'button', 'checkbox', 'radio'].includes(type)) {
                    return;
                }
                
                // Score based on semantic indicators
                let score = 0;
                const searchIndicators = ['search', 'szukaj', 'query', 'find', 'szuk', 'wyszuk'];
                
                // Type is search = high score
                if (type === 'search') score += 10;
                
                // Role search container
                if (role === 'search') score += 8;
                
                // Check name, placeholder, aria for search indicators
                const text = name + ' ' + placeholder + ' ' + ariaLabel + ' ' + id;
                for (const indicator of searchIndicators) {
                    if (text.includes(indicator)) score += 5;
                }
                
                // Location bonus: in header/nav
                const rect = el.getBoundingClientRect();
                if (rect.top < 200) score += 2;  // Near top of page
                
                if (score > 0) {
                    // Generate unique selector
                    let selector = el.tagName.toLowerCase();
                    if (el.id) selector = '#' + el.id;
                    else if (el.getAttribute('name')) selector = '[name="' + el.getAttribute('name') + '"]';
                    else if (type === 'search') selector = 'input[type="search"]';
                    
                    inputs.push({ selector, score, type, name, placeholder: placeholder.substring(0, 30) });
                }
            });
            
            // Sort by score descending
            inputs.sort((a, b) => b.score - a.score);
            return inputs.slice(0, 5);
        }""")
        
        if scored_inputs and len(scored_inputs) > 0:
            best = scored_inputs[0]
            if best['score'] >= 5:  # Minimum confidence threshold
                el = await page.query_selector(best['selector'])
                if el and await el.is_visible():
                    logger.debug(f"Found search input via scoring: {best['selector']} (score: {best['score']})")
                    return ElementInfo(
                        selector=best['selector'],
                        tag='input',
                        text='',
                        attributes={'placeholder': best.get('placeholder', '')},
                        visible=True,
                        location='header'
                    )
    except Exception as e:
        logger.debug(f"Statistical search input finding failed: {e}")
    
    return None
