"""
Feedback CLI

Command-line interface for providing feedback on extraction results.

Usage:
    curllm-feedback rate <run_id> --rating 4 --hint "Prices are correct"
    curllm-feedback show-hints <domain>
    curllm-feedback stats
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Provide feedback on curllm extraction results"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Rate command
    rate_parser = subparsers.add_parser("rate", help="Rate an extraction result")
    rate_parser.add_argument("run_id", help="Run ID from extraction (e.g., from run_log)")
    rate_parser.add_argument("-r", "--rating", type=int, required=True, 
                            choices=[1, 2, 3, 4, 5],
                            help="Rating 1-5 (1=terrible, 5=perfect)")
    rate_parser.add_argument("-H", "--hint", default="",
                            help="Improvement hint")
    rate_parser.add_argument("-m", "--missing", nargs="*", default=[],
                            help="Missing fields (e.g., -m image description)")
    rate_parser.add_argument("-u", "--url", default="",
                            help="URL that was extracted")
    rate_parser.add_argument("-t", "--task", default="extract_products",
                            help="Task type")
    
    # Show hints command
    hints_parser = subparsers.add_parser("hints", help="Show learned hints for a domain")
    hints_parser.add_argument("domain", help="Domain (e.g., ceneo.pl)")
    hints_parser.add_argument("-t", "--task", help="Filter by task type")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show feedback statistics")
    stats_parser.add_argument("-d", "--domain", help="Filter by domain")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export hints to JSON")
    export_parser.add_argument("output", help="Output file path")
    
    # Issues command
    issues_parser = subparsers.add_parser("issues", help="Show common issues")
    issues_parser.add_argument("-t", "--task", help="Filter by task type")
    issues_parser.add_argument("-n", "--limit", type=int, default=10,
                              help="Number of issues to show")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Import here to avoid circular imports
    from curllm_core.feedback import FeedbackSystem, Feedback
    
    system = FeedbackSystem()
    
    if args.command == "rate":
        feedback = Feedback(
            url=args.url or f"run://{args.run_id}",
            task=args.task,
            rating=args.rating,
            hint=args.hint,
            missing_fields=args.missing,
            run_id=args.run_id,
        )
        feedback_id = system.record_feedback(feedback)
        print(f"✅ Recorded feedback #{feedback_id}")
        print(f"   Rating: {'⭐' * args.rating}{'☆' * (5 - args.rating)}")
        if args.hint:
            print(f"   Hint: {args.hint}")
        return 0
    
    elif args.command == "hints":
        hints = system.get_hints_for_url(f"https://{args.domain}", args.task)
        if hints:
            print(f"💡 Learned hints for {args.domain}:")
            for i, hint in enumerate(hints, 1):
                print(f"   {i}. {hint}")
        else:
            print(f"No hints found for {args.domain}")
        return 0
    
    elif args.command == "stats":
        stats = system.get_feedback_summary(args.domain)
        print("📊 Feedback Statistics:")
        print(f"   Total feedback: {stats['total_feedback']}")
        print(f"   Average rating: {'⭐' * round(stats['average_rating'])} ({stats['average_rating']:.1f})")
        print(f"   Good results (4-5): {stats['good_results']}")
        print(f"   Bad results (1-2): {stats['bad_results']}")
        return 0
    
    elif args.command == "export":
        system.export_hints(args.output)
        print(f"✅ Exported hints to {args.output}")
        return 0
    
    elif args.command == "issues":
        issues = system.get_common_issues(args.task, args.limit)
        if issues:
            print("🔍 Common Issues:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. [{issue['occurrences']}x] {issue['hint']}")
        else:
            print("No issues recorded yet")
        return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
