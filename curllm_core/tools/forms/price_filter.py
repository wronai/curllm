"""
Tool for setting price filters on e-commerce sites
"""

from typing import Any, Dict, Optional
from ..base import BaseTool


class PriceFilterTool(BaseTool):
    """Set price min/max filters and apply them"""
    
    async def execute(self, page, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Set price filter fields and optionally submit.
        
        Parameters:
            max: Maximum price value
            min: Minimum price value (optional)
            submit: Whether to submit/apply filter (default: true)
            wait_after_submit_ms: Wait time after submit (default: 3000)
        
        Returns:
            {"success": bool, "url_changed": bool, "new_url": str}
        """
        self.validate_parameters(parameters)
        
        max_price = parameters.get("max")
        min_price = parameters.get("min", None)
        submit = parameters.get("submit", True)
        wait_ms = parameters.get("wait_after_submit_ms", 3000)
        
        initial_url = page.url
        filled_fields = []
        
        # Try to fill max price field
        if max_price is not None:
            max_selectors = [
                "input[name*='price_to' i]",
                "input[name*='max' i][name*='price' i]",
                "input[id*='price_to' i]",
                "input[id*='max' i][id*='price' i]",
                "input[placeholder*='max' i]",
                "input[type='number']:nth-of-type(2)",  # Often 2nd number input is max
                "input[type='text'][name*='cena' i]:nth-of-type(2)"  # Polish sites
            ]
            
            for selector in max_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        await elements[0].fill(str(max_price))
                        filled_fields.append(f"max={max_price}")
                        break
                except Exception:
                    continue
        
        # Try to fill min price field
        if min_price is not None:
            min_selectors = [
                "input[name*='price_from' i]",
                "input[name*='min' i][name*='price' i]",
                "input[id*='price_from' i]",
                "input[id*='min' i][id*='price' i]",
                "input[placeholder*='min' i]",
                "input[type='number']:nth-of-type(1)",  # Often 1st number input is min
                "input[type='text'][name*='cena' i]:nth-of-type(1)"  # Polish sites
            ]
            
            for selector in min_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        await elements[0].fill(str(min_price))
                        filled_fields.append(f"min={min_price}")
                        break
                except Exception:
                    continue
        
        # Submit if requested
        submitted = False
        if submit and filled_fields:
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Zastosuj')",
                "button:has-text('Filtruj')",
                "button:has-text('Apply')",
                "button:has-text('Filter')",
                "button.filter-submit",
                "button.apply-filters"
            ]
            
            for selector in submit_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        await element.click()
                        await page.wait_for_timeout(wait_ms)
                        submitted = True
                        break
                except Exception:
                    continue
        
        final_url = page.url
        url_changed = (final_url != initial_url)
        
        return {
            "success": len(filled_fields) > 0,
            "filled_fields": filled_fields,
            "submitted": submitted,
            "url_changed": url_changed,
            "new_url": final_url if url_changed else initial_url
        }
