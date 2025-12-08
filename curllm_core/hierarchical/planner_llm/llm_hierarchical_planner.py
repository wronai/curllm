import json
from typing import Any, Dict, List, Optional

from .extract_strategic_context import extract_strategic_context

class LLMHierarchicalPlanner:
    """
    LLM-driven hierarchical planner.
    
    NO HARDCODED:
    - Task type keywords
    - Multi-step indicators
    - Form detection patterns
    """
    
    def __init__(self, llm=None):
        self.llm = llm
    
    async def should_use_hierarchical(
        self,
        instruction: str,
        page_context: Dict[str, Any]
    ) -> bool:
        """
        Decide if hierarchical planner is worth the overhead using LLM.
        """
        if not self.llm:
            # Fallback: use context size heuristic
            context_size = self._estimate_context_size(page_context)
            return context_size > 25000
        
        # Quick checks first
        is_simple = await self._is_simple_task_llm(instruction, page_context)
        if is_simple:
            logger.info("✂️ Bypassing hierarchical: simple task")
            return False
        
        is_multi = await self._is_multi_step_llm(instruction)
        if is_multi:
            logger.info("🔧 Using hierarchical: multi-step task")
            return True
        
        # Check context size
        context_size = self._estimate_context_size(page_context)
        if context_size > 25000:
            logger.info(f"🔧 Using hierarchical: large context ({context_size})")
            return True
        
        return False
    
    async def _is_simple_task_llm(
        self,
        instruction: str,
        page_context: Dict[str, Any]
    ) -> bool:
        """Check if task is simple using LLM."""
        forms = page_context.get("forms", [])
        form_count = len(forms)
        field_count = len(forms[0].get("fields", [])) if forms else 0
        
        prompt = f"""Is this a simple, single-action task?

Instruction: "{instruction}"
Page info: {form_count} forms, {field_count} fields in first form

Simple tasks: fill one form, click one button, extract simple data
Complex tasks: multi-step flows, navigation, conditionals

Answer ONLY: simple or complex"""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip().lower()
            return 'simple' in answer
        except Exception:
            # Fallback: simple if 1 form with few fields
            return form_count == 1 and field_count <= 10
    
    async def _is_multi_step_llm(self, instruction: str) -> bool:
        """Check if instruction requires multiple steps using LLM."""
        prompt = f"""Does this instruction require multiple sequential steps?

Instruction: "{instruction}"

Multi-step: "do X then Y", "first A, then B", numbered steps
Single-step: "fill form", "click button", "extract data"

Answer ONLY: multi-step or single-step"""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip().lower()
            return 'multi' in answer
        except Exception:
            return False
    
    async def plan_strategy(
        self,
        instruction: str,
        page_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create execution plan using LLM.
        """
        if not self.llm:
            return {"strategy": "direct", "steps": []}
        
        strategic = extract_strategic_context(page_context)
        
        prompt = f"""Create an execution plan for this task.

Instruction: "{instruction}"

Page summary:
- Title: {strategic.get('title', 'Unknown')}
- Type: {strategic.get('page_type', 'unknown')}
- Forms: {strategic.get('form_count', 0)}
- Interactive elements: {strategic.get('interactive_count', 0)}

Return JSON:
{{
    "strategy": "form_fill|extract|navigate|click",
    "steps": [
        {{"action": "...", "target": "...", "value": "..."}}
    ],
    "needs_details": ["forms", "interactive", ...]
}}

Return ONLY valid JSON."""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip()
            
            import re
            if '```' in answer:
                answer = re.sub(r'```\w*\n?', '', answer)
            
            return json.loads(answer)
        except Exception:
            return {"strategy": "direct", "steps": []}
    
    def _estimate_context_size(self, page_context: Dict[str, Any]) -> int:
        """Estimate context size in characters."""
        try:
            return len(json.dumps(page_context))
        except Exception:
            return 0
