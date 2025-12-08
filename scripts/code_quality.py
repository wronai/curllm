#!/usr/bin/env python3
"""
Code quality analysis for curllm_core.
"""

import os
import ast
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent.parent / "curllm_core"


def analyze_file(path: Path) -> dict:
    """Analyze a single Python file."""
    try:
        content = path.read_text(encoding='utf-8')
        lines = content.split('\n')
        tree = ast.parse(content)
        
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
                functions.append({
                    'name': node.name,
                    'lines': func_lines,
                    'args': len(node.args.args),
                })
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
        
        return {
            'lines': len(lines),
            'functions': functions,
            'classes': classes,
            'long_functions': [f for f in functions if f['lines'] > 50],
        }
    except Exception:
        return {'lines': 0, 'functions': [], 'classes': [], 'long_functions': []}


def main():
    print("=" * 60)
    print("CODE QUALITY ANALYSIS")
    print("=" * 60)
    
    stats = {
        'total_files': 0,
        'total_lines': 0,
        'total_functions': 0,
        'long_functions': [],
        'large_files': [],
    }
    
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if not d.startswith('__') and d != 'deprecated']
        
        for f in files:
            if f.endswith('.py') and not f.startswith('__'):
                path = Path(root) / f
                analysis = analyze_file(path)
                
                stats['total_files'] += 1
                stats['total_lines'] += analysis['lines']
                stats['total_functions'] += len(analysis['functions'])
                
                if analysis['lines'] > 500:
                    stats['large_files'].append({
                        'path': str(path.relative_to(BASE)),
                        'lines': analysis['lines'],
                    })
                
                for func in analysis['long_functions']:
                    stats['long_functions'].append({
                        'file': str(path.relative_to(BASE)),
                        'function': func['name'],
                        'lines': func['lines'],
                    })
    
    print(f"\n📊 Summary:")
    print(f"   Files: {stats['total_files']}")
    print(f"   Lines: {stats['total_lines']:,}")
    print(f"   Functions: {stats['total_functions']}")
    
    print(f"\n📦 Large files (>500 lines):")
    for f in sorted(stats['large_files'], key=lambda x: -x['lines'])[:10]:
        print(f"   {f['lines']:4} lines: {f['path']}")
    
    print(f"\n⚠️  Long functions (>50 lines):")
    for f in sorted(stats['long_functions'], key=lambda x: -x['lines'])[:15]:
        print(f"   {f['lines']:4} lines: {f['file']}::{f['function']}")
    
    print(f"\n✅ Recommendations:")
    if stats['long_functions']:
        print("   - Consider breaking down long functions")
    if stats['large_files']:
        print("   - Consider splitting large files into smaller modules")


if __name__ == "__main__":
    main()
