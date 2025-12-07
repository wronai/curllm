"""
Tests for Currency Translation Component
"""

import pytest


class TestCurrencyDetection:
    """Tests for currency detection"""
    
    def test_detect_from_symbol(self):
        from curllm_core.streamware.components.currency import detect_currency
        
        assert detect_currency("$100") == "USD"
        assert detect_currency("€50") == "EUR"
        assert detect_currency("100 zł") == "PLN"
        assert detect_currency("£75") == "GBP"
    
    def test_detect_from_url(self):
        from curllm_core.streamware.components.currency import detect_currency
        
        assert detect_currency("https://ceneo.pl") == "PLN"
        assert detect_currency("https://amazon.de") == "EUR"
        assert detect_currency("https://amazon.co.uk") == "GBP"
        assert detect_currency("https://amazon.com") == "USD"
    
    def test_detect_from_currency_code(self):
        from curllm_core.streamware.components.currency import detect_currency
        
        assert detect_currency("100 PLN") == "PLN"
        assert detect_currency("100 EUR") == "EUR"
        assert detect_currency("USD 100") == "USD"


class TestCurrencyConversion:
    """Tests for currency conversion"""
    
    def test_usd_to_pln(self):
        from curllm_core.streamware.components.currency import convert_price
        
        result = convert_price(100, "USD", "PLN")
        # Should be approximately 400-450 PLN
        assert 350 < result < 500
    
    def test_eur_to_pln(self):
        from curllm_core.streamware.components.currency import convert_price
        
        result = convert_price(100, "EUR", "PLN")
        # Should be approximately 430-480 PLN (EUR is worth more than USD)
        assert 380 < result < 550
    
    def test_pln_to_usd(self):
        from curllm_core.streamware.components.currency import convert_price
        
        result = convert_price(400, "PLN", "USD")
        # Should be approximately 100 USD
        assert 80 < result < 120
    
    def test_same_currency(self):
        from curllm_core.streamware.components.currency import convert_price
        
        result = convert_price(100, "USD", "USD")
        assert result == 100.0


class TestPriceFilterParsing:
    """Tests for parsing price filters from instructions"""
    
    def test_parse_under_dollar(self):
        from curllm_core.streamware.components.currency import CurrencyTranslator
        
        translator = CurrencyTranslator()
        result = translator.parse_price_filter("Extract products under $100")
        
        assert result is not None
        assert result["amount"] == 100
        assert result["currency"] == "USD"
        assert result["comparison"] == "lt"
    
    def test_parse_below_euro(self):
        from curllm_core.streamware.components.currency import CurrencyTranslator
        
        translator = CurrencyTranslator()
        result = translator.parse_price_filter("Find items below €50")
        
        assert result is not None
        assert result["amount"] == 50
        assert result["currency"] == "EUR"
        assert result["comparison"] == "lt"
    
    def test_parse_over_pln(self):
        from curllm_core.streamware.components.currency import CurrencyTranslator
        
        translator = CurrencyTranslator()
        result = translator.parse_price_filter("Show products over 500 zł")
        
        assert result is not None
        assert result["amount"] == 500
        assert result["currency"] == "PLN"
        assert result["comparison"] == "gt"
    
    def test_parse_between(self):
        from curllm_core.streamware.components.currency import CurrencyTranslator
        
        translator = CurrencyTranslator()
        result = translator.parse_price_filter("Laptops between $500 and $1000")
        
        assert result is not None
        assert result["min"] == 500
        assert result["max"] == 1000
        assert result["currency"] == "USD"
        assert result["comparison"] == "between"
    
    def test_parse_no_filter(self):
        from curllm_core.streamware.components.currency import CurrencyTranslator
        
        translator = CurrencyTranslator()
        result = translator.parse_price_filter("Extract all products")
        
        assert result is None


class TestFilterNormalization:
    """Tests for normalizing filters to target currency"""
    
    def test_normalize_usd_to_pln(self):
        from curllm_core.streamware.components.currency import normalize_price_filter
        
        _, filter_info = normalize_price_filter("products under $100", "PLN")
        
        assert filter_info is not None
        assert filter_info["amount"] == 100
        assert filter_info["currency"] == "USD"
        assert "amount_converted" in filter_info
        assert filter_info["target_currency"] == "PLN"
        # Converted amount should be ~400 PLN
        assert 350 < filter_info["amount_converted"] < 500
    
    def test_normalize_same_currency(self):
        from curllm_core.streamware.components.currency import normalize_price_filter
        
        _, filter_info = normalize_price_filter("products under 100 zł", "PLN")
        
        assert filter_info is not None
        assert filter_info["amount"] == 100
        assert filter_info["currency"] == "PLN"
        # No conversion needed - should not have amount_converted
        assert "amount_converted" not in filter_info or filter_info.get("target_currency") == filter_info.get("currency")


class TestExchangeRates:
    """Tests for exchange rates"""
    
    def test_default_rates_exist(self):
        from curllm_core.streamware.components.currency import EXCHANGE_RATES
        
        assert "USD" in EXCHANGE_RATES
        assert "EUR" in EXCHANGE_RATES
        assert "PLN" in EXCHANGE_RATES
        assert "GBP" in EXCHANGE_RATES
        
        # USD should be base (1.0)
        assert EXCHANGE_RATES["USD"] == 1.0
    
    def test_rate_relationships(self):
        from curllm_core.streamware.components.currency import EXCHANGE_RATES
        
        # PLN should be worth less than USD (rate > 1)
        assert EXCHANGE_RATES["PLN"] > 1
        
        # EUR should be worth more than USD (rate < 1)
        assert EXCHANGE_RATES["EUR"] < 1


class TestCurrencySymbols:
    """Tests for currency symbol mapping"""
    
    def test_common_symbols(self):
        from curllm_core.streamware.components.currency import CURRENCY_SYMBOLS
        
        assert CURRENCY_SYMBOLS["$"] == "USD"
        assert CURRENCY_SYMBOLS["€"] == "EUR"
        assert CURRENCY_SYMBOLS["zł"] == "PLN"
        assert CURRENCY_SYMBOLS["£"] == "GBP"
    
    def test_currency_codes(self):
        from curllm_core.streamware.components.currency import CURRENCY_SYMBOLS
        
        assert CURRENCY_SYMBOLS["USD"] == "USD"
        assert CURRENCY_SYMBOLS["EUR"] == "EUR"
        assert CURRENCY_SYMBOLS["PLN"] == "PLN"
