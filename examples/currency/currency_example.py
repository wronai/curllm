#!/usr/bin/env python3
"""
Currency Translation Example

Shows how curllm automatically converts price filters between currencies.
"""

import asyncio
from playwright.async_api import async_playwright


async def main():
    """
    Demonstrate currency translation for e-commerce extraction.
    """
    print("\n💱 Currency Translation Example")
    print("=" * 50)
    
    # Import the currency translator
    from curllm_core.streamware.components.currency import (
        CurrencyTranslator,
        convert_price,
        detect_currency,
        normalize_price_filter,
        EXCHANGE_RATES,
    )
    
    # 1. Basic conversion
    print("\n📊 1. Basic Currency Conversion")
    print("-" * 40)
    
    conversions = [
        (100, "USD", "PLN"),
        (100, "EUR", "PLN"),
        (500, "USD", "EUR"),
        (1000, "PLN", "USD"),
    ]
    
    for amount, from_curr, to_curr in conversions:
        result = convert_price(amount, from_curr, to_curr)
        print(f"   {amount} {from_curr} → {result:.2f} {to_curr}")
    
    # 2. Currency detection from URL
    print("\n📊 2. Currency Detection from URL")
    print("-" * 40)
    
    urls = [
        "https://ceneo.pl",
        "https://amazon.de",
        "https://amazon.co.uk",
        "https://amazon.com",
        "https://allegro.pl",
    ]
    
    for url in urls:
        currency = detect_currency(url)
        print(f"   {url} → {currency}")
    
    # 3. Parse price filters from instructions
    print("\n📊 3. Parse Price Filters from Instructions")
    print("-" * 40)
    
    instructions = [
        "Extract products under $100",
        "Find items below €50",
        "Show products over 500 zł",
        "Laptops between $500 and $1000",
        "Phones for exactly €299",
    ]
    
    translator = CurrencyTranslator()
    
    for instr in instructions:
        filter_info = translator.parse_price_filter(instr)
        if filter_info:
            if filter_info.get("comparison") == "between":
                print(f"   \"{instr}\"")
                print(f"      → {filter_info['min']}-{filter_info['max']} {filter_info['currency']} ({filter_info['comparison']})")
            else:
                print(f"   \"{instr}\"")
                print(f"      → {filter_info['amount']} {filter_info['currency']} ({filter_info['comparison']})")
    
    # 4. Normalize filter to target currency
    print("\n📊 4. Normalize Filter to Page Currency")
    print("-" * 40)
    
    # Scenario: User searches Polish site with USD price
    instruction = "Extract products under $100"
    target_currency = "PLN"  # Polish site
    
    _, filter_info = normalize_price_filter(instruction, target_currency)
    
    print(f"   User instruction: \"{instruction}\"")
    print(f"   Target site currency: {target_currency}")
    print(f"   Original: {filter_info['amount']} {filter_info['currency']}")
    print(f"   Converted: {filter_info['amount_converted']:.0f} {filter_info['target_currency']}")
    print(f"\n   ✅ Filter will match products under {filter_info['amount_converted']:.0f} zł")
    
    # 5. Full example with page detection
    print("\n📊 5. Full Example with Page Detection")
    print("-" * 40)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("   Loading ceneo.pl...")
            await page.goto("https://ceneo.pl", wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            
            # Detect currency from page
            page_currency = await translator.detect_currency_from_page(page)
            print(f"   Detected page currency: {page_currency}")
            
            # Normalize instruction
            instruction = "Find products under $50"
            _, filter_info = await translator.normalize_filter_to_page_currency(
                instruction,
                page=page
            )
            
            print(f"\n   User wants: \"{instruction}\"")
            print(f"   Page uses: {page_currency}")
            if filter_info:
                converted = filter_info.get('amount_converted', filter_info.get('amount'))
                target = filter_info.get('target_currency', filter_info.get('currency'))
                print(f"   Converted filter: products under {converted:.0f} {target}")
            
        except Exception as e:
            print(f"   Error: {e}")
        finally:
            await browser.close()
    
    # 6. Show exchange rates
    print("\n📊 6. Current Exchange Rates (USD base)")
    print("-" * 40)
    
    for curr in ["EUR", "PLN", "GBP", "CZK", "CHF"]:
        rate = EXCHANGE_RATES.get(curr, "N/A")
        print(f"   1 USD = {rate} {curr}")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
