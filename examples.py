#!/usr/bin/env python3
"""
examples.py - Example usage of curllm for various automation tasks

curllm supports multiple LLM providers via litellm:
- ollama: Local Ollama server (default) - ollama/qwen2.5:7b, ollama/llama3
- openai: OpenAI API - openai/gpt-4o-mini, openai/gpt-4o, openai/o1-mini, openai/o3-mini
- anthropic: Anthropic - anthropic/claude-3-haiku-20240307, anthropic/claude-3-5-sonnet-20240620
- gemini: Google Gemini - gemini/gemini-2.0-flash, gemini/gemini-1.5-pro
- groq: Groq (fast inference) - groq/llama3-70b-8192, groq/llama3-8b-8192
- deepseek: DeepSeek - deepseek/deepseek-chat

API tokens are automatically read from environment variables:
- OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, DEEPSEEK_API_KEY

Usage:
    # Quick start with default provider (ollama)
    curllm "https://example.com" -d "Extract all links"
    
    # Use specific provider
    CURLLM_LLM_PROVIDER=openai/gpt-4o-mini curllm "https://example.com" -d "Extract data"
"""

import asyncio
import json
import os
from curllm_core import CurllmExecutor, LLMConfig, LLMPresets


# ============================================================
# QUICK START EXAMPLES - Minimal code to get started
# ============================================================

async def quick_extract():
    """Simplest extraction example"""
    executor = CurllmExecutor()
    result = await executor.execute_workflow(
        instruction="Extract page title and all links",
        url="https://example.com"
    )
    return result


