"""
Pytest configuration for integration tests
"""

import pytest
import os


def pytest_configure(config):
    """Configure pytest"""
    # Set test environment variables
    os.environ['CURLLM_TEST_MODE'] = 'true'
    os.environ['CURLLM_HEADLESS'] = 'true'
    
    # Set defaults if not provided
    if 'CURLLM_TEST_BASE_URL' not in os.environ:
        os.environ['CURLLM_TEST_BASE_URL'] = 'http://localhost:8080'
        
    if 'CURLLM_OLLAMA_HOST' not in os.environ:
        os.environ['CURLLM_OLLAMA_HOST'] = 'http://localhost:11434'


@pytest.fixture(scope="session")
def base_url():
    """Get base URL for test pages"""
    return os.getenv('CURLLM_TEST_BASE_URL', 'http://localhost:8080')


@pytest.fixture(scope="session")
def ollama_host():
    """Get Ollama host for LLM"""
    return os.getenv('CURLLM_OLLAMA_HOST', 'http://localhost:11434')


@pytest.fixture
async def browser_page():
    """Provide a browser page for tests"""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        yield page
        await browser.close()
