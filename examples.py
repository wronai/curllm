#!/usr/bin/env python3
"""
examples.py - Example usage of curllm for various automation tasks
"""

import asyncio
import json
from curllm_core import CurllmExecutor

async def example_simple_extraction():
    """Example: Extract data from a webpage"""
    print("=== Simple Data Extraction ===")
    
    executor = CurllmExecutor()
    result = await executor.execute_workflow(
        instruction="Extract all email addresses and phone numbers",
        url="https://example.com/contact",
        visual_mode=False
    )
    
    print(f"Result: {json.dumps(result, indent=2)}")

async def example_form_automation():
    """Example: Fill and submit a form"""
    print("\n=== Form Automation ===")
    
    executor = CurllmExecutor()
    result = await executor.execute_workflow(
        instruction=json.dumps({
            "task": "fill_form",
            "fields": {
                "name": "John Doe",
                "email": "john@example.com",
                "message": "This is an automated test message"
            },
            "submit": True
        }),
        url="https://example.com/contact-form",
        visual_mode=True,
        stealth_mode=True
    )
    
    print(f"Form submitted: {result['success']}")

async def example_login_2fa():
    """Example: Login with 2FA"""
    print("\n=== Login with 2FA ===")
    
    executor = CurllmExecutor()
    result = await executor.execute_workflow(
        instruction=json.dumps({
            "workflow": [
                {"action": "navigate", "url": "https://secure-app.com"},
                {"action": "fill", "selector": "#username", "value": "user@example.com"},
                {"action": "fill", "selector": "#password", "value": "SecretPass123"},
                {"action": "click", "selector": "#login-btn"},
                {"action": "wait", "duration": 2000},
                {"action": "fill", "selector": "#2fa-code", "value": "123456"},
                {"action": "click", "selector": "#verify-btn"}
            ]
        }),
        visual_mode=True,
        captcha_solver=True
    )
    
    print(f"Login successful: {result['success']}")

async def example_bql_query():
    """Example: Use BQL for structured extraction"""
    print("\n=== BQL Query Example ===")
    
    executor = CurllmExecutor()
    
    bql_query = """
    query ProductCatalog {
        page(url: "https://shop.example.com/products") {
            products: select(css: ".product-card") {
                name: text(css: ".product-title")
                price: text(css: ".product-price")
                image: attr(css: "img", name: "src")
                inStock: text(css: ".availability")
            }
        }
    }
    """
    
    result = await executor.execute_workflow(
        instruction=bql_query,
        use_bql=True,
        visual_mode=False
    )
    
    print(f"Products found: {len(result.get('result', {}).get('products', []))}")

async def example_captcha_solving():
    """Example: Handle CAPTCHA"""
    print("\n=== CAPTCHA Solving ===")
    
    executor = CurllmExecutor()
    result = await executor.execute_workflow(
        instruction="Fill the form and solve CAPTCHA if present",
        url="https://example.com/protected-form",
        visual_mode=True,
        captcha_solver=True,
        stealth_mode=True
    )
    
    print(f"CAPTCHA solved: {result['success']}")

async def example_pdf_download():
    """Example: Navigate and download PDF"""
    print("\n=== PDF Download ===")
    
    executor = CurllmExecutor()
    result = await executor.execute_workflow(
        instruction=json.dumps({
            "task": "download_report",
            "steps": [
                "Login with credentials",
                "Navigate to Reports section",
                "Select Q4 2024 report",
                "Download PDF"
            ],
            "credentials": {
                "username": "john.doe",
                "password": "SecretPass"
            }
        }),
        url="https://portal.example.com",
        visual_mode=True
    )
    
    print(f"PDF downloaded: {result['success']}")

async def example_price_monitoring():
    """Example: Monitor product prices"""
    print("\n=== Price Monitoring ===")
    
    executor = CurllmExecutor()
    
    products = [
        "https://amazon.com/dp/B08N5WRWNW",
        "https://bestbuy.com/product/6451599",
        "https://newegg.com/p/N82E16814137632"
    ]
    
    for product_url in products:
        result = await executor.execute_workflow(
            instruction="Extract product name and current price",
            url=product_url,
            stealth_mode=True
        )
        
        if result['success']:
            data = result.get('result', {})
            print(f"Product: {data.get('name')} - Price: {data.get('price')}")

