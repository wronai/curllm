"""
Integration Tests for Specialized Orchestrators

Tests all orchestrator types:
- MasterOrchestrator (task routing)
- FormOrchestrator (form filling)
- ExtractionOrchestrator (data extraction)
- ECommerceOrchestrator (shopping tasks)
- LiveInteractionOrchestrator (UI interactions)
"""

import pytest
import os
from playwright.sync_api import sync_playwright


# Get base URL from environment
BASE_URL = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')


class TestMasterOrchestrator:
    """Test task type detection and routing"""
    
    def test_detect_form_task(self):
        """Test form task detection"""
        from curllm_core.orchestrators.master import MasterOrchestrator, TaskType
        
        orch = MasterOrchestrator()
        
        # Form-related instructions should be detected
        form_instructions = [
            "Fill the contact form with name=John",
            "Submit the registration form",
            "Login with username=test",
            "Wypełnij formularz kontaktowy"
        ]
        
        for instr in form_instructions:
            analysis = orch._detect_by_keywords(instr)
            assert analysis.task_type == TaskType.FORM_FILL, f"Failed for: {instr}"
    
    def test_detect_extraction_task(self):
        """Test extraction task detection"""
        from curllm_core.orchestrators.master import MasterOrchestrator, TaskType
        
        orch = MasterOrchestrator()
        
        extraction_instructions = [
            "Extract all product prices",
            "Get links from the page",
            "Find all email addresses",
            "Scrape article titles"
        ]
        
        for instr in extraction_instructions:
            analysis = orch._detect_by_keywords(instr)
            assert analysis.task_type == TaskType.EXTRACTION, f"Failed for: {instr}"
    
    def test_detect_ecommerce_task(self):
        """Test e-commerce task detection"""
        from curllm_core.orchestrators.master import MasterOrchestrator, TaskType
        
        orch = MasterOrchestrator()
        
        ecommerce_instructions = [
            "Add product to cart",
            "Proceed to checkout",
            "Buy laptop under 1000zł",
            "Dodaj do koszyka"
        ]
        
        for instr in ecommerce_instructions:
            analysis = orch._detect_by_keywords(instr)
            assert analysis.task_type == TaskType.ECOMMERCE, f"Failed for: {instr}"
    
    def test_detect_live_interaction_task(self):
        """Test live interaction task detection"""
        from curllm_core.orchestrators.master import MasterOrchestrator, TaskType
        
        orch = MasterOrchestrator()
        
        live_instructions = [
            "Click the submit button",
            "Scroll down 3 times",
            "Hover over the menu",
            "Type hello in the input"
        ]
        
        for instr in live_instructions:
            analysis = orch._detect_by_keywords(instr)
            assert analysis.task_type == TaskType.LIVE_INTERACTION, f"Failed for: {instr}"


class TestFormOrchestrator:
    """Test form filling orchestrator"""
    
    def test_parse_form_data_from_instruction(self):
        """Test parsing form data from instruction"""
        from curllm_core.orchestrators.form import FormOrchestrator
        
        orch = FormOrchestrator()
        
        instruction = "Fill form with name=John Doe, email=john@example.com, message=Hello world"
        data = orch._parse_form_data(instruction)
        
        assert 'name' in data
        assert 'email' in data
        assert 'message' in data
        assert 'John Doe' in data['name']
    
    def test_form_fill_with_browser(self):
        """Test actual form filling in browser"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"{BASE_URL}/01_simple_form.html")
            
            # Fill form manually (simulating orchestrator)
            page.fill('#name', 'Test User')
            page.fill('#email', 'test@example.com')
            page.fill('#message', 'This is a test message')
            page.check('#consent')
            
            # Verify fields are filled
            assert page.input_value('#name') == 'Test User'
            assert page.input_value('#email') == 'test@example.com'
            assert page.is_checked('#consent')
            
            browser.close()


class TestExtractionOrchestrator:
    """Test data extraction orchestrator"""
    
    def test_detect_extraction_type(self):
        """Test extraction type detection"""
        from curllm_core.orchestrators.extraction import ExtractionOrchestrator
        
        orch = ExtractionOrchestrator()
        
        assert orch._detect_extraction_type("Extract product prices") == 'products'
        assert orch._detect_extraction_type("Get all links") == 'links'
        assert orch._detect_extraction_type("Find email addresses") == 'emails'
        assert orch._detect_extraction_type("Scrape article titles") == 'articles'
    
    def test_parse_constraints(self):
        """Test constraint parsing"""
        from curllm_core.orchestrators.extraction import ExtractionOrchestrator
        
        orch = ExtractionOrchestrator()
        
        constraints = orch._parse_constraints("Get products under 150zł")
        assert constraints.get('max_price') == 150
        
        constraints = orch._parse_constraints("First 10 results")
        assert constraints.get('max_count') == 10
    
    def test_product_extraction(self):
        """Test product extraction from page"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"{BASE_URL}/02_products.html")
            
            # Extract products via JavaScript
            products = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('.product')).map(el => ({
                    name: el.querySelector('.product-name')?.textContent,
                    price: el.dataset.price
                }));
            }''')
            
            assert len(products) >= 5
            assert all(p['name'] for p in products)
            
            browser.close()


class TestECommerceOrchestrator:
    """Test e-commerce orchestrator"""
    
    def test_parse_shopping_intent(self):
        """Test shopping intent parsing"""
        from curllm_core.orchestrators.ecommerce import ECommerceOrchestrator
        
        orch = ECommerceOrchestrator()
        
        intent = orch._parse_shopping_intent("Add laptop to cart")
        assert intent['action'] == 'add_to_cart'
        
        intent = orch._parse_shopping_intent("Proceed to checkout with BLIK")
        assert intent['action'] == 'checkout'
        assert intent['payment_method'] == 'blik'
    
    def test_cart_interaction(self):
        """Test cart page interaction"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"{BASE_URL}/09_ecommerce_cart.html")
            
            # Count cart items
            items = page.query_selector_all('.cart-item')
            assert len(items) == 3
            
            # Get cart data
            cart_data = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('.cart-item')).map(item => ({
                    product: item.dataset.product,
                    quantity: item.querySelector('input')?.value
                }));
            }''')
            
            assert len(cart_data) == 3
            assert any(item['product'] == 'laptop' for item in cart_data)
            
            browser.close()


