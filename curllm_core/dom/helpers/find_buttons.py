import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .element_info import ElementInfo

async def find_buttons(
    page,
    text_contains: Optional[str] = None
) -> List[ElementInfo]:
    """
    Find all button elements.
    """
    elements = await page.evaluate("""
        () => {
            const buttons = document.querySelectorAll(
                'button, input[type="submit"], input[type="button"], [role="button"]'
            );
            return Array.from(buttons)
                .filter(el => el.offsetParent !== null)
                .map(el => ({
                    selector: el.id ? '#' + el.id : 
                              el.className ? '.' + el.className.split(' ')[0] :
                              el.tagName.toLowerCase(),
                    tag: el.tagName.toLowerCase(),
                    text: el.innerText?.trim() || el.value || '',
                    attributes: Object.fromEntries(
                        Array.from(el.attributes).map(a => [a.name, a.value])
                    ),
                    visible: true
                }));
        }
    """)
    
    results = [
        ElementInfo(
            selector=e['selector'],
            tag=e['tag'],
            text=e['text'],
            attributes=e['attributes'],
            visible=e['visible'],
            location='unknown'
        )
        for e in elements
    ]
    
    if text_contains:
        results = [e for e in results if text_contains.lower() in e.text.lower()]
    
    return results
