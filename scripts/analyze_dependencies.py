#!/usr/bin/env python3
"""
Analyze file dependencies and usage in curllm_core.

Detects:
1. Import relationships between modules
2. Unused files (not imported anywhere)
3. Files with LLM alternatives (_llm.py versions)
4. Function usage across the codebase
"""

import ast
import os
import re
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Base directory
BASE_DIR = Path(__file__).parent.parent / "curllm_core"


def get_all_python_files(base_dir: Path) -> List[Path]:
    """Get all Python files in directory."""
    files = []
    for root, dirs, filenames in os.walk(base_dir):
        # Skip __pycache__, tests, etc.
        dirs[:] = [d for d in dirs if not d.startswith('__') and d != 'tests']
        for f in filenames:
            if f.endswith('.py') and not f.startswith('__'):
                files.append(Path(root) / f)
    return files


def extract_imports(file_path: Path) -> Tuple[Set[str], Set[str]]:
    """Extract imports from a Python file."""
    imports = set()
    from_imports = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    if module:
                        from_imports.add(f"{module}.{alias.name}")
                    else:
                        from_imports.add(alias.name)
    except Exception as e:
        pass
    
    return imports, from_imports


def extract_functions(file_path: Path) -> List[str]:
    """Extract function and class names from a Python file."""
    functions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                functions.append(node.name)
    except Exception:
        pass
    
    return functions


def get_module_name(file_path: Path, base_dir: Path) -> str:
    """Convert file path to module name."""
    rel_path = file_path.relative_to(base_dir.parent)
    module = str(rel_path).replace('/', '.').replace('\\', '.')
    if module.endswith('.py'):
        module = module[:-3]
    return module


def find_references(base_dir: Path, target_name: str) -> List[Tuple[Path, int]]:
    """Find all references to a name in the codebase."""
    references = []
    pattern = re.compile(rf'\b{re.escape(target_name)}\b')
    
    for file_path in get_all_python_files(base_dir):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    if pattern.search(line):
                        references.append((file_path, i))
        except Exception:
            pass
    
    return references


def analyze_llm_versions(base_dir: Path) -> Dict[str, Dict]:
    """Find files with _llm.py versions."""
    files = get_all_python_files(base_dir)
    llm_versions = {}
    
    for f in files:
        if f.name.endswith('_llm.py'):
            base_name = f.name.replace('_llm.py', '.py')
            original = f.parent / base_name
            
            if original.exists():
                llm_versions[str(f.relative_to(base_dir))] = {
                    'original': str(original.relative_to(base_dir)),
                    'llm_version': str(f.relative_to(base_dir)),
                    'original_exists': True
                }
            else:
                llm_versions[str(f.relative_to(base_dir))] = {
                    'original': base_name,
                    'llm_version': str(f.relative_to(base_dir)),
                    'original_exists': False
                }
    
    return llm_versions


def build_dependency_graph(base_dir: Path) -> Dict[str, Dict]:
    """Build complete dependency graph."""
    files = get_all_python_files(base_dir)
    graph = {}
    
    for file_path in files:
        module_name = get_module_name(file_path, base_dir)
        rel_path = str(file_path.relative_to(base_dir))
        
        imports, from_imports = extract_imports(file_path)
        functions = extract_functions(file_path)
        
        graph[rel_path] = {
            'module': module_name,
            'imports': list(imports),
            'from_imports': list(from_imports),
            'exports': functions,
            'imported_by': [],
            'size': file_path.stat().st_size,
        }
    
    # Find who imports what
    for file_path, data in graph.items():
        all_imports = set(data['imports']) | set(data['from_imports'])
        
        for other_path, other_data in graph.items():
            if file_path == other_path:
                continue
            
            other_module = other_data['module']
            # Check if this file imports the other
            for imp in all_imports:
                if other_module in imp or other_module.split('.')[-1] in imp:
                    graph[other_path]['imported_by'].append(file_path)
                    break
    
    return graph


def find_unused_files(graph: Dict[str, Dict], base_dir: Path) -> List[str]:
    """Find files that are not imported by anything."""
    unused = []
    
    # Entry points that are allowed to have no importers
    entry_points = {
        '__init__.py', '__main__.py', 'cli.py', 'main.py',
        'config.py', 'settings.py'
    }
    
    for file_path, data in graph.items():
        filename = Path(file_path).name
        
        if filename in entry_points:
            continue
        
        if not data['imported_by']:
            # Double-check with grep
            refs = find_references(base_dir, Path(file_path).stem)
            # Filter out self-references
            refs = [(p, l) for p, l in refs if str(p.relative_to(base_dir)) != file_path]
            
            if len(refs) <= 1:  # Only in __init__.py or nowhere
                unused.append(file_path)
    
    return unused


