"""
Integration Tests 3-10: Comprehensive Testing Suite

Tests various automation scenarios using LLM-DSL Bridge.
"""

import pytest
from playwright.async_api import async_playwright
from curllm_core.streamware.llm_bridge import LLMDSLBridge
import os


@pytest.mark.asyncio
async def test_03_login_form():
    """Test 3: Login form automation"""
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"{base_url}/03_login_form.html")
        
        bridge = LLMDSLBridge()
        
        # LLM command for login flow
        login_command = {
            "action": "execute_flow",
            "steps": [
                {"component": "dom-snapshot", "params": {"include_values": True}},
                {"component": "action-plan", "params": {"strategy": "smart"}}
            ],
            "data": {
                "instruction": "Login with username=testuser, password=testpass"
            }
        }
        
        result = bridge.execute_llm_command(login_command)
        assert result['success'] is True
        
        # Fill credentials
        await page.fill('#username', 'testuser')
        await page.fill('#password', 'testpass')
        
        # Submit
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(500)
        
        await browser.close()


@pytest.mark.asyncio
async def test_04_registration_form():
    """Test 4: Multi-field registration form"""
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"{base_url}/04_registration.html")
        
        bridge = LLMDSLBridge()
        
        # Analyze form structure
        analyze_cmd = {
            "action": "analyze_form",
            "components": [{"type": "dom-analyze", "params": {"type": "forms"}}],
            "data": {}
        }
        
        result = bridge.execute_llm_command(analyze_cmd)
        assert result['success'] is True
        
        # Fill registration form
        await page.fill('input[name="firstName"]', 'John')
        await page.fill('input[name="lastName"]', 'Doe')
        await page.fill('input[name="email"]', 'john.doe@example.com')
        await page.fill('input[name="phone"]', '+1234567890')
        await page.select_option('select[name="country"]', 'US')
        await page.fill('input[name="password"]', 'SecurePass123')
        
        # Validate all fields filled
        values = await page.evaluate('''() => {
            const form = document.getElementById('registrationForm');
            const data = new FormData(form);
            return Object.fromEntries(data);
        }''')
        
        assert values['firstName'] == 'John'
        assert values['email'] == 'john.doe@example.com'
        
        await browser.close()


@pytest.mark.asyncio
async def test_05_search_results():
    """Test 5: Search results page navigation"""
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"{base_url}/05_search_results.html")
        
        # Extract search results
        results = await page.query_selector_all('.result')
        assert len(results) == 4
        
        # Get first result title
        first_title = await page.text_content('.result:first-child h3')
        assert 'Laptop' in first_title or 'Best' in first_title
        
        await browser.close()


@pytest.mark.asyncio
async def test_06_data_table():
    """Test 6: Data table extraction"""
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"{base_url}/06_data_table.html")
        
        bridge = LLMDSLBridge()
        
        # Extract table data via LLM command
        extract_cmd = {
            "action": "extract_data",
            "type": "text",
            "page_context": {"url": page.url}
        }
        
        result = bridge.execute_llm_command(extract_cmd)
        assert result['success'] is True
        
        # Verify table has 5 users
        rows = await page.query_selector_all('tbody tr')
        assert len(rows) == 5
        
        # Extract all user data
        users = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('tbody tr')).map(row => ({
                id: row.querySelector('td:nth-child(1)').textContent,
                name: row.querySelector('td:nth-child(2)').textContent,
                email: row.querySelector('td:nth-child(3)').textContent,
                role: row.querySelector('td:nth-child(4)').textContent
            }));
        }''')
        
        assert len(users) == 5
        assert any(u['name'] == 'John Doe' for u in users)
        
        await browser.close()


@pytest.mark.asyncio
async def test_07_newsletter_subscription():
    """Test 7: Newsletter subscription form"""
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"{base_url}/07_newsletter.html")
        
        # Fill newsletter form
        await page.fill('#email', 'newsletter@example.com')
        await page.check('input[name="weekly"]')
        await page.check('input[name="promotions"]')
        
        # Verify checkboxes
        is_weekly_checked = await page.is_checked('input[name="weekly"]')
        is_promo_checked = await page.is_checked('input[name="promotions"]')
        
        assert is_weekly_checked is True
        assert is_promo_checked is True
        
        await browser.close()


@pytest.mark.asyncio
async def test_08_multi_step_form():
    """Test 8: Multi-step form navigation"""
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"{base_url}/08_multi_step_form.html")
        
        bridge = LLMDSLBridge()
        
        # Step 1: Fill personal info
        await page.fill('input[name="fullName"]', 'Jane Doe')
        await page.fill('input[name="email"]', 'jane@example.com')
        await page.fill('input[name="phone"]', '+1234567890')
        
        # Navigate to step 2
        await page.click('.btn-next')
        await page.wait_for_timeout(300)
        
        # Verify step 2 is active
        step2_active = await page.is_visible('.step[data-step="2"].active')
        assert step2_active is True
        
        # Fill shipping info
        await page.fill('input[name="address"]', '123 Main St')
        await page.fill('input[name="city"]', 'New York')
        await page.fill('input[name="zipCode"]', '10001')
        await page.select_option('select[name="country"]', 'US')
        
        await browser.close()


@pytest.mark.asyncio
async def test_09_shopping_cart():
    """Test 9: Shopping cart interaction"""
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"{base_url}/09_ecommerce_cart.html")
        
        # Count cart items
        items = await page.query_selector_all('.cart-item')
        assert len(items) == 3
        
        # Extract cart data
        cart_data = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.cart-item')).map(item => ({
                product: item.getAttribute('data-product'),
                price: item.querySelector('.item-price').textContent,
                quantity: item.querySelector('input[type="number"]').value
            }));
        }''')
        
        assert len(cart_data) == 3
        assert any(item['product'] == 'laptop' for item in cart_data)
        
        await browser.close()


@pytest.mark.asyncio
async def test_10_feedback_form():
    """Test 10: Feedback form with rating"""
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"{base_url}/10_feedback_form.html")
        
        bridge = LLMDSLBridge()
        
        # Plan form filling via LLM
        plan_cmd = {
            "action": "plan_action",
            "instruction": "Fill feedback form with 5-star rating",
            "strategy": "smart"
        }
        
        result = bridge.execute_llm_command(plan_cmd)
        assert result['success'] is True
        
        # Fill feedback form
        await page.fill('input[name="name"]', 'Happy Customer')
        await page.fill('input[name="email"]', 'happy@example.com')
        await page.select_option('select[name="category"]', 'product')
        await page.check('#star5')  # 5-star rating
        await page.fill('textarea[name="feedback"]', 'Great product and service!')
        
        # Verify rating selected
        rating_checked = await page.is_checked('#star5')
        assert rating_checked is True
        
        # Verify all fields filled
        name_value = await page.input_value('input[name="name"]')
        assert name_value == 'Happy Customer'
        
        await browser.close()
