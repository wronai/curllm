"""
Atomic Functions - Specialized micro-functions called via DSL

Each function is:
- Single-purpose
- Statistically-driven (no hardcoded values)
- Context-aware (uses DOM/page state)
- LLM-queryable (can ask LLM for clarification)
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class AtomResult:
    """Result from an atomic function"""
    success: bool
    data: Any = None
    confidence: float = 0.0
    method: str = ""  # statistical, llm, heuristic


class AtomicFunctions:
    """
    Collection of atomic functions for DOM analysis.
    
    NO HARDCODED SELECTORS OR KEYWORDS.
    Uses statistical analysis and LLM queries.
    """
    
    def __init__(self, page=None, llm=None):
        self.page = page
        self.llm = llm
    
    # =========================================================================
    # STATISTICAL ANALYSIS ATOMS
    # =========================================================================
    
    async def find_repeating_pattern(self, min_count: int = 3) -> AtomResult:
        """
        Find repeating DOM patterns using statistical analysis.
        No hardcoded selectors - analyzes DOM structure statistically.
        """
        if not self.page:
            return AtomResult(success=False)
        
        # Get DOM structure statistics
        structure = await self.page.evaluate("""() => {
            const tagPaths = [];
            
            function getPath(el, depth = 0) {
                if (depth > 10 || !el || el === document.body) return '';
                const parent = el.parentElement;
                const tag = el.tagName?.toLowerCase() || '';
                const parentPath = getPath(parent, depth + 1);
                return parentPath ? parentPath + '>' + tag : tag;
            }
            
            // Analyze all elements
            document.querySelectorAll('*').forEach(el => {
                if (el.offsetParent !== null) {
                    tagPaths.push(getPath(el));
                }
            });
            
            return tagPaths;
        }""")
        
        # Statistical analysis - find most common patterns
        counter = Counter(structure)
        common = [(path, count) for path, count in counter.most_common(20) 
                  if count >= min_count and len(path.split('>')) >= 3]
        
        if common:
            return AtomResult(
                success=True,
                data={'patterns': common},
                confidence=min(common[0][1] / 10, 0.95),
                method='statistical'
            )
        
        return AtomResult(success=False)
    
    async def find_input_by_context(self, purpose_description: str) -> AtomResult:
        """
        Find input field by analyzing its context (labels, placeholders, position).
        Uses LLM to understand purpose, NOT hardcoded keywords.
        """
        if not self.page:
            return AtomResult(success=False)
        
        # Get all inputs with their context
        inputs = await self.page.evaluate("""() => {
            const inputs = [];
            document.querySelectorAll('input, textarea, select').forEach((el, idx) => {
                if (el.offsetParent === null || el.type === 'hidden') return;
                
                // Gather context
                const labels = Array.from(el.labels || []).map(l => l.textContent.trim());
                const parent = el.parentElement;
                const siblings = parent ? Array.from(parent.children).map(c => c.textContent?.trim().substring(0, 50)) : [];
                const nearbyText = parent?.textContent?.trim().substring(0, 200) || '';
                
                inputs.push({
                    index: idx,
                    tagName: el.tagName.toLowerCase(),
                    type: el.type || 'text',
                    name: el.name,
                    id: el.id,
                    placeholder: el.placeholder,
                    ariaLabel: el.getAttribute('aria-label'),
                    labels: labels,
                    nearbyText: nearbyText,
                    autocomplete: el.autocomplete,
                });
            });
            return inputs;
        }""")
        
        if not inputs:
            return AtomResult(success=False)
        
        # Use LLM to find best match
        if self.llm:
            prompt = f"""Given these form inputs and their context, which one best matches the purpose: "{purpose_description}"?

Inputs:
{self._format_inputs_for_llm(inputs)}

Respond with ONLY the index number (0-based) of the best matching input, or -1 if none match."""

            try:
                response = await self.llm.agenerate([prompt])
                answer = response.generations[0][0].text.strip()
                
                # Parse index
                match = re.search(r'-?\d+', answer)
                if match:
                    idx = int(match.group())
                    if 0 <= idx < len(inputs):
                        inp = inputs[idx]
                        selector = self._build_selector_from_input(inp)
                        return AtomResult(
                            success=True,
                            data={'selector': selector, 'input': inp},
                            confidence=0.85,
                            method='llm'
                        )
            except Exception as e:
                logger.debug(f"LLM query failed: {e}")
        
        # Fallback: statistical matching based on type attribute
        for inp in inputs:
            if purpose_description.lower() in str(inp).lower():
                selector = self._build_selector_from_input(inp)
                return AtomResult(
                    success=True,
                    data={'selector': selector, 'input': inp},
                    confidence=0.5,
                    method='statistical'
                )
        
        return AtomResult(success=False)
    
    async def find_clickable_by_intent(self, intent: str) -> AtomResult:
        """
        Find clickable element by analyzing page and understanding intent.
        Uses LLM - no hardcoded button labels.
        """
        if not self.page:
            return AtomResult(success=False)
        
        # Get all clickable elements
        clickables = await self.page.evaluate("""() => {
            const results = [];
            const els = document.querySelectorAll('button, a, [role="button"], [onclick], input[type="submit"]');
            
            els.forEach((el, idx) => {
                if (el.offsetParent === null) return;
                
                results.push({
                    index: idx,
                    tagName: el.tagName.toLowerCase(),
                    type: el.type,
                    text: el.textContent?.trim().substring(0, 100),
                    ariaLabel: el.getAttribute('aria-label'),
                    title: el.title,
                    href: el.href,
                    id: el.id,
                    className: el.className,
                });
            });
            
            return results;
        }""")
        
        if not clickables:
            return AtomResult(success=False)
        
        # Use LLM to find best match
        if self.llm:
            prompt = f"""Given these clickable elements, which one best matches the user intent: "{intent}"?

