import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .element_info import ElementInfo

async def find_inputs(
    page,
    input_type: Optional[str] = None,
    purpose: Optional[str] = None
) -> List[ElementInfo]:
    """
    Find input elements, optionally filtered by type or purpose.
    
    Purpose detection uses name, id, placeholder, aria-label.
    """
    elements = await page.evaluate("""
        () => {
            const inputs = document.querySelectorAll('input, textarea, select');
            return Array.from(inputs)
                .filter(el => el.offsetParent !== null)
                .map(el => ({
                    selector: el.id ? '#' + el.id : 
                              el.name ? `[name="${el.name}"]` :
                              el.tagName.toLowerCase(),
                    tag: el.tagName.toLowerCase(),
                    text: el.placeholder || el.value || '',
                    type: el.type || 'text',
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
    
    if input_type:
        results = [e for e in results if e.attributes.get('type') == input_type]
    
    if purpose:
        purpose_lower = purpose.lower()
        
        # Dynamically derive keywords from purpose string
        # This avoids hardcoded keyword lists - purpose itself becomes the keyword
        # Additional common variations are generated from the purpose word
        base_keywords = [purpose_lower]
        
        # Add common variations (language-agnostic approach)
        # These are semantic derivations, not hardcoded selectors
        if len(purpose_lower) > 3:
            # Add partial matches (stem)
            base_keywords.append(purpose_lower[:4])
        
        # The purpose word + its type indicator
        base_keywords.append(f"{purpose_lower}_input")
        base_keywords.append(f"{purpose_lower}_field")
        
        keywords = base_keywords
        
        filtered = []
        for e in results:
            attrs_text = ' '.join([
                e.attributes.get('id', ''),
                e.attributes.get('name', ''),
                e.attributes.get('placeholder', ''),
                e.attributes.get('aria-label', ''),
                e.text
            ]).lower()
            
            if any(kw in attrs_text for kw in keywords):
                filtered.append(e)
        
        results = filtered
    
    return results
