"""
Tests for atomic form components
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

# Test parse_instruction
from curllm_core.streamware.components.form.map_fields import (
    parse_instruction,
    map_user_data_to_fields,
    FIELD_KEYWORDS
)


class TestParseInstruction:
    """Tests for instruction parsing"""
    
    def test_simple_pairs(self):
        result = parse_instruction("Fill form: email=john@example.com, name=John Doe")
        assert result['email'] == 'john@example.com'
        assert result['name'] == 'John Doe'
    
    def test_with_spaces(self):
        result = parse_instruction("email = john@example.com, message = Hello World")
        assert result['email'] == 'john@example.com'
        assert result['message'] == 'Hello World'
    
    def test_polish_keywords(self):
        result = parse_instruction("wypełnij: email=test@test.pl, wiadomość=Treść")
        assert result['email'] == 'test@test.pl'
        assert result['wiadomość'] == 'Treść'
    
    def test_empty_instruction(self):
        result = parse_instruction("")
        assert result == {}
    
    def test_no_pairs(self):
        result = parse_instruction("Just some text without any pairs")
        assert result == {}


class TestMapUserDataToFields:
    """Tests for field mapping"""
    
    def test_map_email_field(self):
        user_data = {'email': 'test@example.com'}
        fields = [
            {'name': 'email-1', 'id': 'field-email', 'type': 'email', 'tag': 'input'}
        ]
        
        mappings = map_user_data_to_fields(user_data, fields)
        
        assert len(mappings) == 1
        assert mappings[0][1] == 'email'  # field_class
        assert mappings[0][2] == 'test@example.com'  # value
    
    def test_map_textarea_to_message(self):
        user_data = {'message': 'Hello World'}
        fields = [
            {'name': 'textarea-1', 'id': '', 'type': 'textarea', 'tag': 'textarea'}
        ]
        
        mappings = map_user_data_to_fields(user_data, fields)
        
        assert len(mappings) == 1
        assert mappings[0][1] == 'message'
    
    def test_no_matching_fields(self):
        user_data = {'name': 'John'}
        fields = [
            {'name': 'email-1', 'id': '', 'type': 'email', 'tag': 'input'}
        ]
        
        mappings = map_user_data_to_fields(user_data, fields)
        
        assert len(mappings) == 0
    
    def test_multiple_mappings(self):
        user_data = {'email': 'test@test.com', 'message': 'Hello'}
        fields = [
            {'name': 'email-1', 'id': '', 'type': 'email', 'tag': 'input'},
            {'name': 'textarea-1', 'id': '', 'type': 'textarea', 'tag': 'textarea'}
        ]
        
        mappings = map_user_data_to_fields(user_data, fields)
        
        assert len(mappings) == 2


class TestFieldKeywords:
    """Tests for field keyword definitions"""
    
    def test_email_keywords(self):
        assert 'email' in FIELD_KEYWORDS
        assert 'mail' in FIELD_KEYWORDS['email']
    
    def test_message_keywords(self):
        assert 'message' in FIELD_KEYWORDS
        assert 'wiadomość' in FIELD_KEYWORDS['message']
    
    def test_phone_keywords(self):
        assert 'phone' in FIELD_KEYWORDS
        assert 'telefon' in FIELD_KEYWORDS['phone']


# Async tests for page interactions - using asyncio.run() for compatibility
import asyncio


class TestDetectForm:
    """Tests for form detection (requires mock page)"""
    
    def test_detect_form_found(self):
        from curllm_core.streamware.components.form.detect import detect_form
        
        async def run_test():
            mock_page = AsyncMock()
            mock_page.evaluate = AsyncMock(return_value=[
                {
                    'id': 'contact-form',
                    'fields': [
                        {'type': 'email', 'name': 'email', 'visible': True},
                        {'type': 'textarea', 'name': 'message', 'visible': True}
                    ]
                }
            ])
            
            result = await detect_form(mock_page)
            
            assert result['found'] is True
            assert result['form_id'] == 'contact-form'
            assert len(result['fields']) == 2
        
        asyncio.run(run_test())
    
    def test_detect_form_not_found(self):
        from curllm_core.streamware.components.form.detect import detect_form
        
        async def run_test():
            mock_page = AsyncMock()
            mock_page.evaluate = AsyncMock(return_value=[])
            
            result = await detect_form(mock_page)
            
            assert result['found'] is False
        
        asyncio.run(run_test())


class TestFillField:
    """Tests for field filling"""
    
    def test_fill_field_success(self):
        from curllm_core.streamware.components.form.fill import fill_field
        
        async def run_test():
            mock_page = AsyncMock()
            mock_page.fill = AsyncMock()
            mock_page.evaluate = AsyncMock()
            
            result = await fill_field(mock_page, '#email', 'test@example.com')
            
            assert result['success'] is True
            assert result['error'] is None
        
        asyncio.run(run_test())
    
    def test_fill_field_failure_with_fallback(self):
        from curllm_core.streamware.components.form.fill import fill_field
        
        async def run_test():
            mock_page = AsyncMock()
            mock_page.fill = AsyncMock(side_effect=Exception("Element not found"))
            mock_page.evaluate = AsyncMock()  # Fallback succeeds
            
            result = await fill_field(mock_page, '#email', 'test@example.com')
            
            # Should succeed via fallback
            assert result['success'] is True
            assert result.get('fallback') is True
        
        asyncio.run(run_test())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
