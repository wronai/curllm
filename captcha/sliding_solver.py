"""Sliding puzzle CAPTCHA solver."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from playwright.async_api import ElementHandle, Frame, Page

try:
    from .captcha_support import TWOCAPTCHA_SUPPORT, TwoCaptcha
    from .captcha_types import CaptchaConfig, logger
except ImportError:
    from captcha_support import TWOCAPTCHA_SUPPORT, TwoCaptcha
    from captcha_types import CaptchaConfig, logger


class SlidingPuzzleSolver:
    """Solver for sliding puzzle CAPTCHAs like on Allegro."""

    def __init__(self, config: CaptchaConfig):
        self.config = config
        self.config.screenshot_dir.mkdir(exist_ok=True)

    async def solve(self, page: Page, frame: Optional[Frame] = None) -> bool:
        """Solve sliding puzzle CAPTCHA. Returns True if solved successfully."""
        context = frame if frame else page
        try:
            puzzle_element = await self._find_puzzle_element(context)
            if not puzzle_element:
                return False

            timestamp = int(time.time())
            screenshot_path = self.config.screenshot_dir / f"puzzle_{timestamp}.png"
            await puzzle_element.screenshot(path=str(screenshot_path))
            logger.info("Saved puzzle screenshot: %s", screenshot_path)

            solution = await self.analyze_puzzle(screenshot_path)
            if not solution:
                logger.warning("Could not analyze puzzle locally, trying alternative methods...")
                return await self.solve_with_2captcha(context, screenshot_path)

            return await self.execute_sliding_solution(context, puzzle_element, solution)
        except Exception as exc:
            logger.error("Error solving sliding puzzle: %s", exc)
            return False

    async def _find_puzzle_element(self, context: Any) -> Optional[ElementHandle]:
        logger.info("Looking for sliding puzzle elements...")
        puzzle_selectors = [
            "canvas",
            '[class*="slide"]',
            '[class*="puzzle"]',
            '[class*="captcha-puzzle"]',
            'div[style*="background-image"]',
        ]
        for selector in puzzle_selectors:
            try:
                puzzle_element = await context.wait_for_selector(selector, timeout=5000)
                if puzzle_element:
                    logger.info("Found puzzle element with selector: %s", selector)
                    return puzzle_element
            except Exception:
                continue
        logger.error("Could not find puzzle element")
        return None

    async def analyze_puzzle(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze sliding puzzle image to find the correct position."""
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return None

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:2]

            if len(contours) >= 2:
                piece_contour = contours[1]
                x, y, w, h = cv2.boundingRect(piece_contour)
                template = gray[y : y + h, x : x + w]
                result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
                _min_val, _max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
                slide_distance = max_loc[0] - x
                logger.info("Detected slide distance: %spx", slide_distance)
                return {
                    "type": "slide",
                    "distance": slide_distance,
                    "start_x": x,
                    "start_y": y,
                    "target_x": max_loc[0],
                    "target_y": max_loc[1],
                }
        except Exception as exc:
            logger.error("Error analyzing puzzle: %s", exc)
        return None

    async def execute_sliding_solution(
        self,
        context: Any,
        element: ElementHandle,
        solution: Dict[str, Any],
    ) -> bool:
        """Execute the sliding action to solve the puzzle."""
        try:
            slider = await self._find_slider(context)
            if not slider:
                return False

            slider_box = await slider.bounding_box()
            if not slider_box:
                return False

            start_x = slider_box["x"] + slider_box["width"] / 2
            start_y = slider_box["y"] + slider_box["height"] / 2
            end_x = start_x + solution["distance"]
            end_y = start_y

            logger.info("Dragging from (%s, %s) to (%s, %s)", start_x, start_y, end_x, end_y)
            await self.human_like_drag(context, start_x, start_y, end_x, end_y)
            await asyncio.sleep(2)

            if await self._has_error_indicator(context):
                logger.warning("Puzzle solution failed")
                return False

            logger.info("Puzzle appears to be solved!")
            return True
        except Exception as exc:
            logger.error("Error executing solution: %s", exc)
            return False

    async def _find_slider(self, context: Any) -> Optional[ElementHandle]:
        slider_selectors = [
            '[class*="slider"]',
            '[class*="handle"]',
            '[class*="drag"]',
            'div[draggable="true"]',
        ]
        for selector in slider_selectors:
            try:
                slider = await context.wait_for_selector(selector, timeout=2000)
                if slider:
                    return slider
            except Exception:
                continue
        logger.error("Could not find slider handle")
        return None

    async def _has_error_indicator(self, context: Any) -> bool:
        error_selectors = ['[class*="error"]', '[class*="fail"]', 'text="Spróbuj ponownie"']
        for selector in error_selectors:
            try:
                error = await context.wait_for_selector(selector, timeout=1000)
                if error:
                    return True
            except Exception:
                pass
        return False

    async def human_like_drag(
        self,
        page: Any,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        steps: int = 20,
    ) -> None:
        """Perform human-like drag operation with bezier curve movement."""
        await page.mouse.move(start_x, start_y)
        await asyncio.sleep(0.1)
        await page.mouse.down()
        await asyncio.sleep(0.1)

        for x, y in self.generate_bezier_points(start_x, start_y, end_x, end_y, steps):
            await page.mouse.move(x, y)
            await asyncio.sleep(0.01 + np.random.random() * 0.02)

        overshoot_x = end_x + np.random.randint(-5, 5)
        await page.mouse.move(overshoot_x, end_y)
        await asyncio.sleep(0.05)
        await page.mouse.move(end_x, end_y)
        await asyncio.sleep(0.1)
        await page.mouse.up()

    def generate_bezier_points(
        self,
        x0: float,
        y0: float,
        x3: float,
        y3: float,
        num_points: int,
    ) -> List[Tuple[float, float]]:
        """Generate points along a bezier curve for natural movement."""
        x1 = x0 + (x3 - x0) * 0.3 + np.random.randint(-20, 20)
        y1 = y0 + np.random.randint(-10, 10)
        x2 = x0 + (x3 - x0) * 0.7 + np.random.randint(-20, 20)
        y2 = y3 + np.random.randint(-10, 10)

        points: list[tuple[float, float]] = []
        for i in range(num_points):
            t = i / (num_points - 1)
            x = (1 - t) ** 3 * x0 + 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t**2 * x2 + t**3 * x3
            y = (1 - t) ** 3 * y0 + 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t**2 * y2 + t**3 * y3
            points.append((x, y))
        return points

    async def solve_with_2captcha(self, context: Any, image_path: Path) -> bool:
        """Fallback to 2captcha service if local solving fails."""
        if not TWOCAPTCHA_SUPPORT or not self.config.use_2captcha:
            logger.warning("2captcha not available or not configured")
            return False

        try:
            solver = TwoCaptcha(self.config.api_key_2captcha)
            with open(image_path, "rb") as handle:
                result = solver.coordinates(
                    handle.read(),
                    lang="pl",
                    hint_text="Przesuń element układanki w odpowiednie miejsce",
                )

            if result and "code" in result:
                coords = result["code"].split(",")
                if len(coords) >= 2:
                    target_x = int(coords[0])
                    target_y = int(coords[1])
                    solution = {
                        "type": "slide",
                        "distance": target_x,
                        "target_x": target_x,
                        "target_y": target_y,
                    }
                    puzzle_element = await context.wait_for_selector("canvas", timeout=5000)
                    return await self.execute_sliding_solution(context, puzzle_element, solution)
        except Exception as exc:
            logger.error("2captcha solving failed: %s", exc)
        return False
