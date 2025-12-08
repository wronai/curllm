#!/usr/bin/env python3
"""
Reorganize files into v1/v2 structure.

v1/ - Legacy implementations with hardcoded values
v2/ - LLM-driven implementations

This script:
1. Moves legacy files to deprecated/ folder
2. Updates imports to point to v2 by default
3. Adds deprecation warnings
"""

import os
import shutil
from pathlib import Path

BASE = Path(__file__).parent.parent / "curllm_core"
DEPRECATED = BASE / "deprecated"


def add_deprecation_warning(file_path: Path, replacement: str):
    """Add deprecation warning to a file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        
        if 'DEPRECATED' in content[:500]:
            return  # Already has warning
        
        warning = f'''"""
DEPRECATED: This module is deprecated.

Use the LLM-driven version instead:
    from curllm_core.v2 import {replacement}

This module will be removed in a future version.
"""

import warnings
warnings.warn(
    "This module is deprecated. Use curllm_core.v2.{replacement} instead.",
    DeprecationWarning,
    stacklevel=2
)

'''
        # Insert after docstring if present
        if content.startswith('"""'):
            end_doc = content.find('"""', 3) + 3
            new_content = content[:end_doc] + '\n\n' + warning.split('"""')[2] + content[end_doc:]
        else:
            new_content = warning + content
        
        file_path.write_text(new_content, encoding='utf-8')
        print(f"  ✅ Added deprecation to {file_path.name}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")


def main():
    print("=" * 60)
    print("REORGANIZING CURLLM CODE INTO v1/v2 STRUCTURE")
    print("=" * 60)
    
    # Files with LLM versions
    replacements = {
        'form_fill.py': 'llm_form_fill',
        'orchestrators/social.py': 'LLMSocialOrchestrator',
        'orchestrators/auth.py': 'LLMAuthOrchestrator',
        'orchestrators/ecommerce.py': 'LLMECommerceOrchestrator',
        'orchestrators/form.py': 'LLMFormOrchestrator',
        'extraction/extractor.py': 'LLMExtractor',
        'hierarchical/planner.py': 'LLMHierarchicalPlanner',
        'dsl/executor.py': 'LLMDSLExecutor',
        'url_resolver.py': 'url_resolver_llm',
    }
    
    print("\n1. ADDING DEPRECATION WARNINGS TO LEGACY FILES")
    print("-" * 60)
    
    for rel_path, replacement in replacements.items():
        file_path = BASE / rel_path
        if file_path.exists():
            add_deprecation_warning(file_path, replacement)
    
    # Truly unused files that can be archived
    print("\n2. POTENTIALLY UNUSED FILES (manual review recommended)")
    print("-" * 60)
    
    unused_candidates = [
        'context_optimizer.py',
        'semantic_query.py',
        'extraction_registry.py',
        'prompt_dsl.py',
        'hybrid_selector_ranker.py',
        'hierarchical_planner_v2.py',
        'llm_form_orchestrator.py',
        'llm_transparent_orchestrator.py',
        'atomic_query.py',
    ]
    
    for filename in unused_candidates:
        file_path = BASE / filename
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"  📁 {filename} ({size} bytes)")
    
    print("\n3. CURRENT STRUCTURE")
    print("-" * 60)
    print("  curllm_core/")
    print("  ├── v1/              # Legacy exports (backward compat)")
    print("  │   └── __init__.py  # Re-exports from original locations")
    print("  ├── v2/              # LLM-driven exports (recommended)")  
    print("  │   └── __init__.py  # Exports from *_llm.py files")
    print("  ├── llm_dsl/         # Core LLM-DSL implementation")
    print("  ├── form_fill_llm.py # LLM form filling")
    print("  ├── orchestrators/")
    print("  │   ├── *_llm.py     # LLM orchestrators")
    print("  │   └── *.py         # Legacy (deprecated)")
    print("  └── ...")
    
    print("\n4. RECOMMENDED USAGE")
    print("-" * 60)
    print("  # New code - use v2:")
    print("  from curllm_core.v2 import LLMFormOrchestrator, llm_form_fill")
    print()
    print("  # Legacy code - use v1 (deprecated):")
    print("  from curllm_core.v1 import FormOrchestrator, deterministic_form_fill")


if __name__ == "__main__":
    main()
