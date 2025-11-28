"""
Integration Test 2: Product Data Extraction

Tests extracting structured data from product listings using LLM-DSL.
Uses sync Playwright API for compatibility with sync DSL components.
"""

import pytest
from playwright.sync_api import sync_playwright
from curllm_core.streamware.llm_bridge import LLMDSLBridge
import os


def test_extract_products_via_llm_dsl():
    """Test extracting product data using LLM-DSL commands"""
    
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto(f"{base_url}/02_product_list.html")
        
        bridge = LLMDSLBridge()
        
        # LLM Command: Extract all products
        extract_command = {
            "action": "extract_data",
            "type": "text",
            "page_context": {
                "url": page.url,
                "title": page.title()
            }
        }
        
        result = bridge.execute_llm_command(extract_command)
        assert result['success'] is True
        
        # Verify products are on page
        products = page.query_selector_all('.product')
        assert len(products) == 5
        
        # Extract product details using JavaScript
        product_data = page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.product')).map(p => ({
                name: p.querySelector('h3').textContent,
                price: p.querySelector('.price').textContent,
                stock: p.querySelector('.stock').textContent
            }));
        }''')
        
        assert len(product_data) == 5
        assert any('Laptop' in p['name'] for p in product_data)
        assert any('$1,299.99' in p['price'] for p in product_data)
        
        browser.close()


def test_filter_products_by_price():
    """Test filtering products by price criteria"""
    
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto(f"{base_url}/02_product_list.html")
        
        # Extract and filter products under $100
        products = page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.product')).map(p => ({
                name: p.querySelector('h3').textContent,
                price: parseFloat(p.querySelector('.price').textContent.replace('$', '').replace(',', ''))
            })).filter(p => p.price < 100);
        }''')
        
        assert len(products) >= 2  # Mouse and USB-C Hub
        
        browser.close()
