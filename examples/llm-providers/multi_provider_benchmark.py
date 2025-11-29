#!/usr/bin/env python3
"""
Multi-Provider Benchmark

Compare response times and quality across different LLM providers.
Only tests providers with API keys set in environment.

Supported providers:
- ollama (local, always available)
- openai (OPENAI_API_KEY)
- anthropic (ANTHROPIC_API_KEY)
- gemini (GEMINI_API_KEY)
- groq (GROQ_API_KEY)
- deepseek (DEEPSEEK_API_KEY)
"""

import asyncio
import os
import time
from curllm_core import CurllmExecutor, LLMConfig


async def benchmark_provider(name: str, llm_config: LLMConfig, url: str, instruction: str):
    """Benchmark a single provider"""
    print(f"\n🔄 Testing: {name}")
    
    try:
        start = time.time()
        
        executor = CurllmExecutor(llm_config=llm_config)
        result = await executor.execute_workflow(
            instruction=instruction,
            url=url
        )
        
        elapsed = time.time() - start
        
        return {
            "provider": name,
            "success": result.get("success", False),
            "time": elapsed,
            "steps": result.get("steps_taken", 0),
            "error": result.get("error") if not result.get("success") else None
        }
        
    except Exception as e:
        return {
            "provider": name,
            "success": False,
            "error": str(e)
        }


async def run_benchmark():
    """Run benchmark across available providers"""
    
    # Define providers to test
    providers = []
    
    # Ollama (local) - always available
    providers.append(("ollama/qwen2.5:7b", LLMConfig(provider="ollama/qwen2.5:7b")))
    
    # Cloud providers - only if API key is set
    if os.getenv("OPENAI_API_KEY"):
        providers.append(("openai/gpt-4o-mini", LLMConfig(provider="openai/gpt-4o-mini")))
    
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append(("anthropic/claude-3-haiku", LLMConfig(provider="anthropic/claude-3-haiku-20240307")))
    
    if os.getenv("GEMINI_API_KEY"):
        providers.append(("gemini/gemini-2.0-flash", LLMConfig(provider="gemini/gemini-2.0-flash")))
    
    if os.getenv("GROQ_API_KEY"):
        providers.append(("groq/llama3-8b", LLMConfig(provider="groq/llama3-8b-8192")))
    
    if os.getenv("DEEPSEEK_API_KEY"):
        providers.append(("deepseek/deepseek-chat", LLMConfig(provider="deepseek/deepseek-chat")))
    
    print(f"📊 Benchmarking {len(providers)} provider(s)")
    print(f"   Available: {', '.join(p[0] for p in providers)}")
    
    # Test parameters
    test_url = "https://example.com"
    test_instruction = "Extract the page title and main paragraph text"
    
    # Run benchmarks
    results = []
    for name, config in providers:
        result = await benchmark_provider(name, config, test_url, test_instruction)
        results.append(result)
    
    # Print results
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    
    for r in sorted(results, key=lambda x: x.get("time", 999)):
        status = "✅" if r.get("success") else "❌"
        time_str = f"{r.get('time', 0):.2f}s" if 'time' in r else "N/A"
        error = f" - {r.get('error')}" if r.get("error") else ""
        print(f"  {status} {r['provider']}: {time_str}{error}")
    
    # Summary
    successful = [r for r in results if r.get("success")]
    if successful:
        fastest = min(successful, key=lambda x: x.get("time", 999))
        print(f"\n🏆 Fastest: {fastest['provider']} ({fastest['time']:.2f}s)")


async def main():
    """Main entry point"""
    print("=" * 60)
    print("curllm Multi-Provider Benchmark")
    print("=" * 60)
    print("\nSet API keys to enable more providers:")
    print("  export OPENAI_API_KEY='sk-...'")
    print("  export ANTHROPIC_API_KEY='sk-ant-...'")
    print("  export GEMINI_API_KEY='...'")
    print("  export GROQ_API_KEY='gsk_...'")
    
    await run_benchmark()


if __name__ == "__main__":
    asyncio.run(main())