async def example_social_media_scraping():
    """Example: Scrape social media profiles"""
    print("\n=== Social Media Scraping ===")
    
    executor = CurllmExecutor()
    result = await executor.execute_workflow(
        instruction="""
        Extract from the profile:
        1. Name
        2. Bio/Description
        3. Number of followers
        4. Recent posts (last 5)
        5. Contact information if available
        """,
        url="https://twitter.com/example_user",
        visual_mode=True,
        stealth_mode=True
    )
    
    print(f"Profile data extracted: {result['success']}")

async def example_table_extraction():
    """Example: Extract tables to CSV"""
    print("\n=== Table Extraction ===")
    
    executor = CurllmExecutor()
    
    bql_query = """
    query FinancialData {
        page(url: "https://finance.example.com/stocks") {
            table: select(css: "table.stock-data") {
                headers: select(css: "thead th") { text }
                rows: select(css: "tbody tr") {
                    cells: select(css: "td") { text }
                }
            }
        }
    }
    """
    
    result = await executor.execute_workflow(
        instruction=bql_query,
        use_bql=True
    )
    
    # Convert to CSV format
    if result['success']:
        table_data = result.get('result', {}).get('table', [])
        print(f"Table extracted with {len(table_data)} rows")

async def example_multi_step_workflow():
    """Example: Complex multi-step workflow"""
    print("\n=== Multi-Step Workflow ===")
    
    executor = CurllmExecutor()
    
    workflow = {
        "name": "E-commerce Order Processing",
        "steps": [
            {
                "name": "Login",
                "url": "https://shop.example.com/login",
                "actions": [
                    {"fill": "#email", "value": "buyer@example.com"},
                    {"fill": "#password", "value": "BuyerPass123"},
                    {"click": "#login-submit"}
                ]
            },
            {
                "name": "Search Product",
                "actions": [
                    {"fill": "#search-box", "value": "wireless headphones"},
                    {"click": "#search-btn"},
                    {"wait": 2000}
                ]
            },
            {
                "name": "Add to Cart",
                "actions": [
                    {"click": ".product-card:first-child .add-to-cart"},
                    {"wait": 1000}
                ]
            },
            {
                "name": "Checkout",
                "actions": [
                    {"click": "#cart-icon"},
                    {"click": "#checkout-btn"},
                    {"fill": "#card-number", "value": "4111111111111111"},
                    {"fill": "#card-exp", "value": "12/25"},
                    {"fill": "#card-cvv", "value": "123"},
                    {"click": "#place-order"}
                ]
            }
        ]
    }
    
    result = await executor.execute_workflow(
        instruction=json.dumps(workflow),
        visual_mode=True,
        stealth_mode=True,
        captcha_solver=True
    )
    
    print(f"Workflow completed: {result['success']}")
    print(f"Total steps: {result.get('steps_taken', 0)}")

# Performance testing
async def benchmark_models():
    """Benchmark different models"""
    print("\n=== Model Benchmarking ===")
    
    models = [
        "qwen2.5:7b",
        "mistral:7b-instruct",
        "llama3.2:3b",
        "phi3:mini"
    ]
    
    test_instruction = "Navigate to page, extract title and first paragraph"
    test_url = "https://example.com"
    
    for model in models:
        print(f"\nTesting model: {model}")
        
        import time
        start = time.time()
        
        executor = CurllmExecutor()
        executor.config.ollama_model = model
        
        result = await executor.execute_workflow(
            instruction=test_instruction,
            url=test_url
        )
        
        elapsed = time.time() - start
        
        print(f"  Success: {result['success']}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Steps: {result.get('steps_taken', 0)}")

async def main():
    """Run all examples"""
    
    examples = [
        example_simple_extraction,
        example_form_automation,
        example_bql_query,
        example_price_monitoring,
        example_table_extraction,
        example_multi_step_workflow
    ]
    
    print("="*50)
    print("curllm Examples - Browser Automation with Local LLM")
    print("="*50)
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
        
        print("\n" + "-"*50)
    
    # Run benchmark
    await benchmark_models()

if __name__ == "__main__":
    asyncio.run(main())
