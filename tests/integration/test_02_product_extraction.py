"""
Integration Test 2: Product Data Extraction

Tests extracting structured data from product listings using LLM-DSL.
"""

import pytest
from playwright.async_api import async_playwright
from curllm_core.streamware.llm_bridge import LLMDSLBridge
import os


@pytest.mark.asyncio
async def test_extract_products_via_llm_dsl():
    """Test extracting product data using LLM-DSL commands"""
    
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"{base_url}/02_product_list.html")
        
        bridge = LLMDSLBridge()
        
        # LLM Command: Extract all products
        extract_command = {
            "action": "extract_data",
            "type": "text",
            "page_context": {
                "url": page.url,
                "title": await page.title()
            }
        }
        
        result = bridge.execute_llm_command(extract_command)
        assert result['success'] is True
        
        # Verify products are on page
        products = await page.query_selector_all('.product')
        assert len(products) == 5
        
        # Extract product details using JavaScript
        product_data = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.product')).map(p => ({
                name: p.querySelector('h3').textContent,
                price: p.querySelector('.price').textContent,
                stock: p.querySelector('.stock').textContent
            }));
        }''')
        
        assert len(product_data) == 5
        assert any('Laptop' in p['name'] for p in product_data)
        assert any('$1,299.99' in p['price'] for p in product_data)
        
        await browser.close()


@pytest.mark.asyncio  
async def test_filter_products_by_price():
    """Test filtering products by price criteria"""
    
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"{base_url}/02_product_list.html")
        
        # Extract and filter products under $100
        products = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.product')).map(p => ({
                name: p.querySelector('h3').textContent,
                price: parseFloat(p.querySelector('.price').textContent.replace('$', '').replace(',', ''))
            })).filter(p => p.price < 100);
        }''')
        
        assert len(products) >= 2  # Mouse and USB-C Hub
        
        await browser.close()
