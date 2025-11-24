from typing import Any, Dict, Optional
from .extraction import product_heuristics


async def multi_stage_product_extract(instruction: str, page, run_logger) -> Optional[Dict[str, Any]]:
    extraction_stages = [
        {"scroll_steps": 2, "wait_ms": 500},
        {"scroll_steps": 3, "wait_ms": 800},
        {"scroll_steps": 5, "wait_ms": 1000},
    ]
    for stage_idx, stage in enumerate(extraction_stages):
        if run_logger:
            run_logger.log_text(f"Product extraction stage {stage_idx + 1}/{len(extraction_stages)}")
        for _ in range(stage["scroll_steps"]):
            try:
                await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8);")
                await page.wait_for_timeout(stage["wait_ms"])
            except Exception:
                pass
        try:
            res_products = await product_heuristics(instruction, page, run_logger)
            if res_products and res_products.get("products"):
                if len(res_products["products"]) >= 3:
                    return res_products
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"Stage {stage_idx + 1} extraction failed: {e}")
    if run_logger:
        run_logger.log_text("Multi-stage extraction incomplete, continuing with LLM planner")
    return None
