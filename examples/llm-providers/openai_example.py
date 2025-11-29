#!/usr/bin/env python3
"""
OpenAI Provider Example

Demonstrates using curllm with OpenAI's GPT models.
Requires: OPENAI_API_KEY environment variable

See: https://docs.litellm.ai/docs/providers/openai
"""

import asyncio
import os
from curllm_core import CurllmExecutor, LLMConfig


async def extract_with_openai():
    """Extract data using OpenAI GPT-4o-mini"""
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Set OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY='sk-...'")
        return
    
    # Create executor with OpenAI provider
    # API key is auto-detected from environment
    llm_config = LLMConfig(
        provider="openai/gpt-4o-mini",
        temperature=0.2,  # Lower for more consistent extraction
        max_tokens=2048
    )
    
    executor = CurllmExecutor(llm_config=llm_config)
    
    print("🤖 Using OpenAI GPT-4o-mini")
    print("📍 Extracting from: https://example.com")
    
    result = await executor.execute_workflow(
        instruction="Extract the page title and all paragraph text",
        url="https://example.com"
    )
    
    if result.get("success"):
        print("✅ Extraction successful")
        print(f"📄 Result: {result.get('result')}")
    else:
        print(f"❌ Failed: {result.get('error', result.get('reason'))}")


async def main():
    """Run OpenAI example"""
    print("=" * 50)
    print("curllm + OpenAI Example")
    print("=" * 50)
    
    await extract_with_openai()


if __name__ == "__main__":
    asyncio.run(main())
