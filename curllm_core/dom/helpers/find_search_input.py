import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .element_info import ElementInfo
from .find_inputs import find_inputs

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
    
    # 2. Try standard approach
    inputs = await find_inputs(page, purpose='search')
    if inputs:
        return inputs[0]
    
    # 3. Fallback: look for common search selectors
    fallback_selectors = [
        'input[type="search"]',
        'input[name="q"]',
        'input[name="query"]',
        'input[name="search"]',
        'input[placeholder*="szukaj" i]',
        'input[placeholder*="search" i]',
        'input[placeholder*="Czego szukasz" i]',
        'input[placeholder*="Wpisz" i]',
        '#search',
        '.search-input',
        '[role="search"] input',
        'header input[type="text"]',
        'nav input[type="text"]',
    ]
    
    for selector in fallback_selectors:
        try:
            el = await page.query_selector(selector)
            if el and await el.is_visible():
                return ElementInfo(
                    selector=selector,
                    tag='input',
                    text='',
                    attributes={},
                    visible=True,
                    location='header'
                )
        except Exception:
            continue
    
    return None
