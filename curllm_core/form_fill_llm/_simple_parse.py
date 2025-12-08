import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import DSLExecutor, AtomicFunctions
from curllm_core.llm_dsl.atoms import AtomResult


def _simple_parse(instruction: str) -> Dict[str, str]:
    """Simple fallback parser (no hardcoded field names)"""
    import re
    pairs = {}
    # Match any key=value pattern
    for match in re.finditer(r'(\w+)\s*[=:]\s*([^,;\n]+)', instruction):
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        if key and value:
            pairs[key] = value
    return pairs
