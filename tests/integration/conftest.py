"""
Pytest configuration for integration tests
"""

import pytest
import os
from pathlib import Path

_fixture_server = None

TEST_PAGES_DIR = Path(__file__).resolve().parents[1] / "test_pages"


def _start_fixture_server() -> str:
    """Serve tests/test_pages on a free loopback port for the session."""
    import http.server
    import functools
    import threading

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(TEST_PAGES_DIR)
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    global _fixture_server
    _fixture_server = server
    return f"http://127.0.0.1:{server.server_address[1]}"


def pytest_configure(config):
    """Configure pytest"""
    # Set test environment variables
    os.environ['CURLLM_TEST_MODE'] = 'true'
    os.environ['CURLLM_HEADLESS'] = 'true'

    # Without an explicit CURLLM_TEST_BASE_URL (docker-compose.test.yml sets
    # one), serve the local fixture pages ourselves so the suite is
    # self-contained instead of timing out against whatever squats on :8080.
    if 'CURLLM_TEST_BASE_URL' not in os.environ and TEST_PAGES_DIR.is_dir():
        os.environ['CURLLM_TEST_BASE_URL'] = _start_fixture_server()
    elif 'CURLLM_TEST_BASE_URL' not in os.environ:
        os.environ['CURLLM_TEST_BASE_URL'] = 'http://localhost:8080'

    if 'CURLLM_OLLAMA_HOST' not in os.environ:
        os.environ['CURLLM_OLLAMA_HOST'] = 'http://localhost:11434'


def pytest_unconfigure(config):
    global _fixture_server
    if _fixture_server is not None:
        _fixture_server.shutdown()
        _fixture_server = None


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
