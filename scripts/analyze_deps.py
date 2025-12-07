#!/usr/bin/env python3
"""
Dependency Analyzer for curllm project

Analyzes:
- Import dependencies between modules
- Circular dependencies
- Logging-related code that could be moved to curllm_logs
- Code organization suggestions
"""

import os
import re
import ast
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def find_python_files(directory: str) -> List[Path]:
    """Find all Python files in directory"""
    files = []
    for root, _, filenames in os.walk(directory):
        # Skip __pycache__, .git, etc.
        if any(skip in root for skip in ['__pycache__', '.git', 'venv', '.venv', 'node_modules']):
            continue
        for filename in filenames:
            if filename.endswith('.py'):
                files.append(Path(root) / filename)
    return files


def extract_imports(filepath: Path) -> Tuple[Set[str], Set[str]]:
    """Extract imports from a Python file"""
    local_imports = set()
    external_imports = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module.startswith('curllm'):
                        local_imports.add(alias.name)
                    else:
                        external_imports.add(module)
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module.startswith('curllm') or node.level > 0:
                        local_imports.add(node.module if node.module else '')
                    else:
                        external_imports.add(module)
    
    except Exception as e:
        print(f"  {YELLOW}Warning: Could not parse {filepath}: {e}{RESET}")
    
    return local_imports, external_imports


def find_logging_code(filepath: Path) -> Dict[str, int]:
    """Find logging-related code patterns"""
    patterns = {
        'logger_usage': r'\blogger\.',
        'logging_import': r'import logging|from logging',
        'log_file_ops': r'\.write\(.*log|log.*\.write|\.md.*write',
        'screenshot_code': r'screenshot|capture.*image|save.*png',
        'markdown_gen': r'\.md|markdown|f\.write.*#|write.*```',
        'json_dumps': r'json\.dumps|json\.dump',
        'datetime_format': r'strftime|datetime\.now',
    }
    
    counts = {k: 0 for k in patterns}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for name, pattern in patterns.items():
            counts[name] = len(re.findall(pattern, content, re.IGNORECASE))
    
    except Exception:
        pass
    
    return counts


def analyze_module_size(filepath: Path) -> Dict[str, int]:
    """Analyze module size metrics"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        tree = ast.parse(content)
        
        classes = 0
        functions = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes += 1
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions += 1
        
        return {
            'lines': len(lines),
            'classes': classes,
            'functions': functions,
            'chars': len(content),
        }
    except Exception:
        return {'lines': 0, 'classes': 0, 'functions': 0, 'chars': 0}


def build_dependency_graph(files: List[Path], base_dir: Path) -> Dict[str, Set[str]]:
    """Build dependency graph between modules"""
    graph = defaultdict(set)
    
    for filepath in files:
        rel_path = filepath.relative_to(base_dir)
        module_name = str(rel_path).replace('/', '.').replace('.py', '')
        
        local_imports, _ = extract_imports(filepath)
        
        for imp in local_imports:
            if imp:
                graph[module_name].add(imp)
    
    return dict(graph)


def find_circular_deps(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Find circular dependencies in the graph"""
    cycles = []
    visited = set()
    rec_stack = set()
    
    def dfs(node: str, path: List[str]):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                # Found cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)
        
        path.pop()
        rec_stack.remove(node)
    
    for node in graph:
        if node not in visited:
            dfs(node, [])
    
    return cycles


def suggest_refactoring(filepath: Path, logging_counts: Dict[str, int], size: Dict[str, int]) -> List[str]:
    """Suggest refactoring based on analysis"""
    suggestions = []
    
    # Check if file has significant logging code
    log_total = sum([
        logging_counts['log_file_ops'],
        logging_counts['markdown_gen'],
        logging_counts['screenshot_code'],
    ])
    
    if log_total >= 5:
        suggestions.append(f"Consider moving logging code to curllm_logs (found {log_total} log-related patterns)")
    
    if logging_counts['screenshot_code'] >= 3:
        suggestions.append("Screenshot handling could be refactored to use curllm_logs.ScreenshotManager")
    
    if size['lines'] > 500:
        suggestions.append(f"Large file ({size['lines']} lines) - consider splitting")
    
    if size['functions'] > 20:
        suggestions.append(f"Many functions ({size['functions']}) - consider grouping into classes")
    
    return suggestions


