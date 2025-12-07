#!/usr/bin/env python3
"""
URL Resolver - Przykład: Automatyczne wykrywanie celu

Scenariusz: User podaje URL i instrukcję w naturalnym języku.
URL Resolver sam wykrywa co user chce osiągnąć i znajduje
odpowiednią stronę.

Bez podawania konkretnego TaskGoal - system sam rozpoznaje intencję.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from curllm_core.url_resolver import UrlResolver
from curllm_core.browser_setup import setup_browser
from curllm_core.stealth import StealthConfig


# Przykłady z naturalnym językiem - bez podawania TaskGoal
EXAMPLES = [
    # Shopping
    {
        "url": "https://www.morele.net",
        "instruction": "Znajdź procesory AMD Ryzen 7",
        "description": "Szukanie produktów → wyszukiwarka sklepu"
    },
    {
        "url": "https://www.x-kom.pl/laptopy",
        "instruction": "Dodaj do koszyka i przejdź do płatności",
        "description": "Koszyk/checkout → znajdzie link do koszyka"
    },
    
    # Informacje
    {
        "url": "https://www.euro.com.pl",
        "instruction": "Ile kosztuje dostawa? Jaki jest czas wysyłki?",
        "description": "Dostawa → strona z informacjami o dostawie"
    },
    {
        "url": "https://www.mediaexpert.pl",
        "instruction": "Chcę zwrócić produkt - jak to zrobić?",
        "description": "Zwroty → strona z polityką zwrotów"
    },
    {
        "url": "https://allegro.pl",
        "instruction": "Mam pytanie do obsługi - gdzie FAQ?",
        "description": "FAQ/Help → centrum pomocy"
    },
    
    # Konto
    {
        "url": "https://www.empik.com/ksiazki",
        "instruction": "Muszę się zalogować do mojego konta",
        "description": "Login → strona logowania"
    },
    {
        "url": "https://www.ceneo.pl",
        "instruction": "Chcę założyć nowe konto w serwisie",
        "description": "Rejestracja → formularz rejestracji"
    },
    
    # Kontakt
    {
        "url": "https://www.komputronik.pl",
        "instruction": "Napisz wiadomość do działu obsługi klienta",
        "description": "Kontakt → formularz kontaktowy"
    },
    
    # Blog/treści
    {
        "url": "https://www.x-kom.pl",
        "instruction": "Pokaż artykuły i poradniki na blogu",
        "description": "Blog → sekcja z artykułami"
    },
    
    # Praca
    {
        "url": "https://allegro.pl",
        "instruction": "Szukam pracy - oferty rekrutacyjne",
        "description": "Kariera → strona z ofertami pracy"
    },
]


async def run_example(example: dict):
    """Run single example with automatic goal detection"""
    print(f"\n{'='*70}")
    print(f"🎯 {example['description']}")
    print(f"   URL: {example['url']}")
    print(f"   Instrukcja: \"{example['instruction']}\"")
    print(f"{'='*70}")
    
    browser = None
    try:
        browser, context = await setup_browser(stealth_mode=True, headless=True)
        page = await context.new_page()
        stealth = StealthConfig()
        await stealth.apply_to_context(context)
        
        resolver = UrlResolver(page=page, llm=None)
        
        # Użyj resolve() z automatycznym wykrywaniem celu
        result = await resolver.resolve(example['url'], example['instruction'])
        
        print(f"\n📊 Wynik:")
        print(f"   Wykryty cel: {result.resolution_method}")
        print(f"   Sukces: {'✅' if result.success else '❌'}")
        print(f"   Rozwiązany URL: {result.resolved_url}")
        
        if result.original_url != result.resolved_url:
            print(f"   📍 Nawigacja: {result.original_url}")
            print(f"              → {result.resolved_url}")
        
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
    print("🎯 URL Resolver - Automatyczne wykrywanie intencji")
    print("   System sam rozpoznaje co user chce osiągnąć")
    print("=" * 70)
    
    successes = 0
    total = len(EXAMPLES)
    
    for example in EXAMPLES:
        if await run_example(example):
            successes += 1
    
    print(f"\n{'='*70}")
    print(f"📊 PODSUMOWANIE")
    print(f"   Udanych: {successes}/{total} ({successes/total*100:.0f}%)")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
