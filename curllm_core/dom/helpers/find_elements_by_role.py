import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .element_info import ElementInfo

async def find_elements_by_role(
    page,
    role: str,
    name_contains: Optional[str] = None
) -> List[ElementInfo]:
    """
    Find elements by ARIA role.
    """
    elements = await page.evaluate(f"""
        () => {{
            const els = document.querySelectorAll('[role="{role}"]');
            return Array.from(els).map(el => ({{
                selector: el.id ? '#' + el.id : el.tagName.toLowerCase(),
                tag: el.tagName.toLowerCase(),
                text: el.innerText?.slice(0, 100) || '',
                attributes: Object.fromEntries(
                    Array.from(el.attributes).map(a => [a.name, a.value])
                ),
                visible: el.offsetParent !== null
            }}));
        }}
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
    
    if name_contains:
        results = [e for e in results if name_contains.lower() in e.text.lower()]
    
    return results
