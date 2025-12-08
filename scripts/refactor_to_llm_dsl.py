#!/usr/bin/env python3
"""
Refactor to LLM-DSL Architecture

This script:
1. Reads hardcoded_report.json
2. Analyzes files with hardcoded values
3. Generates refactoring suggestions using LLM-DSL approach
4. Can automatically apply refactoring (with --apply flag)

Usage:
    python scripts/refactor_to_llm_dsl.py                    # Analyze and suggest
    python scripts/refactor_to_llm_dsl.py --apply            # Apply refactoring
    python scripts/refactor_to_llm_dsl.py --file path/to.py  # Analyze specific file
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class RefactoringSuggestion:
    """A single refactoring suggestion"""
    file: str
    line: int
    old_code: str
    new_code: str
    reason: str
    confidence: float


@dataclass
class FileAnalysis:
    """Analysis result for a file"""
    path: str
    score: int
    hardcoded_count: int
    suggestions: List[RefactoringSuggestion]
    

# Patterns to detect hardcoded values
HARDCODED_PATTERNS = {
    'selector': [
        r'querySelector\([\'"]([^"\']+)[\'"]\)',
        r'querySelectorAll\([\'"]([^"\']+)[\'"]\)',
        r'\$\([\'"]([^"\']+)[\'"]\)',
        r'\.locator\([\'"]([^"\']+)[\'"]\)',
        r'\.query_selector\([\'"]([^"\']+)[\'"]\)',
    ],
    'url_pattern': [
        r'https?://[a-zA-Z0-9.-]+(?:/[^\s\'"]*)?',
    ],
    'keyword_list': [
        r'\[[\'"](name|email|phone|message|subject)[\'"](?:,\s*[\'"][a-z]+[\'"])+\]',
        r'(?:keywords?|labels?|fields?)\s*=\s*\[[^\]]+\]',
    ],
}

# LLM-DSL replacements
LLM_DSL_REPLACEMENTS = {
    # Selector patterns -> LLM-DSL
    r'document\.querySelector\([\'"]([^"\']+)[\'"]\)': 
        'await atoms.find_element_by_purpose("{purpose}")',
    
    r'document\.querySelectorAll\([\'"]([^"\']+)[\'"]\)':
        'await atoms.find_elements_by_pattern("{purpose}")',
    
    r'page\.query_selector\([\'"]([^"\']+)[\'"]\)':
        'await dsl.execute("find_element", purpose="{purpose}")',
    
    # Field keyword lists -> LLM query
    r'for\s+\w+\s+in\s+\[[\'"][a-z]+[\'"](?:,\s*[\'"][a-z]+[\'"])+\]':
        'for field in await atoms.detect_form_fields(form_context)',
    
    # URL patterns -> dynamic resolution
    r'https?://([a-zA-Z0-9.-]+)/([^\s\'"]+)':
        'await url_resolver.resolve_dynamic("{domain}", "{path}")',
}


class RefactorAnalyzer:
    """Analyzes files for refactoring opportunities"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.report_path = self.project_root / "hardcoded_report.json"
    
    def load_report(self) -> Dict:
        """Load hardcoded report if exists"""
        if self.report_path.exists():
            with open(self.report_path) as f:
                return json.load(f)
        return {"files": []}
    
    def analyze_file(self, file_path: str) -> FileAnalysis:
        """Analyze a single file for refactoring opportunities"""
        full_path = self.project_root / file_path
        if not full_path.exists():
            return FileAnalysis(path=file_path, score=0, hardcoded_count=0, suggestions=[])
        
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
        
        suggestions = []
        hardcoded_count = 0
        
        for i, line in enumerate(lines, 1):
            line_suggestions = self._analyze_line(file_path, i, line)
            suggestions.extend(line_suggestions)
            hardcoded_count += len(line_suggestions)
        
        # Calculate score based on findings
        score = sum(s.confidence * 10 for s in suggestions)
        
        return FileAnalysis(
            path=file_path,
            score=int(score),
            hardcoded_count=hardcoded_count,
            suggestions=suggestions
        )
    
    def _analyze_line(self, file_path: str, line_num: int, line: str) -> List[RefactoringSuggestion]:
        """Analyze a single line for hardcoded patterns"""
        suggestions = []
        
        # Check for querySelector patterns
        for pattern in HARDCODED_PATTERNS['selector']:
            matches = re.finditer(pattern, line)
            for match in matches:
                selector = match.group(1) if match.groups() else match.group(0)
                suggestions.append(RefactoringSuggestion(
                    file=file_path,
                    line=line_num,
                    old_code=match.group(0),
                    new_code=self._generate_llm_dsl_replacement(selector, 'selector'),
                    reason=f"Hardcoded selector: {selector}",
                    confidence=0.8
                ))
        
        # Check for keyword lists
        keyword_list_pattern = r'\[[\'"](?:name|email|phone|message)[\'"](?:,\s*[\'"][a-z]+[\'"])+\]'
        if re.search(keyword_list_pattern, line):
            suggestions.append(RefactoringSuggestion(
                file=file_path,
                line=line_num,
                old_code=line.strip(),
                new_code='# Use: await atoms.detect_form_fields(form_context)',
                reason="Hardcoded keyword list - should use LLM to detect field purposes",
                confidence=0.7
            ))
        
        return suggestions
    
    def _generate_llm_dsl_replacement(self, value: str, value_type: str) -> str:
        """Generate LLM-DSL replacement code"""
        if value_type == 'selector':
            # Infer purpose from selector
            purpose = self._infer_purpose_from_selector(value)
            return f'await dsl.find_element(purpose="{purpose}")'
        return f'# TODO: Replace with LLM-DSL query'
    
    def _infer_purpose_from_selector(self, selector: str) -> str:
        """Infer element purpose from selector"""
        selector_lower = selector.lower()
        
        if 'email' in selector_lower or 'mail' in selector_lower:
            return 'email_input'
        if 'name' in selector_lower:
            return 'name_input'
        if 'phone' in selector_lower or 'tel' in selector_lower:
            return 'phone_input'
        if 'message' in selector_lower or 'textarea' in selector_lower:
            return 'message_input'
        if 'submit' in selector_lower or 'button' in selector_lower:
            return 'submit_button'
        if 'search' in selector_lower:
            return 'search_input'
        if 'error' in selector_lower:
            return 'error_message'
        if 'success' in selector_lower:
            return 'success_message'
        
        return 'element'
    
    def get_priority_files(self, limit: int = 20) -> List[FileAnalysis]:
        """Get files ordered by refactoring priority"""
        report = self.load_report()
        
        analyses = []
        for file_info in report.get('files', [])[:limit]:
            analysis = self.analyze_file(file_info['path'])
            analyses.append(analysis)
        
        # Sort by score (highest first)
        analyses.sort(key=lambda a: a.score, reverse=True)
        return analyses