class TestLiveInteractionOrchestrator:
    """Test live interaction orchestrator"""
    
    def test_parse_click_action(self):
        """Test click action parsing"""
        from curllm_core.orchestrators.live import LiveInteractionOrchestrator, ActionType
        
        orch = LiveInteractionOrchestrator()
        
        action = orch._parse_single_action("click on Submit button")
        assert action['type'] == ActionType.CLICK.value
        assert 'submit' in action['target'].lower()
    
    def test_parse_type_action(self):
        """Test type action parsing"""
        from curllm_core.orchestrators.live import LiveInteractionOrchestrator, ActionType
        
        orch = LiveInteractionOrchestrator()
        
        action = orch._parse_single_action("type 'hello world' in search box")
        assert action['type'] == ActionType.TYPE.value
        assert action['value'] == 'hello world'
    
    def test_parse_scroll_action(self):
        """Test scroll action parsing"""
        from curllm_core.orchestrators.live import LiveInteractionOrchestrator, ActionType
        
        orch = LiveInteractionOrchestrator()
        
        action = orch._parse_single_action("scroll down 5 times")
        assert action['type'] == ActionType.SCROLL.value
        assert action['direction'] == 'down'
        assert action['amount'] == 5
    
    def test_interactive_elements(self):
        """Test interaction with page elements"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"{BASE_URL}/11_interactive.html")
            
            # Click button
            page.click('.btn-primary')
            output = page.text_content('#output')
            assert 'Primary clicked' in output or 'action' in output.lower()
            
            # Open and close modal
            page.click('button:has-text("Open Modal")')
            assert page.is_visible('#modal')
            
            page.click('.modal-content button')
            page.wait_for_timeout(300)
            
            browser.close()


class TestValidationSystem:
    """Test the multi-strategy validation system"""
    
    def test_structural_validator(self):
        """Test structural validation"""
        import asyncio
        from curllm_core.validation.structural import StructuralValidator
        
        validator = StructuralValidator()
        
        # Test with successful form result
        result = {
            'success': True,
            'form_fill': {
                'submitted': True,
                'filled': {'name': 'John', 'email': 'john@test.com'},
                'errors': {}
            }
        }
        
        check = asyncio.run(validator.validate(
            instruction="Fill the form",
            result=result
        ))
        
        assert check.passed
        assert check.score >= 0.6
    
    def test_rule_validator(self):
        """Test rule-based validation"""
        import asyncio
        from curllm_core.validation.rules import RuleValidator
        
        validator = RuleValidator()
        
        # Test with extraction result
        result = {
            'products': [
                {'name': 'Product 1', 'price': '99 zł'},
                {'name': 'Product 2', 'price': '149 zł'}
            ]
        }
        
        check = asyncio.run(validator.validate(
            instruction="Extract products",
            result=result
        ))
        
        assert check.passed
        assert 'extraction_not_empty' in [r for r in check.details.get('passed_rules', [])]


class TestMultiStepWorkflow:
    """Test multi-step form workflow"""
    
    def test_multi_step_navigation(self):
        """Test navigating through multi-step form"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"{BASE_URL}/08_multi_step_form.html")
            
            # Verify step 1 is active
            assert page.is_visible('[data-section="1"].active')
            
            # Fill step 1
            page.fill('input[name="fullName"]', 'Test User')
            page.fill('input[name="email"]', 'test@example.com')
            
            # Go to step 2
            page.click('.btn-next')
            page.wait_for_timeout(300)
            
            # Verify step 2 is active
            assert page.is_visible('[data-section="2"].active')
            
            browser.close()


class TestFormValidation:
    """Test form validation detection"""
    
    def test_validation_states(self):
        """Test detecting validation states"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"{BASE_URL}/12_validation_test.html")
            
            # Type invalid username
            page.fill('#username', 'ab')  # Too short
            page.dispatch_event('#username', 'input')
            
            # Should show error
            has_error = page.evaluate('''() => {
                return document.getElementById('username').classList.contains('error');
            }''')
            assert has_error
            
            # Type valid username
            page.fill('#username', 'validuser')
            page.dispatch_event('#username', 'input')
            
            # Should show valid
            has_valid = page.evaluate('''() => {
                return document.getElementById('username').classList.contains('valid');
            }''')
            assert has_valid
            
            browser.close()

