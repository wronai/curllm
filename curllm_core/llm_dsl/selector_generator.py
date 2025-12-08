"""
LLM Selector Generator - Dynamic selector generation using LLM

Instead of hardcoded keyword lists like ['email', 'mail', 'adres'],
the LLM analyzes the page context and generates appropriate selectors.

Architecture:
1. Provide page context (DOM, form structure, labels)
2. LLM generates CSS selectors based on semantic understanding
3. Fallback to statistical analysis if LLM unavailable
"""

import logging
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GeneratedSelector:
    """Result of LLM-generated selector"""
    selector: str
    purpose: str
    confidence: float
    method: str  # 'llm', 'statistical', 'fallback'
    reasoning: str = ""


class LLMSelectorGenerator:
    """
    Generates CSS selectors dynamically using LLM analysis.
    
    NO HARDCODED KEYWORD LISTS.
    LLM understands context and generates appropriate selectors.
    """
    
    def __init__(self, llm=None):
        self.llm = llm
    
    async def generate_field_selector(
        self,
        page,
        purpose: str,
        form_context: Optional[str] = None
    ) -> GeneratedSelector:
        """
        Generate a CSS selector for a form field based on its PURPOSE.
        
        Args:
            page: Playwright page object
            purpose: What the field is for (e.g., "email input", "consent checkbox")
            form_context: Optional HTML context of the form
        
        Returns:
            GeneratedSelector with CSS selector
        """
        # Get page structure for LLM analysis
        page_info = await self._get_page_structure(page)
        
        # Try LLM first
        if self.llm:
            result = await self._generate_with_llm(purpose, page_info, form_context)
            if result and result.confidence > 0.5:
                return result
        
        # Fallback to statistical analysis
        return await self._generate_statistical(page, purpose, page_info)
    
    async def generate_consent_selector(self, page) -> GeneratedSelector:
        """
        Generate selector for consent/GDPR checkbox using LLM.
        
        LLM analyzes all checkboxes and their labels to find consent-related ones.
        """
        page_info = await self._get_checkbox_info(page)
        
        if self.llm:
            prompt = f"""Analyze these checkboxes and find the consent/GDPR/terms checkbox.

Checkboxes found:
{json.dumps(page_info.get('checkboxes', [])[:20], indent=2)}

Labels found:
{json.dumps(page_info.get('labels', [])[:20], indent=2)}

Return JSON:
{{"found": true/false, "checkbox_index": N, "selector": "CSS selector", "confidence": 0.0-1.0, "reason": "why this is consent"}}

If no consent checkbox found, return: {{"found": false, "reason": "no consent checkbox"}}
"""
            try:
                response = await self.llm.aquery(prompt)
                result = self._parse_llm_response(response)
                
                if result and result.get('found'):
                    return GeneratedSelector(
                        selector=result.get('selector', ''),
                        purpose='consent_checkbox',
                        confidence=result.get('confidence', 0.5),
                        method='llm',
                        reasoning=result.get('reason', '')
                    )
            except Exception as e:
                logger.debug(f"LLM consent detection failed: {e}")
        
        # Fallback: find required checkbox
        return await self._find_required_checkbox(page)
    
    async def generate_success_indicator_selector(self, page) -> GeneratedSelector:
        """
        Generate selector for form success indicators using LLM.
        
        LLM analyzes visible messages to detect success confirmation.
        """
        messages = await self._get_visible_messages(page)
        
        if self.llm:
            prompt = f"""Analyze these visible messages and find success indicators after form submission.

Messages found:
{json.dumps(messages[:30], indent=2)}

Return JSON:
{{"found": true/false, "message_index": N, "selector": "CSS selector", "is_success": true/false, "confidence": 0.0-1.0}}
"""
            try:
                response = await self.llm.aquery(prompt)
                result = self._parse_llm_response(response)
                
                if result and result.get('found') and result.get('is_success'):
                    return GeneratedSelector(
                        selector=result.get('selector', ''),
                        purpose='success_indicator',
                        confidence=result.get('confidence', 0.5),
                        method='llm'
                    )
            except Exception as e:
                logger.debug(f"LLM success detection failed: {e}")
        
        # Fallback: check for success-like classes
        return GeneratedSelector(
            selector='',
            purpose='success_indicator',
            confidence=0.0,
            method='fallback'
        )
    
    async def generate_error_indicator_selector(self, page, field_selector: str) -> GeneratedSelector:
        """
        Generate selector for field error messages using LLM.
        """
        error_context = await self._get_error_context(page, field_selector)
        
        if self.llm:
            prompt = f"""Analyze this field context and find error message elements.

Field: {field_selector}
Nearby elements:
{json.dumps(error_context[:20], indent=2)}

Return JSON:
{{"found": true/false, "selector": "CSS selector for error", "error_text": "the error message", "confidence": 0.0-1.0}}
"""
            try:
                response = await self.llm.aquery(prompt)
                result = self._parse_llm_response(response)
                
                if result and result.get('found'):
                    return GeneratedSelector(
                        selector=result.get('selector', ''),
                        purpose='error_indicator',
                        confidence=result.get('confidence', 0.5),
                        method='llm',
                        reasoning=result.get('error_text', '')
                    )
            except Exception as e:
                logger.debug(f"LLM error detection failed: {e}")
        
        return GeneratedSelector(
            selector='',
            purpose='error_indicator',
            confidence=0.0,
            method='fallback'
        )
    
    async def _get_page_structure(self, page) -> Dict:
        """Get page structure for LLM analysis"""
        return await page.evaluate("""() => {
            const result = {
                inputs: [],
                labels: [],
                buttons: []
            };
            
            // Get all visible inputs
            document.querySelectorAll('input, textarea, select').forEach((el, i) => {
                if (el.offsetParent === null) return;
                result.inputs.push({
                    index: i,
                    tag: el.tagName.toLowerCase(),
                    type: el.type || 'text',
                    name: el.name,
                    id: el.id,
                    placeholder: el.placeholder,
                    ariaLabel: el.getAttribute('aria-label'),
                    required: el.required,
                    className: el.className?.split(' ').slice(0, 3).join(' ')
                });
            });
            
            // Get all labels
            document.querySelectorAll('label').forEach((el, i) => {
                result.labels.push({
                    index: i,
                    text: el.textContent?.trim().substring(0, 100),
                    for: el.getAttribute('for')
                });
            });
            
            return result;
        }""")
    
    async def _get_checkbox_info(self, page) -> Dict:
        """Get checkbox information for consent detection"""
        return await page.evaluate("""() => {
            const result = {
                checkboxes: [],
                labels: []
            };
            
            document.querySelectorAll('input[type="checkbox"]').forEach((cb, i) => {
                if (cb.offsetParent === null) return;
                
                // Find associated label
                let labelText = '';
                if (cb.id) {
                    const label = document.querySelector(`label[for="${cb.id}"]`);
                    if (label) labelText = label.textContent?.trim();
                }
                if (!labelText) {
                    const parentLabel = cb.closest('label');
                    if (parentLabel) labelText = parentLabel.textContent?.trim();
                }
                
                result.checkboxes.push({
                    index: i,
                    id: cb.id,
                    name: cb.name,
                    required: cb.required,
                    labelText: labelText?.substring(0, 200),
                    className: cb.className
                });
            });
            
            return result;
        }""")
    
    async def _get_visible_messages(self, page) -> List[Dict]:
        """Get visible text messages for success/error detection"""
        return await page.evaluate("""() => {
            const messages = [];
            
            // Find elements that might contain messages
            const candidates = document.querySelectorAll(
                '[class*="message"], [class*="alert"], [class*="notice"], ' +
                '[class*="success"], [class*="error"], [class*="warning"], ' +
                '[role="alert"], [role="status"]'
            );
            
            candidates.forEach((el, i) => {
                if (el.offsetParent === null) return;
                const text = el.textContent?.trim();
                if (!text || text.length > 500) return;
                
                messages.push({
                    index: i,
                    text: text.substring(0, 200),
                    className: el.className,
                    tagName: el.tagName.toLowerCase()
                });
            });
            
            return messages;
        }""")
    
    async def _get_error_context(self, page, field_selector: str) -> List[Dict]:
        """Get context around a field for error detection"""
        return await page.evaluate("""(selector) => {
            const field = document.querySelector(selector);
            if (!field) return [];
            
            const context = [];
            const parent = field.parentElement;
            
            if (parent) {
                // Get siblings and nearby elements
                Array.from(parent.children).forEach((el, i) => {
                    if (el === field) return;
                    const text = el.textContent?.trim();
                    if (!text || text.length > 200) return;
                    
                    context.push({
                        index: i,
                        text: text,
                        className: el.className,
                        tagName: el.tagName.toLowerCase(),
                        isVisible: el.offsetParent !== null
                    });
                });
            }
            
            return context;
        }""", field_selector)
    
    async def _generate_with_llm(
        self,
        purpose: str,
        page_info: Dict,
        form_context: Optional[str]
    ) -> Optional[GeneratedSelector]:
        """Generate selector using LLM"""
        prompt = f"""Analyze this page structure and generate a CSS selector for: "{purpose}"

Inputs found:
{json.dumps(page_info.get('inputs', [])[:15], indent=2)}

Labels found:
{json.dumps(page_info.get('labels', [])[:15], indent=2)}

Return JSON:
{{"selector": "CSS selector", "confidence": 0.0-1.0, "reasoning": "why this selector"}}
"""
        
        try:
            response = await self.llm.aquery(prompt)
            result = self._parse_llm_response(response)
            
            if result and result.get('selector'):
                return GeneratedSelector(
                    selector=result['selector'],
                    purpose=purpose,
                    confidence=result.get('confidence', 0.5),
                    method='llm',
                    reasoning=result.get('reasoning', '')
                )
        except Exception as e:
            logger.debug(f"LLM selector generation failed: {e}")
        
        return None
    
    async def _generate_statistical(
        self,
        page,
        purpose: str,
        page_info: Dict
    ) -> GeneratedSelector:
        """Fallback: generate selector using statistical analysis"""
        purpose_lower = purpose.lower()
        
        # Score inputs based on purpose words in their attributes
        best_score = 0
        best_selector = ''
        
        for inp in page_info.get('inputs', []):
            score = 0
            text = f"{inp.get('name', '')} {inp.get('id', '')} {inp.get('placeholder', '')} {inp.get('ariaLabel', '')}".lower()
            
            # Simple word overlap scoring
            for word in purpose_lower.split():
                if word in text:
                    score += 1
            
            if score > best_score:
                best_score = score
                if inp.get('id'):
                    best_selector = f"#{inp['id']}"
                elif inp.get('name'):
                    best_selector = f"[name=\"{inp['name']}\"]"
        
        return GeneratedSelector(
            selector=best_selector,
            purpose=purpose,
            confidence=min(best_score * 0.3, 0.9) if best_score > 0 else 0.0,
            method='statistical'
        )
    
    async def _find_required_checkbox(self, page) -> GeneratedSelector:
        """Fallback: find required checkbox"""
        selector = await page.evaluate("""() => {
            const cb = document.querySelector('input[type="checkbox"][required]');
            if (cb && cb.offsetParent !== null) {
                cb.setAttribute('data-llm-consent', 'true');
                return '[data-llm-consent="true"]';
            }
            return null;
        }""")
        
        if selector:
            return GeneratedSelector(
                selector=selector,
                purpose='consent_checkbox',
                confidence=0.4,
                method='fallback'
            )
        
        return GeneratedSelector(
            selector='',
            purpose='consent_checkbox',
            confidence=0.0,
            method='fallback'
        )
    
    def _parse_llm_response(self, response: str) -> Optional[Dict]:
        """Parse LLM JSON response"""
        try:
            json_match = re.search(r'\{[^{}]+\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return None


# Convenience function
async def generate_selector(page, purpose: str, llm=None) -> GeneratedSelector:
    """
    Generate CSS selector for a purpose using LLM.
    
    Example:
        selector = await generate_selector(page, "email input field", llm=my_llm)
        if selector.confidence > 0.5:
            await page.fill(selector.selector, "test@example.com")
    """
    generator = LLMSelectorGenerator(llm=llm)
    return await generator.generate_field_selector(page, purpose)
