"""
Tool for infinite scroll handling - loads dynamic content by scrolling
"""

from typing import Any, Dict, Optional
from ..base import BaseTool


class ScrollLoadTool(BaseTool):
    """Handle infinite scroll to load dynamic content"""
    
    async def execute(self, page, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Scroll page to load more content (infinite scroll pattern).
        
        Parameters:
            times: Number of times to scroll down
            wait_ms: Milliseconds to wait between scrolls (default: 600)
            direction: Scroll direction - 'down' or 'up' (default: 'down')
            wait_for_selector: Optional selector to wait for after each scroll
        
        Returns:
            {"success": bool, "scrolls_performed": int, "final_scroll_y": int}
        """
        self.validate_parameters(parameters)
        
        times = parameters.get("times", 3)
        wait_ms = parameters.get("wait_ms", 600)
        direction = parameters.get("direction", "down")
        wait_for_selector = parameters.get("wait_for_selector", None)
        
        scroll_multiplier = 1 if direction == "down" else -1
        scrolls_performed = 0
        
        for i in range(times):
            try:
                # Scroll by viewport height
                await page.evaluate(
                    f"window.scrollBy(0, {scroll_multiplier} * window.innerHeight);"
                )
                scrolls_performed += 1
                
                # Wait longer on first scroll to let initial content load
                wait_time = wait_ms * 1.5 if i == 0 else wait_ms
                await page.wait_for_timeout(int(wait_time))
                
                # Optionally wait for specific selector
                if wait_for_selector:
                    try:
                        await page.wait_for_selector(wait_for_selector, timeout=wait_ms)
                    except Exception:
                        pass  # Continue even if selector not found
                
            except Exception as e:
                print(f"Scroll {i+1} failed: {e}")
                break
        
        # Get final scroll position
        final_scroll_y = await page.evaluate("window.scrollY")
        
        return {
            "success": scrolls_performed > 0,
            "scrolls_performed": scrolls_performed,
            "final_scroll_y": final_scroll_y,
            "direction": direction
        }
