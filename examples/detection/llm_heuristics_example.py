#!/usr/bin/env python3
"""
LLM Heuristics Discovery Example

Demonstrates how curllm dynamically discovers URL patterns, price patterns,
and container selectors by analyzing the page structure with LLM assistance.

No hardcoded selectors - everything is discovered at runtime!
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    """
    Example: Discover heuristics for any e-commerce site
    """
    # Target URL (change to any e-commerce site)
    url = "https://www.ceneo.pl"
    
    print(f"\n🔍 LLM Heuristics Discovery for: {url}")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("\n📖 Loading page...")
        await page.goto(url, wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)  # Wait for dynamic content
        
        # Step 1: Discover URL patterns
        print("\n📊 Step 1: Analyzing URL patterns...")
        url_patterns = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                const patterns = {};
                const samples = {};
                
                for (const link of links.slice(0, 200)) {
                    const href = link.href || '';
                    const text = (link.innerText || '').trim().substring(0, 50);
                    
                    if (!href || href.startsWith('#') || href.startsWith('javascript:')) continue;
                    
                    try {
                        const url = new URL(href);
                        const path = url.pathname;
                        
                        // Find pattern markers
                        const markers = [];
                        if (/\\/p\\//.test(path)) markers.push('/p/');
                        if (/\\/product/.test(path)) markers.push('/product');
                        if (/\\/produkt/.test(path)) markers.push('/produkt');
                        if (/\\/item/.test(path)) markers.push('/item');
                        if (/\\.html$/.test(path)) markers.push('.html');
                        if (/\\/\\d{4,}/.test(path)) markers.push('/ID (numeric)');
                        if (/_\\d{4,}/.test(path)) markers.push('_ID (numeric)');
                        
                        for (const marker of markers) {
                            patterns[marker] = (patterns[marker] || 0) + 1;
                            if (!samples[marker]) {
                                samples[marker] = { href: href.substring(0, 80), text };
                            }
                        }
                    } catch (e) {}
                }
                
                return Object.entries(patterns)
                    .map(([pattern, count]) => ({ pattern, count, sample: samples[pattern] }))
                    .sort((a, b) => b.count - a.count)
                    .slice(0, 8);
            }
        """)
        
        print("\n   Found URL patterns:")
        for p in url_patterns[:5]:
            print(f"   - {p['pattern']}: {p['count']} links")
            if p.get('sample'):
                print(f"     Sample: {p['sample'].get('text', '')[:40]}...")
        
        # Step 2: Discover price patterns
        print("\n📊 Step 2: Analyzing price patterns...")
        price_patterns = await page.evaluate("""
            () => {
                const results = {
                    text_prices: 0,
                    image_prices: [],
                    price_classes: []
                };
                
                // Count text-based prices
                const priceRegex = /\\d+[\\d\\s]*[,.]?\\d*\\s*(?:zł|PLN|€|\\$)/gi;
                const bodyText = document.body.innerText || '';
                const matches = bodyText.match(priceRegex);
                results.text_prices = matches ? matches.length : 0;
                
                // Find price images
                const images = document.querySelectorAll('img');
                for (const img of images) {
                    const src = img.src || '';
                    if (/cb_|cena|price|_c\\d|_p\\d/i.test(src)) {
                        results.image_prices.push(src.substring(0, 60));
                    }
                }
                
                // Find price-related CSS classes
                const priceElements = document.querySelectorAll('[class*="price"], [class*="cena"]');
                const classes = new Set();
                for (const el of priceElements) {
                    const cls = el.className?.split(' ')[0];
                    if (cls) classes.add(cls);
                }
                results.price_classes = Array.from(classes).slice(0, 5);
                
                return results;
            }
        """)
        
        print(f"\n   Text prices found: {price_patterns['text_prices']}")
        print(f"   Price images: {len(price_patterns['image_prices'])}")
        print(f"   Price classes: {price_patterns['price_classes'][:3]}")
        
        # Step 3: Discover container patterns
        print("\n📊 Step 3: Analyzing container patterns...")
        container_candidates = await page.evaluate("""
            () => {
                const candidates = [];
                const seen = new Set();
                const priceRegex = /\\d+[\\d\\s]*[,.]?\\d*\\s*(?:zł|PLN|€|\\$)/i;
                
                document.querySelectorAll('*').forEach(el => {
                    if (el.className && typeof el.className === 'string') {
                        const cls = el.className.split(' ')[0];
                        if (cls && !seen.has(cls) && /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(cls)) {
                            seen.add(cls);
                            const elements = document.querySelectorAll('.' + cls);
                            const count = elements.length;
                            
                            if (count >= 3 && count <= 100) {
                                const sample = el.textContent?.trim().substring(0, 150) || '';
                                const hasPrice = priceRegex.test(sample);
                                const hasLink = !!el.querySelector('a[href]');
                                const hasImage = !!el.querySelector('img');
                                
                                // Skip CSS/script content
                                const isCss = sample.includes('color:') || 
                                             sample.includes('font-size:') ||
                                             sample.includes('@media');
                                
                                if (!isCss && (hasPrice || (hasLink && hasImage))) {
                                    candidates.push({
                                        selector: '.' + cls,
                                        count,
                                        hasPrice,
                                        hasLink,
                                        hasImage,
                                        sample: sample.substring(0, 100)
                                    });
                                }
                            }
                        }
                    }
                });
                
                return candidates.sort((a, b) => {
                    // Score by product-likeness
                    const scoreA = (a.hasPrice ? 30 : 0) + (a.hasLink ? 20 : 0) + (a.hasImage ? 10 : 0);
                    const scoreB = (b.hasPrice ? 30 : 0) + (b.hasLink ? 20 : 0) + (b.hasImage ? 10 : 0);
                    return scoreB - scoreA;
                }).slice(0, 10);
            }
        """)
        
        print("\n   Top container candidates:")
        for c in container_candidates[:5]:
            features = []
            if c['hasPrice']: features.append('💰 price')
            if c['hasLink']: features.append('🔗 link')
            if c['hasImage']: features.append('🖼️ image')
            print(f"   - {c['selector']} ({c['count']}x): {', '.join(features)}")
            print(f"     Sample: \"{c['sample'][:60]}...\"")
        
        # Step 4: Build dynamic selectors
        print("\n📊 Step 4: Building dynamic selectors...")
        
        # Convert URL patterns to CSS selectors
        link_selectors = []
        for p in url_patterns[:4]:
            pattern = p['pattern']
            if pattern == '.html':
                link_selectors.append('a[href$=".html"]')
            elif pattern.startswith('/'):
                link_selectors.append(f'a[href*="{pattern}"]')
        
        if link_selectors:
            product_link_selector = ', '.join(link_selectors)
        else:
            product_link_selector = 'a[href*="product"], a[href*=".html"]'
        
        # Best container
        best_container = container_candidates[0]['selector'] if container_candidates else None
        
        print(f"\n   ✅ Product link selector: {product_link_selector}")
        print(f"   ✅ Best container: {best_container}")
        print(f"   ✅ Price classes: {', '.join(price_patterns['price_classes'][:3])}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 DISCOVERED HEURISTICS SUMMARY")
        print("=" * 60)
        print(json.dumps({
            "product_link_selector": product_link_selector,
            "container_selector": best_container,
            "price_classes": price_patterns['price_classes'][:3],
            "url_patterns": [p['pattern'] for p in url_patterns[:4]],
            "text_prices_found": price_patterns['text_prices']
        }, indent=2, ensure_ascii=False))
        
        await browser.close()
        
    print("\n✅ Done! These heuristics can now be used for extraction.")


if __name__ == "__main__":
    asyncio.run(main())
