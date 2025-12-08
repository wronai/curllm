import logging
from typing import Dict, Any, Optional, List


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
