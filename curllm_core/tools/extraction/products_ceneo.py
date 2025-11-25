"""
Specialized tool for extracting products from Ceneo.pl

Optimized for Polish e-commerce site with specific DOM patterns,
price formatting, and URL structures.
"""

from typing import Any, Dict, Optional
import re
from ..base import BaseTool


class ProductsCeneoTool(BaseTool):
    """Extract products from Ceneo.pl with price filtering"""
    
    async def execute(self, page, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract products from Ceneo using specialized heuristics.
        
        Parameters:
            max_price: Maximum price threshold in PLN
            min_price: Minimum price threshold in PLN (default: 0)
            max_results: Maximum number of products to return (default: 50)
        
        Returns:
            {"products": [{"name": str, "price": float, "url": str}, ...]}
        """
        self.validate_parameters(parameters)
        
        max_price = parameters.get("max_price", 999999)
        min_price = parameters.get("min_price", 0)
        max_results = parameters.get("max_results", 50)
        
        # JavaScript execution for DOM extraction
        items = await page.evaluate(
            """
            (minPrice, maxPrice, maxResults) => {
                const normPrice = (s) => {
                    s = String(s||'').replace(/\\s+/g,'');
                    s = s.replace(/\\.(?=\\d{3}(?:[\\.,]|$))/g,'');
                    s = s.replace(',', '.');
                    const n = parseFloat(s);
                    return isNaN(n) ? null : n;
                };
                
                const extractPrice = (text) => {
                    // Ceneo-specific price patterns
                    const patterns = [
                        /(\\d[\\d\\s]*(?:[\\.,]\\d{2})?)\\s*(?:zł|PLN|złotych)/i,
                        /od\\s*(\\d[\\d\\s]*(?:[\\.,]\\d{2})?)\\s*(?:zł|PLN)/i,
                        /cena[:\\s]*(\\d[\\d\\s]*(?:[\\.,]\\d{2})?)\\s*(?:zł|PLN)/i,
                    ];
                    
                    for (const pattern of patterns) {
                        const m = text.match(pattern);
                        if (m && m[1]) {
                            return normPrice(m[1]);
                        }
                    }
                    return null;
                };
                
                // Ceneo-specific selectors (optimized)
                const productSelectors = [
                    '.product-box',
                    '.product-item',
                    '[data-product-id]',
                    '.js_product-box',
                    'article[data-offer-id]'
                ];
                
                const possibleContainers = [];
                for (const selector of productSelectors) {
                    const elements = Array.from(document.querySelectorAll(selector));
                    if (elements.length > 0) {
                        possibleContainers.push(...elements);
                        break; // Use first matching selector
                    }
                }
                
                // Fallback to generic container detection
                if (possibleContainers.length === 0) {
                    possibleContainers.push(...Array.from(document.querySelectorAll('*')).filter(el => {
                        const text = el.innerText || '';
                        const hasPrice = extractPrice(text) !== null;
                        const hasLink = el.querySelector('a[href]') !== null;
                        const textLength = text.length;
                        return hasPrice && hasLink && textLength > 20 && textLength < 500;
                    }));
                }
                
                const products = new Map();
                
                for (const el of possibleContainers) {
                    const text = el.innerText || '';
                    const price = extractPrice(text);
                    
                    if (price === null || price > maxPrice || price < minPrice) continue;
                    
                    const link = el.querySelector('a[href]');
                    if (!link) continue;
                    
                    const url = link.href;
                    const nameFromLink = (link.innerText || '').trim();
                    let name = nameFromLink;
                    
                    // Extract better product name from text
                    if (!name || name.length < 5) {
                        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 5);
                        name = lines.find(line => 
                            !/^\\d+/.test(line) &&
                            !/zł|PLN/i.test(line) &&
                            !/(Bestseller|Reklama|POPRZEDNIE|NASTĘPNE)/i.test(line) &&
                            line.length > 5 && line.length < 140
                        ) || nameFromLink;
                    }
                    
                    if (!name || !url) continue;
                    
                    // Validate Ceneo product URL
                    try {
                        const u = new URL(url);
                        const hostOk = /(^|\\.)ceneo\\.pl$/i.test(u.hostname);
                        const pathOk = /\\d{4,}/.test(u.pathname);
                        
                        if (!hostOk || !pathOk) continue;
                        
                        // Skip non-product pages
                        if (/redirect\\.ceneo\\.pl|GotoBoxUrl|from\\?site=|lp,\\d+|\\/ssl-|\\/wydarzenia/i.test(url)) {
                            continue;
                        }
                    } catch (e) {
                        continue;
                    }
                    
                    const key = url;
                    if (!products.has(key)) {
                        products.set(key, { name, price, url });
                    }
                    
                    if (products.size >= maxResults) break;
                }
                
                return Array.from(products.values());
            }
            """,
            min_price,
            max_price,
            max_results
        )
        
        # Post-process and validate
        valid_products = []
        skip_keywords = [
            "szukaj", "koszyk", "kategorie", "zobacz", "pokaż", "następne", "poprzednie",
            "regulamin", "polityka", "privacy", "terms", "cookie"
        ]
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            price = item.get("price")
            name = item.get("name", "").strip()
            url = item.get("url", "")
            
            if not (price and name and url):
                continue
            
            if any(skip in name.lower() for skip in skip_keywords):
                continue
            
            if len(name) < 5:
                continue
            
            valid_products.append({
                "name": name,
                "price": float(price),
                "url": url
            })
        
        return {"products": valid_products}
