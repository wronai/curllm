# Currency Translation Examples

Demonstrates how curllm handles currency conversion for price filters.

## Problem

When searching Polish e-commerce sites like ceneo.pl with:
```bash
curllm "https://ceneo.pl" -d "Extract products under $100"
```

The site uses PLN (złoty), but user specified USD. Without translation:
- "$100" doesn't match any prices on page
- No products are extracted

## Solution

The `CurrencyTranslator` component automatically:
1. Detects the currency used on the page (PLN from `.pl` domain)
2. Parses the price filter from instruction ("under $100")
3. Converts to local currency ($100 → ~405 zł)
4. Applies the converted filter

## Usage

### Basic Conversion

```python
from curllm_core.streamware.components.currency import convert_price, detect_currency

# Simple conversion
pln_amount = convert_price(100, "USD", "PLN")
print(f"$100 = {pln_amount:.0f} zł")  # $100 = 405 zł

# Detect currency from URL
currency = detect_currency("https://ceneo.pl")
print(f"Site currency: {currency}")  # PLN
```

### Filter Normalization

```python
from curllm_core.streamware.components.currency import normalize_price_filter

# Normalize instruction filter
instruction = "Extract products under $100"
_, filter_info = normalize_price_filter(instruction, target_currency="PLN")

print(filter_info)
# {
#     "amount": 100,
#     "currency": "USD",
#     "comparison": "lt",
#     "amount_converted": 405.0,
#     "target_currency": "PLN"
# }
```

### With Page Detection

```python
import asyncio
from curllm_core.streamware.components.currency import CurrencyTranslator

async def main():
    translator = CurrencyTranslator()
    
    # With Playwright page
    instruction = "Find laptops under €500"
    modified, filter_info = await translator.normalize_filter_to_page_currency(
        instruction,
        page=playwright_page,  # Auto-detects currency from page
    )
    
    print(f"Original: €500")
    print(f"Converted: {filter_info['amount_converted']:.0f} {filter_info['target_currency']}")

asyncio.run(main())
```

## Supported Currencies

| Symbol | Code | Example |
|--------|------|---------|
| $ | USD | $100 |
| € | EUR | €100 |
| zł | PLN | 100 zł |
| £ | GBP | £100 |
| Kč | CZK | 100 Kč |
| kr | SEK | 100 kr |
| Ft | HUF | 100 Ft |

## Exchange Rates

Default rates are built-in. For live rates, set:
```bash
export EXCHANGE_RATE_API_KEY="your_api_key"
```

## Files

| File | Description |
|------|-------------|
| `currency_example.py` | Full example with page detection |
| `simple_conversion.py` | Basic conversion examples |
