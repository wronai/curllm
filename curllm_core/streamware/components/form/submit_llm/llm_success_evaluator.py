from typing import Dict, Any, Optional, List


class LLMSuccessEvaluator:
    """
    LLM-driven submission success evaluation.
    """
    
    def __init__(self, llm=None):
        self.llm = llm
    
    async def evaluate_submission(
        self,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to evaluate if form submission was successful.
        
        Args:
            before_state: Page state before submission
            after_state: Page state after submission
            instruction: User instruction for context
            
        Returns:
            {success: bool, confidence: float, reason: str}
        """
        diff = self._compute_diff(before_state, after_state)
        
        if not self.llm:
            return self._evaluate_heuristic(diff)
        
        try:
            prompt = f"""Was this form submission successful?

Changes after clicking submit:
- URL changed: {diff['url_changed']} ({before_state.get('url', '')} -> {after_state.get('url', '')})
- Form disappeared: {diff['form_disappeared']}
- New errors appeared: {diff['new_errors']}
- New text on page: {diff['new_text'][:500] if diff['new_text'] else 'None'}

{f'User goal: {instruction}' if instruction else ''}

Respond with JSON:
{{"success": true/false, "confidence": 0.0-1.0, "reason": "brief explanation"}}"""

            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            import json
            import re
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    'success': bool(data.get('success', False)),
                    'confidence': float(data.get('confidence', 0.5)),
                    'reason': data.get('reason', ''),
                    'diff': diff
                }
        except Exception as e:
            logger.debug(f"LLM success evaluation failed: {e}")
        
        return self._evaluate_heuristic(diff)
    
    def _compute_diff(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute page state differences."""
        diff = {
            'url_changed': before.get('url') != after.get('url'),
            'title_changed': before.get('title') != after.get('title'),
            'form_disappeared': before.get('form_count', 0) > after.get('form_count', 0),
            'new_errors': after.get('error_count', 0) > before.get('error_count', 0),
            'new_text': ''
        }
        
        before_text = before.get('visible_text_preview', '')
        after_text = after.get('visible_text_preview', '')
        
        if after_text != before_text:
            new_parts = []
            for line in after_text.split('\n'):
                if line.strip() and line not in before_text:
                    new_parts.append(line.strip())
            diff['new_text'] = '\n'.join(new_parts[:10])
        
        return diff
    
    def _evaluate_heuristic(self, diff: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback heuristic success evaluation."""
        success = False
        confidence = 0.5
        reason = 'Unknown'
        
        if diff.get('new_errors'):
            success = False
            confidence = 0.8
            reason = 'Errors appeared'
        elif diff.get('url_changed'):
            success = True
            confidence = 0.8
            reason = 'URL changed after submit'
        elif diff.get('form_disappeared'):
            success = True
            confidence = 0.7
            reason = 'Form disappeared'
        elif diff.get('new_text'):
            # Assume success if new text appeared (could be confirmation)
            success = True
            confidence = 0.5
            reason = 'New text appeared'
        
        return {
            'success': success,
            'confidence': confidence,
            'reason': reason,
            'diff': diff
        }
