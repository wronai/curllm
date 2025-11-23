#!/usr/bin/env python3
from typing import Optional

from .logger import RunLogger

SLIDER_TEXT_PATTERNS = [
    "przesuń w prawo",
    "przesun w prawo",
    "przesuń, aby",
    "przesun, aby",
    "ułóż układankę",
    "uloz ukladanke",
]


async def _frame_has_slider(frame) -> bool:
    try:
        txt = await frame.evaluate("() => (document.body && document.body.innerText || '').toLowerCase()")
        if txt and any(p in txt for p in SLIDER_TEXT_PATTERNS):
            return True
    except Exception:
        pass
    return False


async def attempt_slider_challenge(page, run_logger: Optional[RunLogger] = None) -> bool:
    """Heuristic slider solver: finds a captcha frame with slider text and drags across the visible widget.
    Returns True if a drag gesture was attempted.
    Note: This is best-effort and may not always pass the challenge.
    """
    target_frame = None
    try:
        for fr in page.frames:
            if fr == page.main_frame:
                continue
            if await _frame_has_slider(fr):
                target_frame = fr
                break
    except Exception:
        target_frame = None
    if not target_frame:
        return False

    # Try to find a canvas/track area; fallback to frame body
    try:
        track = target_frame.locator("canvas").first
        if await track.count() == 0:
            track = target_frame.locator("div").first
        box = await track.bounding_box()
    except Exception:
        box = None
    if not box:
        try:
            body = target_frame.locator("body")
            box = await body.bounding_box()
        except Exception:
            box = None
    if not box:
        return False

    # Compute drag path from left to right within the box
    start_x = box["x"] + max(10, box["width"] * 0.1)
    end_x = box["x"] + max(20, box["width"] * 0.85)
    y = box["y"] + box["height"] * 0.5

    try:
        await page.mouse.move(start_x, y)
        await page.mouse.down()
        steps = 20
        for i in range(steps):
            nx = start_x + (end_x - start_x) * (i + 1) / steps
            await page.mouse.move(nx, y)
        await page.mouse.up()
        if run_logger:
            run_logger.log_text("Attempted slider drag gesture in CAPTCHA frame")
        # Give the widget a moment to validate
        try:
            await page.wait_for_timeout(1200)
        except Exception:
            pass
        return True
    except Exception:
        return False