async def quick_extract_with_provider():
    """Quick extraction with specific LLM provider"""
    # Provider auto-detects API key from environment
    executor = CurllmExecutor(
        llm_config=LLMConfig(provider="openai/gpt-4o-mini")
    )
    result = await executor.execute_workflow(
        instruction="Extract all product names and prices",
        url="https://example.com/products"
    )
    return result

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
        page(url: "https://ceneo.pl") {
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

# ============================================================
# LLM PROVIDER EXAMPLES
# ============================================================

async def example_with_openai():
    """Example: Using OpenAI as LLM provider"""
    print("\n=== OpenAI Provider Example ===")
    
    # Method 1: Direct configuration
    llm_config = LLMConfig(
        provider="openai/gpt-4o-mini",
        api_token=os.getenv("OPENAI_API_KEY"),  # Or set api_token directly
        temperature=0.3
    )
    
    executor = CurllmExecutor(llm_config=llm_config)
    result = await executor.execute_workflow(
        instruction="Extract the page title and main heading",
        url="https://example.com",
    )
    
    print(f"Result: {json.dumps(result.get('result'), indent=2)}")


async def example_with_anthropic():
    """Example: Using Anthropic Claude as LLM provider"""
    print("\n=== Anthropic Provider Example ===")
    
    # API token will be read from ANTHROPIC_API_KEY environment variable
    llm_config = LLMConfig(
        provider="anthropic/claude-3-haiku-20240307",
        temperature=0.2
    )
    
    executor = CurllmExecutor(llm_config=llm_config)
    result = await executor.execute_workflow(
        instruction="Extract all links from the page",
        url="https://example.com",
    )
    
    print(f"Result: {json.dumps(result.get('result'), indent=2)}")


async def example_with_gemini():
    """Example: Using Google Gemini as LLM provider"""
    print("\n=== Gemini Provider Example ===")
    
    # API token will be read from GEMINI_API_KEY environment variable
    llm_config = LLMConfig(
        provider="gemini/gemini-2.0-flash",
        temperature=0.3
    )
    
    executor = CurllmExecutor(llm_config=llm_config)
    result = await executor.execute_workflow(
        instruction="Summarize the page content",
        url="https://example.com",
    )
    
    print(f"Result: {json.dumps(result.get('result'), indent=2)}")


async def example_with_groq():
    """Example: Using Groq (fast cloud Llama) as LLM provider"""
    print("\n=== Groq Provider Example ===")
    
    # Groq offers fast inference for open source models
    llm_config = LLMConfig(
        provider="groq/llama3-70b-8192",
        # api_token="env:GROQ_API_KEY"  # Alternative: specify env var explicitly
    )
    
    executor = CurllmExecutor(llm_config=llm_config)
    result = await executor.execute_workflow(
        instruction="Extract product information",
        url="https://example.com",
    )
    
    print(f"Result: {json.dumps(result.get('result'), indent=2)}")


async def example_with_deepseek():
    """Example: Using DeepSeek as LLM provider"""
    print("\n=== DeepSeek Provider Example ===")
    
    llm_config = LLMConfig(
        provider="deepseek/deepseek-chat",
        temperature=0.3
    )
    
    executor = CurllmExecutor(llm_config=llm_config)
    result = await executor.execute_workflow(
        instruction="Extract the main content",
        url="https://example.com",
    )
    
    print(f"Result: {json.dumps(result.get('result'), indent=2)}")


async def example_with_presets():
    """Example: Using LLMPresets for quick configuration"""
    print("\n=== LLM Presets Example ===")
    
    # Available presets:
    # - LLMPresets.local_fast()      - Fast local Ollama model
    # - LLMPresets.local_balanced()  - Balanced local model (default)
    # - LLMPresets.local_smart()     - Smart local model for complex tasks
    # - LLMPresets.openai_fast()     - Fast OpenAI model (gpt-4o-mini)
    # - LLMPresets.openai_smart()    - Smart OpenAI model (gpt-4o)
    # - LLMPresets.anthropic_fast()  - Fast Claude model
    # - LLMPresets.anthropic_smart() - Smart Claude model
    # - LLMPresets.gemini_fast()     - Fast Gemini model
    # - LLMPresets.groq_fast()       - Fast Groq model
    # - LLMPresets.groq_smart()      - Smart Groq model
    # - LLMPresets.deepseek()        - DeepSeek model
    
    # Use a preset
    executor = CurllmExecutor(llm_config=LLMPresets.openai_fast())
    
    result = await executor.execute_workflow(
        instruction="Extract page title",
        url="https://example.com",
    )
    
    print(f"Result: {json.dumps(result.get('result'), indent=2)}")


async def example_env_based_config():
    """Example: Configuration from environment variables"""
    print("\n=== Environment-based Configuration ===")
    
    # Set environment variables:
    # CURLLM_LLM_PROVIDER=openai/gpt-4o-mini
    # OPENAI_API_KEY=sk-...
    
    # LLMConfig.from_env() reads these automatically
    llm_config = LLMConfig.from_env()
    print(f"Provider: {llm_config.provider_name}/{llm_config.model_name}")
    print(f"Has API token: {llm_config.resolved_api_token is not None}")
    
    executor = CurllmExecutor(llm_config=llm_config)
    result = await executor.execute_workflow(
        instruction="Extract page title",
        url="https://example.com",
    )
    
    print(f"Result: {json.dumps(result.get('result'), indent=2)}")


# Performance testing
async def benchmark_providers():
    """Benchmark different LLM providers"""
    print("\n=== Provider Benchmarking ===")
    
    import time
    
    # Define providers to test (only test those with API keys set)
    providers = []
    
    # Always test local Ollama
    providers.append(("ollama/qwen2.5:7b", LLMConfig(provider="ollama/qwen2.5:7b")))
    
    # Test cloud providers if API keys are set
    if os.getenv("OPENAI_API_KEY"):
        providers.append(("openai/gpt-4o-mini", LLMConfig(provider="openai/gpt-4o-mini")))
    
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append(("anthropic/claude-3-haiku", LLMConfig(provider="anthropic/claude-3-haiku-20240307")))
    
    if os.getenv("GEMINI_API_KEY"):
        providers.append(("gemini/gemini-2.0-flash", LLMConfig(provider="gemini/gemini-2.0-flash")))
    
    if os.getenv("GROQ_API_KEY"):
        providers.append(("groq/llama3-8b", LLMConfig(provider="groq/llama3-8b-8192")))
    
    if os.getenv("DEEPSEEK_API_KEY"):
        providers.append(("deepseek/deepseek-chat", LLMConfig(provider="deepseek/deepseek-chat")))
    
    test_instruction = "Navigate to page, extract title and first paragraph"
    test_url = "https://example.com"
    
    results = []
    for name, llm_config in providers:
        print(f"\nTesting: {name}")
        
        try:
            start = time.time()
            
            executor = CurllmExecutor(llm_config=llm_config)
            result = await executor.execute_workflow(
                instruction=test_instruction,
                url=test_url
            )
            
            elapsed = time.time() - start
            
            results.append({
                "provider": name,
                "success": result['success'],
                "time": elapsed,
                "steps": result.get('steps_taken', 0)
            })
            
            print(f"  Success: {result['success']}")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Steps: {result.get('steps_taken', 0)}")
            
        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                "provider": name,
                "success": False,
                "error": str(e)
            })
    
    print("\n=== Benchmark Summary ===")
    for r in results:
        status = "✅" if r.get("success") else "❌"
        time_str = f"{r.get('time', 0):.2f}s" if 'time' in r else "N/A"
        print(f"  {status} {r['provider']}: {time_str}")

async def main():
    """Run all examples"""
    
    # Basic automation examples
    basic_examples = [
        example_simple_extraction,
        example_form_automation,
        example_bql_query,
        example_price_monitoring,
        example_table_extraction,
        example_multi_step_workflow
    ]
    
    # LLM provider examples (require API keys)
    provider_examples = [
        example_env_based_config,  # Works with any config
        # Uncomment below if you have API keys set:
        # example_with_openai,
        # example_with_anthropic,
        # example_with_gemini,
        # example_with_groq,
        # example_with_deepseek,
        # example_with_presets,
    ]
    
    print("="*60)
    print("curllm Examples - Browser Automation with Multi-Provider LLM")
    print("="*60)
    print("\nSupported providers: ollama, openai, anthropic, gemini, groq, deepseek")
    print()
    
    print("\n" + "="*60)
    print("BASIC EXAMPLES")
    print("="*60)
    
    for example in basic_examples:
        try:
            await example()
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
        
        print("\n" + "-"*50)
    
    print("\n" + "="*60)
    print("LLM PROVIDER EXAMPLES")
    print("="*60)
    
    for example in provider_examples:
        try:
            await example()
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
        
        print("\n" + "-"*50)
    
    # Run provider benchmark
    await benchmark_providers()


if __name__ == "__main__":
    asyncio.run(main())
