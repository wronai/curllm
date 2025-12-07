"""
Currency Translator Module

Handles currency detection, conversion, and normalization for price filtering.
Supports dynamic exchange rates via API and LLM-assisted currency detection.
"""

import re
import os
import json
import asyncio
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime, timedelta
from pathlib import Path


# Default exchange rates (USD base) - updated periodically
# These are approximate rates as of late 2024
EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "PLN": 4.05,
    "GBP": 0.79,
    "CHF": 0.88,
    "CZK": 23.5,
    "SEK": 10.8,
    "NOK": 11.0,
    "DKK": 6.9,
    "HUF": 365.0,
    "RON": 4.6,
    "BGN": 1.8,
    "UAH": 41.0,
    "RUB": 92.0,
    "JPY": 150.0,
    "CNY": 7.2,
    "INR": 83.5,
    "BRL": 5.0,
    "AUD": 1.55,
    "CAD": 1.37,
}

# Currency symbols and their codes
CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "zł": "PLN",
    "PLN": "PLN",
    "£": "GBP",
    "CHF": "CHF",
    "Fr.": "CHF",
    "Kč": "CZK",
    "CZK": "CZK",
    "kr": "SEK",  # Could be SEK, NOK, DKK
    "SEK": "SEK",
    "NOK": "NOK",
    "DKK": "DKK",
    "Ft": "HUF",
    "HUF": "HUF",
    "lei": "RON",
    "лв": "BGN",
    "₴": "UAH",
    "₽": "RUB",
    "¥": "JPY",
    "元": "CNY",
    "₹": "INR",
    "R$": "BRL",
    "A$": "AUD",
    "C$": "CAD",
    "USD": "USD",
    "EUR": "EUR",
    "GBP": "GBP",
}

# TLD to currency mapping (for detecting page currency)
TLD_CURRENCY = {
    ".pl": "PLN",
    ".de": "EUR",
    ".fr": "EUR",
    ".it": "EUR",
    ".es": "EUR",
    ".nl": "EUR",
    ".be": "EUR",
    ".at": "EUR",
    ".ie": "EUR",
    ".pt": "EUR",
    ".fi": "EUR",
    ".gr": "EUR",
    ".uk": "GBP",
    ".co.uk": "GBP",
    ".ch": "CHF",
    ".cz": "CZK",
    ".se": "SEK",
    ".no": "NOK",
    ".dk": "DKK",
    ".hu": "HUF",
    ".ro": "RON",
    ".bg": "BGN",
    ".ua": "UAH",
    ".ru": "RUB",
    ".jp": "JPY",
    ".cn": "CNY",
    ".in": "INR",
    ".br": "BRL",
    ".au": "AUD",
    ".ca": "CAD",
    ".com": "USD",  # Default for .com
    ".us": "USD",
}


