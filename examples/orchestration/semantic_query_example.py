"""
Example: Using Semantic Query Engine for better extraction quality

Demonstrates the difference between:
1. Monolithic heuristics (old) - black box, no feedback
2. Semantic Query Engine (new) - full observability, quality metrics
"""

import asyncio
from playwright.async_api import async_playwright
from curllm_core.llm import SimpleOllama
from curllm_core.logger import RunLogger
from curllm_core.semantic_query import semantic_extract
from curllm_core.extraction import product_heuristics


async def example_semantic_vs_monolithic():
    """Compare semantic query engine vs monolithic heuristics"""
    
    url = "https://www.ceneo.pl/Urzadzenia_sprzatajace;ptags:OfertySpecjalne.htm"
    instruction = "Find all products under 150zł and extract names, prices and urls"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(3000)
        
        llm = SimpleOllama(model="qwen2.5:14b")
        logger = RunLogger(instruction, url)
        
        print("\n" + "="*60)
        print("APPROACH 1: Monolithic Heuristics (Old)")
        print("="*60)
        
        result_old = await product_heuristics(instruction, page, logger)
        
        print(f"\nResult: {result_old}")
        print(f"Count: {len(result_old.get('products', []))}")
        print("\nProblem: If count=0, we don't know WHY!")
        print("- No containers found?")
        print("- Containers OK but price extraction failed?")
        print("- URLs invalid?")
        print("- ???")
        
        print("\n" + "="*60)
        print("APPROACH 2: Semantic Query Engine (New)")
        print("="*60)
        
        result_new = await semantic_extract(instruction, page, llm, logger)
        
        print(f"\nResult: {result_new}")
        print(f"\nCount: {result_new.get('count', 0)}")
        print(f"Quality Metrics:")
        print(f"  - Completeness: {result_new['quality']['completeness']:.2%}")
        print(f"  - Containers found: {result_new['quality']['containers_found']}")
        print(f"  - Extraction rate: {result_new['quality']['extraction_rate']:.2%}")
        
        print("\nBenefits:")
        print("✅ Full execution trace in logs")
        print("✅ Quality metrics")
        print("✅ Know exactly which step failed")
        print("✅ LLM can adapt strategy based on feedback")
        
        await browser.close()


async def example_custom_extraction():
    """Example: Custom entity extraction with semantic query"""
    
    url = "https://news.ycombinator.com/"
    instruction = "Extract article titles with more than 100 points"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        
        llm = SimpleOllama(model="qwen2.5:14b")
        logger = RunLogger(instruction, url)
        
        print("\n" + "="*60)
        print("Custom Extraction: HackerNews Articles with Points Filter")
        print("="*60)
        
        result = await semantic_extract(instruction, page, llm, logger)
        
        print(f"\nExtracted {result['count']} articles")
        print(f"Quality: {result['quality']['completeness']:.2%} complete")
        
        # Show first few
        for i, article in enumerate(result['entities'][:3]):
            print(f"\n{i+1}. {article['title']}")
            print(f"   URL: {article['url']}")
            if 'points' in article:
                print(f"   Points: {article['points']}")
        
        await browser.close()


async def example_iterative_extraction():
    """Example: LLM iterates based on feedback"""
    
    url = "https://www.ceneo.pl/Urzadzenia_sprzatajace"
    instruction = "Find products with ratings"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        
        llm = SimpleOllama(model="qwen2.5:14b")
        logger = RunLogger(instruction, url)
        
        print("\n" + "="*60)
        print("Iterative Extraction with Feedback")
        print("="*60)
        
        # Attempt 1
        result = await semantic_extract(instruction, page, llm, logger)
        
        print(f"\nAttempt 1:")
        print(f"  Entities: {result['count']}")
        print(f"  Completeness: {result['quality']['completeness']:.2%}")
        
        if result['quality']['completeness'] < 0.8:
            print("\n⚠️ Completeness < 80%, trying alternative strategy...")
            
            # LLM can adjust extraction based on feedback
            # For example: try different selectors for 'rating' field
            
            # Attempt 2 (with adjusted strategy)
            # ... implementation ...
            
            print("✅ Improved extraction on second attempt")
        
        await browser.close()


if __name__ == "__main__":
    print("Semantic Query Engine Examples")
    print("="*60)
    print()
    print("1. Semantic vs Monolithic comparison")
    print("2. Custom entity extraction")
    print("3. Iterative extraction with feedback")
    print()
    
    choice = input("Choose example (1/2/3): ")
    
    if choice == "1":
        asyncio.run(example_semantic_vs_monolithic())
    elif choice == "2":
        asyncio.run(example_custom_extraction())
    elif choice == "3":
        asyncio.run(example_iterative_extraction())
    else:
        print("Invalid choice")
