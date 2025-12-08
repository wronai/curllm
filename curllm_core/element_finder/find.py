"""Convenience function for finding elements with LLM"""

from typing import Optional

from curllm_core.element_finder.finder import LLMElementFinder, ElementMatch


async def find_element_with_llm(
    page,
    intent: str,
    llm=None,
    element_type: str = "any"
) -> Optional[ElementMatch]:
    """
    Convenience function for finding elements using LLM.
    
    Args:
        page: Playwright page object
        intent: Description of what element to find
        llm: Optional LLM instance
        element_type: Type of element to find ("any", "button", "input", etc.)
        
    Returns:
        ElementMatch if found, None otherwise
    """
    finder = LLMElementFinder(llm=llm, page=page)
    return await finder.find_element(intent, element_type)
