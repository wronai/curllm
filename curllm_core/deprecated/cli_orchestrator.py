#!/usr/bin/env python3
"""
CLI for Orchestrator - Execute complex natural language commands

Usage:
    python -m curllm_core.cli_orchestrator "Wejdź na example.com i wyślij formularz..."
    
    # Dry run (parse and plan only)
    python -m curllm_core.cli_orchestrator --dry-run "..."
    
    # With visible browser
    python -m curllm_core.cli_orchestrator --visible "..."
"""

import asyncio
import argparse
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from curllm_core.orchestrator import Orchestrator, OrchestratorConfig


def parse_args():
    parser = argparse.ArgumentParser(
        description="Execute complex natural language commands with curllm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Wejdź na prototypowanie.pl i wyślij formularz z email info@test.com"
  %(prog)s --dry-run "Otwórz morele.net i znajdź RAM DDR5"
  %(prog)s --visible "Przejdź do x-kom.pl i dodaj laptop do koszyka"
        """
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        help="Natural language command to execute"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and plan only, don't execute"
    )
    
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Show browser window (not headless)"
    )
    
    parser.add_argument(
        "--no-stealth",
        action="store_true",
        help="Disable stealth mode"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds (default: 120)"
    )
    
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="Directory for logs (default: logs)"
    )
    
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Only show parsed command, don't plan or execute"
    )
    
    return parser.parse_args()


async def main():
    args = parse_args()
    
    if not args.command:
        print("Usage: curllm_orchestrator 'Your command here'")
        print("\nExamples:")
        print("  'Wejdź na prototypowanie.pl i wyślij formularz kontaktowy'")
        print("  'Otwórz morele.net i znajdź pamięci RAM DDR5'")
        print("\nOptions:")
        print("  --dry-run   Parse and plan only")
        print("  --visible   Show browser window")
        return 1
    
    # Parse only mode
    if args.parse_only:
        from curllm_core.command_parser import CommandParser
        
        parser = CommandParser()
        parsed = parser.parse(args.command)
        
        print("\n📝 PARSED COMMAND:")
        print(f"   Domain: {parsed.target_domain}")
        print(f"   URL: {parsed.get_url()}")
        print(f"   Goal: {parsed.primary_goal.value}")
        print(f"   Email: {parsed.form_data.email}")
        print(f"   Name: {parsed.form_data.name}")
        print(f"   Phone: {parsed.form_data.phone}")
        print(f"   Message: {parsed.form_data.message}")
        print(f"   Search: {parsed.search_query}")
        print(f"   Confidence: {parsed.confidence:.0%}")
        print(f"\n   Notes:")
        for note in parsed.parsing_notes:
            print(f"   - {note}")
        return 0
    
    # Create config
    # Resolve log_dir relative to current working directory (not script location)
    log_dir = args.log_dir
    if not os.path.isabs(log_dir):
        log_dir = os.path.join(os.getcwd(), log_dir)
    
    config = OrchestratorConfig(
        headless=not args.visible,
        stealth_mode=not args.no_stealth,
        timeout_seconds=args.timeout,
        log_dir=log_dir,
        dry_run=args.dry_run
    )
    
    # Execute
    print(f"\n{'='*60}")
    print(f"🚀 CURLLM ORCHESTRATOR")
    print(f"{'='*60}")
    print(f"Command: {args.command[:80]}...")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
    print(f"Browser: {'Visible' if args.visible else 'Headless'}")
    print(f"{'='*60}\n")
    
    orchestrator = Orchestrator(config)
    result = await orchestrator.execute(args.command)
    
    # Print results
    print(f"\n{'='*60}")
    print(f"📊 RESULT: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
    print(f"{'='*60}")
    
    if result.parsed:
        print(f"\n📝 Parsed:")
        print(f"   Domain: {result.parsed.target_domain}")
        print(f"   Goal: {result.parsed.primary_goal.value}")
        print(f"   Confidence: {result.parsed.confidence:.0%}")
    
    if result.plan:
        print(f"\n📋 Plan ({len(result.plan.steps)} steps):")
        for i, step in enumerate(result.plan.steps):
            status = "✅" if step.status.value == "completed" else "❌" if step.status.value == "failed" else "⏳"
            print(f"   {i+1}. {status} {step.step_type.value}: {step.description}")
    
    if result.step_results and not args.dry_run:
        print(f"\n⚡ Execution:")
        for sr in result.step_results:
            status = "✅" if sr.success else "❌"
            print(f"   {sr.step_index + 1}. {status} {sr.step_type} ({sr.duration_ms}ms)")
            if sr.error:
                print(f"      Error: {sr.error}")
            if sr.step_type == "screenshot" and sr.screenshot_path:
                print(f"      Screenshot: {sr.screenshot_path}")
    
    if result.final_url:
        print(f"\n🌐 Final URL: {result.final_url}")
    
    if result.extracted_data:
        print(f"\n📦 Extracted Data:")
        import json
        print(json.dumps(result.extracted_data, indent=2, ensure_ascii=False)[:500])
    
    if result.error:
        print(f"\n❌ Error: {result.error}")
    
    if result.log_path:
        print(f"\n📄 Log: {result.log_path}")
    
    print(f"\n⏱️ Duration: {result.duration_ms}ms")
    print(f"{'='*60}\n")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
