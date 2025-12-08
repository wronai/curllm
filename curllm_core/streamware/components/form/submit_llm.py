"""
LLM-Driven Form Submit - No hardcoded keywords

Uses LLM to:
1. Detect submit buttons without hardcoded text patterns
2. Evaluate submission success from page changes
3. Detect error messages without hardcoded selectors
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class LLMSubmitDetector:
    """
    LLM-driven submit button detection - no hardcoded keywords.
    """
    
    def __init__(self, llm=None):
        self.llm = llm
    
    async def find_submit_button(
        self,
        page,
        form_selector: Optional[str] = None,
        instruction: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to find the submit button.
        
        Args:
            page: Playwright page
            form_selector: Optional form container selector
            instruction: User instruction for context
            
        Returns:
            Button info dict or None
        """
        buttons = await self._get_all_buttons(page, form_selector)
        
        if not buttons:
            return None
        
        if not self.llm:
            return self._find_submit_heuristic(buttons)
        
        try:
            buttons_info = [
                f"- {b['text']} (type={b['type']}, classes={b['classes'][:50]})"
                for b in buttons[:10]
            ]
            
            prompt = f"""Which button submits this form?

Buttons found:
{chr(10).join(buttons_info)}

{f'User wants to: {instruction}' if instruction else ''}

Respond with the button text that submits the form, or "NONE" if unclear."""

            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Find matching button
            content_lower = content.lower().strip()
            for btn in buttons:
                if btn['text'].lower() in content_lower or content_lower in btn['text'].lower():
                    return btn
            
            # If LLM says first one or mentions submit
            if buttons and ('first' in content_lower or 'submit' in content_lower):
                return buttons[0]
                
        except Exception as e:
            logger.debug(f"LLM submit detection failed: {e}")
        
        return self._find_submit_heuristic(buttons)
    
    def _find_submit_heuristic(self, buttons: List[Dict]) -> Optional[Dict]:
        """Fallback heuristic for submit detection."""
        for btn in buttons:
            if btn.get('type') == 'submit':
                return btn
        return buttons[0] if buttons else None
    
    async def _get_all_buttons(
        self,
        page,
        form_selector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all clickable buttons from page."""
        js = f"""
        () => {{
            const container = {f'document.querySelector("{form_selector}")' if form_selector else 'document'};
            if (!container) return [];
            
            const buttons = [];
            container.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"]').forEach((el, idx) => {{
                const rect = el.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) return;
                
                buttons.push({{
                    selector: el.id ? '#' + el.id : (el.name ? '[name="' + el.name + '"]' : `button:nth-of-type(${{idx + 1}})`),
                    text: (el.innerText || el.value || '').trim().substring(0, 100),
                    type: (el.type || el.tagName || '').toLowerCase(),
                    classes: el.className || ''
                }});
            }});
            
            return buttons;
        }}
        """
        try:
            return await page.evaluate(js) or []
        except Exception:
            return []


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


async def submit_form_llm(
    page,
    llm=None,
    form_selector: Optional[str] = None,
    instruction: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit form using LLM-driven detection.
    
    Args:
        page: Playwright page
        llm: LLM client
        form_selector: Optional form selector
        instruction: User instruction
        
    Returns:
        {success: bool, button: dict, evaluation: dict}
    """
    from .submit import capture_page_state
    
    detector = LLMSubmitDetector(llm)
    evaluator = LLMSuccessEvaluator(llm)
    
    # Capture state before
    before_state = await capture_page_state(page)
    
    # Find submit button
    button = await detector.find_submit_button(page, form_selector, instruction)
    
    if not button:
        return {
            'success': False,
            'error': 'No submit button found',
            'button': None,
            'evaluation': None
        }
    
    # Click submit
    try:
        await page.click(button['selector'])
        await page.wait_for_timeout(1000)  # Wait for response
    except Exception as e:
        return {
            'success': False,
            'error': f'Click failed: {e}',
            'button': button,
            'evaluation': None
        }
    
    # Capture state after
    after_state = await capture_page_state(page)
    
    # Evaluate success
    evaluation = await evaluator.evaluate_submission(before_state, after_state, instruction)
    
    return {
        'success': evaluation.get('success', False),
        'button': button,
        'evaluation': evaluation
    }
