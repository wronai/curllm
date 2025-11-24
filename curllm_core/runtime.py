#!/usr/bin/env python3
import json
from typing import Any, Dict, Tuple

DEFAULT_RUNTIME: Dict[str, Any] = {
    "include_dom_html": True,
    "dom_max_chars": 30000,
    "dom_max_cap": 60000,
    "smart_click": True,
    "action_timeout_ms": 15000,
    "wait_after_click_ms": 1200,
    "wait_after_nav_ms": 1500,
    "no_click": False,
    "scroll_load": True,
    "fastpath": False,
    "use_external_slider_solver": True,
    "stall_limit": 5,
    "planner_growth_per_step": 2000,
    "planner_max_cap": 40000,
}


def parse_runtime_from_instruction(instruction: str | None) -> Tuple[str | None, Dict[str, Any]]:
    """Extract runtime params from JSON-like instruction.
    Accepts schemas like {instruction:"...", params:{...}} or arbitrary dicts with a string field.
    Returns (normalized_instruction, runtime_dict).
    """
    runtime: Dict[str, Any] = dict(DEFAULT_RUNTIME)
    if not instruction or not isinstance(instruction, str):
        return instruction, runtime
    s = instruction.strip()
    if not s.startswith("{"):
        return instruction, runtime
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            if isinstance(obj.get("params"), dict):
                runtime.update(obj["params"])  # type: ignore[arg-type]
                try:
                    presets = {
                        "deep_scan": {
                            "include_dom_html": True,
                            "scroll_load": True,
                            "dom_max_chars": 60000,
                            "dom_max_cap": 60000,
                            "stall_limit": 7,
                            "planner_growth_per_step": 3000,
                            "planner_max_cap": 40000,
                            "action_timeout_ms": 20000,
                            "wait_after_nav_ms": 2500,
                            "wait_after_click_ms": 1500,
                        },
                        "fast_scan": {
                            "include_dom_html": True,
                            "scroll_load": False,
                            "dom_max_chars": 20000,
                            "dom_max_cap": 30000,
                            "stall_limit": 3,
                            "planner_growth_per_step": 1500,
                            "planner_max_cap": 30000,
                            "action_timeout_ms": 8000,
                            "wait_after_nav_ms": 800,
                            "wait_after_click_ms": 800,
                        },
                        "max_dom": {
                            "include_dom_html": True,
                            "scroll_load": True,
                            "dom_max_chars": 60000,
                            "dom_max_cap": 60000,
                            "stall_limit": 9,
                            "planner_growth_per_step": 4000,
                            "planner_max_cap": 60000,
                            "action_timeout_ms": 22000,
                            "wait_after_nav_ms": 3000,
                            "wait_after_click_ms": 1800,
                        },
                    }
                    p = obj["params"].get("preset")
                    if isinstance(p, str) and p in presets:
                        runtime.update(presets[p])
                except Exception:
                    pass
            for key in ("instruction", "task", "data", "query"):
                if isinstance(obj.get(key), str):
                    instruction = obj[key]  # type: ignore[index]
                    break
    except Exception:
        pass
    return instruction, runtime
