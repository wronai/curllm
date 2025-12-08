#!/usr/bin/env python3
"""
URL Resolver - Przykład: Szukanie formularza kontaktowego

Scenariusz: User podaje dowolną stronę firmową/sklepową,
ale chce znaleźć formularz kontaktowy do wypełnienia.

URL Resolver:
1. Analizuje stronę
2. Szuka linków do kontaktu w menu/stopce
3. Nawiguje do strony kontaktowej
4. Zwraca URL z formularzem
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

# Realne przykłady - różne strony
EXAMPLES = [
    {
        "name": "Morele.net - kontakt",
        "url": "https://www.morele.net",
        "instruction": "Wypełnij formularz kontaktowy",
        "goal": TaskGoal.FIND_CONTACT_FORM
    },
    {
        "name": "Allegro - pomoc/kontakt",
        "url": "https://allegro.pl",
        "instruction": "Napisz wiadomość do obsługi klienta",
        "goal": TaskGoal.FIND_CONTACT_FORM
    },
    {
        "name": "OLX - kontakt",
        "url": "https://www.olx.pl",
        "instruction": "Skontaktuj się z supportem",
        "goal": TaskGoal.FIND_CONTACT_FORM
    },
    {
        "name": "Ceneo - kontakt",
        "url": "https://www.ceneo.pl",
        "instruction": "Wyślij zapytanie do obsługi",
        "goal": TaskGoal.FIND_CONTACT_FORM
    },
]
async def run_example(example: dict):
    """Run single example"""
    print(f"\n{'='*60}")
    print(f"📧 {example['name']}")
    print(f"   URL: {example['url']}")
    print(f"   Instrukcja: {example['instruction']}")
    print(f"{'='*60}")
    
    playwright = None
    browser = None
    try:
        playwright, browser, context, page = await create_browser(headless=True, stealth_mode=True)
        
        
        
        
        llm = get_llm()
        resolver = UrlResolver(page=page, llm=llm)
        
        # Użyj resolve_for_goal bezpośrednio dla konkretnego celu
        result = await resolver.resolve_for_goal(example['url'], example['goal'])
        
        print(f"\n📊 Wynik:")
        print(f"   Sukces: {'✅' if result.success else '❌'}")
        print(f"   Metoda: {result.resolution_method}")
        print(f"   Rozwiązany URL: {result.resolved_url}")
        print(f"   Kroki: {' → '.join(result.steps_taken)}")
        
        if result.success:
            # Sprawdź czy strona ma formularz
            has_form = await page.evaluate("""
                () => {
                    const forms = document.querySelectorAll('form');
                    const inputs = document.querySelectorAll('input[type="email"], textarea');
                    return forms.length > 0 || inputs.length > 0;
                }
            """)
            print(f"   Formularz wykryty: {'✅' if has_form else '❌'}")
        
        await close_browser(playwright, browser, context, page)
        return result.success
        
    except Exception as e:
        print(f"   ❌ Błąd: {e}")
        await close_browser(playwright, browser)
        return False
async def main():
    print("📧 URL Resolver - Przykłady szukania formularzy kontaktowych")
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
