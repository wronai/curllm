#!/usr/bin/env python3
"""
Example: Using Specialized Orchestrators

Demonstrates how to use the new orchestrator architecture:
- MasterOrchestrator for automatic task routing
- AuthOrchestrator for authentication tasks
- FormOrchestrator for form filling
- ExtractionOrchestrator for data extraction
"""

import os
import sys
import asyncio
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright
from curllm_core.orchestrators import (
    MasterOrchestrator,
    AuthOrchestrator,
    FormOrchestrator,
    ExtractionOrchestrator,
    TaskType
)
from curllm_core.llm_factory import get_llm


async def example_master_orchestrator():
    """Example: Using MasterOrchestrator for automatic task routing"""
    print("\n" + "=" * 60)
    print("Example 1: Master Orchestrator (Automatic Routing)")
    print("=" * 60)
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Initialize orchestrator
        llm = get_llm()
        orchestrator = MasterOrchestrator(llm=llm, page=page)
        
        # Test different task types
        tasks = [
            ("Login with email=test@example.com password=secret123", TaskType.AUTH),
            ("Fill contact form with name=John email=john@test.com", TaskType.FORM_FILL),
            ("Extract all product prices from this page", TaskType.EXTRACTION),
        ]
        
        for instruction, expected_type in tasks:
            print(f"\n📝 Instruction: {instruction}")
            
            # Analyze task (without executing)
            analysis = await orchestrator.analyze_task(instruction)
            print(f"   Detected Type: {analysis.task_type.value}")
            print(f"   Confidence: {analysis.confidence:.0%}")
            print(f"   Expected: {expected_type.value}")
            
            if analysis.task_type == expected_type:
                print("   ✅ Correct detection!")
            else:
                print("   ⚠️  Type mismatch")
        
        await browser.close()


async def example_auth_orchestrator():
    """Example: Using AuthOrchestrator directly"""
    print("\n" + "=" * 60)
    print("Example 2: Auth Orchestrator")
    print("=" * 60)
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        
        llm = get_llm()
        auth_orch = AuthOrchestrator(llm=llm, page=page)
        
        # Test credential parsing
        instructions = [
            "Login with email=user@example.com password=pass123",
            "Zaloguj się user=jan hasło=tajne",
            "Login email=test@test.com pass=abc code=123456",
        ]
        
        for instruction in instructions:
            print(f"\n📝 Instruction: {instruction}")
            creds = auth_orch._parse_credentials(instruction)
            print(f"   Parsed: {creds}")
        
        await browser.close()


async def example_form_orchestrator():
    """Example: Using FormOrchestrator"""
    print("\n" + "=" * 60)
    print("Example 3: Form Orchestrator")
    print("=" * 60)
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        
        llm = get_llm()
        form_orch = FormOrchestrator(llm=llm, page=page)
        
        # Test form data parsing
        instruction = "Fill form with name=John Doe, email=john@example.com, message=Hello world"
        print(f"\n📝 Instruction: {instruction}")
        
        data = form_orch._parse_form_data(instruction)
        print(f"   Parsed Data: {data}")
        
        await browser.close()


async def example_extraction_orchestrator():
    """Example: Using ExtractionOrchestrator"""
    print("\n" + "=" * 60)
    print("Example 4: Extraction Orchestrator")
    print("=" * 60)
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        
        llm = get_llm()
        extract_orch = ExtractionOrchestrator(llm=llm, page=page)
        
        # Test extraction type detection
        instructions = [
            "Extract product prices",
            "Get all links",
            "Find email addresses",
            "Scrape article titles",
        ]
        
        for instruction in instructions:
            print(f"\n📝 Instruction: {instruction}")
            ext_type = extract_orch._detect_extraction_type(instruction)
            print(f"   Detected Type: {ext_type}")
        
        await browser.close()


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("🎯 Orchestrator Examples")
    print("=" * 60)
    
    try:
        await example_master_orchestrator()
        await example_auth_orchestrator()
        await example_form_orchestrator()
        await example_extraction_orchestrator()
        
        print("\n" + "=" * 60)
        print("✅ All examples completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

