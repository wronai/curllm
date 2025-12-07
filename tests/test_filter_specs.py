"""Tests for specs filtering."""

import pytest
from functions.extractors.specs.filter_specs import (
    filter_specs,
    categorize_specs,
    is_excluded,
    is_technical
)


class TestFilterSpecs:
    """Test specs filtering functions."""
    
    def test_is_excluded_pricing(self):
        """Test that pricing data is excluded."""
        assert is_excluded("1 szt+", "82,95 Zł") is True
        assert is_excluded("10 szt+", "7,1949 Zł") is True
        assert is_excluded("Rabaty ilościowe", "Wyślij zapytanie") is True
    
    def test_is_excluded_stock(self):
        """Test that stock data is excluded."""
        assert is_excluded("na magazynie", "10 szt") is True
    
    def test_is_excluded_technical(self):
        """Test that technical data is NOT excluded."""
        assert is_excluded("Operating Pressure", "-500...500Pa") is False
        assert is_excluded("Supply Voltage", "2,7...5,5V") is False
    
    def test_is_technical(self):
        """Test technical pattern matching."""
        assert is_technical("Operating Pressure") is True
        assert is_technical("Supply Voltage") is True
        assert is_technical("Temperature Range") is True
        assert is_technical("Output Type") is True
        assert is_technical("Producent") is True
        assert is_technical("1 szt+") is False
    
    def test_filter_specs(self):
        """Test full filtering."""
        data = {
            "Operating Pressure": "-500...500Pa",
            "Supply Voltage": "2,7...5,5V",
            "1 szt+": "82,95 Zł",
            "10 szt+": "7,1949 Zł",
            "na magazynie  10 szt": "(19. Dec 2025: 2 szt)",
        }
        
        filtered = filter_specs(data)
        
        assert "Operating Pressure" in filtered
        assert "Supply Voltage" in filtered
        assert "1 szt+" not in filtered
        assert "10 szt+" not in filtered
        assert "na magazynie" not in str(filtered)
    
    def test_categorize_specs(self):
        """Test categorization."""
        data = {
            "Operating Pressure": "-500...500Pa",
            "1 szt+": "82,95 Zł",
            "na magazynie  10 szt": "(19. Dec 2025)",
            "RoHS": "Tak",
        }
        
        categories = categorize_specs(data)
        
        assert "Operating Pressure" in categories["technical"]
        assert "1 szt+" in categories["pricing"]
        assert "na magazynie  10 szt" in categories["stock"]
