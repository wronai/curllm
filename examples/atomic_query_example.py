#!/usr/bin/env python3
"""
Example: Atomic Query & Multi-Format Export

Demonstrates:
- Atomic queries with fluent API
- Product extraction with filtering
- Export to multiple formats
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

# Import atomic query and export systems
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from curllm_core.atomic_query import AtomicQuery, ProductQuery, quick_extract_products
from curllm_core.data_export import DataExporter


async def example_basic_query():
    """Example 1: Basic atomic query"""
    print("\n🔍 Example 1: Basic Atomic Query")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Go to a page with products
        await page.goto("https://news.ycombinator.com")
        
        # Create atomic query
        query = AtomicQuery(page)
        
        # Chain operations
        result = await (
            query
            .find(".athing")  # Find story containers
            .limit(10)  # Only first 10
            .map("""
                el => {
                    const titleEl = el.querySelector('.titleline a');
                    const scoreEl = document.querySelector(`#score_${el.id}`);
                    return {
                        title: titleEl?.innerText || '',
                        url: titleEl?.href || '',
                        score: scoreEl?.innerText || '0'
                    };
                }
            """)
            .execute()
        )
        
        print(f"✅ Found {len(result.data)} stories")
        print(f"📊 Sample: {result.data[0] if result.data else 'None'}")
        
        await browser.close()
        
        return result.data


async def example_product_query():
    """Example 2: Specialized product query"""
    print("\n🛍️  Example 2: Product Query")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Simple demo with a fake product page
        await page.set_content("""
        <html>
            <body>
                <div class="product">
                    <h3 class="name">Product A</h3>
                    <span class="price">99.99 zł</span>
                    <a href="/product-a">Link</a>
                </div>
                <div class="product">
                    <h3 class="name">Product B</h3>
                    <span class="price">149.99 zł</span>
                    <a href="/product-b">Link</a>
                </div>
                <div class="product">
                    <h3 class="name">Product C</h3>
                    <span class="price">199.99 zł</span>
                    <a href="/product-c">Link</a>
                </div>
            </body>
        </html>
        """)
        
        # Use ProductQuery
        query = ProductQuery(page)
        
        result = await (
            query
            .find(".product")
            .extract_product(
                name_sel=".name",
                price_sel=".price",
                url_sel="a"
            )
            .filter_by_price(max_price=150)  # Only products <= 150 zł
            .execute()
        )
        
        print(f"✅ Found {len(result.data)} products under 150 zł")
        for product in result.data:
            print(f"   - {product['name']}: {product['price']} zł")
        
        await browser.close()
        
        return result.data


async def example_quick_functions():
    """Example 3: Quick convenience functions"""
    print("\n⚡ Example 3: Quick Functions")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.set_content("""
        <html>
            <body>
                <div class="product">
                    <h3>Product 1</h3>
                    <span class="price">50 zł</span>
                    <a href="/p1">Link</a>
                </div>
                <div class="product">
                    <h3>Product 2</h3>
                    <span class="price">120 zł</span>
                    <a href="/p2">Link</a>
                </div>
            </body>
        </html>
        """)
        
        # Quick product extraction
        products = await quick_extract_products(
            page,
            container_selector=".product",
            name_selector="h3",
            price_selector=".price",
            url_selector="a",
            max_price=150,
            limit=50
        )
        
        print(f"✅ Extracted {len(products)} products quickly")
        for p in products:
            print(f"   - {p['name']}: {p['price']} zł")
        
        await browser.close()
        
        return products


def example_multi_format_export():
    """Example 4: Export to multiple formats"""
    print("\n📤 Example 4: Multi-Format Export")
    print("=" * 50)
    
    # Sample data
    products = [
        {"name": "Product A", "price": 99.99, "url": "https://example.com/a", "rating": 4.5},
        {"name": "Product B", "price": 149.99, "url": "https://example.com/b", "rating": 4.8},
        {"name": "Product C", "price": 79.99, "url": "https://example.com/c", "rating": 4.2},
    ]
    
    # Create exporter
    exporter = DataExporter(products, metadata={"source": "example", "count": len(products)})
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Export to multiple formats
    print("Exporting to multiple formats...")
    
    # JSON
    exporter.to_json(output_dir / "products.json", pretty=True)
    print("✅ Exported to JSON (output/products.json)")
    
    # CSV
    exporter.to_csv(output_dir / "products.csv")
    print("✅ Exported to CSV (output/products.csv)")
    
    # Markdown
    exporter.to_markdown(output_dir / "products.md")
    print("✅ Exported to Markdown (output/products.md)")
    
    # HTML
    exporter.to_html(output_dir / "products.html", include_style=True)
    print("✅ Exported to HTML (output/products.html)")
    
    # XML
    exporter.to_xml(output_dir / "products.xml")
    print("✅ Exported to XML (output/products.xml)")
    
    # JSONL
    exporter.to_jsonl(output_dir / "products.jsonl")
    print("✅ Exported to JSONL (output/products.jsonl)")
    
    print(f"\n📁 All files saved to: {output_dir.absolute()}")
    
    # Show sample outputs
    print("\n📄 Sample Markdown output:")
    md = exporter.to_markdown()
    print(md[:200] + "...")
    
    print("\n📄 Sample CSV output:")
    csv = exporter.to_csv()
    print(csv[:150] + "...")


async def example_complete_workflow():
    """Example 5: Complete workflow - scrape and export"""
    print("\n🚀 Example 5: Complete Workflow")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Simulate product page
        await page.set_content("""
        <html>
            <body>
                <h1>Product Catalog</h1>
                <div class="products">
                    <div class="product available">
                        <h3 class="title">Gaming Laptop</h3>
                        <span class="price">2999.99 zł</span>
                        <div class="rating" data-rating="4.7">⭐⭐⭐⭐⭐</div>
                        <a href="/laptop-1" class="link">View</a>
                    </div>
                    <div class="product available">
                        <h3 class="title">Wireless Mouse</h3>
                        <span class="price">149.99 zł</span>
                        <div class="rating" data-rating="4.5">⭐⭐⭐⭐⭐</div>
                        <a href="/mouse-1" class="link">View</a>
                    </div>
                    <div class="product out-of-stock">
                        <h3 class="title">Keyboard</h3>
                        <span class="price">399.99 zł</span>
                        <div class="rating" data-rating="4.3">⭐⭐⭐⭐</div>
                        <a href="/keyboard-1" class="link">View</a>
                    </div>
                </div>
            </body>
        </html>
        """)
        
        # Build complex query
        query = AtomicQuery(page)
        
        result = await (
            query
            .find(".product")
            .filter("el => el.classList.contains('available')")  # Only in stock
            .map("""
                el => {
                    const title = el.querySelector('.title')?.innerText || '';
                    const priceText = el.querySelector('.price')?.innerText || '';
                    const price = parseFloat(priceText.replace(/[^0-9.]/g, ''));
                    const rating = parseFloat(el.querySelector('.rating')?.getAttribute('data-rating') || '0');
                    const url = el.querySelector('.link')?.href || '';
                    
                    return {title, price, rating, url, inStock: true};
                }
            """)
            .filter("item => item.rating >= 4.5")  # Only highly rated
            .execute()
        )
        
        await browser.close()
        
        print(f"✅ Scraped {len(result.data)} high-rated, in-stock products")
        
        if result.data:
            # Export to multiple formats
            exporter = DataExporter(result.data, metadata=result.metadata)
            
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            exporter.to_json(output_dir / "filtered_products.json", pretty=True)
            exporter.to_csv(output_dir / "filtered_products.csv")
            exporter.to_markdown(output_dir / "filtered_products.md")
            
            print(f"📤 Exported to JSON, CSV, and Markdown")
            print(f"📁 Location: {output_dir.absolute()}")
            
            # Show results
            print("\n📊 Results:")
            for product in result.data:
                print(f"   • {product['title']} - {product['price']} zł (⭐ {product['rating']})")


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("🎯 Atomic Query & Export System Examples")
    print("=" * 60)
    
    try:
        # Run examples
        await example_basic_query()
        await example_product_query()
        await example_quick_functions()
        example_multi_format_export()
        await example_complete_workflow()
        
        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
