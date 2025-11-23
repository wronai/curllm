#!/usr/bin/env python3
from __future__ import annotations
import importlib
import sys
from pathlib import Path
from typing import Optional

from .logger import RunLogger
from .captcha_slider import _frame_has_slider

CANDIDATE_MODULES = [
    "captcha.allegro_captcha_solver",
    "allegro_captcha_solver",
    "captcha.captcha_solver",
    "captcha_solver",
]


async def _detect_slider(page) -> bool:
    try:
        for fr in page.frames:
            if fr == page.main_frame:
                continue
            if await _frame_has_slider(fr):
                return True
    except Exception:
        pass
    return False


async def try_external_slider_solver(page, run_logger: Optional[RunLogger] = None) -> Optional[bool]:
    """Attempt to import and run an external Allegro sliding puzzle solver provided by the user.
    Looks for modules in ./captcha/ and root python path. Supports both class-based and function-based APIs.
    Returns True if it believes the puzzle was solved, False if attempted and failed, or None if no plugin found.
    """
    # Only try if current page looks like slider context
    try:
        looks_slider = await _detect_slider(page)
        if not looks_slider:
            return None
    except Exception:
        pass

    # Ensure ./captcha is importable if present
    try:
        for base in [Path(__file__).resolve().parent.parent, Path.cwd()]:
            capdir = base / "captcha"
            if capdir.is_dir():
                p = str(capdir)
                if p not in sys.path:
                    sys.path.insert(0, p)
    except Exception:
        pass

    module = None
    for name in CANDIDATE_MODULES:
        try:
            module = importlib.import_module(name)
            if module:
                break
        except Exception:
            module = None
    if not module:
        if run_logger:
            run_logger.log_kv("ext_slider_solver_module", "not_found")
        return None

    if run_logger:
        run_logger.log_kv("ext_slider_solver_module", getattr(module, "__name__", "unknown"))

    # Try class APIs first
    solver = None
    for cls_name in ("AllegroSlidingPuzzleSolver", "SlidingPuzzleSolver", "CaptchaSolver"):
        try:
            cls = getattr(module, cls_name, None)
            if cls:
                solver = cls()
                break
        except Exception:
            continue

    # Try function-based APIs
    func_candidates = []
    if not solver:
        for fn in ("solve_allegro_puzzle", "solve_slider", "solve"):
            f = getattr(module, fn, None)
            if callable(f):
                func_candidates.append(f)
        if not func_candidates and run_logger:
            run_logger.log_kv("ext_slider_solver_api", "not_found")

    try:
        if solver:
            # Prefer a well-named method if present
            for meth in ("solve_allegro_puzzle", "solve_slider", "solve"):
                m = getattr(solver, meth, None)
                if callable(m):
                    ok = await m(page)
                    if run_logger:
                        run_logger.log_kv("ext_slider_solver_method", meth)
                    return bool(ok)
            # If no suitable method, consider it a no-op
            return False
        # Try function candidates
        for f in func_candidates:
            ok = await f(page)
            if run_logger:
                run_logger.log_kv("ext_slider_solver_function", getattr(f, "__name__", "function"))
            return bool(ok)
    except Exception as e:
        if run_logger:
            run_logger.log_kv("ext_slider_solver_error", str(e))
        return False

    return None
