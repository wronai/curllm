#!/usr/bin/env python3
"""
generate_report.py - Generate Markdown report from test results
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Colors for terminal output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def load_results():
    """Load all JSON results from results/ directory."""
    results_dir = Path("results")
    results = {}
    
    for json_file in results_dir.glob("*.json"):
        distro = json_file.stem
        try:
            with open(json_file, 'r') as f:
                results[distro] = json.load(f)
        except Exception as e:
            print(f"{RED}Error loading {json_file}: {e}{NC}")
    
    return results

def generate_markdown(results):
    """Generate Markdown report from results."""
    
    md = []
    
    # Header
    md.append("# curllm - Linux Cross-Platform Test Results")
    md.append("")
    md.append(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    md.append("")
    md.append("---")
    md.append("")
    
    # Summary Table
    md.append("## Summary")
    md.append("")
    md.append("| Distribution | Version | Python | Tests Passed | Tests Failed | Duration | Status |")
    md.append("|--------------|---------|--------|--------------|--------------|----------|--------|")
    
    total_passed = 0
    total_failed = 0
    total_duration = 0
    
    for distro, data in sorted(results.items()):
        status = "✅ PASS" if data['tests_failed'] == 0 else "❌ FAIL"
        md.append(f"| {data['distro'].capitalize()} | {data['version']} | {data['python_version']} | {data['tests_passed']} | {data['tests_failed']} | {data['duration']}s | {status} |")
        
        total_passed += data['tests_passed']
        total_failed += data['tests_failed']
        total_duration += data['duration']
    
    md.append("")
    md.append(f"**Total Tests:** {total_passed + total_failed}")
    md.append(f"**Total Passed:** {total_passed}")
    md.append(f"**Total Failed:** {total_failed}")
    md.append(f"**Total Duration:** {total_duration}s")
    md.append("")
    
    # Overall status
    if total_failed == 0:
        md.append("### ✅ Overall Status: ALL TESTS PASSED")
    else:
        md.append("### ❌ Overall Status: SOME TESTS FAILED")
    
    md.append("")
    md.append("---")
    md.append("")
    
    # Detailed Results
    md.append("## Detailed Results")
    md.append("")
    
    for distro, data in sorted(results.items()):
        md.append(f"### {data['distro'].capitalize()} {data['version']}")
        md.append("")
        md.append(f"- **Python Version:** {data['python_version']}")
        md.append(f"- **Tests Passed:** {data['tests_passed']}")
        md.append(f"- **Tests Failed:** {data['tests_failed']}")
        md.append(f"- **Duration:** {data['duration']}s")
        md.append(f"- **Timestamp:** {data['timestamp']}")
        md.append("")
        
        # Test details
        if 'tests' in data and data['tests']:
            md.append("#### Test Details")
            md.append("")
            md.append("| Test | Status |")
            md.append("|------|--------|")
            
            for test in data['tests']:
                status_icon = "✅" if test['status'] == 'pass' else "❌"
                test_name = test['name']
                md.append(f"| {test_name} | {status_icon} |")
            
            md.append("")
            
            # Failed tests details
            failed_tests = [t for t in data['tests'] if t['status'] == 'fail']
            if failed_tests:
                md.append("#### Failed Tests")
                md.append("")
                for test in failed_tests:
                    md.append(f"- **{test['name']}**")
                    if 'error' in test:
                        md.append(f"  - Error: `{test['error']}`")
                md.append("")
        
        md.append("---")
        md.append("")
    
    # Platform Compatibility Matrix
    md.append("## Platform Compatibility Matrix")
    md.append("")
    md.append("| Feature | Ubuntu | Debian | Fedora | Alpine | Status |")
    md.append("|---------|--------|--------|--------|--------|--------|")
    
    # Extract common test names
    all_tests = set()
    for data in results.values():
        if 'tests' in data:
            for test in data['tests']:
                all_tests.add(test['name'])
    
    for test_name in sorted(all_tests):
        row = [test_name]
        all_pass = True
        
        for distro in ['ubuntu', 'debian', 'fedora', 'alpine']:
            if distro in results:
                test = next((t for t in results[distro].get('tests', []) if t['name'] == test_name), None)
                if test:
                    if test['status'] == 'pass':
                        row.append("✅")
                    else:
                        row.append("❌")
                        all_pass = False
                else:
                    row.append("➖")
                    all_pass = False
            else:
                row.append("❓")
                all_pass = False
        
        row.append("✅ ALL" if all_pass else "⚠️ PARTIAL")
        md.append("| " + " | ".join(row) + " |")
    
    md.append("")
    md.append("**Legend:**")
    md.append("- ✅ = Test passed")
    md.append("- ❌ = Test failed")
    md.append("- ➖ = Test not run")
    md.append("- ❓ = Platform not tested")
    md.append("")
    
    # Recommendations
    md.append("---")
    md.append("")
    md.append("## Recommendations")
    md.append("")
    
    if total_failed == 0:
        md.append("✅ **curllm is ready for production on all tested Linux distributions!**")
        md.append("")
        md.append("All platforms passed all tests. The package can be safely installed via PyPI on:")
        md.append("")
        for distro, data in sorted(results.items()):
            md.append(f"- {data['distro'].capitalize()} {data['version']} (Python {data['python_version']})")
    else:
        md.append("⚠️ **Some issues detected on certain platforms:**")
        md.append("")
        for distro, data in sorted(results.items()):
            if data['tests_failed'] > 0:
                md.append(f"- **{data['distro'].capitalize()} {data['version']}:** {data['tests_failed']} test(s) failed")
        md.append("")
        md.append("Please review failed tests above and fix issues before release.")
    
    md.append("")
    md.append("---")
    md.append("")
    
    # Installation Instructions
    md.append("## Installation Instructions")
    md.append("")
    md.append("### From PyPI")
    md.append("")
    md.append("```bash")
    md.append("pip install curllm")
    md.append("```")
    md.append("")
    md.append("### From Source")
    md.append("")
    md.append("```bash")
    md.append("git clone https://github.com/wronai/curllm.git")
    md.append("cd curllm")
    md.append("make install")
    md.append("```")
    md.append("")
    
    # System Requirements
    md.append("## System Requirements")
    md.append("")
    md.append("Based on test results, curllm requires:")
    md.append("")
    md.append("- **Python:** 3.8+ (tested with " + ", ".join(sorted(set(d['python_version'] for d in results.values()))) + ")")
    md.append("- **OS:** Linux (Ubuntu, Debian, Fedora, Alpine supported)")
    md.append("- **Dependencies:** pip, venv, build tools")
    md.append("- **Optional:** Docker (for containerized deployment)")
    md.append("")
    
    # Footer
    md.append("---")
    md.append("")
    md.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*")
    md.append("")
    
    return "\n".join(md)

def main():
    """Main function."""
    print(f"{BLUE}Generating Markdown report...{NC}")
    
    # Load results
    results = load_results()
    
    if not results:
        print(f"{RED}No test results found in results/ directory{NC}")
        return 1
    
    print(f"{GREEN}Loaded results from {len(results)} distribution(s){NC}")
    
    # Generate report
    markdown = generate_markdown(results)
    
    # Save report
    output_file = "LINUX_TEST_RESULTS.md"
    with open(output_file, 'w') as f:
        f.write(markdown)
    
    print(f"{GREEN}✓ Report saved to {output_file}{NC}")
    
    # Also copy to project root
    try:
        import shutil
        shutil.copy(output_file, "../../LINUX_TEST_RESULTS.md")
        print(f"{GREEN}✓ Report copied to project root{NC}")
    except Exception as e:
        print(f"{YELLOW}Warning: Could not copy to root: {e}{NC}")
    
    return 0

if __name__ == "__main__":
    exit(main())
