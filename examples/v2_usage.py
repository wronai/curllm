#!/usr/bin/env python3
"""
Example: Using CurLLM v2 API (LLM-driven, no hardcoded selectors)

This example shows how to use the new v2 API which uses LLM
for dynamic element detection instead of hardcoded selectors.
"""

import asyncio
from curllm_core.v2 import (
    # Core
    AtomicFunctions,
    DSLQueryGenerator,
    
    # Form filling
    llm_form_fill,
    LLMFormOrchestrator,
    
    # Other orchestrators
    LLMAuthOrchestrator,
    LLMExtractor,
)


async def example_form_fill():
    """Example: Fill a form using v2 LLM-driven approach."""
    from playwright.async_api import async_playwright
    from curllm_core import setup_llm
    
    llm = setup_llm()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://httpbin.org/forms/post")
        
        # v2 way: natural language instruction
        result = await llm_form_fill(
            instruction="Fill the form with customer name John Doe and email john@example.com",
            page=page,
            llm=llm,
        )
        
        print(f"Success: {result.success}")
        print(f"Filled fields: {result.filled_fields}")
        print(f"Submitted: {result.submitted}")
        
        await browser.close()


async def example_orchestrator():
    """Example: Use LLM orchestrator for form automation."""
    from playwright.async_api import async_playwright
    from curllm_core import setup_llm
    
    llm = setup_llm()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://example.com/contact")
        
        # v2 orchestrator
        orch = LLMFormOrchestrator(llm=llm, page=page)
        result = await orch.orchestrate(
            "Fill the contact form with my details: name=John, email=john@test.com, message=Hello"
        )
        
        print(f"Form result: {result}")
        
        await browser.close()


async def example_atomic_functions():
    """Example: Use atomic functions directly for fine-grained control."""
    from playwright.async_api import async_playwright
    from curllm_core import setup_llm
    
    llm = setup_llm()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://example.com")
        
        # AtomicFunctions provide low-level LLM-driven operations
        atoms = AtomicFunctions(page=page, llm=llm)
        
        # Find email field by context (no hardcoded selector!)
        result = await atoms.find_input_by_context("email address input field")
        if result.success:
            selector = result.data.get('selector')
            await page.fill(selector, "test@example.com")
        
        # Find submit button by intent
        result = await atoms.find_clickable_by_intent("submit the form")
        if result.success:
            await page.click(result.data.get('selector'))
        
        await browser.close()


async def example_extraction():
    """Example: Extract data using v2 LLM extractor."""
    from playwright.async_api import async_playwright
    from curllm_core import setup_llm
    
    llm = setup_llm()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://example.com/products")
        
        extractor = LLMExtractor(page=page, llm=llm)
        result = await extractor.extract(
            "Extract all product names and prices from this page"
        )
        
        print(f"Extracted: {result}")
        
        await browser.close()


def example_api_request():
    """Example: Use v2 via HTTP API."""
    import requests
    
    response = requests.post(
        "http://localhost:5000/api/execute",
        json={
            "url": "https://example.com/contact",
            "data": "Fill the contact form with name John and email john@test.com",
            "use_v2": True,  # Enable LLM-driven v2 API
        }
    )
    
    print(response.json())


if __name__ == "__main__":
    print("CurLLM v2 Examples")
    print("=" * 50)
    print()
    print("Available examples:")
    print("  1. example_form_fill() - LLM-driven form filling")
    print("  2. example_orchestrator() - Form orchestrator")
    print("  3. example_atomic_functions() - Low-level atomic functions")
    print("  4. example_extraction() - Data extraction")
    print("  5. example_api_request() - HTTP API with use_v2=True")
    print()
    print("Run with: asyncio.run(example_form_fill())")
