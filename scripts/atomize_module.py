#!/usr/bin/env python3
"""
Atomize Module Script
Splits a Python module into a directory where each class and function is in its own file.
Maintains backward compatibility via __init__.py.
"""

import os
import ast
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class Atomizer:
    def __init__(self, file_path: str, dry_run: bool = False):
        self.file_path = Path(file_path)
        self.dry_run = dry_run
        self.source_code = self.file_path.read_text('utf-8')
        self.tree = ast.parse(self.source_code)
        self.imports = []
        self.items = [] # List of (name, type, node, source_segment)

    def analyze(self):
        """Analyze the file to find imports and top-level definitions."""
        lines = self.source_code.splitlines(keepends=True)
        
        for node in self.tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self.imports.append(ast.get_source_segment(self.source_code, node))
            elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                # Get the full source including decorators
                segment = ast.get_source_segment(self.source_code, node)
                
                # Manually check for decorators if they might be missed or to be safe
                # Sometimes get_source_segment misses preceding decorators if there are newlines
                if node.decorator_list:
                    # Find the start of the first decorator
                    first_dec = node.decorator_list[0]
                    start_line = first_dec.lineno
                    end_line = node.end_lineno
                    
                    # Extract lines directly from source
                    segment = "".join(lines[start_line-1:end_line])
                
                self.items.append({
                    'name': node.name,
                    'type': type(node).__name__,
                    'code': segment
                })
            elif isinstance(node, ast.Assign):
                # Global variables/constants - keep in __init__ or separate file?
                # For now, let's keep them in a '_constants.py' or similar if significant,
                # but simple approach: if it looks like a constant (UPPERCASE), put in __init__ or specific file.
                # To simplify, we might lose module-level code that isn't a def/class if we aren't careful.
                pass

    def atomize(self):
        """Execute the split."""
        self.analyze()
        
        if not self.items:
            logger.warning(f"No classes or functions found in {self.file_path}")
            return

        target_dir = self.file_path.with_suffix('') # e.g. module.py -> module/
        
        if self.dry_run:
            logger.info(f"Would create directory: {target_dir}")
            for item in self.items:
                logger.info(f"Would create file: {target_dir / item['name']}.py")
            return

        # Create directory
        if target_dir.exists():
            if not target_dir.is_dir():
                logger.error(f"{target_dir} exists but is not a directory. Aborting.")
                return
        else:
            target_dir.mkdir(parents=True)

        # Prepare common imports
        # Adjust relative imports because we are one level deeper
        adjusted_imports = []
        for imp in self.imports:
            if imp.startswith("from ."):
                # form .foo -> from ..foo
                adjusted_imports.append("from ." + imp[5:])
            elif "from .." in imp:
                # from ..foo -> from ...foo
                adjusted_imports.append(imp.replace("from ..", "from ...", 1))
            else:
                adjusted_imports.append(imp)
        
        header = "".join(imp + "\n" for imp in adjusted_imports if imp)
        
        created_files = []
        
        # Pre-calculate filenames to resolve dependencies
        name_to_filename = {}
        for item in self.items:
            filename = self._to_snake_case(item['name'])
            name_to_filename[item['name']] = filename
            created_files.append((item['name'], filename))

        # Write individual files
        for item in self.items:
            filename = name_to_filename[item['name']]
            file_dest = target_dir / f"{filename}.py"
            
            # Check for dependencies on other items in this module
            extra_imports = []
            for other_name, other_filename in name_to_filename.items():
                if other_name == item['name']:
                    continue
                # Simple check: if the other name appears in the code of this item
                if other_name in item['code']:
                    extra_imports.append(f"from .{other_filename} import {other_name}")
            
            with open(file_dest, 'w', encoding='utf-8') as f:
                f.write(header + "\n")
                if extra_imports:
                    f.write("\n".join(extra_imports) + "\n")
                f.write("\n")
                f.write(item['code'] + "\n")
            
            logger.info(f"Created {file_dest}")

        # Create __init__.py
        init_file = target_dir / "__init__.py"
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(f'"""\nAtomized access to {self.file_path.stem}\n"""\n\n')
            for name, filename in created_files:
                f.write(f"from .{filename} import {name}\n")
            
            all_exports = [name for name, _ in created_files]
            f.write(f"\n__all__ = {all_exports!r}\n")
        
        logger.info(f"Created {init_file}")
        
        # Rename original file to .bak just in case
        backup_path = self.file_path.with_suffix('.py.bak')
        shutil.move(self.file_path, backup_path)
        logger.info(f"Moved original file to {backup_path}")

    def _to_snake_case(self, name: str) -> str:
        """Simple CamelCase to snake_case converter."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Atomize a Python module')
    parser.add_argument('file', help='Path to python file to atomize')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen')
    
    args = parser.parse_args()
    
    atomizer = Atomizer(args.file, args.dry_run)
    atomizer.atomize()
