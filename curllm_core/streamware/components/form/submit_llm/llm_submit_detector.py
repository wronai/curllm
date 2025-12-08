from typing import Dict, Any, Optional, List


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
