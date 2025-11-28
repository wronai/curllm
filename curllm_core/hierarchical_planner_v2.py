"""
Hierarchical Planner V2 - Refactored using Streamware DSL

This is a complete refactoring of the hierarchical planner to use
modular Streamware components instead of monolithic functions.

Key improvements:
1. DOM snapshot with ACTUAL field values (fixes empty value bug)
2. Action validation after each step
3. Loop detection and prevention
4. Modular decision tree components
5. Better error handling and diagnostics
"""

from typing import Any, Dict, List, Optional
from .streamware import flow, pipeline
from .streamware.components.dom_fix import DOMSnapshotComponent
from .streamware.components.decision import (
    DOMAnalyzeComponent,
    ActionPlanComponent,
    ActionValidateComponent
)
from .diagnostics import get_logger

logger = get_logger(__name__)


class HierarchicalPlannerV2:
    """
    Streamware-based hierarchical planner
    
    Uses modular components for:
    - DOM analysis
    - Action planning
    - Validation
    - Loop detection
    """
    
    def __init__(self, page, config: Optional[Dict] = None):
        """
        Initialize planner
        
        Args:
            page: Playwright page object
            config: Optional configuration
        """
        self.page = page
        self.config = config or {}
        self.history = []
        self.snapshots = []
        
    async def execute(self, instruction: str, max_steps: int = 10) -> Dict[str, Any]:
        """
        Execute instruction using Streamware components
        
        Args:
            instruction: Natural language instruction
            max_steps: Maximum number of steps
            
        Returns:
            Execution result with success status
        """
        logger.info(f"Starting Hierarchical Planner V2: {instruction}")
        
        step = 0
        last_action = None
        loop_count = 0
        
        while step < max_steps:
            logger.info(f"Step {step + 1}/{max_steps}")
            
            try:
                # 1. Capture DOM snapshot with ACTUAL values
                snapshot = await self._capture_snapshot()
                self.snapshots.append(snapshot)
                
                # 2. Analyze DOM
                analysis = self._analyze_dom(snapshot)
                logger.debug(f"DOM analysis: {analysis}")
                
                # 3. Plan next action
                action = self._plan_action(instruction, analysis)
                logger.info(f"Planned action: {action.get('type')} - {action.get('field', '')}")
                
                # 4. Check for completion
                if action.get('type') == 'complete':
                    logger.info(f"Task complete: {action.get('reason')}")
                    return {
                        'success': True,
                        'steps': step,
                        'reason': action.get('reason'),
                        'history': self.history
                    }
                    
                # 5. Check for loops
                if last_action and self._is_same_action(action, last_action):
                    loop_count += 1
                    if loop_count >= 3:
                        logger.warning("Loop detected, stopping")
                        return {
                            'success': False,
                            'steps': step,
                            'reason': 'loop_detected',
                            'history': self.history
                        }
                else:
                    loop_count = 0
                    
                # 6. Execute action
                before_snapshot = snapshot
                await self._execute_action(action)
                
                # 7. Wait for page to update
                await self.page.wait_for_timeout(1000)
                
                # 8. Validate action
                after_snapshot = await self._capture_snapshot()
                validation = self._validate_action(action, before_snapshot, after_snapshot)
                
                if not validation.get('success'):
                    logger.warning(f"Action validation failed: {validation.get('reason')}")
                else:
                    logger.info(f"Action validated: {validation}")
                    
                # 9. Add to history
                self.history.append({
                    'step': step,
                    'action': action,
                    'validation': validation
                })
                
                last_action = action
                step += 1
                
            except Exception as e:
                logger.error(f"Error in step {step}: {e}")
                return {
                    'success': False,
                    'steps': step,
                    'reason': f'error: {str(e)}',
                    'history': self.history
                }
                
        return {
            'success': False,
            'steps': step,
            'reason': 'max_steps_reached',
            'history': self.history
        }
        
    async def _capture_snapshot(self) -> Dict[str, Any]:
        """Capture DOM snapshot using Streamware component"""
        try:
            # Use new DOM snapshot component that captures ACTUAL values
            snapshot = (
                flow("dom-snapshot://capture?include_values=true")
                .with_data({'page': self.page})
                .run()
            )
            return snapshot
        except Exception as e:
            logger.error(f"Snapshot capture failed: {e}")
            # Fallback to basic snapshot
            return {
                'title': self.page.title(),
                'url': self.page.url,
                'forms': [],
                'error': str(e)
            }
            
    def _analyze_dom(self, snapshot: Dict) -> Dict[str, Any]:
        """Analyze DOM using Streamware component"""
        analysis = (
            flow("dom-analyze://extract?type=forms")
            .with_data({'page_context': snapshot})
            .run()
        )
        return analysis
        
    def _plan_action(self, instruction: str, analysis: Dict) -> Dict[str, Any]:
        """Plan next action using Streamware component"""
        # Use smart strategy with loop detection
        action = (
            flow("action-plan://decide?strategy=smart")
            .with_data({
                'instruction': instruction,
                'page_analysis': analysis,
                'history': self.history
            })
            .run()
        )
        return action
        
    async def _execute_action(self, action: Dict):
        """Execute planned action on the page"""
        action_type = action.get('type')
        
        if action_type == 'fill':
            selector = action.get('selector')
            value = action.get('value', '')
            
            try:
                # Fill field
                await self.page.fill(selector, value)
                logger.info(f"Filled {selector} with '{value}'")
            except Exception as e:
                logger.error(f"Fill failed: {e}")
                raise
                
        elif action_type == 'click':
            selector = action.get('selector')
            
            try:
                await self.page.click(selector)
                logger.info(f"Clicked {selector}")
            except Exception as e:
                logger.error(f"Click failed: {e}")
                raise
                
        elif action_type == 'wait':
            duration = action.get('duration', 500)
            await self.page.wait_for_timeout(duration)
            
        else:
            logger.warning(f"Unknown action type: {action_type}")
            
    def _validate_action(self, action: Dict, before: Dict, after: Dict) -> Dict[str, Any]:
        """Validate action execution using Streamware component"""
        validation = (
            flow(f"action-validate://check?type={action.get('type', 'fill')}")
            .with_data({
                'action': action,
                'before_state': before,
                'after_state': after
            })
            .run()
        )
        return validation
        
    def _is_same_action(self, action1: Dict, action2: Dict) -> bool:
        """Check if two actions are the same"""
        return (
            action1.get('type') == action2.get('type') and
            action1.get('selector') == action2.get('selector') and
            action1.get('value') == action2.get('value')
        )


