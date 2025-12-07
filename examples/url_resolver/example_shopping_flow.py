#!/usr/bin/env python3
"""
URL Resolver - Przykład: Flow zakupowy (koszyk, checkout, logowanie)

Scenariusz: User chce dokończyć zakupy lub się zalogować,
ale podał dowolny URL ze sklepu.

URL Resolver znajduje:
- Koszyk
- Stronę checkout
- Panel logowania
- Stronę rejestracji
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from curllm_core.url_resolver import UrlResolver, TaskGoal
from curllm_core.browser_setup import setup_browser
from curllm_core.stealth import apply_stealth


# Realne przykłady - flow zakupowy
EXAMPLES = [
    # Koszyk
    {
        "name": "Morele - koszyk",
        "url": "https://www.morele.net/laptopy-31/",
        "instruction": "Pokaż mój koszyk",
        "goal": TaskGoal.FIND_CART
    },
    {
        "name": "X-kom - koszyk",
        "url": "https://www.x-kom.pl",
        "instruction": "Przejdź do koszyka zakupowego",
        "goal": TaskGoal.FIND_CART
    },
    {
        "name": "Allegro - koszyk",
        "url": "https://allegro.pl",
        "instruction": "Otwórz koszyk",
        "goal": TaskGoal.FIND_CART
    },
    
    # Logowanie
    {
        "name": "Morele - logowanie",
        "url": "https://www.morele.net",
        "instruction": "Zaloguj się do konta",
        "goal": TaskGoal.FIND_LOGIN
    },
    {
        "name": "Allegro - logowanie",
        "url": "https://allegro.pl/kategoria/komputery",
        "instruction": "Chcę się zalogować",
        "goal": TaskGoal.FIND_LOGIN
    },
    
    # Rejestracja
    {
        "name": "X-kom - rejestracja",
        "url": "https://www.x-kom.pl",
        "instruction": "Załóż nowe konto",
        "goal": TaskGoal.FIND_REGISTER
    },
    
    # Moje konto
    {
        "name": "MediaExpert - moje konto",
        "url": "https://www.mediaexpert.pl",
        "instruction": "Pokaż moje zamówienia w koncie",
        "goal": TaskGoal.FIND_ACCOUNT
    },
]


async def run_example(example: dict):
    """Run single example"""
    print(f"\n{'='*60}")
    print(f"🛒 {example['name']}")
    print(f"   URL: {example['url']}")
    print(f"   Instrukcja: {example['instruction']}")
    print(f"   Cel: {example['goal'].value}")
    print(f"{'='*60}")
    
    browser = None
    try:
        browser, context = await setup_browser(stealth_mode=True, headless=True)
        page = await context.new_page()
        await apply_stealth(page)
        
        resolver = UrlResolver(page=page, llm=None)
        result = await resolver.resolve_for_goal(example['url'], example['goal'])
        
        print(f"\n📊 Wynik:")
        print(f"   Sukces: {'✅' if result.success else '❌'}")
        print(f"   Metoda: {result.resolution_method}")
        print(f"   Rozwiązany URL: {result.resolved_url}")
        print(f"   Kroki: {' → '.join(result.steps_taken)}")
        
        await page.close()
        await context.close()
        await browser.close()
        
        return result.success
        
    except Exception as e:
        print(f"   ❌ Błąd: {e}")
        if browser:
            try:
                await browser.close()
            except:
                pass
        return False


async def main():
    print("🛒 URL Resolver - Flow zakupowy")
    print("   (koszyk, checkout, logowanie, rejestracja)")
    print("=" * 60)
    
    successes = 0
    for example in EXAMPLES:
        if await run_example(example):
            successes += 1
    
    print(f"\n{'='*60}")
    print(f"📊 Podsumowanie: {successes}/{len(EXAMPLES)} udanych")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