class CurrencyTranslator:
    """
    Translates prices between currencies.
    
    Supports:
    - Static exchange rates (built-in)
    - Dynamic rates via API (optional)
    - LLM-assisted currency detection
    - Page-based currency detection (TLD, meta tags)
    """
    
    def __init__(
        self,
        llm=None,
        run_logger=None,
        cache_dir: Optional[Path] = None,
        api_key: Optional[str] = None
    ):
        self.llm = llm
        self.run_logger = run_logger
        self.cache_dir = cache_dir or Path.home() / ".cache" / "curllm" / "currency"
        self.api_key = api_key or os.getenv("EXCHANGE_RATE_API_KEY")
        self._rates_cache: Optional[Dict[str, float]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=12)
    
    def _log(self, message: str, data: Any = None):
        """Log to run logger if available."""
        if self.run_logger:
            if data:
                self.run_logger.log_text(f"💱 {message}: {json.dumps(data, ensure_ascii=False)}")
            else:
                self.run_logger.log_text(f"💱 {message}")
    
    def get_rates(self) -> Dict[str, float]:
        """Get current exchange rates (from cache or default)."""
        if self._rates_cache and self._cache_timestamp:
            if datetime.now() - self._cache_timestamp < self._cache_ttl:
                return self._rates_cache
        
        # Try to load from file cache
        cache_file = self.cache_dir / "rates.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    if datetime.fromisoformat(data["timestamp"]) > datetime.now() - self._cache_ttl:
                        self._rates_cache = data["rates"]
                        self._cache_timestamp = datetime.fromisoformat(data["timestamp"])
                        return self._rates_cache
            except Exception:
                pass
        
        return EXCHANGE_RATES
    
    async def fetch_live_rates(self) -> Dict[str, float]:
        """Fetch live exchange rates from API (if key available)."""
        if not self.api_key:
            self._log("No API key, using default rates")
            return EXCHANGE_RATES
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Using exchangerate.host (free tier)
                url = f"https://api.exchangerate.host/latest?base=USD&access_key={self.api_key}"
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success"):
                            rates = data.get("rates", {})
                            self._rates_cache = rates
                            self._cache_timestamp = datetime.now()
                            
                            # Save to file cache
                            try:
                                self.cache_dir.mkdir(parents=True, exist_ok=True)
                                with open(self.cache_dir / "rates.json", "w") as f:
                                    json.dump({
                                        "rates": rates,
                                        "timestamp": datetime.now().isoformat()
                                    }, f)
                            except Exception:
                                pass
                            
                            self._log("Fetched live rates", {"currencies": len(rates)})
                            return rates
        except Exception as e:
            self._log(f"Failed to fetch live rates: {e}")
        
        return EXCHANGE_RATES
    
    def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        rates: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Price value
            from_currency: Source currency code (e.g., "USD")
            to_currency: Target currency code (e.g., "PLN")
            rates: Optional custom rates dict
            
        Returns:
            Converted amount
        """
        rates = rates or self.get_rates()
        
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # Get rates (relative to USD)
        from_rate = rates.get(from_currency, 1.0)
        to_rate = rates.get(to_currency, 1.0)
        
        # Convert: amount in from_currency -> USD -> to_currency
        usd_amount = amount / from_rate
        result = usd_amount * to_rate
        
        self._log(f"Converted {amount} {from_currency} → {result:.2f} {to_currency}")
        return result
    
    def detect_currency_from_url(self, url: str) -> str:
        """Detect likely currency from URL domain."""
        url_lower = url.lower()
        
        for tld, currency in TLD_CURRENCY.items():
            if tld in url_lower:
                return currency
        
        return "USD"  # Default
    
    async def detect_currency_from_page(self, page) -> str:
        """Detect currency used on page by analyzing content."""
        try:
            currency_info = await page.evaluate("""
                () => {
                    const results = {
                        url: window.location.href,
                        symbols: {},
                        meta_currency: null,
                        lang: document.documentElement.lang || navigator.language
                    };
                    
                    // Check meta tags
                    const metaCurrency = document.querySelector('meta[property="og:price:currency"], meta[name="currency"]');
                    if (metaCurrency) {
                        results.meta_currency = metaCurrency.content;
                    }
                    
                    // Count currency symbols in page text
                    const text = document.body.innerText || '';
                    const symbols = ['$', '€', 'zł', '£', 'Kč', 'kr', 'Ft', '₽', '¥'];
                    for (const sym of symbols) {
                        const count = (text.match(new RegExp('\\\\d+[\\\\s,\\\\.]*\\\\d*\\\\s*' + sym.replace('$', '\\\\$'), 'g')) || []).length;
                        const countAfter = (text.match(new RegExp(sym.replace('$', '\\\\$') + '\\\\s*\\\\d+', 'g')) || []).length;
                        if (count + countAfter > 0) {
                            results.symbols[sym] = count + countAfter;
                        }
                    }
                    
                    // Check for PLN/EUR/USD text patterns
                    const plnCount = (text.match(/\\d+[\\s,\\.]*\\d*\\s*(PLN|zł)/gi) || []).length;
                    const eurCount = (text.match(/\\d+[\\s,\\.]*\\d*\\s*(EUR|€)/gi) || []).length;
                    const usdCount = (text.match(/\\d+[\\s,\\.]*\\d*\\s*(USD|\\$)/gi) || []).length;
                    
                    if (plnCount > 0) results.symbols['PLN'] = (results.symbols['PLN'] || 0) + plnCount;
                    if (eurCount > 0) results.symbols['EUR'] = (results.symbols['EUR'] || 0) + eurCount;
                    if (usdCount > 0) results.symbols['USD'] = (results.symbols['USD'] || 0) + usdCount;
                    
                    return results;
                }
            """)
            
            # Priority: meta tag > most common symbol > URL TLD
            if currency_info.get("meta_currency"):
                return currency_info["meta_currency"]
            
            symbols = currency_info.get("symbols", {})
            if symbols:
                # Find most common symbol
                most_common = max(symbols.items(), key=lambda x: x[1])
                symbol = most_common[0]
                currency = CURRENCY_SYMBOLS.get(symbol, "USD")
                self._log(f"Detected currency from page: {currency}", {"symbol": symbol, "count": most_common[1]})
                return currency
            
            # Fallback to URL detection
            return self.detect_currency_from_url(currency_info.get("url", ""))
            
        except Exception as e:
            self._log(f"Currency detection failed: {e}")
            return "USD"
    
    def parse_price_filter(self, instruction: str) -> Optional[Dict[str, Any]]:
        """
        Parse price filter from instruction.
        
        Args:
            instruction: User instruction like "products under $100"
            
        Returns:
            Dict with: amount, currency, comparison (lt/gt/eq)
        """
        patterns = [
            # Under/below patterns
            (r'(?:under|below|less than|cheaper than|<)\s*([€$£]|zł|PLN|EUR|USD|GBP)?\s*([\d,\.]+)\s*([€$£]|zł|PLN|EUR|USD|GBP)?', 'lt'),
            # Over/above patterns  
            (r'(?:over|above|more than|>)\s*([€$£]|zł|PLN|EUR|USD|GBP)?\s*([\d,\.]+)\s*([€$£]|zł|PLN|EUR|USD|GBP)?', 'gt'),
            # Between patterns
            (r'(?:between|from)\s*([€$£]|zł|PLN|EUR|USD|GBP)?\s*([\d,\.]+)\s*(?:and|to|-)\s*([€$£]|zł|PLN|EUR|USD|GBP)?\s*([\d,\.]+)', 'between'),
            # Exact patterns
            (r'(?:for|at|exactly|=)\s*([€$£]|zł|PLN|EUR|USD|GBP)?\s*([\d,\.]+)\s*([€$£]|zł|PLN|EUR|USD|GBP)?', 'eq'),
        ]
        
        for pattern, comparison in patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if comparison == 'between':
                    currency1 = groups[0] or groups[2] or "$"
                    amount1 = float(groups[1].replace(",", ""))
                    amount2 = float(groups[3].replace(",", ""))
                    currency_code = CURRENCY_SYMBOLS.get(currency1, "USD")
                    return {
                        "min": amount1,
                        "max": amount2,
                        "currency": currency_code,
                        "comparison": comparison
                    }
                else:
                    currency = groups[0] or groups[2] or "$"
                    amount = float(groups[1].replace(",", ""))
                    currency_code = CURRENCY_SYMBOLS.get(currency, "USD")
                    return {
                        "amount": amount,
                        "currency": currency_code,
                        "comparison": comparison
                    }
        
        return None
    
    async def normalize_filter_to_page_currency(
        self,
        instruction: str,
        page=None,
        target_currency: Optional[str] = None
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Normalize price filter in instruction to page's currency.
        
        Args:
            instruction: User instruction
            page: Playwright page (for currency detection)
            target_currency: Override target currency
            
        Returns:
            Tuple of (modified_instruction, filter_info)
        """
        filter_info = self.parse_price_filter(instruction)
        if not filter_info:
            return instruction, None
        
        # Detect page currency
        if target_currency:
            page_currency = target_currency
        elif page:
            page_currency = await self.detect_currency_from_page(page)
        else:
            page_currency = "USD"
        
        source_currency = filter_info["currency"]
        
        # No conversion needed if same currency
        if source_currency == page_currency:
            return instruction, filter_info
        
        # Convert amounts
        rates = self.get_rates()
        
        if filter_info.get("comparison") == "between":
            min_converted = self.convert(filter_info["min"], source_currency, page_currency, rates)
            max_converted = self.convert(filter_info["max"], source_currency, page_currency, rates)
            filter_info["min_converted"] = min_converted
            filter_info["max_converted"] = max_converted
            filter_info["target_currency"] = page_currency
            
            self._log(
                f"Converted filter: {filter_info['min']}-{filter_info['max']} {source_currency} → "
                f"{min_converted:.0f}-{max_converted:.0f} {page_currency}"
            )
        else:
            amount_converted = self.convert(filter_info["amount"], source_currency, page_currency, rates)
            filter_info["amount_converted"] = amount_converted
            filter_info["target_currency"] = page_currency
            
            self._log(
                f"Converted filter: {filter_info['amount']} {source_currency} → "
                f"{amount_converted:.0f} {page_currency}"
            )
        
        return instruction, filter_info


