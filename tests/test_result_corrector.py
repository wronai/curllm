"""Tests for result corrector module."""

import pytest
from curllm_core.result_corrector import (
    detect_required_fields,
    check_fields_present,
    validate_field_values,
    analyze_and_report,
)


class TestDetectRequiredFields:
    """Test field detection from instructions."""
    
    def test_detect_price(self):
        """Test detection of price field."""
        fields = detect_required_fields("Find all products with prices under 500PLN")
        assert "price" in fields
    
    def test_detect_multiple_fields(self):
        """Test detection of multiple fields."""
        fields = detect_required_fields("Get product names and prices from this page")
        assert "price" in fields
        assert "name" in fields
    
    def test_detect_polish(self):
        """Test detection with Polish keywords."""
        fields = detect_required_fields("Pobierz nazwy i ceny produktów")
        assert "price" in fields  # "ceny" matches price
        assert "name" in fields   # "nazwy" matches name
    
    def test_default_for_products(self):
        """Test default fields for product extraction."""
        # When "product" is mentioned without specific fields, defaults are added
        fields = detect_required_fields("Extract all products with prices from page")
        assert "name" in fields
        assert "price" in fields


class TestCheckFieldsPresent:
    """Test field presence checking."""
    
    def test_all_present(self):
        """Test when all fields present."""
        data = {"items": [{"name": "Test", "price": "99 zł", "url": "/test"}]}
        present, missing = check_fields_present(data, ["name", "price", "url"])
        assert present == ["name", "price", "url"]
        assert missing == []
    
    def test_missing_price(self):
        """Test when price is missing."""
        data = {"items": [{"name": "Test", "url": "/test"}]}
        present, missing = check_fields_present(data, ["name", "price", "url"])
        assert "name" in present
        assert "url" in present
        assert "price" in missing
    
    def test_list_data(self):
        """Test with list data format."""
        data = [{"name": "Test", "image": "img.jpg"}]
        present, missing = check_fields_present(data, ["name", "price"])
        assert "name" in present
        assert "price" in missing


class TestValidateFieldValues:
    """Test field value validation."""
    
    def test_valid_prices(self):
        """Test valid price values."""
        data = [{"price": "99.99 zł"}, {"price": "150 PLN"}]
        issues = validate_field_values(data, "price")
        assert len(issues) == 0
    
    def test_javascript_url(self):
        """Test detection of JavaScript URLs."""
        data = [{"url": "javascript:void(0)"}]
        issues = validate_field_values(data, "url")
        assert any("JavaScript" in issue for issue in issues)
    
    def test_short_name(self):
        """Test detection of too short names."""
        data = [{"name": "AB"}]
        issues = validate_field_values(data, "name")
        assert any("too short" in issue for issue in issues)


class TestAnalyzeAndReport:
    """Test full analysis."""
    
    def test_missing_price_detection(self):
        """Test that missing price is detected."""
        instruction = "Find products with prices"
        data = {"items": [{"name": "Product 1", "url": "/p1"}]}
        
        result = analyze_and_report(instruction, data)
        
        assert "price" in result.missing_fields
    
    def test_no_missing_fields(self):
        """Test when all fields present."""
        instruction = "Get product names"
        data = {"items": [{"name": "Product 1"}]}
        
        result = analyze_and_report(instruction, data)
        
        assert "name" not in result.missing_fields
    
    def test_suggestions_for_missing_price(self):
        """Test that suggestions are generated for missing price."""
        instruction = "Find all prices"
        data = {"items": [{"name": "Product 1"}]}
        
        result = analyze_and_report(instruction, data)
        
        assert len(result.suggestions) > 0
        assert any("price" in s.lower() for s in result.suggestions)
