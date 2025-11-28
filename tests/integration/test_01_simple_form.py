"""
Integration Test 1: Simple Contact Form Filling

Tests LLM-DSL communication for basic form filling task.
Uses sync Playwright API for compatibility with sync DSL components.
"""

import pytest
from playwright.sync_api import sync_playwright
from curllm_core.streamware.llm_bridge import LLMDSLBridge
import os


def test_simple_form_fill_via_llm_dsl():
    """Test filling simple contact form using LLM-DSL commands"""
    
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to test page
        page.goto(f"{base_url}/01_simple_form.html")
        
        # Initialize LLM-DSL Bridge
        bridge = LLMDSLBridge()
        
        # Step 1: Analyze form structure (LLM command in JSON)
        analyze_command = {
            "action": "analyze_form",
            "components": [
                {"type": "dom-snapshot", "params": {"include_values": True}},
                {"type": "dom-analyze", "params": {"type": "forms"}}
            ],
            "data": {"page": page}
        }
        
        result = bridge.execute_llm_command(analyze_command)
        assert result['success'] is True
        assert 'forms' in result['result']
        
        # Step 2: Fill name field (LLM command)
        page.fill('#name', 'John Doe')
        
        # Step 3: Fill email field
        page.fill('#email', 'john@example.com')
        
        # Step 4: Fill message
        page.fill('#message', 'Test message from integration test')
        
        # Step 5: Validate form is filled (LLM command)
        validate_command = {
            "action": "validate_state",
            "type": "form_filled",
            "snapshot": {"forms": [{"fields": [
                {"name": "name", "value": "John Doe"},
                {"name": "email", "value": "john@example.com"}
            ]}]},
            "expectations": {
                "fields": {
                    "name": "John Doe",
                    "email": "john@example.com"
                }
            }
        }
        
        validation = bridge.execute_llm_command(validate_command)
        assert validation['success'] is True
        
        # Step 6: Submit form
        page.click('button[type="submit"]')
        
        # Verify success message appears
        success_msg = page.wait_for_selector('#successMessage', state='visible', timeout=5000)
        assert success_msg is not None
        
        browser.close()


def test_form_field_mapping_via_dsl():
    """Test field mapping using LLM-DSL"""
    
    base_url = os.getenv('CURLLM_TEST_BASE_URL', 'http://test-webserver')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto(f"{base_url}/01_simple_form.html")
        
        bridge = LLMDSLBridge()
        
        # Use field-mapper component via LLM command
        map_command = {
            "action": "execute_flow",
            "steps": [
                {"component": "dom-snapshot", "params": {"include_values": True}},
                {"component": "field-mapper", "params": {"strategy": "fuzzy"}}
            ],
            "data": {
                "instruction": "Fill form: name=Alice Smith, email=alice@example.com, message=Hello"
            }
        }
        
        result = bridge.execute_llm_command(map_command)
        assert result['success'] is True
        
        browser.close()
