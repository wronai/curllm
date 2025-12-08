import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import DSLExecutor, AtomicFunctions
from curllm_core.llm_dsl.atoms import AtomResult


async def _trigger_field_events(page, selector: str):
    """Trigger input events after filling field"""
    await page.evaluate("""(sel) => {
        const el = document.querySelector(sel);
        if (el) {
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            el.dispatchEvent(new Event('blur', {bubbles: true}));
        }
    }""", selector)