class LLMDSLMigrator:
    """Generates LLM-DSL migration code"""
    
    @staticmethod
    def generate_element_finder_call(purpose: str, context: str = "") -> str:
        """Generate LLM-DSL element finder call"""
        return f'''
# LLM-DSL: Dynamic element finding
element = await self.dsl.execute("find_element", {{
    "purpose": "{purpose}",
    "context": page_context,
    "use_llm": True,
    "fallback_strategies": ["semantic", "visual", "structural"]
}})
'''

    @staticmethod
    def generate_form_field_detection() -> str:
        """Generate LLM-DSL form field detection"""
        return '''
# LLM-DSL: Dynamic form field detection
form_fields = await self.dsl.execute("analyze_form", {
    "context": form_html,
    "detect_purposes": True,
    "use_llm": True
})

for field in form_fields.data:
    field_type = field["purpose"]  # email, name, phone, etc.
    element = field["element"]
    # Fill based on detected purpose
'''

    @staticmethod
    def generate_url_resolver_call(goal: str) -> str:
        """Generate LLM-DSL URL resolver call"""
        return f'''
# LLM-DSL: Dynamic URL resolution
url = await self.dsl.execute("resolve_url", {{
    "goal": "{goal}",
    "page_context": await atoms.analyze_page_structure(),
    "use_sitemap": True,
    "use_link_analysis": True
}})
'''


