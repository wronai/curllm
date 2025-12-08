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
        purpose_keywords = {
            'email': ['email', 'mail', 'e-mail'],
            'password': ['password', 'haslo', 'hasło'],
            'name': ['name', 'imie', 'imię', 'nazwisko'],
            'phone': ['phone', 'tel', 'telefon', 'mobile'],
            'search': ['search', 'szukaj', 'query', 'q'],
            'message': ['message', 'wiadomosc', 'wiadomość', 'text', 'comment'],
        }
        
        keywords = purpose_keywords.get(purpose_lower, [purpose_lower])
        
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
