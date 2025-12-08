#!/usr/bin/env python3
"""
Find Hardcoded Values Script

Scans the codebase for hardcoded:
- CSS selectors
- URLs and domains
- XPath expressions
- Regex patterns
- Field labels/names
- Form element identifiers

These should be replaced with dynamic LLM-based detection
using curllm_core.element_finder, curllm_core.dom, etc.
"""

import os
import re
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Set
from collections import defaultdict


@dataclass
class HardcodedFinding:
    """A hardcoded value found in code"""
    file: str
    line: int
    type: str  # selector, url, regex, label, xpath
    value: str
    context: str  # surrounding code
    severity: str  # high, medium, low
    suggestion: str  # what to use instead


@dataclass
class FileAnalysis:
    """Analysis results for a single file"""
    path: str
    findings: List[HardcodedFinding] = field(default_factory=list)
    score: int = 0  # higher = more hardcoded values


# Patterns to detect hardcoded values
PATTERNS = {
    # CSS Selectors
    'selector': [
        r'["\'](?:div|span|input|button|a|form|table|tr|td|ul|li|nav|header|footer|article|section)\s*[\.\#\[\>][\w\-\.\#\[\]\=\"\'\s\>\:\(\)]+["\']',
        r'["\'][\.\#][\w\-]+(?:\s*[\.\#\>\s][\w\-\[\]\=\"\']+)*["\']',
        r'querySelector\s*\(\s*["\'][^"\']+["\']',
        r'querySelectorAll\s*\(\s*["\'][^"\']+["\']',
        r'\$\s*\(\s*["\'][^"\']+["\']',
    ],
    
    # URLs and domains
    'url': [
        r'https?://[\w\-\.]+\.(?:com|pl|net|org|io|eu)(?:/[\w\-\./\?\=\&]*)?',
        r'["\'](?:www\.)?[\w\-]+\.(?:com|pl|net|org|io|eu)["\']',
    ],
    
    # XPath expressions
    'xpath': [
        r'//[\w\-\@\[\]\=\"\'\/\.\*\(\)]+',
        r'xpath\s*=\s*["\'][^"\']+["\']',
    ],
    
    # Hardcoded regex patterns (complex ones)
    'regex': [
        r're\.compile\s*\(\s*r?["\'][^"\']{30,}["\']',
        r'r["\'][\^\$][\w\\\.\*\+\?\[\]\(\)\{\}\|]+[\^\$]?["\']',
    ],
    
    # Form field names/labels
    'label': [
        r'["\'](?:email|phone|telefon|imię|nazwisko|name|surname|message|wiadomość|adres|address|miasto|city|kod|zip|country|kraj)["\']',
        r'name\s*=\s*["\'][\w\-]+["\']',
        r'id\s*=\s*["\'][\w\-]+["\']',
    ],
    
    # Aria labels
    'aria': [
        r'aria-label\s*=\s*["\'][^"\']+["\']',
        r'\[aria-[\w\-]+\s*=\s*["\'][^"\']+["\'\]',
    ],
}

# Files/directories to skip
SKIP_PATTERNS = [
    '__pycache__',
    '.git',
    'venv',
    '.egg-info',
    'node_modules',
    '.pytest_cache',
    'test_',  # Skip test files
    'tests/',
    '.md',
    '.json',
    '.yaml',
    '.yml',
    '.txt',
    '.html',
    '.css',
    '.js',
    # Configuration/definition files (intentionally contain selectors)
    'dom_selectors.py',  # Centralized selector definitions with LLM fallback
    'url_patterns.py',   # URL pattern definitions
    'patterns.py',       # Pattern definitions
    'constants.py',      # Constants file
    'config.py',         # Configuration
    'llm_config.py',     # LLM configuration
]

# Known good patterns (dynamic detection)
GOOD_PATTERNS = [
    'LLMElementFinder',
    'find_element_with_llm',
    'find_link_for_goal',
    'dom_helpers',
    'element_finder',
    'DynamicPatternDetector',
    'analyze_page_type',
    # Dynamic JavaScript patterns
    '${k}',  # Template variable
    '${',    # Template string
    'keywords.forEach',
    'findField(',
    'score +=',
    'FIND_FORM_FIELDS_JS',
    'VALIDATE_FIELDS_JS',
    'detect_',  # Dynamic detection functions
    'find_',    # Dynamic find functions
]


def should_skip(path: str) -> bool:
    """Check if file should be skipped"""
    for pattern in SKIP_PATTERNS:
        if pattern in path:
            return True
    return False


def get_severity(finding_type: str, value: str) -> str:
    """Determine severity based on type and value"""
    if finding_type == 'selector' and len(value) > 50:
        return 'high'
    if finding_type == 'url' and 'http' in value:
        return 'high'
    if finding_type == 'xpath':
        return 'high'
    if finding_type == 'regex' and len(value) > 40:
        return 'medium'
    return 'low'


def get_suggestion(finding_type: str) -> str:
    """Get suggestion for replacing hardcoded value"""
    suggestions = {
        'selector': 'Use curllm_core.element_finder.LLMElementFinder.find_element() for dynamic element detection',
        'url': 'Use curllm_core.url_resolution.UrlResolver.find_url_for_goal() for dynamic URL discovery',
        'xpath': 'Use curllm_core.dom.find_elements_by_role() or LLMElementFinder for dynamic element finding',
        'regex': 'Use curllm_core.detection.DynamicPatternDetector for pattern detection',
        'label': 'Use curllm_core.form_fill for intelligent form field matching',
        'aria': 'Use curllm_core.dom.find_links_by_aria() for aria-based element finding',
    }
    return suggestions.get(finding_type, 'Consider using LLM-based dynamic detection')


