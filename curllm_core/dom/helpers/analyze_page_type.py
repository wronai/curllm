import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse


async def analyze_page_type(page) -> Dict[str, Any]:
    """
    Analyze the current page to determine its type.
    """
    return await page.evaluate("""
        () => {
            const url = location.href.toLowerCase();
            const title = document.title.toLowerCase();
            const body = document.body.innerText.toLowerCase().slice(0, 5000);
            
            // Count various elements
            const products = document.querySelectorAll('[class*="product"], [class*="offer"], [class*="item"]').length;
            const forms = document.querySelectorAll('form').length;
            const inputs = document.querySelectorAll('input, textarea').length;
            const prices = (body.match(/\\d+[,.]\\d{2}\\s*(zł|pln|eur|usd|€|\\$)/gi) || []).length;
            
            // Determine page type
            let pageType = 'other';
            let confidence = 0.3;
            
            if (url.includes('/koszyk') || url.includes('/cart')) {
                pageType = 'cart';
                confidence = 0.9;
            } else if (url.includes('/login') || url.includes('/logowanie')) {
                pageType = 'login';
                confidence = 0.9;
            } else if (url.includes('/kontakt') || url.includes('/contact')) {
                pageType = 'contact';
                confidence = 0.9;
            } else if (products > 10 || prices > 5) {
                pageType = 'product_listing';
                confidence = Math.min(0.9, 0.5 + products * 0.02);
            } else if (url.includes('/search') || url.includes('/szukaj') || url.includes('q=')) {
                pageType = 'search_results';
                confidence = 0.8;
            } else if (forms > 0 && inputs > 3) {
                pageType = 'form';
                confidence = 0.7;
            } else if (url === location.origin + '/' || url === location.origin) {
                pageType = 'home';
                confidence = 0.9;
            }
            
            return {
                type: pageType,
                confidence: confidence,
                url: location.href,
                title: document.title,
                stats: {
                    products: products,
                    forms: forms,
                    inputs: inputs,
                    prices: prices
                }
            };
        }
    """)