Elements:
{self._format_clickables_for_llm(clickables)}

Respond with ONLY the index number of the best match, or -1 if none match."""

            try:
                response = await self.llm.agenerate([prompt])
                answer = response.generations[0][0].text.strip()
                
                match = re.search(r'-?\d+', answer)
                if match:
                    idx = int(match.group())
                    if 0 <= idx < len(clickables):
                        el = clickables[idx]
                        selector = self._build_clickable_selector(el)
                        return AtomResult(
                            success=True,
                            data={'selector': selector, 'element': el},
                            confidence=0.85,
                            method='llm'
                        )
            except Exception as e:
                logger.debug(f"LLM query failed: {e}")
        
        return AtomResult(success=False)
    
    async def analyze_page_structure(self) -> AtomResult:
        """
        Analyze page structure statistically.
        Returns structural analysis without hardcoded assumptions.
        """
        if not self.page:
            return AtomResult(success=False)
        
        analysis = await self.page.evaluate("""() => {
            const stats = {
                forms: document.querySelectorAll('form').length,
                inputs: document.querySelectorAll('input:not([type="hidden"])').length,
                buttons: document.querySelectorAll('button, input[type="submit"]').length,
                links: document.querySelectorAll('a[href]').length,
                images: document.querySelectorAll('img').length,
                tables: document.querySelectorAll('table').length,
                lists: document.querySelectorAll('ul, ol').length,
                headers: document.querySelectorAll('h1, h2, h3').length,
                navigation: document.querySelectorAll('nav, [role="navigation"]').length,
            };
            
            // Detect page type based on statistics
            const pageFeatures = [];
            if (stats.forms > 0) pageFeatures.push('has_forms');
            if (stats.inputs > 3) pageFeatures.push('input_heavy');
            if (stats.tables > 0) pageFeatures.push('has_tables');
            if (stats.lists > 2) pageFeatures.push('list_based');
            if (stats.images > 10) pageFeatures.push('image_heavy');
            
            return {
                stats,
                features: pageFeatures,
                title: document.title,
                url: location.href,
            };
        }""")
        
        return AtomResult(
            success=True,
            data=analysis,
            confidence=0.95,
            method='statistical'
        )
    
    async def find_url_by_intent(self, intent: str) -> AtomResult:
        """
        Find URL on page by understanding intent.
        Uses LLM to match links - no hardcoded URL patterns.
        """
        if not self.page:
            return AtomResult(success=False)
        
        # Get all links
        links = await self.page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('a[href]').forEach((a, idx) => {
                if (a.offsetParent === null) return;
                
                results.push({
                    index: idx,
                    href: a.href,
                    text: a.textContent?.trim().substring(0, 100),
                    ariaLabel: a.getAttribute('aria-label'),
                    title: a.title,
                });
            });
            return results.slice(0, 100);  // Limit for LLM context
        }""")
        
        if not links:
            return AtomResult(success=False)
        
        if self.llm:
            prompt = f"""Given these links, which one best matches the intent: "{intent}"?

Links:
{self._format_links_for_llm(links)}

Respond with ONLY the index number of the best match, or -1 if none match."""

            try:
                response = await self.llm.agenerate([prompt])
                answer = response.generations[0][0].text.strip()
                
                match = re.search(r'-?\d+', answer)
                if match:
                    idx = int(match.group())
                    if 0 <= idx < len(links):
                        link = links[idx]
                        return AtomResult(
                            success=True,
                            data={'url': link['href'], 'link': link},
                            confidence=0.85,
                            method='llm'
                        )
            except Exception as e:
                logger.debug(f"LLM query failed: {e}")
        
        return AtomResult(success=False)
    
    async def detect_message_type(self) -> AtomResult:
        """
        Detect if page shows success/error/info message.
        Uses LLM to understand page state - no hardcoded message selectors.
        """
        if not self.page:
            return AtomResult(success=False)
        
        # Get visible text that might be messages
        page_text = await self.page.evaluate("""() => {
            // Focus on prominent text (headers, alerts, messages)
            const prominent = [];
            
            document.querySelectorAll('*').forEach(el => {
                if (el.offsetParent === null) return;
                
                const style = getComputedStyle(el);
                const fontSize = parseFloat(style.fontSize);
                const isProminent = fontSize > 14 || 
                                   style.fontWeight > 500 ||
                                   el.tagName.match(/^H[1-6]$/);
                
                if (isProminent && el.children.length === 0) {
                    const text = el.textContent?.trim();
                    if (text && text.length > 3 && text.length < 200) {
                        prominent.push({
                            text,
                            color: style.color,
                            bgColor: style.backgroundColor,
                        });
                    }
                }
            });
            
            return prominent.slice(0, 30);
        }""")
        
        if not page_text:
            return AtomResult(success=False)
        
        if self.llm:
            prompt = f"""Analyze these prominent text elements from a webpage. 
Is there a success message, error message, or neither?

Text elements:
{self._format_messages_for_llm(page_text)}

Respond in format:
TYPE: success|error|info|none
TEXT: [the actual message if found]
CONFIDENCE: 0.0-1.0"""

            try:
                response = await self.llm.agenerate([prompt])
                answer = response.generations[0][0].text.strip()
                
                # Parse response
                msg_type = 'none'
                msg_text = ''
                confidence = 0.5
                
                for line in answer.split('\n'):
                    if line.startswith('TYPE:'):
                        msg_type = line.split(':')[1].strip().lower()
                    elif line.startswith('TEXT:'):
                        msg_text = line.split(':', 1)[1].strip()
                    elif line.startswith('CONFIDENCE:'):
                        try:
                            confidence = float(line.split(':')[1].strip())
                        except:
                            pass
                
                if msg_type != 'none':
                    return AtomResult(
                        success=True,
                        data={'type': msg_type, 'text': msg_text},
                        confidence=confidence,
                        method='llm'
                    )
            except Exception as e:
                logger.debug(f"LLM query failed: {e}")
        
        return AtomResult(success=False)
    
    async def extract_data_pattern(self, description: str) -> AtomResult:
        """
        Extract data matching a description.
        LLM identifies what and where to extract - no hardcoded patterns.
        """
        if not self.page or not self.llm:
            return AtomResult(success=False)
        
        # Get page content
        content = await self.page.evaluate("""() => {
            return {
                title: document.title,
                text: document.body.innerText.substring(0, 5000),
                html: document.body.innerHTML.substring(0, 10000),
            };
        }""")
        
        prompt = f"""Extract data matching this description: "{description}"

Page content:
Title: {content['title']}
Text (truncated): {content['text'][:2000]}

Return extracted data as JSON. If no matching data found, return {{"found": false}}"""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip()
            
            # Try to parse JSON
            import json
            # Clean markdown code blocks
            if '```' in answer:
                answer = re.sub(r'```\w*\n?', '', answer)
            
            data = json.loads(answer)
            if data.get('found') is not False:
                return AtomResult(
                    success=True,
                    data=data,
                    confidence=0.8,
                    method='llm'
                )
        except Exception as e:
            logger.debug(f"LLM extraction failed: {e}")
        
        return AtomResult(success=False)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _format_inputs_for_llm(self, inputs: List[Dict]) -> str:
        lines = []
        for i, inp in enumerate(inputs[:20]):
            ctx = []
            if inp.get('labels'):
                ctx.append(f"labels: {inp['labels']}")
            if inp.get('placeholder'):
                ctx.append(f"placeholder: {inp['placeholder']}")
            if inp.get('name'):
                ctx.append(f"name: {inp['name']}")
            if inp.get('ariaLabel'):
                ctx.append(f"aria: {inp['ariaLabel']}")
            if inp.get('type'):
                ctx.append(f"type: {inp['type']}")
            
            lines.append(f"[{i}] {inp['tagName']} - {', '.join(ctx)}")
        return '\n'.join(lines)
    
    def _format_clickables_for_llm(self, clickables: List[Dict]) -> str:
        lines = []
        for i, el in enumerate(clickables[:30]):
            text = el.get('text', '')[:50]
            aria = el.get('ariaLabel', '')
            lines.append(f"[{i}] {el['tagName']}: \"{text}\" (aria: {aria})")
        return '\n'.join(lines)
    
    def _format_links_for_llm(self, links: List[Dict]) -> str:
        lines = []
        for i, link in enumerate(links[:50]):
            text = link.get('text', '')[:40]
            href = link.get('href', '')
            lines.append(f"[{i}] \"{text}\" -> {href}")
        return '\n'.join(lines)
    
    def _format_messages_for_llm(self, messages: List[Dict]) -> str:
        lines = []
        for msg in messages:
            lines.append(f"- \"{msg['text']}\" (color: {msg.get('color', 'unknown')})")
        return '\n'.join(lines)
    
    def _build_selector_from_input(self, inp: Dict) -> str:
        if inp.get('id'):
            return f"#{inp['id']}"
        if inp.get('name'):
            return f"{inp['tagName']}[name=\"{inp['name']}\"]"
        return f"{inp['tagName']}:nth-of-type({inp['index'] + 1})"
    
    def _build_clickable_selector(self, el: Dict) -> str:
        if el.get('id'):
            return f"#{el['id']}"
        text = el.get('text', '')[:30]
        if text:
            return f"{el['tagName']}:has-text(\"{text}\")"
        return f"{el['tagName']}:nth-of-type({el['index'] + 1})"