def analyze_file(filepath: str) -> FileAnalysis:
    """Analyze a single file for hardcoded values"""
    analysis = FileAnalysis(path=filepath)
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return analysis
    
    for line_num, line in enumerate(lines, 1):
        # Skip if line contains good patterns (already using dynamic detection)
        if any(good in line for good in GOOD_PATTERNS):
            continue
        
        # Skip comments
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('"""'):
            continue
        
        for finding_type, patterns in PATTERNS.items():
            for pattern in patterns:
                try:
                    matches = re.findall(pattern, line, re.IGNORECASE)
                    for match in matches:
                        # Skip if it's a variable or function parameter
                        if match.startswith('$') or '{' in match:
                            continue
                        
                        finding = HardcodedFinding(
                            file=filepath,
                            line=line_num,
                            type=finding_type,
                            value=match[:100],  # Truncate long values
                            context=line.strip()[:150],
                            severity=get_severity(finding_type, match),
                            suggestion=get_suggestion(finding_type),
                        )
                        analysis.findings.append(finding)
                        
                        # Score based on severity
                        if finding.severity == 'high':
                            analysis.score += 3
                        elif finding.severity == 'medium':
                            analysis.score += 2
                        else:
                            analysis.score += 1
                except re.error:
                    pass
    
    return analysis


def scan_directory(root_dir: str) -> List[FileAnalysis]:
    """Scan directory for Python files with hardcoded values"""
    results = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip certain directories
        dirnames[:] = [d for d in dirnames if not should_skip(d)]
        
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            
            filepath = os.path.join(dirpath, filename)
            if should_skip(filepath):
                continue
            
            analysis = analyze_file(filepath)
            if analysis.findings:
                results.append(analysis)
    
    # Sort by score (most hardcoded values first)
    results.sort(key=lambda x: x.score, reverse=True)
    return results


def generate_report(results: List[FileAnalysis], output_path: str = None):
    """Generate analysis report"""
    total_findings = sum(len(r.findings) for r in results)
    high_severity = sum(1 for r in results for f in r.findings if f.severity == 'high')
    medium_severity = sum(1 for r in results for f in r.findings if f.severity == 'medium')
    
    report = []
    report.append("=" * 80)
    report.append("HARDCODED VALUES ANALYSIS REPORT")
    report.append("=" * 80)
    report.append("")
    report.append(f"Total files with hardcoded values: {len(results)}")
    report.append(f"Total findings: {total_findings}")
    report.append(f"  - High severity: {high_severity}")
    report.append(f"  - Medium severity: {medium_severity}")
    report.append(f"  - Low severity: {total_findings - high_severity - medium_severity}")
    report.append("")
    
    # Group by type
    by_type = defaultdict(list)
    for r in results:
        for f in r.findings:
            by_type[f.type].append(f)
    
    report.append("FINDINGS BY TYPE:")
    report.append("-" * 40)
    for ftype, findings in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
        report.append(f"  {ftype}: {len(findings)} occurrences")
    report.append("")
    
    # Top 20 files to refactor
    report.append("TOP 20 FILES TO REFACTOR (by score):")
    report.append("-" * 40)
    for i, r in enumerate(results[:20], 1):
        report.append(f"  {i:2}. {r.path} (score: {r.score}, findings: {len(r.findings)})")
    report.append("")
    
    # Detailed findings for high severity
    report.append("HIGH SEVERITY FINDINGS:")
    report.append("-" * 40)
    for r in results:
        for f in r.findings:
            if f.severity == 'high':
                report.append(f"\n  File: {f.file}:{f.line}")
                report.append(f"  Type: {f.type}")
                report.append(f"  Value: {f.value[:80]}...")
                report.append(f"  Suggestion: {f.suggestion}")
    
    report_text = "\n".join(report)
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report_text)
        print(f"Report saved to: {output_path}")
    
    return report_text


def generate_json(results: List[FileAnalysis], output_path: str):
    """Generate JSON output for further processing"""
    data = {
        'summary': {
            'total_files': len(results),
            'total_findings': sum(len(r.findings) for r in results),
        },
        'files': [
            {
                'path': r.path,
                'score': r.score,
                'findings': [asdict(f) for f in r.findings]
            }
            for r in results
        ]
    }
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"JSON saved to: {output_path}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Find hardcoded values in curllm codebase')
    parser.add_argument('--dir', default='curllm_core', help='Directory to scan')
    parser.add_argument('--output', default='hardcoded_report.txt', help='Output report file')
    parser.add_argument('--json', default='hardcoded_report.json', help='JSON output file')
    parser.add_argument('--top', type=int, default=20, help='Number of top files to show')
    
    args = parser.parse_args()
    
    print(f"Scanning {args.dir} for hardcoded values...")
    results = scan_directory(args.dir)
    
    report = generate_report(results, args.output)
    print(report)
    
    generate_json(results, args.json)
    
    # Print refactoring priority list
    print("\n" + "=" * 80)
    print("FILES TO REFACTOR (priority order):")
    print("=" * 80)
    for i, r in enumerate(results[:args.top], 1):
        rel_path = r.path.replace('curllm_core/', '')
        high = sum(1 for f in r.findings if f.severity == 'high')
        print(f"{i:2}. {rel_path:<50} | score: {r.score:3} | high: {high}")


if __name__ == '__main__':
    main()