def analyze_function_usage(base_dir: Path, graph: Dict[str, Dict]) -> Dict[str, Dict]:
    """Analyze which functions are actually used."""
    function_usage = {}
    
    for file_path, data in graph.items():
        for func in data['exports']:
            if func.startswith('_') and not func.startswith('__'):
                continue  # Skip private functions
            
            refs = find_references(base_dir, func)
            # Filter self-references
            refs = [(p, l) for p, l in refs 
                    if str(p.relative_to(base_dir)) != file_path]
            
            function_usage[f"{file_path}::{func}"] = {
                'file': file_path,
                'function': func,
                'usage_count': len(refs),
                'used_in': [str(p.relative_to(base_dir)) for p, _ in refs[:5]]
            }
    
    return function_usage


def main():
    print("=" * 70)
    print("CURLLM DEPENDENCY ANALYSIS")
    print("=" * 70)
    
    # Build dependency graph
    print("\n📊 Building dependency graph...")
    graph = build_dependency_graph(BASE_DIR)
    print(f"   Found {len(graph)} Python files")
    
    # Find LLM versions
    print("\n🔄 Finding LLM versions...")
    llm_versions = analyze_llm_versions(BASE_DIR)
    print(f"   Found {len(llm_versions)} files with _llm.py versions")
    
    for llm_file, info in llm_versions.items():
        status = "✅ has original" if info['original_exists'] else "❌ no original"
        print(f"      {llm_file} → {info['original']} ({status})")
    
    # Find unused files
    print("\n🗑️  Finding unused files...")
    unused = find_unused_files(graph, BASE_DIR)
    print(f"   Found {len(unused)} potentially unused files:")
    for f in sorted(unused)[:20]:
        size = graph[f]['size']
        exports = len(graph[f]['exports'])
        print(f"      {f} ({size} bytes, {exports} exports)")
    
    # Analyze duplicate functionality
    print("\n🔍 Analyzing duplicate functionality...")
    duplicates = []
    for llm_file, info in llm_versions.items():
        if info['original_exists']:
            orig = info['original']
            orig_usage = len(graph.get(orig, {}).get('imported_by', []))
            llm_usage = len(graph.get(llm_file, {}).get('imported_by', []))
            
            duplicates.append({
                'original': orig,
                'llm_version': llm_file,
                'original_imports': orig_usage,
                'llm_imports': llm_usage,
                'recommendation': 'keep_llm' if llm_usage >= orig_usage else 'keep_both'
            })
    
    for dup in duplicates:
        print(f"   {dup['original']}")
        print(f"      Original imports: {dup['original_imports']}")
        print(f"      LLM imports: {dup['llm_imports']}")
        print(f"      Recommendation: {dup['recommendation']}")
    
    # Save detailed report
    report = {
        'summary': {
            'total_files': len(graph),
            'llm_versions': len(llm_versions),
            'unused_files': len(unused),
            'duplicates': len(duplicates)
        },
        'llm_versions': llm_versions,
        'unused_files': unused,
        'duplicates': duplicates,
        'graph': {k: {
            'module': v['module'],
            'imports_count': len(v['imports']) + len(v['from_imports']),
            'exports_count': len(v['exports']),
            'imported_by_count': len(v['imported_by']),
            'imported_by': v['imported_by'][:5]
        } for k, v in graph.items()}
    }
    
    report_path = Path(__file__).parent / "dependency_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Detailed report saved to: {report_path}")
    
    # Recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    
    print("\n1. FILES TO ARCHIVE (v1/):")
    for dup in duplicates:
        if dup['recommendation'] == 'keep_llm':
            print(f"   - {dup['original']} → move to v1/")
    
    print("\n2. FILES TO KEEP AS PRIMARY (v2/):")
    for llm_file in llm_versions.keys():
        print(f"   - {llm_file}")
    
    print("\n3. POTENTIALLY UNUSED FILES (review):")
    for f in sorted(unused)[:10]:
        print(f"   - {f}")


if __name__ == "__main__":
    main()
