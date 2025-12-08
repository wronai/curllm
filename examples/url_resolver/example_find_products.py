#!/usr/bin/env python3
"""
URL Resolver - Przykład: Szukanie produktów

Scenariusz: User podaje stronę główną sklepu, ale chce
znaleźć konkretną kategorię produktów (np. RAM DDR5).

URL Resolver:
1. Analizuje stronę główną
2. Wykrywa że brak szukanych produktów
3. Używa wyszukiwarki sklepu lub nawiguje do kategorii
4. Zwraca URL z odpowiednimi produktami
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from curllm_core.url_resolver import UrlResolver
from browser_helper import create_browser, close_browser

# Try to create LLM (optional)
def get_llm():
    try:
        from curllm_core.llm_config import LLMConfig
        config = LLMConfig()
        return config.get_llm()
    except Exception:
        pass
    return None
# Realne przykłady - strony główne sklepów
EXAMPLES = [
    {
        "name": "Morele.net - szukanie RAM DDR5",
        "url": "https://www.morele.net",
        "instruction": "Znajdź pamięci RAM DDR5 32GB",
        "expected": "Powinien znaleźć kategorię RAM DDR5 lub wyniki wyszukiwania"
    },
    {
        "name": "X-kom - szukanie laptopów gamingowych",
        "url": "https://www.x-kom.pl",
        "instruction": "Pokaż laptopy gamingowe",
        "expected": "Powinien nawigować do kategorii laptopów gaming"
    },
    {
        "name": "Allegro - szukanie słuchawek",
        "url": "https://allegro.pl",
        "instruction": "Znajdź słuchawki bezprzewodowe Sony",
        "expected": "Powinien użyć wyszukiwarki i znaleźć oferty"
    },
    {
        "name": "MediaExpert - szukanie telewizorów",
        "url": "https://www.mediaexpert.pl",
        "instruction": "Wylistuj telewizory 55 cali",
        "expected": "Powinien znaleźć kategorię TV 55\""
    },
]
async def run_example(example: dict):
    """Run single example"""
    print(f"\n{'='*60}")
    print(f"📍 {example['name']}")
    print(f"   URL: {example['url']}")
    print(f"   Instrukcja: {example['instruction']}")
    print(f"   Oczekiwane: {example['expected']}")
    print(f"{'='*60}")
    
    playwright = None
    playwright = None
    browser = None
    try:
        playwright, browser, context, page = await create_browser(headless=True, stealth_mode=True)
        
        llm = get_llm()
        resolver = UrlResolver(page=page, llm=llm)
        result = await resolver.resolve(example['url'], example['instruction'])
        
        print(f"\n📊 Wynik:")
        print(f"   Sukces: {'✅' if result.success else '❌'}")
        print(f"   Metoda: {result.resolution_method}")
        print(f"   Oryginalny URL: {result.original_url}")
        print(f"   Rozwiązany URL: {result.resolved_url}")
        print(f"   Kroki: {' → '.join(result.steps_taken)}")
        
        if result.page_match:
            print(f"   Typ strony: {result.page_match.page_type}")
            print(f"   Znaleziono produktów: {result.page_match.found_items}")
            print(f"   Pewność dopasowania: {result.page_match.confidence:.0%}")
        
        await close_browser(playwright, browser, context, page)
        return result.success
        
    except Exception as e:
        print(f"   ❌ Błąd: {e}")
        await close_browser(playwright, browser)
        return False
async def main():
    print("🔍 URL Resolver - Przykłady szukania produktów")
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