def main():
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}  curllm Dependency Analyzer{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")
    
    base_dir = Path(__file__).parent.parent
    
    # Analyze curllm_core
    print(f"{BOLD}📦 Analyzing curllm_core...{RESET}\n")
    
    core_dir = base_dir / 'curllm_core'
    core_files = find_python_files(core_dir)
    
    # Collect statistics
    all_external_imports = set()
    logging_candidates = []
    large_files = []
    
    for filepath in sorted(core_files):
        rel_path = filepath.relative_to(base_dir)
        local_imports, external_imports = extract_imports(filepath)
        all_external_imports.update(external_imports)
        
        logging_counts = find_logging_code(filepath)
        size = analyze_module_size(filepath)
        suggestions = suggest_refactoring(filepath, logging_counts, size)
        
        if suggestions or logging_counts['log_file_ops'] > 0 or logging_counts['screenshot_code'] > 0:
            logging_candidates.append((rel_path, logging_counts, size, suggestions))
        
        if size['lines'] > 300:
            large_files.append((rel_path, size))
    
    # Print external dependencies
    print(f"{BOLD}📚 External Dependencies:{RESET}")
    for dep in sorted(all_external_imports):
        print(f"  - {dep}")
    
    # Print logging candidates
    print(f"\n{BOLD}📝 Files with Logging/Screenshot code (candidates for curllm_logs):{RESET}\n")
    
    for rel_path, counts, size, suggestions in logging_candidates:
        print(f"  {BLUE}{rel_path}{RESET}")
        print(f"    Lines: {size['lines']}, Functions: {size['functions']}")
        if counts['log_file_ops'] > 0:
            print(f"    {YELLOW}Log file ops: {counts['log_file_ops']}{RESET}")
        if counts['screenshot_code'] > 0:
            print(f"    {YELLOW}Screenshot code: {counts['screenshot_code']}{RESET}")
        if counts['markdown_gen'] > 0:
            print(f"    {YELLOW}Markdown gen: {counts['markdown_gen']}{RESET}")
        for sug in suggestions:
            print(f"    {GREEN}→ {sug}{RESET}")
        print()
    
    # Print large files
    print(f"\n{BOLD}📊 Large Files (>300 lines):{RESET}\n")
    for rel_path, size in sorted(large_files, key=lambda x: x[1]['lines'], reverse=True):
        print(f"  {rel_path}: {size['lines']} lines, {size['functions']} functions")
    
    # Build and analyze dependency graph
    print(f"\n{BOLD}🔗 Dependency Analysis:{RESET}\n")
    
    graph = build_dependency_graph(core_files, base_dir)
    cycles = find_circular_deps(graph)
    
    if cycles:
        print(f"  {RED}⚠️  Circular dependencies found:{RESET}")
        for cycle in cycles[:5]:  # Show max 5
            print(f"    {' → '.join(cycle)}")
    else:
        print(f"  {GREEN}✅ No circular dependencies found{RESET}")
    
    # Analyze curllm_logs
    print(f"\n{BOLD}📦 Analyzing curllm_logs...{RESET}\n")
    
    logs_dir = base_dir / 'curllm_logs'
    if logs_dir.exists():
        logs_files = find_python_files(logs_dir)
        print(f"  Files: {len(logs_files)}")
        for filepath in sorted(logs_files):
            size = analyze_module_size(filepath)
            print(f"    {filepath.name}: {size['lines']} lines, {size['functions']} functions")
    
    # Summary and recommendations
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}📋 Summary & Recommendations:{RESET}")
    print(f"{'='*60}\n")
    
    print(f"{BOLD}Files to potentially move to curllm_logs:{RESET}")
    print("  1. curllm_core/screenshots.py → curllm_logs/screenshots.py (already done)")
    print("  2. curllm_core/logger.py → curllm_logs/logger.py")
    print("  3. curllm_core/config_logger.py → curllm_logs/config_logger.py")
    print("  4. Log-related functions from orchestrator.py")
    print("  5. Log-related functions from server.py")
    
    print(f"\n{BOLD}Additional refactoring suggestions:{RESET}")
    print("  • Create curllm_logs.RunLogger for unified run logging")
    print("  • Move all markdown report generation to curllm_logs")
    print("  • Add HTML report export to curllm_logs")
    print("  • Unify screenshot management across all modules")
    
    print(f"\n{BOLD}README.md updates needed:{RESET}")
    print("  • Document orchestrator natural language commands")
    print("  • Add curllm_logs package documentation")
    print("  • Document log file formats and locations")
    
    print(f"\n{GREEN}Analysis complete!{RESET}\n")


if __name__ == '__main__':
    main()
