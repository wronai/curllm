#!/usr/bin/env python3
"""
Script to detect and fix missing logger definitions in Python files.

Finds files that:
- Use `logger.` (debug/info/warning/error/exception)
- But don't have `logger = logging.getLogger(__name__)`

Usage:
    python scripts/fix_missing_loggers.py --scan          # Just scan and report
    python scripts/fix_missing_loggers.py --fix           # Scan and fix
    python scripts/fix_missing_loggers.py --fix --dry-run # Show what would be fixed
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Set


# Patterns
LOGGER_USAGE_PATTERN = re.compile(r'\blogger\.(debug|info|warning|error|exception|critical)\s*\(')
LOGGER_DEFINITION_PATTERN = re.compile(r'^\s*logger\s*=\s*logging\.getLogger\s*\(', re.MULTILINE)
LOGGING_IMPORT_PATTERN = re.compile(r'^import logging\b|^from logging import', re.MULTILINE)

# Directories to skip
SKIP_DIRS = {
    'venv', '.venv', 'env', '.env',
    '__pycache__', '.git', '.idea', '.cursor',
    'node_modules', 'build', 'dist', '.eggs',
    'htmlcov', '.pytest_cache', '.mypy_cache',
    'curllm.egg-info',
}

# Files to skip
SKIP_FILES = {
    '__init__.py',  # Often has different logger patterns
    'conftest.py',
    'setup.py',
}


def find_python_files(root_dir: Path, skip_tests: bool = False) -> List[Path]:
    """Find all Python files in directory tree."""
    python_files = []
    
    for path in root_dir.rglob('*.py'):
        # Skip directories
        if any(skip_dir in path.parts for skip_dir in SKIP_DIRS):
            continue
        
        # Skip specific files
        if path.name in SKIP_FILES:
            continue
        
        # Optionally skip tests
        if skip_tests and 'test' in path.name.lower():
            continue
        
        python_files.append(path)
    
    return sorted(python_files)


def check_file_for_missing_logger(filepath: Path) -> Tuple[bool, bool, bool]:
    """
    Check if file uses logger but doesn't define it.
    
    Returns:
        (uses_logger, has_definition, has_logging_import)
    """
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception:
        return False, False, False
    
    uses_logger = bool(LOGGER_USAGE_PATTERN.search(content))
    has_definition = bool(LOGGER_DEFINITION_PATTERN.search(content))
    has_logging_import = bool(LOGGING_IMPORT_PATTERN.search(content))
    
    return uses_logger, has_definition, has_logging_import


def fix_missing_logger(filepath: Path, dry_run: bool = False) -> bool:
    """
    Fix a file by adding logger definition.
    
    Returns True if file was fixed.
    """
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ❌ Error reading {filepath}: {e}")
        return False
    
    # Check if already has definition
    if LOGGER_DEFINITION_PATTERN.search(content):
        return False
    
    # Check if uses logger
    if not LOGGER_USAGE_PATTERN.search(content):
        return False
    
    lines = content.split('\n')
    new_lines = []
    
    # Find the right place to insert logger definition
    # Strategy: After all imports, before first function/class definition
    
    import_section_end = 0
    has_logging_import = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track if we have logging import
        if re.match(r'^import logging\b', stripped) or re.match(r'^from logging import', stripped):
            has_logging_import = True
            import_section_end = i + 1
        
        # Track end of import section
        if stripped.startswith('import ') or stripped.startswith('from '):
            import_section_end = i + 1
        
        # Also include empty lines right after imports
        elif stripped == '' and import_section_end > 0 and i == import_section_end:
            import_section_end = i + 1
    
    # Build new content
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Insert after import section
        if i == import_section_end - 1:
            # Add logging import if missing
            if not has_logging_import:
                # Find where to add import logging
                # Look for first import line
                for j, l in enumerate(new_lines):
                    if l.strip().startswith('import ') or l.strip().startswith('from '):
                        new_lines.insert(j, 'import logging')
                        import_section_end += 1
                        break
                else:
                    # No imports found, add at beginning (after docstring if any)
                    insert_pos = 0
                    if new_lines and new_lines[0].strip().startswith('"""'):
                        # Skip docstring
                        for k in range(1, len(new_lines)):
                            if '"""' in new_lines[k]:
                                insert_pos = k + 1
                                break
                    new_lines.insert(insert_pos, 'import logging')
                    new_lines.insert(insert_pos + 1, '')
            
            # Add logger definition
            new_lines.append('')
            new_lines.append('logger = logging.getLogger(__name__)')
    
    new_content = '\n'.join(new_lines)
    
    # Verify the fix
    if not LOGGER_DEFINITION_PATTERN.search(new_content):
        print(f"  ⚠️ Fix didn't work for {filepath}")
        return False
    
    if dry_run:
        print(f"  🔧 Would fix: {filepath}")
        return True
    
    try:
        filepath.write_text(new_content, encoding='utf-8')
        print(f"  ✅ Fixed: {filepath}")
        return True
    except Exception as e:
        print(f"  ❌ Error writing {filepath}: {e}")
        return False


def scan_project(root_dir: Path) -> List[Tuple[Path, bool]]:
    """
    Scan project for files with missing logger definitions.
    
    Returns list of (filepath, has_logging_import) tuples.
    """
    files = find_python_files(root_dir)
    missing = []
    
    for filepath in files:
        uses_logger, has_definition, has_logging_import = check_file_for_missing_logger(filepath)
        
        if uses_logger and not has_definition:
            missing.append((filepath, has_logging_import))
    
    return missing


def main():
    parser = argparse.ArgumentParser(description='Detect and fix missing logger definitions')
    parser.add_argument('--scan', action='store_true', help='Scan and report only')
    parser.add_argument('--fix', action='store_true', help='Fix missing loggers')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without changing files')
    parser.add_argument('--dir', type=str, default='.', help='Directory to scan (default: current)')
    
    args = parser.parse_args()
    
    if not args.scan and not args.fix:
        args.scan = True  # Default to scan
    
    root_dir = Path(args.dir).resolve()
    
    print(f"🔍 Scanning: {root_dir}")
    print()
    
    missing = scan_project(root_dir)
    
    if not missing:
        print("✅ No files with missing logger definitions found!")
        return 0
    
    print(f"📋 Found {len(missing)} files with missing logger definitions:")
    print()
    
    for filepath, has_logging_import in missing:
        relative = filepath.relative_to(root_dir)
        import_status = "✓ has import" if has_logging_import else "✗ needs import"
        print(f"  • {relative} ({import_status})")
    
    print()
    
    if args.fix:
        print("🔧 Fixing files...")
        print()
        
        fixed_count = 0
        for filepath, _ in missing:
            if fix_missing_logger(filepath, dry_run=args.dry_run):
                fixed_count += 1
        
        print()
        if args.dry_run:
            print(f"📊 Would fix {fixed_count}/{len(missing)} files")
        else:
            print(f"📊 Fixed {fixed_count}/{len(missing)} files")
    else:
        print("💡 Run with --fix to automatically add logger definitions")
        print("   Run with --fix --dry-run to preview changes")
    
    return 0 if not missing else 1


if __name__ == '__main__':
    sys.exit(main())
