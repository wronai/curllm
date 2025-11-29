#!/usr/bin/env python3
"""
Example: Dynamic Pattern Detection

Demonstrates generic, adaptive container detection without hard-coded selectors.
Works on ANY e-commerce site!
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from curllm_core.dynamic_detector import (
    DynamicPatternDetector,
    GenericFieldExtractor,
    dynamic_extract
)


async def example_skapiec():
    """Example 1: Skapiec.pl - where traditional methods fail"""
    print("\n🛒 Example 1: Skapiec.pl (Dynamic Detection)")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Loading Skapiec.pl...")
        await page.goto("https://www.skapiec.pl", wait_until="domcontentloaded")
        await asyncio.sleep(2)  # Let page load
        
        # Use dynamic detection
        print("\n🔍 Running dynamic pattern detection...")
        detector = DynamicPatternDetector(page)
        container_info = await detector.detect_product_containers()
        
        if container_info:
            print(f"\n✅ Found pattern!")
            print(f"   Selector: {container_info['selector']}")
            print(f"   Count: {container_info['count']}")
            print(f"   Confidence: {container_info['confidence']:.2%}")
            print(f"   Structure: {container_info['structure']['tag']} with {len(container_info['structure'].get('classes', []))} classes")
            
            # Now extract fields
            print(f"\n🔧 Detecting fields in {container_info['selector']}...")
            extractor = GenericFieldExtractor(page)
            fields = await extractor.detect_fields(container_info['selector'])
            
            if fields:
                print("✅ Detected fields:")
                for field_name, field_info in fields.items():
                    print(f"   {field_name}: {field_info['selector']}")
                
                # Extract products
                print(f"\n📦 Extracting products...")
                products = await extractor.extract_all(
                    container_info['selector'],
                    fields,
                    max_items=10
                )
                
                print(f"✅ Extracted {len(products)} products:")
                for i, product in enumerate(products[:5], 1):
                    name = product.get('name', 'N/A')[:50]
                    price = product.get('price', 'N/A')
                    print(f"   {i}. {name}... - {price} zł")
            else:
                print("❌ Could not detect fields")
        else:
            print("❌ No patterns detected")
        
        await browser.close()


async def example_ceneo():
    """Example 2: Ceneo.pl - verify it still works"""
    print("\n🛒 Example 2: Ceneo.pl (Verification)")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Loading Ceneo.pl...")
        await page.goto(
            "https://www.ceneo.pl/Komputery;0020-30-0-0-1.htm",
            wait_until="domcontentloaded"
        )
        await asyncio.sleep(2)
        
        print("\n🔍 Running dynamic detection...")
        result = await dynamic_extract(page, "Find products", max_items=10)
        
        if result.get('count', 0) > 0:
            print(f"\n✅ Success!")
            print(f"   Products: {result['count']}")
            print(f"   Container: {result['container']['selector']}")
            print(f"   Confidence: {result['container']['confidence']:.2%}")
            
            print(f"\n📦 Sample products:")
            for i, product in enumerate(result['products'][:5], 1):
                name = product.get('name', 'N/A')[:50]
                price = product.get('price', 'N/A')
                print(f"   {i}. {name}... - {price} zł")
        else:
            print(f"❌ No products found: {result.get('reason')}")
        
        await browser.close()


async def example_fake_site():
    """Example 3: Fake site with custom structure"""
    print("\n🛒 Example 3: Custom HTML Structure")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Create fake HTML with unusual class names
        await page.set_content("""
        <html>
            <body>
                <div class="xyz-listing">
                    <div class="abc-product-wrapper">
                        <h3 class="qwe-title">Gaming Laptop Pro</h3>
                        <span class="zxc-cost">2999.99 zł</span>
                        <a href="/product/1" class="rty-link">View</a>
                        <img src="/img1.jpg" alt="Product 1">
                    </div>
                    <div class="abc-product-wrapper">
                        <h3 class="qwe-title">Wireless Mouse</h3>
                        <span class="zxc-cost">149.99 zł</span>
                        <a href="/product/2" class="rty-link">View</a>
                        <img src="/img2.jpg" alt="Product 2">
                    </div>
                    <div class="abc-product-wrapper">
                        <h3 class="qwe-title">Mechanical Keyboard</h3>
                        <span class="zxc-cost">399.99 zł</span>
                        <a href="/product/3" class="rty-link">View</a>
                        <img src="/img3.jpg" alt="Product 3">
                    </div>
                    <div class="abc-product-wrapper">
                        <h3 class="qwe-title">USB Hub</h3>
                        <span class="zxc-cost">89.99 zł</span>
                        <a href="/product/4" class="rty-link">View</a>
                        <img src="/img4.jpg" alt="Product 4">
                    </div>
                    <div class="abc-product-wrapper">
                        <h3 class="qwe-title">Monitor 27 inch</h3>
                        <span class="zxc-cost">1299.99 zł</span>
                        <a href="/product/5" class="rty-link">View</a>
                        <img src="/img5.jpg" alt="Product 5">
                    </div>
                    <div class="abc-product-wrapper">
                        <h3 class="qwe-title">Webcam HD</h3>
                        <span class="zxc-cost">249.99 zł</span>
                        <a href="/product/6" class="rty-link">View</a>
                        <img src="/img6.jpg" alt="Product 6">
                    </div>
                </div>
            </body>
        </html>
        """)
        
        print("Custom HTML with unusual class names:")
        print("  - Container: .abc-product-wrapper")
        print("  - Name: .qwe-title")
        print("  - Price: .zxc-cost")
        print("  - Link: .rty-link")
        
        print("\n🔍 Can dynamic detector find these?")
        result = await dynamic_extract(page, "Find products")
        
        if result.get('count', 0) > 0:
            print(f"\n✅ YES! Found {result['count']} products")
            print(f"   Detected container: {result['container']['selector']}")
            print(f"   Confidence: {result['container']['confidence']:.2%}")
            
            detected_fields = result.get('fields', {})
            print(f"\n🔧 Detected field selectors:")
            for field_name, field_info in detected_fields.items():
                print(f"   {field_name}: {field_info['selector']}")
            
            print(f"\n📦 Extracted products:")
            for i, product in enumerate(result['products'], 1):
                print(f"   {i}. {product.get('name')} - {product.get('price')} zł")
        else:
            print(f"❌ Failed: {result.get('reason')}")
        
        await browser.close()


async def example_comparison():
    """Example 4: Compare traditional vs dynamic"""
    print("\n⚔️  Example 4: Traditional vs Dynamic")
    print("=" * 60)
    
    html = """
    <html>
        <body>
            <div class="strange-wrapper-2024-v3">
                <article class="offer-item-xyz">
                    <h2>Product A</h2>
                    <span>199.99 zł</span>
                    <a href="/a">Link</a>
                </article>
                <article class="offer-item-xyz">
                    <h2>Product B</h2>
                    <span>299.99 zł</span>
                    <a href="/b">Link</a>
                </article>
                <article class="offer-item-xyz">
                    <h2>Product C</h2>
                    <span>399.99 zł</span>
                    <a href="/c">Link</a>
                </article>
                <article class="offer-item-xyz">
                    <h2>Product D</h2>
                    <span>499.99 zł</span>
                    <a href="/d">Link</a>
                </article>
                <article class="offer-item-xyz">
                    <h2>Product E</h2>
                    <span>599.99 zł</span>
                    <a href="/e">Link</a>
                </article>
            </div>
        </body>
    </html>
    """
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html)
        
        # Traditional approach
        print("\n📌 Traditional Approach (Hard-coded):")
        traditional_selectors = [
            ".product", ".item", ".box", ".card",
            "[data-product]", ".product-card"
        ]
        
        found_traditional = False
        for selector in traditional_selectors:
            count = await page.evaluate(f"""
                () => document.querySelectorAll('{selector}').length
            """)
            print(f"   Trying {selector}: {count} elements")
            if count > 0:
                found_traditional = True
                break
        
        if not found_traditional:
            print("   ❌ FAILED - No selectors matched!")
        
        # Dynamic approach
        print("\n🔍 Dynamic Approach:")
        result = await dynamic_extract(page, "Find products")
        
        if result.get('count', 0) > 0:
            print(f"   ✅ SUCCESS - Found {result['count']} products")
            print(f"   Detected: {result['container']['selector']}")
            print(f"   Confidence: {result['container']['confidence']:.2%}")
        else:
            print(f"   ❌ Failed: {result.get('reason')}")
        
        await browser.close()


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("🎯 Dynamic Pattern Detection Examples")
    print("=" * 60)
    
    try:
        # Example 3: Fake site (fast, always works)
        await example_fake_site()
        
        # Example 4: Comparison (demonstrates the difference)
        await example_comparison()
        
        # Example 1: Real Skapiec (may be slow/blocked)
        # await example_skapiec()
        
        # Example 2: Real Ceneo (may be slow/blocked)
        # await example_ceneo()
        
        print("\n" + "=" * 60)
        print("✅ Examples completed!")
        print("=" * 60)
        print("\n💡 Key Takeaways:")
        print("   - Dynamic detection works on ANY structure")
        print("   - No hard-coded selectors needed")
        print("   - Adapts to unusual class names")
        print("   - High confidence scoring")
        print("   - Generic field extraction")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
