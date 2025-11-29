#!/usr/bin/env python3
"""
Product Extraction Example

Extract product data from e-commerce pages using curllm.
Supports multiple LLM providers via LLMConfig.
"""

import asyncio
import json
import os
from curllm_core import CurllmExecutor, LLMConfig


async def extract_products_basic(url: str):
    """Basic product extraction using default Ollama"""
    
    executor = CurllmExecutor()
    
    result = await executor.execute_workflow(
        instruction="Extract all products with name, price, and image URL",
        url=url
    )
    
    return result


async def extract_products_with_filter(url: str, max_price: float):
    """Extract products with price filter"""
    
    # Use OpenAI if available, otherwise Ollama
    if os.getenv("OPENAI_API_KEY"):
        llm_config = LLMConfig(provider="openai/gpt-4o-mini")
    else:
        llm_config = LLMConfig(provider="ollama/qwen2.5:7b")
    
    executor = CurllmExecutor(llm_config=llm_config)
    
    result = await executor.execute_workflow(
        instruction=f"Extract all products under ${max_price} with name, price, and URL",
        url=url
    )
    
    return result


async def extract_products_structured(url: str):
    """Extract products with structured schema"""
    
    executor = CurllmExecutor()
    
    # Define expected structure in instruction
    instruction = """
    Extract all products from this page. For each product, extract:
    - name: product title/name
    - price: numeric price value
    - currency: currency symbol or code
    - url: product link URL
    - image: product image URL
    - in_stock: boolean availability
    
    Return as JSON array.
    """
    
    result = await executor.execute_workflow(
        instruction=instruction,
        url=url
    )
    
    return result


async def main():
    """Run extraction examples"""
    
    # Example URL (replace with real URL)
    test_url = "https://example.com/products"
    
    print("=" * 50)
    print("Product Extraction Examples")
    print("=" * 50)
    
    # Example 1: Basic extraction
    print("\n📦 Basic Extraction:")
    result = await extract_products_basic(test_url)
    print(f"   Success: {result.get('success')}")
    if result.get('success'):
        print(f"   Products: {json.dumps(result.get('result'), indent=2)[:500]}...")
    
    # Example 2: With price filter
    print("\n💰 Filtered Extraction (under $100):")
    result = await extract_products_with_filter(test_url, 100.0)
    print(f"   Success: {result.get('success')}")


if __name__ == "__main__":
    asyncio.run(main())