def print_analysis_report(analyses: List[FileAnalysis]):
    """Print formatted analysis report"""
    print("\n" + "=" * 80)
    print("LLM-DSL REFACTORING ANALYSIS")
    print("=" * 80)
    
    total_suggestions = sum(a.hardcoded_count for a in analyses)
    print(f"\nTotal files analyzed: {len(analyses)}")
    print(f"Total refactoring suggestions: {total_suggestions}")
    
    print("\n" + "-" * 80)
    print("TOP FILES TO REFACTOR:")
    print("-" * 80)
    
    for i, analysis in enumerate(analyses[:20], 1):
        print(f"\n{i:2}. {analysis.path}")
        print(f"    Score: {analysis.score}, Hardcoded values: {analysis.hardcoded_count}")
        
        if analysis.suggestions[:3]:
            print(f"    Sample suggestions:")
            for s in analysis.suggestions[:3]:
                print(f"      Line {s.line}: {s.reason[:60]}...")


def generate_migration_plan(analyses: List[FileAnalysis]) -> str:
    """Generate a migration plan document"""
    plan = """
# LLM-DSL Migration Plan

## Overview
This plan outlines the migration from hardcoded selectors/keywords to LLM-DSL architecture.

## Architecture Changes

### Before (Hardcoded)
```python
# Hardcoded selector
element = document.querySelector('input[name="email"]')

# Hardcoded keyword list
for field in ["name", "email", "phone"]:
    # ...
```

### After (LLM-DSL)
```python
# LLM-driven element finding
element = await dsl.execute("find_element", {
    "purpose": "email_input",
    "context": page_context
})

# LLM-driven field detection
fields = await dsl.execute("analyze_form", {
    "form_context": form_html,
    "detect_purposes": True
})
for field in fields.data:
    # ...
```

## Files to Migrate (Priority Order)

"""
    
    for i, analysis in enumerate(analyses[:20], 1):
        plan += f"\n### {i}. `{analysis.path}`\n"
        plan += f"- Score: {analysis.score}\n"
        plan += f"- Hardcoded values: {analysis.hardcoded_count}\n"
        
        if analysis.suggestions[:5]:
            plan += "- Key changes needed:\n"
            for s in analysis.suggestions[:5]:
                plan += f"  - Line {s.line}: {s.reason}\n"
    
    plan += """
## Migration Steps

1. **Phase 1: Core Modules** (atoms.py, executor.py)
   - Ensure all atomic functions are LLM-queryable
   - Add fallback strategies for each function

2. **Phase 2: Form Handling** (form_fill.py, field_filler.py)
   - Replace hardcoded field keywords with LLM detection
   - Use semantic analysis for form understanding

3. **Phase 3: URL Resolution** (url_resolver.py, dom_helpers.py)
   - Replace hardcoded URL patterns with LLM analysis
   - Use page structure analysis for navigation

4. **Phase 4: Orchestrators** (orchestrator.py, steps.py)
   - Integrate LLM-DSL for all element interactions
   - Add context-aware fallbacks

## Testing

After each phase:
1. Run `make test` to verify no regressions
2. Run example scripts to verify functionality
3. Compare success rates before/after
"""
    
    return plan


def main():
    parser = argparse.ArgumentParser(description="Refactor to LLM-DSL architecture")
    parser.add_argument("--file", help="Analyze specific file")
    parser.add_argument("--apply", action="store_true", help="Apply refactoring")
    parser.add_argument("--plan", action="store_true", help="Generate migration plan")
    parser.add_argument("--output", default="migration_plan.md", help="Output file for plan")
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    analyzer = RefactorAnalyzer(str(project_root))
    
    if args.file:
        # Analyze specific file
        analysis = analyzer.analyze_file(args.file)
        print_analysis_report([analysis])
    else:
        # Analyze all priority files
        analyses = analyzer.get_priority_files(limit=30)
        print_analysis_report(analyses)
        
        if args.plan:
            plan = generate_migration_plan(analyses)
            output_path = project_root / args.output
            with open(output_path, 'w') as f:
                f.write(plan)
            print(f"\n✅ Migration plan saved to: {output_path}")
    
    if args.apply:
        print("\n⚠️ Auto-apply not yet implemented. Review suggestions manually.")


if __name__ == "__main__":
    main()
