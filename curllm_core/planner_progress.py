from typing import Any, Dict, Optional, Tuple
from .rerun_cmd import build_rerun_curl


def progress_tick(
    page_context: Dict[str, Any],
    last_sig: Optional[str],
    no_progress: int,
    progressive_depth: int,
    runtime: Dict[str, Any],
    run_logger,
    result: Dict[str, Any],
    instruction: str,
    url: str | None,
    stall_limit: int,
) -> tuple[Optional[str], int, int, bool]:
    sig = f"{page_context.get('url','')}|{page_context.get('title','')}|{len(page_context.get('interactive',[])):04d}|{len(page_context.get('dom_preview',''))}"
    if last_sig is None:
        last_sig = sig
        no_progress = 0
    elif sig == last_sig:
        no_progress += 1
        if no_progress > 1:
            progressive_depth = min(progressive_depth + 1, 3)
            dom_cap = int(runtime.get("dom_max_cap", 60000) or 60000)
            runtime["dom_max_chars"] = min(int(runtime.get("dom_max_chars", 20000)) * progressive_depth, dom_cap)
            if run_logger:
                run_logger.log_text(f"No progress for {no_progress} steps. Increasing DOM depth to {runtime['dom_max_chars']} chars")
            try:
                params = {
                    "include_dom_html": True,
                    "dom_max_chars": runtime.get("dom_max_chars", 20000),
                    "stall_limit": stall_limit,
                    "planner_growth_per_step": int(runtime.get("planner_growth_per_step", 2000)),
                    "planner_max_cap": int(runtime.get("planner_max_cap", 20000)),
                    "preset": "deep_scan",
                }
                cmd = build_rerun_curl(instruction, url or "", params)
                result["meta"]["hints"].append("Increased DOM depth due to no progress. You can also retry with these parameters.")
                result["meta"]["suggested_commands"].append(cmd)
            except Exception:
                pass
    else:
        last_sig = sig
        no_progress = 0
        progressive_depth = 1
    if no_progress >= stall_limit:
        if progressive_depth < 3:
            progressive_depth = 3
            runtime["dom_max_chars"] = int(runtime.get("dom_max_cap", 60000) or 60000)
            no_progress = stall_limit - 1
        else:
            if run_logger:
                run_logger.log_text(f"No progress detected for {stall_limit} consecutive steps. Stopping early.")
            try:
                params = {
                    "include_dom_html": True,
                    "dom_max_chars": int(runtime.get("dom_max_cap", 60000) or 60000),
                    "stall_limit": stall_limit + 2,
                    "planner_growth_per_step": int(runtime.get("planner_growth_per_step", 2000)) + 1000,
                    "planner_max_cap": int(runtime.get("planner_max_cap", 20000)) + 5000,
                    "preset": "deep_scan",
                }
                cmd = build_rerun_curl(instruction, url or "", params)
                result["meta"]["hints"].append("Stall limit reached. Consider increasing stall_limit and DOM cap and retry.")
                result["meta"]["suggested_commands"].append(cmd)
                status = page_context.get("status") or {}
                if bool(status.get("human_verify_possible")):
                    result["meta"]["hints"].append("Human verification likely. Consider retrying with stealth and/or manual verification strategies.")
                    cmd2 = build_rerun_curl(instruction, url or "", {**params}, top_level={"stealth_mode": True, "url": url or ""})
                    result["meta"]["suggested_commands"].append(cmd2)
            except Exception:
                pass
            return last_sig, no_progress, progressive_depth, True
    return last_sig, no_progress, progressive_depth, False
