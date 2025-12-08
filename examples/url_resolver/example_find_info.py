#!/usr/bin/env python3
"""
URL Resolver - Przykład: Szukanie informacji (FAQ, zwroty, dostawa)

Scenariusz: User pyta o politykę sklepu (zwroty, gwarancja, dostawa)
ale podał tylko stronę główną lub jakąś inną podstronę.

URL Resolver automatycznie znajduje odpowiednią stronę informacyjną.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from curllm_core.url_resolver import UrlResolver, TaskGoal
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

# Realne przykłady - szukanie informacji
EXAMPLES = [
    # Polityka zwrotów
    {
        "name": "X-kom - polityka zwrotów",
        "url": "https://www.x-kom.pl",
        "instruction": "Jaka jest polityka zwrotów? Jak zwrócić produkt?",
        "goal": TaskGoal.FIND_RETURNS,
        "expected_keywords": ["zwrot", "reklamacja", "return"]
    },
    {
        "name": "Morele - zwroty i reklamacje",
        "url": "https://www.morele.net",
        "instruction": "Chcę złożyć reklamację produktu",
        "goal": TaskGoal.FIND_RETURNS,
        "expected_keywords": ["zwrot", "reklamacja"]
    },
    
    # Informacje o dostawie
    {
        "name": "Allegro - koszty dostawy",
        "url": "https://allegro.pl",
        "instruction": "Ile kosztuje dostawa? Jakie są opcje wysyłki?",
        "goal": TaskGoal.FIND_SHIPPING,
        "expected_keywords": ["dostawa", "shipping", "wysyłka"]
    },
    {
        "name": "MediaExpert - dostawa",
        "url": "https://www.mediaexpert.pl",
        "instruction": "Sprawdź czas dostawy i koszty wysyłki",
        "goal": TaskGoal.FIND_SHIPPING,
        "expected_keywords": ["dostawa", "wysyłka"]
    },
    
    # FAQ / Pomoc
    {
        "name": "Ceneo - FAQ",
        "url": "https://www.ceneo.pl",
        "instruction": "Mam pytanie - gdzie FAQ?",
        "goal": TaskGoal.FIND_FAQ,
        "expected_keywords": ["faq", "pytania", "pomoc"]
    },
    
    # Gwarancja
    {
        "name": "RTV Euro AGD - gwarancja",
        "url": "https://www.euro.com.pl",
        "instruction": "Jakie są warunki gwarancji?",
        "goal": TaskGoal.FIND_WARRANTY,
        "expected_keywords": ["gwarancja", "warranty", "serwis"]
    },
    
    # Regulamin
    {
        "name": "Empik - regulamin",
        "url": "https://www.empik.com",
        "instruction": "Pokaż regulamin sklepu",
        "goal": TaskGoal.FIND_TERMS,
        "expected_keywords": ["regulamin", "terms", "warunki"]
    },
]
async def run_example(example: dict):
    """Run single example"""
    print(f"\n{'='*60}")
    print(f"📋 {example['name']}")
    print(f"   URL: {example['url']}")
    print(f"   Instrukcja: {example['instruction']}")
    print(f"   Cel: {example['goal'].value}")
    print(f"{'='*60}")
    
    playwright = None
    browser = None
    try:
        playwright, browser, context, page = await create_browser(headless=True, stealth_mode=True)
        
        
        
        
        llm = get_llm()
        resolver = UrlResolver(page=page, llm=llm)
        result = await resolver.resolve_for_goal(example['url'], example['goal'])
        
        print(f"\n📊 Wynik:")
        print(f"   Sukces: {'✅' if result.success else '❌'}")
        print(f"   Metoda: {result.resolution_method}")
        print(f"   Rozwiązany URL: {result.resolved_url}")
        
        # Sprawdź czy URL zawiera oczekiwane słowa kluczowe
        url_lower = result.resolved_url.lower()
        matches = [kw for kw in example['expected_keywords'] if kw in url_lower]
        if matches:
            print(f"   ✅ URL zawiera: {', '.join(matches)}")
        else:
            print(f"   ⚠️ URL nie zawiera oczekiwanych słów kluczowych")
        
        await close_browser(playwright, browser, context, page)
        
        
        
        return result.success
        
    except Exception as e:
        print(f"   ❌ Błąd: {e}")
        await close_browser(playwright, browser)
        return False
async def main():
    print("📋 URL Resolver - Przykłady szukania informacji")
    print("   (FAQ, zwroty, dostawa, gwarancja, regulamin)")
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