# Convenience functions

async def execute_with_planner_v2(page, instruction: str, max_steps: int = 10) -> Dict[str, Any]:
    """
    Execute instruction using Hierarchical Planner V2
    
    Args:
        page: Playwright page
        instruction: Natural language instruction
        max_steps: Maximum steps
        
    Returns:
        Execution result
    """
    planner = HierarchicalPlannerV2(page)
    return await planner.execute(instruction, max_steps)


def create_form_fill_flow(instruction: str) -> str:
    """
    Create a Streamware flow for form filling
    
    This demonstrates how to express the entire form filling
    process as a declarative flow.
    
    Args:
        instruction: Form filling instruction
        
    Returns:
        Flow URI
    """
    # Parse instruction to extract fields
    from .streamware.components.dom_fix import FieldMapperComponent
    from .streamware import StreamwareURI
    
    mapper = FieldMapperComponent(StreamwareURI("field-mapper://map?strategy=fuzzy"))
    
    # This would be used to create a YAML flow dynamically
    flow_definition = {
        'name': 'Form Fill Flow',
        'instruction': instruction,
        'steps': [
            {'component': 'dom-snapshot://capture', 'params': {'include_values': True}},
            {'component': 'dom-analyze://extract', 'params': {'type': 'forms'}},
            {'component': 'field-mapper://map', 'params': {'strategy': 'fuzzy'}},
            {'component': 'action-plan://decide', 'params': {'strategy': 'smart'}},
        ]
    }
    
    return flow_definition
