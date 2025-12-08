import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .link_info import LinkInfo

async def extract_all_links(page) -> List[LinkInfo]:
    """
    Extract all links from page with context information.
    
    This is the foundational function - other functions filter these results.
    """
    links = await page.evaluate("""
        () => {
            const getLocation = (el) => {
                let node = el;
                while (node && node !== document.body) {
                    const tag = node.tagName?.toLowerCase();
                    const role = node.getAttribute('role');
                    const cls = node.className?.toLowerCase() || '';
                    
                    if (tag === 'header' || role === 'banner' || cls.includes('header')) return 'header';
                    if (tag === 'footer' || role === 'contentinfo' || cls.includes('footer')) return 'footer';
                    if (tag === 'nav' || role === 'navigation' || cls.includes('nav')) return 'nav';
                    if (tag === 'aside' || cls.includes('sidebar')) return 'sidebar';
                    if (tag === 'main' || role === 'main') return 'main';
                    
                    node = node.parentElement;
                }
                return 'main';
            };
            
            const getContext = (el, maxLen = 100) => {
                const parent = el.closest('li, div, p, section, article') || el.parentElement;
                if (!parent) return '';
                return parent.innerText?.slice(0, maxLen).replace(/\\s+/g, ' ').trim() || '';
            };
            
            return Array.from(document.querySelectorAll('a[href]'))
                .filter(a => a.offsetParent !== null)  // visible
                .map(a => ({
                    url: a.href,
                    text: a.innerText?.trim().slice(0, 100) || '',
                    ariaLabel: a.getAttribute('aria-label') || '',
                    title: a.title || '',
                    location: getLocation(a),
                    context: getContext(a),
                    tagName: a.tagName
                }))
                .filter(l => l.url && !l.url.startsWith('javascript:'));
        }
    """)
    
    return [
        LinkInfo(
            url=l['url'],
            text=l['text'],
            aria_label=l.get('ariaLabel'),
            title=l.get('title'),
            location=l['location'],
            context=l['context'],
            score=0.0,
            method='extract'
        )
        for l in links
    ]
