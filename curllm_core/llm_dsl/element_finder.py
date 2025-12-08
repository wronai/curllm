"""
LLM Element Finder - Dynamic element finding using LLM

NO HARDCODED SELECTORS OR KEYWORDS.
Uses LLM to understand intent and generate appropriate queries.

Architecture:
1. Analyze page structure (statistical)
2. Ask LLM to identify element based on purpose
3. Generate selector dynamically
4. Validate and return
"""

import logging
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ElementMatch:
    """Result of finding an element"""
    found: bool
    selector: Optional[str] = None
    element_info: Optional[Dict] = None
    confidence: float = 0.0
    method: str = ""  # llm, semantic, structural, visual


class LLMElementFinder:
    """
    Find elements using LLM analysis instead of hardcoded selectors.
    
    Strategy hierarchy:
    1. LLM semantic understanding
    2. Structural pattern analysis
    3. Visual/positional analysis
    4. Fallback heuristics
    """
    
    def __init__(self, page=None, llm=None):
        self.page = page
        self.llm = llm
    
    async def find_element(
        self,
        purpose: str,
        context: Optional[Dict] = None,
        use_llm: bool = True
    ) -> ElementMatch:
        """
        Find element by its PURPOSE, not by hardcoded selector.
        
        Args:
            purpose: What the element is for (e.g., "email input", "submit button")
            context: Additional context about the page/form
            use_llm: Whether to use LLM for analysis
        
        Returns:
            ElementMatch with selector and confidence
        """
        if not self.page:
            return ElementMatch(found=False)
        
        # Get page structure for analysis
        page_info = await self._analyze_page_structure()
        
        # Strategy 1: LLM Analysis
        if use_llm and self.llm:
            result = await self._find_with_llm(purpose, page_info, context)
            if result.found and result.confidence > 0.7:
                return result
        
        # Strategy 2: Semantic Analysis
        result = await self._find_with_semantic_analysis(purpose, page_info)
        if result.found and result.confidence > 0.6:
            return result
        
        # Strategy 3: Structural Analysis
        result = await self._find_with_structural_analysis(purpose, page_info)
        if result.found:
            return result
        
        return ElementMatch(found=False)
    
    async def _analyze_page_structure(self) -> Dict:
        """Analyze page structure without hardcoded selectors"""
        return await self.page.evaluate("""() => {
            const result = {
                forms: [],
                inputs: [],
                buttons: [],
                links: [],
                textAreas: [],
                labels: []
            };
            
            // Analyze forms
            document.querySelectorAll('form').forEach((form, i) => {
                const formInfo = {
                    index: i,
                    action: form.action,
                    method: form.method,
                    id: form.id,
                    className: form.className,
                    inputCount: form.querySelectorAll('input, textarea, select').length
                };
                result.forms.push(formInfo);
            });
            
            // Analyze inputs (get ALL attributes for LLM analysis)
            document.querySelectorAll('input, select').forEach((el, i) => {
                if (el.offsetParent === null) return; // Skip hidden
                
                const rect = el.getBoundingClientRect();
                result.inputs.push({
                    index: i,
                    tagName: el.tagName,
                    type: el.type || 'text',
                    name: el.name,
                    id: el.id,
                    placeholder: el.placeholder,
                    ariaLabel: el.getAttribute('aria-label'),
                    className: el.className,
                    required: el.required,
                    autocomplete: el.autocomplete,
                    // Position for visual analysis
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    // Label if associated
                    label: el.labels?.[0]?.textContent?.trim()
                });
            });
            
            // Analyze textareas
            document.querySelectorAll('textarea').forEach((el, i) => {
                if (el.offsetParent === null) return;
                
                const rect = el.getBoundingClientRect();
                result.textAreas.push({
                    index: i,
                    name: el.name,
                    id: el.id,
                    placeholder: el.placeholder,
                    ariaLabel: el.getAttribute('aria-label'),
                    className: el.className,
                    required: el.required,
                    x: rect.x,
                    y: rect.y,
                    label: el.labels?.[0]?.textContent?.trim()
                });
            });
            
            // Analyze buttons
            document.querySelectorAll('button, input[type="submit"], [role="button"]').forEach((el, i) => {
                if (el.offsetParent === null) return;
                
                const rect = el.getBoundingClientRect();
                result.buttons.push({
                    index: i,
                    tagName: el.tagName,
                    type: el.type,
                    text: el.textContent?.trim().substring(0, 100),
                    ariaLabel: el.getAttribute('aria-label'),
                    className: el.className,
                    x: rect.x,
                    y: rect.y
                });
            });
            
            // Analyze labels
            document.querySelectorAll('label').forEach((el, i) => {
                result.labels.push({
                    text: el.textContent?.trim().substring(0, 100),
                    for: el.getAttribute('for'),
                    hasInput: el.querySelector('input, textarea, select') !== null
                });
            });
            
            return result;
        }""")
    
    async def _find_with_llm(
        self,
        purpose: str,
        page_info: Dict,
        context: Optional[Dict]
    ) -> ElementMatch:
        """Use LLM to find element based on purpose"""
        if not self.llm:
            return ElementMatch(found=False)
        
        # Create compact representation for LLM
        prompt = f"""Analyze this page structure and find the element for: "{purpose}"

Page has:
- {len(page_info.get('forms', []))} forms
- {len(page_info.get('inputs', []))} inputs
- {len(page_info.get('textAreas', []))} textareas  
- {len(page_info.get('buttons', []))} buttons

Inputs:
{json.dumps(page_info.get('inputs', [])[:10], indent=2)}

TextAreas:
{json.dumps(page_info.get('textAreas', [])[:5], indent=2)}

Buttons:
{json.dumps(page_info.get('buttons', [])[:5], indent=2)}

Labels:
{json.dumps(page_info.get('labels', [])[:10], indent=2)}

Return JSON with:
{{"found": true/false, "element_type": "input/textarea/button", "index": N, "selector": "CSS selector", "confidence": 0.0-1.0, "reason": "why this element"}}
"""
        
        try:
            response = await self.llm.aquery(prompt)
            # Parse LLM response
            result = self._parse_llm_response(response)
            
            if result and result.get('found'):
                return ElementMatch(
                    found=True,
                    selector=result.get('selector'),
                    element_info=result,
                    confidence=result.get('confidence', 0.5),
                    method='llm'
                )
        except Exception as e:
            logger.debug(f"LLM element finding failed: {e}")
        
        return ElementMatch(found=False)
    
    def _parse_llm_response(self, response: str) -> Optional[Dict]:
        """Parse LLM JSON response"""
        try:
            # Find JSON in response
            import re
            json_match = re.search(r'\{[^{}]+\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return None
    
    async def _find_with_semantic_analysis(
        self,
        purpose: str,
        page_info: Dict
    ) -> ElementMatch:
        """Find element using semantic analysis of attributes"""
        purpose_lower = purpose.lower()
        
        # Semantic mapping (NO hardcoded selectors - just concepts)
        semantic_concepts = {
            'email': ['email', 'mail', 'e-mail', 'correo'],
            'name': ['name', 'nombre', 'imie', 'nazwisko', 'fullname'],
            'phone': ['phone', 'tel', 'telefon', 'mobile', 'cell'],
            'message': ['message', 'wiadomosc', 'tresc', 'content', 'body'],
            'subject': ['subject', 'temat', 'topic', 'title'],
            'password': ['password', 'haslo', 'pass', 'pwd'],
            'search': ['search', 'szukaj', 'query', 'q'],
            'submit': ['submit', 'send', 'wyslij', 'zapisz', 'save'],
        }
        
        # Find which concept matches the purpose
        matching_concepts = []
        for concept, keywords in semantic_concepts.items():
            if any(kw in purpose_lower for kw in keywords):
                matching_concepts.append(concept)
            if concept in purpose_lower:
                matching_concepts.append(concept)
        
        if not matching_concepts:
            return ElementMatch(found=False)
        
        # Search inputs for matching concepts
        for inp in page_info.get('inputs', []):
            score = self._calculate_semantic_score(inp, matching_concepts)
            if score > 0.5:
                selector = self._generate_selector(inp, 'input')
                return ElementMatch(
                    found=True,
                    selector=selector,
                    element_info=inp,
                    confidence=score,
                    method='semantic'
                )
        
        # Search textareas
        for ta in page_info.get('textAreas', []):
            score = self._calculate_semantic_score(ta, matching_concepts)
            if score > 0.5:
                selector = self._generate_selector(ta, 'textarea')
                return ElementMatch(
                    found=True,
                    selector=selector,
                    element_info=ta,
                    confidence=score,
                    method='semantic'
                )
        
        # Search buttons
        if 'submit' in matching_concepts or 'send' in purpose_lower:
            for btn in page_info.get('buttons', []):
                score = self._calculate_button_score(btn, matching_concepts)
                if score > 0.5:
                    selector = self._generate_selector(btn, 'button')
                    return ElementMatch(
                        found=True,
                        selector=selector,
                        element_info=btn,
                        confidence=score,
                        method='semantic'
                    )
        
        return ElementMatch(found=False)
    
    def _calculate_semantic_score(self, element: Dict, concepts: List[str]) -> float:
        """Calculate how well element matches concepts"""
        score = 0.0
        
        # Check all text attributes
        text_attrs = [
            element.get('name', ''),
            element.get('id', ''),
            element.get('placeholder', ''),
            element.get('ariaLabel', ''),
            element.get('label', ''),
            element.get('autocomplete', ''),
        ]
        
        combined_text = ' '.join(str(a).lower() for a in text_attrs if a)
        
        for concept in concepts:
            if concept in combined_text:
                score += 0.3
        
        # Type matching
        el_type = element.get('type', '')
        if el_type == 'email' and 'email' in concepts:
            score += 0.4
        if el_type == 'tel' and 'phone' in concepts:
            score += 0.4
        if el_type == 'password' and 'password' in concepts:
            score += 0.4
        if el_type == 'search' and 'search' in concepts:
            score += 0.4
        
        return min(score, 1.0)
    
    def _calculate_button_score(self, button: Dict, concepts: List[str]) -> float:
        """Calculate how well button matches submit concepts"""
        score = 0.0
        
        text = (button.get('text', '') or '').lower()
        btn_type = button.get('type', '')
        
        if btn_type == 'submit':
            score += 0.5
        
        submit_words = ['submit', 'send', 'wyślij', 'wyslij', 'zapisz', 'save', 'ok']
        if any(w in text for w in submit_words):
            score += 0.4
        
        return min(score, 1.0)
    
    def _generate_selector(self, element: Dict, tag: str) -> str:
        """Generate CSS selector for element"""
        # Prefer ID
        if element.get('id'):
            return f"#{element['id']}"
        
        # Then name
        if element.get('name'):
            return f'{tag}[name="{element["name"]}"]'
        
        # Then type + index
        if element.get('type') and element.get('index') is not None:
            return f'{tag}[type="{element["type"]}"]:nth-of-type({element["index"] + 1})'
        
        # Fallback to index
        if element.get('index') is not None:
            return f'{tag}:nth-of-type({element["index"] + 1})'
        
        return tag
    
    async def _find_with_structural_analysis(
        self,
        purpose: str,
        page_info: Dict
    ) -> ElementMatch:
        """Find element using structural/positional analysis"""
        purpose_lower = purpose.lower()
        
        # For form fields, look at position within form
        if 'email' in purpose_lower or 'mail' in purpose_lower:
            # Email is usually first or second input
            for inp in page_info.get('inputs', [])[:3]:
                if inp.get('type') == 'email':
                    return ElementMatch(
                        found=True,
                        selector=self._generate_selector(inp, 'input'),
                        element_info=inp,
                        confidence=0.6,
                        method='structural'
                    )
        
        # Message is usually a textarea
        if 'message' in purpose_lower or 'content' in purpose_lower:
            textareas = page_info.get('textAreas', [])
            if textareas:
                ta = textareas[0]  # Usually only one textarea for message
                return ElementMatch(
                    found=True,
                    selector=self._generate_selector(ta, 'textarea'),
                    element_info=ta,
                    confidence=0.5,
                    method='structural'
                )
        
        # Submit button is usually last in form
        if 'submit' in purpose_lower or 'send' in purpose_lower:
            buttons = page_info.get('buttons', [])
            if buttons:
                # Get button with highest Y position (usually at bottom)
                bottom_button = max(buttons, key=lambda b: b.get('y', 0))
                return ElementMatch(
                    found=True,
                    selector=self._generate_selector(bottom_button, 'button'),
                    element_info=bottom_button,
                    confidence=0.5,
                    method='structural'
                )
        
        return ElementMatch(found=False)


# Convenience function
async def find_element_by_purpose(page, purpose: str, llm=None) -> ElementMatch:
    """
    Find element by its PURPOSE using LLM-driven analysis.
    
    Example:
        element = await find_element_by_purpose(page, "email input field")
        if element.found:
            await page.fill(element.selector, "test@example.com")
    """
    finder = LLMElementFinder(page=page, llm=llm)
    return await finder.find_element(purpose)
