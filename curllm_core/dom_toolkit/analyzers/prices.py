"""
Price Detector - Find and Extract Prices

Handles multiple price formats:
- Text prices (1 234,56 zł, $99.99, €50,00)
- Image-based prices (common in Polish shops)
- Multiple currencies
"""

from typing import Dict, List, Any


class PriceDetector:
    """
    Detect and extract prices from DOM.
    
    Supports:
    - Multiple currencies (PLN, EUR, USD, GBP)
    - Various formats (1234.56, 1 234,56)
    - Image-based prices (gral.pl style)
    - Price labels ("Cena:", "Price:")
    """
    
    @staticmethod
    async def find_all_prices(page, limit: int = 100) -> Dict[str, Any]:
        """
        Find all price-like elements on the page.
        
        Returns categorized prices: text, image, labeled.
        """
        return await page.evaluate("""
            (limit) => {
                const results = {
                    text_prices: [],
                    image_prices: [],
                    labeled_prices: [],
                    total_found: 0
                };
                
                // Price patterns for various currencies
                const patterns = {
                    pln: /(\\d+[\\d\\s]*(?:[,.]\\d{2})?)\\s*(?:zł|PLN)/gi,
                    eur: /(\\d+[\\d\\s]*(?:[,.]\\d{2})?)\\s*€/gi,
                    usd: /\\$\\s*(\\d+[\\d\\s]*(?:[,.]\\d{2})?)/gi,
                    gbp: /£\\s*(\\d+[\\d\\s]*(?:[,.]\\d{2})?)/gi,
                    generic: /(\\d+[\\d\\s]*[,.]\\d{2})(?!\\d)/g
                };
                
                // Find TEXT prices
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let node;
                while ((node = walker.nextNode()) && results.text_prices.length < limit) {
                    const text = node.textContent.trim();
                    if (text.length < 3 || text.length > 100) continue;
                    
                    for (const [currency, pattern] of Object.entries(patterns)) {
                        pattern.lastIndex = 0;  // Reset regex
                        const match = pattern.exec(text);
                        if (match) {
                            const parent = node.parentElement;
                            const cls = parent && typeof parent.className === 'string'
                                ? parent.className.split(' ').filter(c => c.length > 0)[0]
                                : null;
                            
                            results.text_prices.push({
                                value: match[1] || match[0],
                                currency: currency === 'generic' ? 'unknown' : currency.toUpperCase(),
                                text: text,
                                selector: parent ? parent.tagName.toLowerCase() + (cls ? '.' + cls : '') : null
                            });
                            break;
                        }
                    }
                }
                
                // Find IMAGE-based prices
                const priceImagePatterns = ['cb_', 'cn_', 'cena', 'price', 'koszyk'];
                const images = document.querySelectorAll('img[src]');
                
                for (const img of images) {
                    const src = img.src || '';
                    if (priceImagePatterns.some(p => src.toLowerCase().includes(p))) {
                        const parent = img.parentElement;
                        results.image_prices.push({
                            src: src.slice(0, 100),
                            parent_tag: parent ? parent.tagName.toLowerCase() : null,
                            near_text: parent ? (parent.textContent || '').slice(0, 50) : null
                        });
                    }
                    
                    if (results.image_prices.length >= limit) break;
                }
                
                // Find LABELED prices (Cena: 123 zł)
                const labels = ['cena', 'price', 'koszt', 'wartość'];
                const allElements = document.querySelectorAll('*');
                
                for (const el of allElements) {
                    const text = (el.textContent || '').toLowerCase();
                    if (text.length > 100) continue;
                    
                    for (const label of labels) {
                        if (text.includes(label + ':') || text.includes(label + ' ')) {
                            const priceMatch = text.match(/(\\d+[\\d\\s]*[,.]\\d{2})/);
                            if (priceMatch) {
                                results.labeled_prices.push({
                                    label: label,
                                    value: priceMatch[1],
                                    full_text: text.slice(0, 50)
                                });
                                break;
                            }
                        }
                    }
                    
                    if (results.labeled_prices.length >= limit) break;
                }
                
                results.total_found = results.text_prices.length + 
                                     results.image_prices.length + 
                                     results.labeled_prices.length;
                
                return results;
            }
        """, limit)
    
    @staticmethod
    async def get_price_distribution(page) -> Dict[str, Any]:
        """
        Analyze price distribution on the page.
        
        Returns: price ranges, common values, outliers.
        Useful for filtering "under $X" queries.
        """
        return await page.evaluate("""
            () => {
                const prices = [];
                const pricePattern = /(\\d+[\\d\\s]*(?:[,.]\\d{2})?)\\s*(?:zł|PLN|€|\\$|USD|EUR)/gi;
                
                const text = document.body.textContent || '';
                let match;
                while ((match = pricePattern.exec(text)) !== null) {
                    const numStr = match[1].replace(/\\s/g, '').replace(',', '.');
                    const num = parseFloat(numStr);
                    if (!isNaN(num) && num > 0 && num < 1000000) {
                        prices.push(num);
                    }
                }
                
                if (prices.length === 0) {
                    return { found: false };
                }
                
                prices.sort((a, b) => a - b);
                
                return {
                    found: true,
                    count: prices.length,
                    min: prices[0],
                    max: prices[prices.length - 1],
                    median: prices[Math.floor(prices.length / 2)],
                    percentile_25: prices[Math.floor(prices.length * 0.25)],
                    percentile_75: prices[Math.floor(prices.length * 0.75)],
                    sample: prices.slice(0, 10)
                };
            }
        """)
    
    @staticmethod
    async def extract_price_from_selector(page, selector: str) -> Dict[str, Any]:
        """
        Extract price from elements matching selector.
        
        Returns extracted price values with parsing details.
        """
        return await page.evaluate("""
            (selector) => {
                const elements = document.querySelectorAll(selector);
                const results = [];
                
                const parsePrice = (text) => {
                    // Try multiple patterns
                    const patterns = [
                        /(\\d+[\\d\\s]*[,.]\\d{2})\\s*(?:zł|PLN)/i,
                        /€\\s*(\\d+[\\d\\s]*[,.]\\d{2})/i,
                        /\\$\\s*(\\d+[\\d\\s]*[,.]\\d{2})/i,
                        /(\\d+[\\d\\s]*[,.]\\d{2})/
                    ];
                    
                    for (const pattern of patterns) {
                        const match = text.match(pattern);
                        if (match) {
                            const numStr = match[1].replace(/\\s/g, '').replace(',', '.');
                            return {
                                raw: match[0],
                                value: parseFloat(numStr),
                                pattern: pattern.source.slice(0, 30)
                            };
                        }
                    }
                    return null;
                };
                
                for (const el of Array.from(elements).slice(0, 20)) {
                    const text = (el.textContent || '').trim();
                    const price = parsePrice(text);
                    
                    if (price) {
                        results.push({
                            text: text.slice(0, 50),
                            ...price
                        });
                    }
                }
                
                return {
                    selector: selector,
                    matches: elements.length,
                    prices: results,
                    success_rate: results.length / Math.max(elements.length, 1)
                };
            }
        """, selector)
    
    @staticmethod
    async def detect_price_format(page) -> Dict[str, Any]:
        """
        Detect the price format used on the page.
        
        Returns: currency, decimal separator, thousands separator.
        """
        return await page.evaluate("""
            () => {
                const text = document.body.textContent || '';
                
                // Detect currency
                const currencyPatterns = {
                    'PLN': /zł|PLN/i,
                    'EUR': /€|EUR/i,
                    'USD': /\\$|USD/i,
                    'GBP': /£|GBP/i
                };
                
                const currencies = {};
                for (const [currency, pattern] of Object.entries(currencyPatterns)) {
                    const matches = text.match(new RegExp(pattern, 'g'));
                    currencies[currency] = matches ? matches.length : 0;
                }
                
                const primaryCurrency = Object.entries(currencies)
                    .sort((a, b) => b[1] - a[1])[0];
                
                // Detect decimal format
                const commaDecimal = (text.match(/\\d+,\\d{2}\\s*(?:zł|PLN|€)/g) || []).length;
                const dotDecimal = (text.match(/\\d+\\.\\d{2}\\s*(?:\\$|USD|GBP)/g) || []).length;
                
                return {
                    primary_currency: primaryCurrency ? primaryCurrency[0] : 'unknown',
                    currency_counts: currencies,
                    decimal_separator: commaDecimal > dotDecimal ? ',' : '.',
                    thousands_separator: commaDecimal > dotDecimal ? ' ' : ','
                };
            }
        """)
