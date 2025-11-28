"""
Live Interaction Orchestrator - Real-time GUI automation

Handles:
- Direct click/hover/drag operations
- Keyboard input and shortcuts
- Scroll and navigation
- Wait and observe patterns
- Multi-step interaction sequences
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class ActionType(Enum):
    """Types of live interactions"""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    HOVER = "hover"
    DRAG = "drag"
    TYPE = "type"
    PRESS = "press"
    SCROLL = "scroll"
    WAIT = "wait"
    SELECT = "select"
    FOCUS = "focus"


class LiveInteractionOrchestrator:
    """
    Specialized orchestrator for real-time GUI interactions.
    
    Features:
    - Natural language to action translation
    - Smart element detection
    - Action verification
    - Error recovery
    - Interaction chaining
    """
    
    def __init__(self, llm=None, page=None, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
        self._action_history = []
    
    async def orchestrate(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute live interaction workflow.
        
        Args:
            instruction: User's interaction instruction
            page_context: Current page state
            
        Returns:
            Interaction result with action details
        """
        self._log("🎮 LIVE INTERACTION ORCHESTRATOR", "header")
        
        result = {
            'success': False,
            'actions_executed': [],
            'final_state': None
        }
        
        try:
            # Phase 1: Parse instruction into actions
            actions = await self._parse_actions(instruction)
            self._log(f"Parsed {len(actions)} actions")
            
            # Phase 2: Execute actions sequentially
            for i, action in enumerate(actions):
                self._log(f"Action {i+1}: {action['type']}")
                
                action_result = await self._execute_action(action)
                result['actions_executed'].append({
                    'action': action,
                    'success': action_result['success'],
                    'details': action_result
                })
                
                # Add to history for context
                self._action_history.append({
                    'action': action,
                    'result': action_result
                })
                
                if not action_result['success']:
                    self._log(f"Action failed: {action_result.get('error')}", "error")
                    # Try recovery
                    if not await self._recover_from_failure(action, action_result):
                        break
            
            # Phase 3: Capture final state
            result['final_state'] = await self._capture_state()
            
            # Determine overall success
            result['success'] = all(
                a['success'] for a in result['actions_executed']
            )
            
        except Exception as e:
            result['error'] = str(e)
            self._log(f"Live interaction failed: {e}", "error")
        
        return result
    
    async def _parse_actions(self, instruction: str) -> List[Dict[str, Any]]:
        """Parse instruction into executable actions"""
        actions = []
        instr_lower = instruction.lower()
        
        # Split by common action words or "then"/"and"
        parts = re.split(r'\s+(?:then|and|,)\s+', instruction, flags=re.IGNORECASE)
        
        for part in parts:
            action = self._parse_single_action(part)
            if action:
                actions.append(action)
        
        # If no actions parsed, try LLM
        if not actions and self.llm:
            actions = await self._parse_with_llm(instruction)
        
        # Fallback: try to parse as single action
        if not actions:
            action = self._parse_single_action(instruction)
            if action:
                actions.append(action)
        
        return actions
    
    def _parse_single_action(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse a single action from text"""
        text_lower = text.lower().strip()
        
        # Click patterns
        click_match = re.search(
            r'(?:click|kliknij|naciśnij)\s+(?:on\s+)?(?:the\s+)?["\']?(.+?)["\']?$',
            text_lower
        )
        if click_match:
            return {
                'type': ActionType.CLICK.value,
                'target': click_match.group(1).strip(),
                'original': text
            }
        
        # Double click
        if 'double' in text_lower and 'click' in text_lower:
            target_match = re.search(r'double.click\s+(?:on\s+)?(.+)', text_lower)
            if target_match:
                return {
                    'type': ActionType.DOUBLE_CLICK.value,
                    'target': target_match.group(1).strip(),
                    'original': text
                }
        
        # Right click
        if 'right' in text_lower and 'click' in text_lower:
            target_match = re.search(r'right.click\s+(?:on\s+)?(.+)', text_lower)
            if target_match:
                return {
                    'type': ActionType.RIGHT_CLICK.value,
                    'target': target_match.group(1).strip(),
                    'original': text
                }
        
        # Hover patterns
        hover_match = re.search(
            r'(?:hover|najedź)\s+(?:on\s+|over\s+|na\s+)?(.+)',
            text_lower
        )
        if hover_match:
            return {
                'type': ActionType.HOVER.value,
                'target': hover_match.group(1).strip(),
                'original': text
            }
        
        # Type/input patterns
        type_match = re.search(
            r'(?:type|wpisz|enter|wprowadź)\s+["\'](.+?)["\']\s*(?:in(?:to)?\s+(.+))?',
            text_lower
        )
        if type_match:
            return {
                'type': ActionType.TYPE.value,
                'value': type_match.group(1),
                'target': type_match.group(2).strip() if type_match.group(2) else None,
                'original': text
            }
        
        # Keyboard press patterns
        press_match = re.search(
            r'(?:press|naciśnij)\s+(.+)',
            text_lower
        )
        if press_match:
            key = press_match.group(1).strip()
            return {
                'type': ActionType.PRESS.value,
                'key': self._normalize_key(key),
                'original': text
            }
        
        # Scroll patterns
        scroll_match = re.search(
            r'(?:scroll|przewiń)\s+(up|down|góra|dół|left|right)?(?:\s+(\d+)\s*(?:times|px|razy)?)?',
            text_lower
        )
        if scroll_match:
            direction = scroll_match.group(1) or 'down'
            amount = int(scroll_match.group(2)) if scroll_match.group(2) else 1
            return {
                'type': ActionType.SCROLL.value,
                'direction': direction,
                'amount': amount,
                'original': text
            }
        
        # Wait patterns
        wait_match = re.search(
            r'(?:wait|poczekaj|czekaj)\s+(?:for\s+)?(\d+)\s*(?:seconds?|s|sekund)?',
            text_lower
        )
        if wait_match:
            return {
                'type': ActionType.WAIT.value,
                'duration': int(wait_match.group(1)),
                'original': text
            }
        
        # Wait for element
        wait_el_match = re.search(
            r'wait\s+(?:for|until)\s+(.+?)(?:\s+appears?)?$',
            text_lower
        )
        if wait_el_match:
            return {
                'type': ActionType.WAIT.value,
                'target': wait_el_match.group(1).strip(),
                'original': text
            }
        
        # Select patterns
        select_match = re.search(
            r'(?:select|wybierz)\s+["\']?(.+?)["\']?\s+(?:from|in|z)\s+(.+)',
            text_lower
        )
        if select_match:
            return {
                'type': ActionType.SELECT.value,
                'value': select_match.group(1),
                'target': select_match.group(2).strip(),
                'original': text
            }
        
        # Focus patterns
        focus_match = re.search(
            r'(?:focus|skup)\s+(?:on\s+)?(.+)',
            text_lower
        )
        if focus_match:
            return {
                'type': ActionType.FOCUS.value,
                'target': focus_match.group(1).strip(),
                'original': text
            }
        
        return None
    
    async def _parse_with_llm(self, instruction: str) -> List[Dict[str, Any]]:
        """Use LLM to parse complex instructions"""
        if not self.llm:
            return []
        
        prompt = f"""Parse this UI instruction into actions.

INSTRUCTION: {instruction}

ACTION TYPES: click, double_click, right_click, hover, type, press, scroll, wait, select, focus

Return JSON array:
[
    {{"type": "click", "target": "button text or selector"}},
    {{"type": "type", "value": "text to type", "target": "input field"}},
    {{"type": "wait", "duration": 2}},
    ...
]

JSON:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            text = response.get('text', '')
            
            start = text.find('[')
            end = text.rfind(']')
            if start >= 0 and end > start:
                return json.loads(text[start:end+1])
        except Exception:
            pass
        
        return []
    
    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action"""
        if not self.page:
            return {'success': False, 'error': 'No page'}
        
        action_type = action.get('type')
        result = {'success': False}
        
        try:
            if action_type == ActionType.CLICK.value:
                result = await self._do_click(action)
                
            elif action_type == ActionType.DOUBLE_CLICK.value:
                result = await self._do_double_click(action)
                
            elif action_type == ActionType.RIGHT_CLICK.value:
                result = await self._do_right_click(action)
                
            elif action_type == ActionType.HOVER.value:
                result = await self._do_hover(action)
                
            elif action_type == ActionType.TYPE.value:
                result = await self._do_type(action)
                
            elif action_type == ActionType.PRESS.value:
                result = await self._do_press(action)
                
            elif action_type == ActionType.SCROLL.value:
                result = await self._do_scroll(action)
                
            elif action_type == ActionType.WAIT.value:
                result = await self._do_wait(action)
                
            elif action_type == ActionType.SELECT.value:
                result = await self._do_select(action)
                
            elif action_type == ActionType.FOCUS.value:
                result = await self._do_focus(action)
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _do_click(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute click action"""
        target = action.get('target', '')
        selector = await self._find_element(target)
        
        if selector:
            await self.page.click(selector)
            await self.page.wait_for_timeout(300)
            return {'success': True, 'selector': selector}
        
        return {'success': False, 'error': f'Element not found: {target}'}
    
    async def _do_double_click(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute double click action"""
        target = action.get('target', '')
        selector = await self._find_element(target)
        
        if selector:
            await self.page.dblclick(selector)
            await self.page.wait_for_timeout(300)
            return {'success': True, 'selector': selector}
        
        return {'success': False, 'error': f'Element not found: {target}'}
    
    async def _do_right_click(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute right click action"""
        target = action.get('target', '')
        selector = await self._find_element(target)
        
        if selector:
            await self.page.click(selector, button='right')
            await self.page.wait_for_timeout(300)
            return {'success': True, 'selector': selector}
        
        return {'success': False, 'error': f'Element not found: {target}'}
    
    async def _do_hover(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute hover action"""
        target = action.get('target', '')
        selector = await self._find_element(target)
        
        if selector:
            await self.page.hover(selector)
            await self.page.wait_for_timeout(300)
            return {'success': True, 'selector': selector}
        
        return {'success': False, 'error': f'Element not found: {target}'}
    
    async def _do_type(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute type action"""
        value = action.get('value', '')
        target = action.get('target')
        
        if target:
            selector = await self._find_element(target)
            if selector:
                await self.page.fill(selector, value)
                return {'success': True, 'typed': value}
        else:
            # Type into focused element
            await self.page.keyboard.type(value)
            return {'success': True, 'typed': value}
        
        return {'success': False, 'error': 'Could not type'}
    
    async def _do_press(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute key press action"""
        key = action.get('key', '')
        await self.page.keyboard.press(key)
        return {'success': True, 'pressed': key}
    
    async def _do_scroll(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scroll action"""
        direction = action.get('direction', 'down')
        amount = action.get('amount', 1)
        
        if direction in ['down', 'dół']:
            delta = 500 * amount
        elif direction in ['up', 'góra']:
            delta = -500 * amount
        elif direction == 'left':
            await self.page.evaluate(f'window.scrollBy(-{500 * amount}, 0)')
            return {'success': True}
        elif direction == 'right':
            await self.page.evaluate(f'window.scrollBy({500 * amount}, 0)')
            return {'success': True}
        else:
            delta = 500
        
        await self.page.evaluate(f'window.scrollBy(0, {delta})')
        await self.page.wait_for_timeout(300)
        return {'success': True, 'scrolled': delta}
    
    async def _do_wait(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute wait action"""
        duration = action.get('duration')
        target = action.get('target')
        
        if duration:
            await self.page.wait_for_timeout(duration * 1000)
            return {'success': True, 'waited': duration}
        
        if target:
            selector = await self._find_element(target)
            if selector:
                await self.page.wait_for_selector(selector, timeout=10000)
                return {'success': True, 'waited_for': target}
        
        return {'success': False, 'error': 'Invalid wait action'}
    
    async def _do_select(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute select action"""
        value = action.get('value', '')
        target = action.get('target', '')
        
        selector = await self._find_element(target)
        if selector:
            await self.page.select_option(selector, value)
            return {'success': True, 'selected': value}
        
        return {'success': False, 'error': f'Select not found: {target}'}
    
    async def _do_focus(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute focus action"""
        target = action.get('target', '')
        selector = await self._find_element(target)
        
        if selector:
            await self.page.focus(selector)
            return {'success': True, 'focused': selector}
        
        return {'success': False, 'error': f'Element not found: {target}'}
    
    async def _find_element(self, target: str) -> Optional[str]:
        """Find element by text, aria-label, or selector"""
        if not target:
            return None
        
        # If it's already a valid selector, try it directly
        if target.startswith(('#', '.', '[', 'button', 'input', 'a')):
            try:
                if await self.page.query_selector(target):
                    return target
            except Exception:
                pass
        
        # Try text-based selectors
        text_selectors = [
            f'text="{target}"',
            f'button:has-text("{target}")',
            f'a:has-text("{target}")',
            f'[aria-label*="{target}" i]',
            f'[title*="{target}" i]',
            f'[placeholder*="{target}" i]'
        ]
        
        for selector in text_selectors:
            try:
                if await self.page.query_selector(selector):
                    return selector
            except Exception:
                continue
        
        # Try finding by ID/class containing target text
        partial_selectors = [
            f'#{target}',
            f'.{target}',
            f'[id*="{target}" i]',
            f'[class*="{target}" i]'
        ]
        
        for selector in partial_selectors:
            try:
                if await self.page.query_selector(selector):
                    return selector
            except Exception:
                continue
        
        return None
    
    def _normalize_key(self, key: str) -> str:
        """Normalize key name for Playwright"""
        key_map = {
            'enter': 'Enter',
            'esc': 'Escape',
            'escape': 'Escape',
            'tab': 'Tab',
            'space': 'Space',
            'backspace': 'Backspace',
            'delete': 'Delete',
            'up': 'ArrowUp',
            'down': 'ArrowDown',
            'left': 'ArrowLeft',
            'right': 'ArrowRight',
            'ctrl+c': 'Control+c',
            'ctrl+v': 'Control+v',
            'ctrl+a': 'Control+a'
        }
        
        return key_map.get(key.lower(), key)
    
    async def _recover_from_failure(
        self,
        action: Dict[str, Any],
        result: Dict[str, Any]
    ) -> bool:
        """Try to recover from action failure"""
        # Simple recovery strategies
        
        # If element not found, try scrolling
        if 'not found' in result.get('error', '').lower():
            await self.page.evaluate('window.scrollBy(0, 300)')
            await self.page.wait_for_timeout(500)
            
            # Retry action
            retry_result = await self._execute_action(action)
            return retry_result.get('success', False)
        
        return False
    
    async def _capture_state(self) -> Dict[str, Any]:
        """Capture current page state"""
        if not self.page:
            return {}
        
        try:
            return await self.page.evaluate('''() => ({
                url: window.location.href,
                title: document.title,
                scroll: {
                    x: window.scrollX,
                    y: window.scrollY
                },
                focused: document.activeElement?.tagName
            })''')
        except Exception:
            return {}
    
    def _log(self, message: str, level: str = "info"):
        """Log message"""
        if self.run_logger:
            if level == "header":
                self.run_logger.log_text(f"\n{'='*50}")
                self.run_logger.log_text(message)
                self.run_logger.log_text(f"{'='*50}\n")
            elif level == "error":
                self.run_logger.log_text(f"❌ {message}")
            else:
                self.run_logger.log_text(f"   {message}")

