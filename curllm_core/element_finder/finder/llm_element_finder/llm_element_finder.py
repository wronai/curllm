import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from ..element_match import ElementMatch
from ..page_context import PageContext


logger = logging.getLogger(__name__)

class LLMElementFinder:
    """
    Use LLM to find elements on page based on intent.
    
    Instead of hardcoding selectors like:
        'input[type="email"]', 'input[name*="email"]'
    
    We ask LLM:
        "Find the email input field on this page given the DOM structure"
    
    This works on any website regardless of their specific HTML structure.
    """
    
    def __init__(self, llm=None, page=None):
        """
        Args:
            llm: LangChain-compatible LLM client
            page: Playwright page object
        """
        self.llm = llm
        self.page = page
    
    async def get_page_context(self) -> PageContext:
        """Extract page context for LLM analysis"""
        if not self.page:
            return PageContext("", "", "", [], [], [], [])
        
        try:
            context = await self.page.evaluate("""
                () => {
                    // Get visible text (limited)
                    const visibleText = document.body.innerText.slice(0, 3000);
                    
                    // Get all form fields with their attributes
                    const inputs = Array.from(document.querySelectorAll('input, textarea, select'))
                        .filter(el => el.offsetParent !== null)  // Only visible
                        .slice(0, 30)
                        .map(el => ({
                            tag: el.tagName.toLowerCase(),
                            type: el.type || '',
                            name: el.name || '',
                            id: el.id || '',
                            placeholder: el.placeholder || '',
                            ariaLabel: el.getAttribute('aria-label') || '',
                            className: el.className.split(' ').slice(0, 3).join(' '),
                            visible: el.offsetParent !== null,
                            value: el.value ? '[has value]' : '',
                        }));
                    
                    // Get buttons
                    const buttons = Array.from(document.querySelectorAll('button, input[type="submit"], [role="button"]'))
                        .filter(el => el.offsetParent !== null)
                        .slice(0, 20)
                        .map(el => ({
                            tag: el.tagName.toLowerCase(),
                            type: el.type || '',
                            text: el.innerText?.slice(0, 50) || '',
                            id: el.id || '',
                            className: el.className.split(' ').slice(0, 3).join(' '),
                            ariaLabel: el.getAttribute('aria-label') || '',
                        }));
                    
                    // Get important links
                    const links = Array.from(document.querySelectorAll('a[href]'))
                        .filter(el => el.offsetParent !== null && el.innerText.trim())
                        .slice(0, 30)
                        .map(el => ({
                            text: el.innerText.trim().slice(0, 50),
                            href: el.getAttribute('href'),
                            id: el.id || '',
                        }));
                    
                    // Get forms
                    const forms = Array.from(document.querySelectorAll('form'))
                        .map(f => ({
                            id: f.id || '',
                            action: f.action || '',
                            method: f.method || '',
                            inputCount: f.querySelectorAll('input, textarea').length,
                        }));
                    
                    return {
                        url: location.href,
                        title: document.title,
                        visibleText: visibleText,
                        inputs: inputs,
                        buttons: buttons,
                        links: links,
                        forms: forms,
                    };
                }
            """)
            
            return PageContext(
                url=context.get('url', ''),
                title=context.get('title', ''),
                visible_text=context.get('visibleText', ''),
                form_fields=context.get('inputs', []),
                buttons=context.get('buttons', []),
                links=context.get('links', []),
                inputs=context.get('inputs', []),
            )
        except Exception as e:
            logger.error(f"Failed to get page context: {e}")
            return PageContext("", "", "", [], [], [], [])
    
    async def find_element(
        self,
        intent: str,
        element_type: str = "any",
        context_hint: str = ""
    ) -> Optional[ElementMatch]:
        """
        Find element using LLM based on intent.
        
        Args:
            intent: What we're looking for, e.g., "email input field", "submit button"
            element_type: Type hint - "input", "button", "link", "textarea", "any"
            context_hint: Additional context, e.g., "for contact form"
            
        Returns:
            ElementMatch with selector and confidence
        """
        # Get page context
        page_context = await self.get_page_context()
        
        # If no LLM available, fall back to heuristic matching
        if not self.llm:
            return await self._heuristic_find(intent, element_type, page_context)
        
        # Build prompt for LLM
        prompt = self._build_find_element_prompt(intent, element_type, context_hint, page_context)
        
        try:
            response = await self._call_llm(prompt)
            return self._parse_element_response(response)
        except Exception as e:
            logger.warning(f"LLM element finding failed: {e}, using heuristic")
            return await self._heuristic_find(intent, element_type, page_context)
    
    async def find_form_field(
        self,
        field_purpose: str,
        value_to_fill: str = ""
    ) -> Optional[ElementMatch]:
        """
        Find form field for specific purpose.
        
        Args:
            field_purpose: "email", "name", "phone", "message", "password", etc.
            value_to_fill: Optional value hint for better matching
            
        Returns:
            ElementMatch with selector
        """
        page_context = await self.get_page_context()
        
        if not self.llm:
            return await self._heuristic_find_field(field_purpose, page_context)
        
        prompt = f"""Analyze this page and find the form field for: {field_purpose}

Page URL: {page_context.url}
Page title: {page_context.title}

Available input fields:
{json.dumps(page_context.inputs, indent=2, ensure_ascii=False)}

Task: Find the input field that should be used for "{field_purpose}"
{f'The value to be entered is: {value_to_fill}' if value_to_fill else ''}

Respond in JSON format:
{{
    "found": true/false,
    "selector": "CSS selector to find the element",
    "confidence": 0.0-1.0,
    "reasoning": "Why this is the right field"
}}"""

        try:
            response = await self._call_llm(prompt)
            return self._parse_element_response(response)
        except Exception:
            return await self._heuristic_find_field(field_purpose, page_context)
    
    async def find_submit_button(
        self,
        form_context: str = "contact form"
    ) -> Optional[ElementMatch]:
        """Find the submit button for a form"""
        page_context = await self.get_page_context()
        
        if not self.llm:
            return await self._heuristic_find_button(page_context)
        
        prompt = f"""Find the submit button for {form_context} on this page.

Page URL: {page_context.url}
Available buttons:
{json.dumps(page_context.buttons, indent=2, ensure_ascii=False)}

Respond in JSON:
{{
    "found": true/false,
    "selector": "CSS selector for submit button",
    "confidence": 0.0-1.0,
    "reasoning": "Why this is the submit button"
}}"""

        try:
            response = await self._call_llm(prompt)
            return self._parse_element_response(response)
        except Exception:
            return await self._heuristic_find_button(page_context)
    
    async def find_search_input(self) -> Optional[ElementMatch]:
        """Find the search input on the page"""
        page_context = await self.get_page_context()
        
        if not self.llm:
            return await self._heuristic_find_search(page_context)
        
        prompt = f"""Find the search input field on this page.

Page URL: {page_context.url}
Available inputs:
{json.dumps(page_context.inputs, indent=2, ensure_ascii=False)}

Look for inputs that are likely search boxes (type=search, placeholder contains search/szukaj, etc.)

Respond in JSON:
{{
    "found": true/false,
    "selector": "CSS selector",
    "confidence": 0.0-1.0,
    "reasoning": "Why this is the search input"
}}"""

        try:
            response = await self._call_llm(prompt)
            return self._parse_element_response(response)
        except Exception:
            return await self._heuristic_find_search(page_context)
    
    async def find_link(
        self,
        link_purpose: str
    ) -> Optional[ElementMatch]:
        """Find a link based on purpose (e.g., 'contact', 'cart', 'login')"""
        page_context = await self.get_page_context()
        
        if not self.llm:
            return await self._heuristic_find_link(link_purpose, page_context)
        
        prompt = f"""Find a link for: {link_purpose}

Page URL: {page_context.url}
Available links:
{json.dumps(page_context.links, indent=2, ensure_ascii=False)}

Respond in JSON:
{{
    "found": true/false,
    "selector": "CSS selector or href pattern",
    "href": "the link URL",
    "confidence": 0.0-1.0,
    "reasoning": "Why this is the right link"
}}"""

        try:
            response = await self._call_llm(prompt)
            return self._parse_element_response(response)
        except Exception:
            return await self._heuristic_find_link(link_purpose, page_context)
    
    def _build_find_element_prompt(
        self,
        intent: str,
        element_type: str,
        context_hint: str,
        page_context: PageContext
    ) -> str:
        """Build prompt for LLM to find element"""
        
        elements_info = ""
        if element_type in ["input", "any"]:
            elements_info += f"\nInput fields:\n{json.dumps(page_context.inputs[:15], indent=2, ensure_ascii=False)}"
        if element_type in ["button", "any"]:
            elements_info += f"\nButtons:\n{json.dumps(page_context.buttons[:10], indent=2, ensure_ascii=False)}"
        if element_type in ["link", "any"]:
            elements_info += f"\nLinks:\n{json.dumps(page_context.links[:15], indent=2, ensure_ascii=False)}"
        
        return f"""You are analyzing a web page to find a specific element.

Task: Find element for: "{intent}"
Element type: {element_type}
{f'Context: {context_hint}' if context_hint else ''}

Page URL: {page_context.url}
Page title: {page_context.title}
{elements_info}

Analyze the available elements and determine which one matches the intent.
Consider:
- Element attributes (name, id, placeholder, aria-label)
- Element type and purpose
- Position and context on page

Respond in JSON format:
{{
    "found": true/false,
    "selector": "CSS selector that uniquely identifies the element",
    "element_type": "input/button/link/textarea",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this is the right element"
}}"""
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        if hasattr(self.llm, 'ainvoke'):
            response = await self.llm.ainvoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        elif hasattr(self.llm, 'invoke'):
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        else:
            raise ValueError("LLM doesn't have invoke method")
    
    def _parse_element_response(self, response: str) -> Optional[ElementMatch]:
        """Parse LLM response into ElementMatch"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if not json_match:
                return None
            
            data = json.loads(json_match.group())
            
            if not data.get('found', False):
                return None
            
            return ElementMatch(
                selector=data.get('selector', ''),
                confidence=float(data.get('confidence', 0.5)),
                reasoning=data.get('reasoning', ''),
                element_type=data.get('element_type', 'unknown'),
                attributes=data.get('attributes', {})
            )
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return None
    
    # =========================================================================
    # Heuristic fallbacks (when LLM is not available)
    # These use statistical/pattern-based matching instead of hardcoded selectors
    # =========================================================================
    
    async def _heuristic_find(
        self,
        intent: str,
        element_type: str,
        context: PageContext
    ) -> Optional[ElementMatch]:
        """Fallback heuristic matching based on intent keywords"""
        intent_lower = intent.lower()
        
        # Score elements based on keyword matching
        if element_type in ["input", "any"]:
            scored = self._score_inputs_by_intent(context.inputs, intent_lower)
            if scored:
                best = scored[0]
                return ElementMatch(
                    selector=self._build_selector(best[1]),
                    confidence=best[0],
                    reasoning="Heuristic match based on attribute keywords",
                    element_type="input",
                    attributes=best[1]
                )
        
        if element_type in ["button", "any"]:
            scored = self._score_buttons_by_intent(context.buttons, intent_lower)
            if scored:
                best = scored[0]
                return ElementMatch(
                    selector=self._build_selector(best[1]),
                    confidence=best[0],
                    reasoning="Heuristic match based on button text",
                    element_type="button",
                    attributes=best[1]
                )
        
        return None
    
    async def _heuristic_find_field(
        self,
        field_purpose: str,
        context: PageContext
    ) -> Optional[ElementMatch]:
        """Find form field using heuristic matching"""
        purpose_lower = field_purpose.lower()
        
        # Keywords for each field type (statistical approach)
        field_keywords = {
            "email": ["email", "mail", "e-mail", "@"],
            "name": ["name", "imię", "nazwisko", "imie", "nazwa"],
            "phone": ["phone", "tel", "telefon", "mobile", "komórka"],
            "message": ["message", "wiadomość", "wiadomosc", "treść", "tresc", "opis", "content", "textarea"],
            "password": ["password", "hasło", "haslo", "pass"],
            "subject": ["subject", "temat", "tytuł", "tytul"],
        }
        
        keywords = field_keywords.get(purpose_lower, [purpose_lower])
        scored = self._score_inputs_by_keywords(context.inputs, keywords)
        
        # For message fields, also boost textareas
        if purpose_lower == "message":
            for i, (score, inp) in enumerate(scored):
                if inp.get('tag') == 'textarea':
                    scored[i] = (score + 0.5, inp)  # Boost textarea for message
            
            # If no keyword matches but we have textareas, use the first visible textarea
            textareas = [inp for inp in context.inputs if inp.get('tag') == 'textarea']
            if not scored and textareas:
                # Return first textarea with high confidence
                return ElementMatch(
                    selector=self._build_selector(textareas[0]),
                    confidence=0.8,
                    reasoning="Using textarea for message (most likely message field)",
                    element_type="textarea",
                    attributes=textareas[0]
                )
            
            # Re-sort after boosting
            scored.sort(key=lambda x: x[0], reverse=True)
        
        if scored:
            best = scored[0]
            return ElementMatch(
                selector=self._build_selector(best[1]),
                confidence=best[0],
                reasoning=f"Matched keywords: {keywords}",
                element_type=best[1].get('tag', 'input'),
                attributes=best[1]
            )
        
        return None
    
    async def _heuristic_find_button(
        self,
        context: PageContext
    ) -> Optional[ElementMatch]:
        """Find submit button using heuristics"""
        submit_keywords = ["submit", "wyślij", "send", "zapisz", "save", "ok", "potwierdź", "confirm"]
        
        scored = []
        for btn in context.buttons:
            score = 0
            text = (btn.get('text', '') + ' ' + btn.get('ariaLabel', '')).lower()
            
            for kw in submit_keywords:
                if kw in text:
                    score += 0.3
            
            if btn.get('type') == 'submit':
                score += 0.5
            
            if score > 0:
                scored.append((score, btn))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        if scored:
            best = scored[0]
            return ElementMatch(
                selector=self._build_selector(best[1]),
                confidence=min(best[0], 1.0),
                reasoning="Matched submit keywords",
                element_type="button",
                attributes=best[1]
            )
        
        return None
    
    async def _heuristic_find_search(
        self,
        context: PageContext
    ) -> Optional[ElementMatch]:
        """Find search input using heuristics"""
        search_keywords = ["search", "szukaj", "wyszukaj", "znajdź", "query", "q"]
        
        scored = self._score_inputs_by_keywords(context.inputs, search_keywords)
        
        # Also boost inputs with type="search"
        for i, (score, inp) in enumerate(scored):
            if inp.get('type') == 'search':
                scored[i] = (score + 0.5, inp)
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        if scored:
            best = scored[0]
            return ElementMatch(
                selector=self._build_selector(best[1]),
                confidence=min(best[0], 1.0),
                reasoning="Matched search keywords",
                element_type="input",
                attributes=best[1]
            )
        
        return None
    
    async def _heuristic_find_link(
        self,
        purpose: str,
        context: PageContext
    ) -> Optional[ElementMatch]:
        """Find link by purpose using heuristics"""
        purpose_lower = purpose.lower()
        
        scored = []
        for link in context.links:
            score = 0
            text = link.get('text', '').lower()
            href = link.get('href', '').lower()
            
            if purpose_lower in text or purpose_lower in href:
                score += 0.5
            
            # Partial matches
            for word in purpose_lower.split():
                if word in text:
                    score += 0.2
                if word in href:
                    score += 0.1
            
            if score > 0:
                scored.append((score, link))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        if scored:
            best = scored[0]
            href = best[1].get('href', '')
            return ElementMatch(
                selector=f'a[href="{href}"]' if href else f'a:has-text("{best[1].get("text", "")}")',
                confidence=min(best[0], 1.0),
                reasoning=f"Matched purpose: {purpose}",
                element_type="link",
                attributes=best[1]
            )
        
        return None
    
    def _score_inputs_by_intent(
        self,
        inputs: List[Dict],
        intent: str
    ) -> List[Tuple[float, Dict]]:
        """Score inputs by how well they match intent"""
        scored = []
        intent_words = intent.split()
        
        for inp in inputs:
            score = 0
            searchable = (
                inp.get('name', '') + ' ' +
                inp.get('id', '') + ' ' +
                inp.get('placeholder', '') + ' ' +
                inp.get('ariaLabel', '') + ' ' +
                inp.get('type', '')
            ).lower()
            
            for word in intent_words:
                if word in searchable:
                    score += 0.3
            
            if score > 0:
                scored.append((min(score, 1.0), inp))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored
    
    def _score_inputs_by_keywords(
        self,
        inputs: List[Dict],
        keywords: List[str]
    ) -> List[Tuple[float, Dict]]:
        """Score inputs by keyword matching"""
        scored = []
        
        for inp in inputs:
            score = 0
            searchable = (
                inp.get('name', '') + ' ' +
                inp.get('id', '') + ' ' +
                inp.get('placeholder', '') + ' ' +
                inp.get('ariaLabel', '') + ' ' +
                inp.get('type', '') + ' ' +
                inp.get('className', '')
            ).lower()
            
            for kw in keywords:
                if kw in searchable:
                    score += 0.3
            
            if score > 0:
                scored.append((min(score, 1.0), inp))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored
    
    def _score_buttons_by_intent(
        self,
        buttons: List[Dict],
        intent: str
    ) -> List[Tuple[float, Dict]]:
        """Score buttons by intent matching"""
        scored = []
        
        for btn in buttons:
            score = 0
            searchable = (
                btn.get('text', '') + ' ' +
                btn.get('ariaLabel', '') + ' ' +
                btn.get('id', '')
            ).lower()
            
            for word in intent.split():
                if word in searchable:
                    score += 0.3
            
            if score > 0:
                scored.append((min(score, 1.0), btn))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored
    
    def _build_selector(self, element: Dict) -> str:
        """Build CSS selector from element attributes"""
        tag = element.get('tag', 'input')
        
        # Prefer ID
        if element.get('id'):
            return f"#{element['id']}"
        
        # Then name
        if element.get('name'):
            return f"{tag}[name=\"{element['name']}\"]"
        
        # Then type + placeholder
        if element.get('type') and element.get('placeholder'):
            return f"{tag}[type=\"{element['type']}\"][placeholder*=\"{element['placeholder'][:20]}\"]"
        
        # Then placeholder alone
        if element.get('placeholder'):
            return f"{tag}[placeholder*=\"{element['placeholder'][:20]}\"]"
        
        # Then aria-label
        if element.get('ariaLabel'):
            return f"{tag}[aria-label*=\"{element['ariaLabel'][:20]}\"]"
        
        # Fallback to class
        if element.get('className'):
            first_class = element['className'].split()[0]
            return f"{tag}.{first_class}"
        
        return tag
