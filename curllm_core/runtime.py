#!/usr/bin/env python3
import json
import os
from typing import Any, Dict, Tuple
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    try:
        load_dotenv()
    except Exception:
        pass

def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    try:
        return int(str(v).strip())
    except Exception:
        return default


_diff_fields_env = os.getenv("CURLLM_DIFF_FIELDS", "href,title,url").strip()
_diff_fields_default = [s.strip() for s in _diff_fields_env.split(",") if s.strip()] if _diff_fields_env else ["href", "title", "url"]

DEFAULT_RUNTIME: Dict[str, Any] = {
    "include_dom_html": _env_bool("CURLLM_INCLUDE_DOM_HTML", True),
    "dom_max_chars": _env_int("CURLLM_DOM_MAX_CHARS", 60000),
    "dom_max_cap": _env_int("CURLLM_DOM_MAX_CAP", 60000),
    "smart_click": _env_bool("CURLLM_SMART_CLICK", True),
    "action_timeout_ms": _env_int("CURLLM_ACTION_TIMEOUT_MS", 22000),
    "wait_after_click_ms": _env_int("CURLLM_WAIT_AFTER_CLICK_MS", 1800),
    "wait_after_nav_ms": _env_int("CURLLM_WAIT_AFTER_NAV_MS", 3000),
    "no_click": _env_bool("CURLLM_NO_CLICK", False),
    "scroll_load": _env_bool("CURLLM_SCROLL_LOAD", True),
    "fastpath": _env_bool("CURLLM_FASTPATH", False),
    "hierarchical_planner": _env_bool("CURLLM_HIERARCHICAL_PLANNER", True),
    "refine_instruction": _env_bool("CURLLM_REFINE_INSTRUCTION", False),
    # result storage and diffing
    "store_results": _env_bool("CURLLM_STORE_RESULTS", False),
    "result_key": os.getenv("CURLLM_RESULT_KEY"),
    "diff_mode": os.getenv("CURLLM_DIFF_MODE", "none"),  # none|new|changed|delta|all
    "diff_fields": _diff_fields_default,
    "keep_history": _env_int("CURLLM_KEEP_HISTORY", 10),
    "include_prev_results": _env_bool("CURLLM_INCLUDE_PREV_RESULTS", False),
    "use_external_slider_solver": _env_bool("CURLLM_USE_EXTERNAL_SLIDER_SOLVER", True),
    "stall_limit": _env_int("CURLLM_STALL_LIMIT", 9),
    "planner_growth_per_step": _env_int("CURLLM_PLANNER_GROWTH_PER_STEP", 3000),
    "planner_max_cap": _env_int("CURLLM_PLANNER_MAX_CAP", 60000),
    "planner_base_chars": _env_int("CURLLM_PLANNER_BASE_CHARS", 12000),
}


def parse_runtime_from_instruction(instruction: str | None) -> Tuple[str | None, Dict[str, Any]]:
    """Extract runtime params from JSON-like instruction.
    Accepts schemas like {instruction:"...", params:{...}} or arbitrary dicts with a string field.
    Returns (normalized_instruction, runtime_dict).
    """
    runtime: Dict[str, Any] = dict(DEFAULT_RUNTIME)
    # Optional default preset from env (applies before per-request params)
    try:
        _preset_env = os.getenv("CURLLM_RUNTIME_PRESET")
        if _preset_env:
            presets_env = {
                "deep_scan": {
                    "include_dom_html": True,
                    "scroll_load": True,
                    "dom_max_chars": 60000,
                    "dom_max_cap": 60000,
                    "stall_limit": 9,
                    "planner_growth_per_step": 3000,
                    "planner_max_cap": 60000,
                    "action_timeout_ms": 22000,
                    "wait_after_nav_ms": 3000,
                    "wait_after_click_ms": 1800,
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
            if _preset_env in presets_env:
                runtime.update(presets_env[_preset_env])
    except Exception:
        pass
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
                            "stall_limit": 9,
                            "planner_growth_per_step": 3000,
                            "planner_max_cap": 60000,
                            "action_timeout_ms": 22000,
                            "wait_after_nav_ms": 3000,
                            "wait_after_click_ms": 1800,
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