# Convenience functions

def detect_currency(text_or_url: str) -> str:
    """Detect currency from text or URL."""
    # Check for currency symbols in text
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in text_or_url:
            return code
    
    # Check TLD
    for tld, currency in TLD_CURRENCY.items():
        if tld in text_or_url.lower():
            return currency
    
    return "USD"


def convert_price(
    amount: float,
    from_currency: str,
    to_currency: str
) -> float:
    """Simple price conversion using default rates."""
    translator = CurrencyTranslator()
    return translator.convert(amount, from_currency, to_currency)


def normalize_price_filter(
    instruction: str,
    target_currency: str = "PLN"
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Normalize price filter in instruction.
    
    Example:
        >>> normalize_price_filter("products under $100", "PLN")
        ("products under $100", {"amount": 100, "currency": "USD", "amount_converted": 405, "target_currency": "PLN", ...})
    """
    translator = CurrencyTranslator()
    filter_info = translator.parse_price_filter(instruction)
    
    if not filter_info:
        return instruction, None
    
    source_currency = filter_info["currency"]
    
    if source_currency != target_currency:
        if filter_info.get("comparison") == "between":
            filter_info["min_converted"] = convert_price(filter_info["min"], source_currency, target_currency)
            filter_info["max_converted"] = convert_price(filter_info["max"], source_currency, target_currency)
        else:
            filter_info["amount_converted"] = convert_price(filter_info["amount"], source_currency, target_currency)
        filter_info["target_currency"] = target_currency
    
    return instruction, filter_info
