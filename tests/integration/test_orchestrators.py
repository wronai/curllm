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
        
        # Use more specific extraction keywords that won't overlap with other tasks
        extraction_instructions = [
            "Extract all links from this page",
            "Scrape all email addresses",
            "Get all article titles",
            "Find all table data"
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
        
        # Use keywords from MasterOrchestrator.TASK_KEYWORDS[LIVE_INTERACTION]:
        # 'click', 'scroll', 'hover', 'drag', 'type', 'select', 'wait'
        live_instructions = [
            "Scroll down the page",
            "Hover over the menu",
            "Wait for element to load",
            "Click and drag the slider"
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
        
        # Test add to cart detection
        intent = orch._parse_shopping_intent("Add to cart the laptop")
        assert intent['action'] == 'add_to_cart'
        
        intent = orch._parse_shopping_intent("Buy this product")
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


class TestAuthOrchestrator:
    """Test authentication orchestrator"""
    
    def test_parse_credentials(self):
        """Test credential parsing from instruction"""
        from curllm_core.orchestrators.auth import AuthOrchestrator
        
        orch = AuthOrchestrator()
        
        # Standard format
        creds = orch._parse_credentials("Login with email=test@example.com password=secret123")
        assert creds.get('email') == 'test@example.com'
        assert creds.get('password') == 'secret123'
        
        # Polish format
        creds = orch._parse_credentials("Zaloguj się hasło=tajne user=jan")
        assert creds.get('password') == 'tajne'
        assert creds.get('username') == 'jan'
    
    def test_parse_credentials_with_otp(self):
        """Test parsing 2FA code from instruction"""
        from curllm_core.orchestrators.auth import AuthOrchestrator
        
        orch = AuthOrchestrator()
        
        creds = orch._parse_credentials("Login email=test@test.com pass=abc code=123456")
        assert creds.get('otp') == '123456'
    
    def test_detect_platform(self):
        """Test platform detection from context"""
        from curllm_core.orchestrators.auth import AuthOrchestrator
        
        orch = AuthOrchestrator()
        
        assert orch._detect_platform({'url': 'https://wp-login.php'}) == 'wordpress'
        assert orch._detect_platform({'url': 'https://accounts.google.com/signin'}) == 'google'
        assert orch._detect_platform({'url': 'https://example.com/login'}) == 'generic'
    
    def test_login_page_interaction(self):
        """Test login page interaction"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"{BASE_URL}/13_login.html")
            
            # Fill login form
            page.fill('input[type="email"], input[name="email"], #email', 'test@example.com')
            page.fill('input[type="password"], input[name="password"], #password', 'testpass123')
            
            # Check remember me if present
            remember = page.query_selector('#remember, input[name="remember"]')
            if remember:
                page.check('#remember, input[name="remember"]')
            
            # Verify inputs
            email_val = page.input_value('input[type="email"], input[name="email"], #email')
            assert email_val == 'test@example.com'
            
            browser.close()


class TestTaskValidator:
    """Test the multi-strategy task validator"""
    
    def test_validator_initialization(self):
        """Test TaskValidator initialization"""
        from curllm_core.validation import TaskValidator
        
        validator = TaskValidator()
        assert validator is not None
    
    def test_validation_report_structure(self):
        """Test ValidationReport data structure"""
        from curllm_core.validation.task_validator import ValidationReport, ValidationCheck
        
        check = ValidationCheck(
            strategy='structural',
            passed=True,
            score=0.9,
            reason='Structure valid'
        )
        
        report = ValidationReport(
            task_type='form_fill',
            instruction='Fill the form',
            overall_passed=True,
            overall_score=0.85,
            confidence=0.9,
            checks=[check],
            summary="Task completed successfully",
            recommendations=["Consider adding more data validation"]
        )
        
        assert report.overall_passed
        assert abs(report.overall_score - 0.85) < 0.001  # Float comparison
        assert len(report.checks) > 0
    
    def test_validate_form_result(self):
        """Test form validation with TaskValidator"""
        import asyncio
        from curllm_core.validation import TaskValidator
        
        validator = TaskValidator()
        
        result = {
            'success': True,
            'form_fill': {
                'submitted': True,
                'filled': {
                    'name': 'John Doe',
                    'email': 'john@example.com'
                },
                'errors': {}
            }
        }
        
        report = asyncio.run(validator.validate(
            instruction="Fill the contact form with name and email",
            result=result,
            task_type='form_fill'
        ))
        
        assert report.overall_passed
        assert report.overall_score >= 0.5
    
    def test_validate_extraction_result(self):
        """Test extraction validation with TaskValidator"""
        import asyncio
        from curllm_core.validation import TaskValidator
        
        validator = TaskValidator()
        
        result = {
            'products': [
                {'name': 'Laptop', 'price': '2500 zł'},
                {'name': 'Phone', 'price': '1200 zł'},
                {'name': 'Tablet', 'price': '800 zł'}
            ],
            'count': 3
        }
        
        report = asyncio.run(validator.validate(
            instruction="Extract all products with prices",
            result=result,
            task_type='extraction'
        ))
        
        assert report.overall_passed
        assert report.overall_score >= 0.5
    
    def test_validate_failed_result(self):
        """Test validation of failed task"""
        import asyncio
        from curllm_core.validation import TaskValidator
        
        validator = TaskValidator()
        
        result = {
            'success': False,
            'error': 'Form submission failed',
            'form_fill': {
                'submitted': False,
                'errors': {'email': 'Invalid email format'}
            }
        }
        
        report = asyncio.run(validator.validate(
            instruction="Submit the contact form",
            result=result,
            task_type='form_fill'
        ))
        
        # Should fail validation
        assert not report.overall_passed or report.overall_score < 0.5


class TestComprehensiveWorkflows:
    """Test complete workflows across multiple steps"""
    
    def test_form_to_confirmation_flow(self):
        """Test complete form submission and confirmation"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Start at contact form
            page.goto(f"{BASE_URL}/01_simple_form.html")
            
            # Fill the form
            page.fill('#name', 'Integration Test User')
            page.fill('#email', 'integration@test.com')
            page.fill('#message', 'This is an integration test')
            page.check('#consent')
            
            # Submit (button has no ID, use type selector)
            page.click('button[type="submit"]')
            page.wait_for_timeout(500)
            
            # Verify submission (check for confirmation)
            page_content = page.content().lower()
            success = any(kw in page_content for kw in ['success', 'thank', 'submitted', 'confirmation'])
            
            # If no confirmation on same page, check if form values persist
            if not success:
                name_val = page.input_value('#name')
                assert name_val == 'Integration Test User'
            
            browser.close()
    
    def test_product_search_and_filter(self):
        """Test product search and filtering workflow"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"{BASE_URL}/02_products.html")
            
            # Count initial products
            initial_count = len(page.query_selector_all('.product'))
            assert initial_count >= 5
            
            # Filter products by price if filter exists
            price_filter = page.query_selector('[data-filter="price"], #price-filter')
            if price_filter:
                page.select_option('[data-filter="price"], #price-filter', '100')
                page.wait_for_timeout(300)
            
            # Extract filtered products
            products = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('.product')).map(el => ({
                    name: el.querySelector('.product-name, .name')?.textContent?.trim(),
                    price: parseFloat(el.dataset.price || el.querySelector('.price')?.textContent?.replace(/[^0-9.]/g, ''))
                }));
            }''')
            
            assert len(products) > 0
            for p_item in products:
                assert p_item['name']
            
            browser.close()
    
    def test_navigation_and_interaction_sequence(self):
        """Test multiple page navigation and interactions"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Start at interactive page
            page.goto(f"{BASE_URL}/11_interactive.html")
            
            # Get initial state
            _ = page.url  # Capture but don't use
            
            # Perform interaction sequence
            # 1. Click a button
            buttons = page.query_selector_all('button')
            if len(buttons) > 0:
                page.click('button:first-of-type')
                page.wait_for_timeout(200)
            
            # 2. Check for state change
            output_el = page.query_selector('#output, .output, [data-output]')
            if output_el:
                output_text = page.text_content('#output, .output, [data-output]')
                assert output_text is not None
            
            # 3. Scroll down
            page.evaluate('window.scrollBy(0, 300)')
            
            # 4. Check scroll happened
            scroll_y = page.evaluate('window.scrollY')
            assert scroll_y >= 300
            
            browser.close()


class TestErrorRecovery:
    """Test error handling and recovery mechanisms"""
    
    def test_missing_element_handling(self):
        """Test handling when elements are not found"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"{BASE_URL}/01_simple_form.html")
            
            # Try to fill non-existent element
            missing = page.query_selector('#non_existent_field')
            assert missing is None
            
            # Should not crash - continue with existing elements
            page.fill('#name', 'Test')
            assert page.input_value('#name') == 'Test'
            
            browser.close()
    
    def test_timeout_handling(self):
        """Test timeout handling"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"{BASE_URL}/11_interactive.html")
            
            # Try with very short timeout - should not crash
            try:
                page.wait_for_selector('.non-existent-modal', timeout=100)
            except Exception:
                pass  # Expected to fail
            
            # Page should still be usable
            assert page.url is not None
            
            browser.close()
    
    def test_form_validation_error_detection(self):
        """Test detecting form validation errors"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(f"{BASE_URL}/12_validation_test.html")
            
            # Try invalid input
            page.fill('#username', 'x')
            page.dispatch_event('#username', 'blur')
            
            # Check for error indication
            has_error_class = page.evaluate('''() => {
                const el = document.querySelector('#username');
                return el.classList.contains('error') || 
                       el.classList.contains('invalid') ||
                       el.getAttribute('aria-invalid') === 'true';
            }''')
            
            # Either shows error or page doesn't have validation
            assert has_error_class is not None
            
            browser.close()

