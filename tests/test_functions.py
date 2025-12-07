"""Tests for atomic functions."""

import pytest


class TestPriceExtractors:
    """Test price extraction functions."""
    
    def test_extract_polish_price(self):
        from functions.extractors.prices import extract_polish_price
        
        assert extract_polish_price("1 234,56 zł") == 1234.56
        assert extract_polish_price("999.99 PLN") == 999.99
        assert extract_polish_price("od 500 zł") == 500.0
        assert extract_polish_price("") is None
        assert extract_polish_price(None) is None
    
    def test_extract_euro_price(self):
        from functions.extractors.prices import extract_euro_price
        
        assert extract_euro_price("€99.99") == 99.99
        assert extract_euro_price("50,00 EUR") == 50.0
        assert extract_euro_price("") is None
    
    def test_extract_usd_price(self):
        from functions.extractors.prices import extract_usd_price
        
        assert extract_usd_price("$99.99") == 99.99
        assert extract_usd_price("USD 1,234.56") == 1234.56
        assert extract_usd_price("") is None
    
    def test_normalize_price_string(self):
        from functions.extractors.prices import normalize_price_string
        
        assert normalize_price_string("1 234,56") == 1234.56
        assert normalize_price_string("999.99") == 999.99
        assert normalize_price_string("1.234,56") == 1234.56
        assert normalize_price_string("") is None
    
    def test_extract_any_price(self):
        from functions.extractors.prices import extract_any_price
        
        result = extract_any_price("1 234,56 zł")
        assert result == (1234.56, "PLN")
        
        result = extract_any_price("$99.99")
        assert result == (99.99, "USD")
        
        result = extract_any_price("€50.00")
        assert result == (50.0, "EUR")
    
    def test_extract_price_range(self):
        from functions.extractors.prices import extract_price_range
        
        assert extract_price_range("100-200 zł") == (100.0, 200.0)
        assert extract_price_range("od 50 do 100 PLN") == (50.0, 100.0)
        assert extract_price_range("no price") is None


class TestNameExtractors:
    """Test name extraction functions."""
    
    def test_clean_product_name(self):
        from functions.extractors.names import clean_product_name
        
        assert clean_product_name("iPhone 15 Pro 999 zł") == "iPhone 15 Pro"
        assert clean_product_name("  Samsung Galaxy   S24  ") == "Samsung Galaxy S24"
        assert clean_product_name("") is None
    
    def test_extract_product_name(self):
        from functions.extractors.names import extract_product_name
        
        assert extract_product_name("<h3>iPhone 15</h3>") == "iPhone 15"
        assert extract_product_name("Product: Laptop Dell") == "Laptop Dell"
    
    def test_extract_title(self):
        from functions.extractors.names import extract_title
        
        assert extract_title("Best Laptops 2024 | TechReview") == "Best Laptops 2024"
        # "iPhone 15 - Apple (PL)" -> "iPhone 15" is the first part before " - "
        result = extract_title("iPhone 15 Pro Max - Apple Store")
        assert "iPhone" in result
    
    def test_is_valid_product_name(self):
        from functions.extractors.names import is_valid_product_name
        
        assert is_valid_product_name("iPhone 15 Pro") is True
        assert is_valid_product_name("Login") is False
        assert is_valid_product_name("Zobacz więcej") is False
        assert is_valid_product_name("") is False
        assert is_valid_product_name("123") is False
    
    def test_extract_brand(self):
        from functions.extractors.names import extract_brand
        
        assert extract_brand("Apple iPhone 15 Pro") == "Apple"
        assert extract_brand("Samsung Galaxy S24") == "Samsung"
        assert extract_brand("Laptop Dell XPS 15") == "Dell"


class TestPatternRegistry:
    """Test pattern registry."""
    
    def test_register_and_get_pattern(self):
        from functions.patterns.registry import register_pattern, get_pattern
        
        pattern = register_pattern(
            name="test.pattern",
            pattern=r'\d+',
            description="Match digits"
        )
        
        assert pattern is not None
        assert pattern.name == "test.pattern"
        
        retrieved = get_pattern("test.pattern")
        assert retrieved is not None
        assert retrieved.pattern == r'\d+'
    
    def test_pattern_match(self):
        from functions.patterns.registry import register_pattern
        
        pattern = register_pattern(
            name="test.match",
            pattern=r'(\d+)\s*zł',
            description="Match price"
        )
        
        match = pattern.match("100 zł")
        assert match is not None
        assert match.group(1) == "100"
        
        match = pattern.match("no price")
        assert match is None
    
    def test_pattern_tracking(self):
        from functions.patterns.registry import register_pattern
        
        pattern = register_pattern(
            name="test.tracking",
            pattern=r'\d+',
            description="Test tracking"
        )
        
        initial_success = pattern.success_count
        initial_failure = pattern.failure_count
        
        pattern.record_success()
        assert pattern.success_count == initial_success + 1
        
        pattern.record_failure()
        assert pattern.failure_count == initial_failure + 1
