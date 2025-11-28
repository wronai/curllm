"""
LLM Planner - Action planning using LLM.
"""
import json
from typing import Any, Dict, Optional, List


async def generate_action(
    llm: Any,
    instruction: str,
    page_context: Dict,
    step: int,
    run_logger=None,
    max_chars: int = 8000,
    growth_per_step: int = 2000,
    max_cap: int = 20000
) -> Dict:
    """
    Generate next action based on instruction and page context.
    
    Args:
        llm: LLM instance
        instruction: User instruction
        page_context: Current page context
        step: Current step number
        run_logger: Optional logger
        max_chars: Initial context char limit
        growth_per_step: Context growth per step
        max_cap: Maximum context chars
        
    Returns:
        Action dict with type, selector, value, etc.
    """
    # Adaptive context sizing
    adaptive_chars = min(max_chars + (step * growth_per_step), max_cap)
    
    # Prune nulls from context
    def _prune_nulls(obj):
        if isinstance(obj, dict):
            pruned = {k: _prune_nulls(v) for k, v in obj.items()}
            return {k: v for k, v in pruned.items() 
                    if v is not None and not (isinstance(v, (list, dict)) and len(v) == 0)}
        if isinstance(obj, list):
            pruned_list = [_prune_nulls(x) for x in obj]
            return [x for x in pruned_list 
                    if x is not None and not (isinstance(x, (list, dict)) and len(x) == 0)]
        return obj
    
    context_json = json.dumps(_prune_nulls(page_context), indent=2)
    context_str = context_json[:adaptive_chars]
    
    # Build tool history summary
    th_summary = _build_tool_history_summary(page_context)
    
    # Build product context if needed
    product_context = _build_product_context(instruction)
    
    # Build prompt
    prompt = _build_action_prompt(
        instruction=instruction,
        context=context_str,
        step=step,
        th_summary=th_summary,
        product_context=product_context
    )
    
    # Log prompt
    if run_logger:
        run_logger.log_text(f"\n### Step {step} - LLM Action Planning\n")
        run_logger.log_text(f"Context chars: {len(context_str)}")
    
    # Invoke LLM
    try:
        if hasattr(llm, 'ainvoke'):
            result = await llm.ainvoke(prompt)
            response = result.get('text', str(result))
        elif hasattr(llm, 'generate'):
            response = await llm.generate(prompt)
        else:
            response = str(await llm(prompt))
        
        # Parse response
        action = _parse_action_response(response)
        
        if run_logger and action:
            run_logger.log_text(f"Action: `{action.get('type', 'unknown')}`")
        
        return action
        
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"❌ LLM error: {e}")
        return {"type": "error", "error": str(e)}


def _build_tool_history_summary(page_context: Dict) -> str:
    """Build summary of recent tool history."""
    try:
        th = page_context.get("tool_history") or []
        if not isinstance(th, list) or not th:
            return ""
        
        parts = []
        for item in th[-3:]:
            try:
                name = item.get("tool")
                res = item.get("result") or {}
                if isinstance(res, dict):
                    if "links" in res:
                        cnt = len(res.get("links") or [])
                        parts.append(f"{name}: links={cnt}")
                    elif "form_fill" in res:
                        ff = res.get("form_fill") or {}
                        parts.append(f"{name}: form_fill.submitted={ff.get('submitted')}")
                    else:
                        parts.append(f"{name}: keys={list(res.keys())}")
            except Exception:
                continue
        
        if parts:
            return "\nTool History:\n- " + "\n- ".join(parts) + "\n"
        
    except Exception:
        pass
    
    return ""


def _build_product_context(instruction: str) -> str:
    """Build product extraction context if needed."""
    low = (instruction or "").lower()
    if not any(k in low for k in ["product", "produkt", "price", "cena", "zł", "pln"]):
        return ""
    
    return """
IMPORTANT: For products, use the products.extract TOOL:
```json
{
  "type": "tool",
  "tool_name": "products.extract",
  "args": {},
  "reason": "Extracting products using dynamic pattern detection"
}
```
"""


def _build_action_prompt(
    instruction: str,
    context: str,
    step: int,
    th_summary: str = "",
    product_context: str = ""
) -> str:
    """Build the action planning prompt."""
    return f"""You are a browser automation agent. Analyze the page and decide the next action.

INSTRUCTION: {instruction}

STEP: {step}
{th_summary}
{product_context}
PAGE CONTEXT:
{context}

Respond with ONE JSON action:

For clicking: {{"type": "click", "selector": "CSS_SELECTOR", "reason": "..."}}
For filling: {{"type": "fill", "selector": "CSS_SELECTOR", "value": "...", "reason": "..."}}
For scrolling: {{"type": "scroll", "reason": "..."}}
For waiting: {{"type": "wait", "reason": "..."}}
For tools: {{"type": "tool", "tool_name": "...", "args": {{}}, "reason": "..."}}
For completion: {{"type": "complete", "data": {{}}, "reason": "..."}}

JSON:"""


def _parse_action_response(response: str) -> Dict:
    """Parse action from LLM response."""
    import re
    
    # Try to find JSON in response
    try:
        # Look for JSON object
        match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    
    # Fallback: try to parse whole response
    try:
        return json.loads(response)
    except Exception:
        pass
    
    return {"type": "error", "error": "Failed to parse LLM response"}


class ActionPlanner:
    """
    Stateful action planner using LLM.
    
    Maintains history and adapts context per step.
    """
    
    def __init__(self, llm, instruction: str, run_logger=None):
        self.llm = llm
        self.instruction = instruction
        self.run_logger = run_logger
        self.history: List[Dict] = []
        self.step = 0
    
    async def next_action(self, page_context: Dict) -> Dict:
        """
        Generate next action.
        
        Args:
            page_context: Current page context
            
        Returns:
            Action dict
        """
        self.step += 1
        
        # Add history to context
        context = dict(page_context)
        context["action_history"] = self.history[-5:]  # Last 5 actions
        
        action = await generate_action(
            llm=self.llm,
            instruction=self.instruction,
            page_context=context,
            step=self.step,
            run_logger=self.run_logger
        )
        
        self.history.append(action)
        return action
    
    def reset(self):
        """Reset planner state."""
        self.history = []
        self.step = 0
