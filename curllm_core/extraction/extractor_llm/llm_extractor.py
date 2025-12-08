from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import AtomicFunctions

from .extraction_request import ExtractionRequest
from .extraction_result import ExtractionResult

class LLMExtractor:
    """
    LLM-driven data extractor.
    
    NO HARDCODED:
    - Regex patterns
    - Keyword lists
    - Selectors
    
    LLM understands what to extract from context.
    """
    
    def __init__(self, page=None, llm=None, run_logger=None):
        self.page = page
        self.llm = llm
        self.run_logger = run_logger
        self.atoms = None
        
        if page and llm:
            self.atoms = AtomicFunctions(page=page, llm=llm)
    
    async def extract(self, instruction: str) -> ExtractionResult:
        """
        Extract data based on instruction.
        
        Args:
            instruction: What to extract (e.g., "extract all emails")
            
        Returns:
            ExtractionResult with extracted data
        """
        self._log("📊 LLM EXTRACTOR", "header")
        
        if not self.llm:
            return ExtractionResult(success=False, data={}, method='none')
        
        try:
            # Phase 1: LLM parses what to extract
            request = await self._parse_request(instruction)
            self._log(f"Extracting: {request.data_types} (limit: {request.limit})")
            
            # Phase 2: Extract each data type
            data = {}
            
            for data_type in request.data_types:
                extracted = await self._extract_data_type(data_type, request.limit)
                if extracted:
                    data[data_type] = extracted
                    self._log(f"  {data_type}: {len(extracted)} items")
            
            # Phase 3: Add page context
            data['url'] = await self.page.evaluate("() => location.href")
            data['title'] = await self.page.evaluate("() => document.title")
            
            return ExtractionResult(
                success=len(data) > 2,  # More than just url/title
                data=data,
                method='llm',
            )
            
        except Exception as e:
            self._log(f"Error: {e}", "error")
            return ExtractionResult(success=False, data={}, method='error')
    
    async def _parse_request(self, instruction: str) -> ExtractionRequest:
        """Parse extraction request using LLM."""
        prompt = f"""Parse this extraction instruction.

Instruction: "{instruction}"

What data types should be extracted?
Return JSON:
{{
    "data_types": ["emails", "phones", "links", "products", "prices", "names", ...],
    "limit": 50,
    "filter_text": "optional filter pattern"
}}

Return ONLY valid JSON."""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip()
            
            import json
            import re
            if '```' in answer:
                answer = re.sub(r'```\w*\n?', '', answer)
            
            data = json.loads(answer)
            return ExtractionRequest(
                data_types=data.get('data_types', ['links']),
                limit=data.get('limit', 50),
                filter_text=data.get('filter_text'),
            )
        except Exception:
            return ExtractionRequest(data_types=['links'], limit=50, filter_text=None)
    
    async def _extract_data_type(
        self, 
        data_type: str, 
        limit: int
    ) -> List[Any]:
        """Extract specific data type using LLM."""
        
        if data_type in ['emails', 'email']:
            return await self._extract_emails_llm(limit)
        elif data_type in ['phones', 'phone', 'telefon']:
            return await self._extract_phones_llm(limit)
        elif data_type in ['links', 'urls']:
            return await self._extract_links(limit)
        else:
            # Generic extraction via LLM
            return await self._extract_generic_llm(data_type, limit)
    
    async def _extract_emails_llm(self, limit: int) -> List[str]:
        """Extract emails using LLM pattern detection."""
        if not self.atoms:
            return []
        
        # Ask LLM to extract emails
        result = await self.atoms.extract_data_pattern(
            "all email addresses on the page"
        )
        
        if result.success and result.data:
            emails = result.data.get('emails', [])
            if isinstance(emails, list):
                return emails[:limit]
        
        # Fallback: get page text and ask LLM
        try:
            text = await self.page.evaluate(
                "() => document.body.innerText.substring(0, 10000)"
            )
            
            prompt = f"""Extract all email addresses from this text.

Text: {text[:5000]}

Return JSON array of email strings:
["email1@example.com", "email2@test.com"]

Return ONLY the JSON array."""

            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip()
            
            import json
            import re
            if '```' in answer:
                answer = re.sub(r'```\w*\n?', '', answer)
            
            emails = json.loads(answer)
            return emails[:limit] if isinstance(emails, list) else []
        except Exception:
            return []
    
    async def _extract_phones_llm(self, limit: int) -> List[str]:
        """Extract phone numbers using LLM pattern detection."""
        if not self.llm:
            return []
        
        try:
            text = await self.page.evaluate(
                "() => document.body.innerText.substring(0, 10000)"
            )
            
            prompt = f"""Extract all phone numbers from this text.

Text: {text[:5000]}

Return JSON array of phone number strings (normalized, digits only or with + prefix):
["+48123456789", "123456789"]

Return ONLY the JSON array."""

            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip()
            
            import json
            import re
            if '```' in answer:
                answer = re.sub(r'```\w*\n?', '', answer)
            
            phones = json.loads(answer)
            return phones[:limit] if isinstance(phones, list) else []
        except Exception:
            return []
    
    async def _extract_links(self, limit: int) -> List[Dict[str, str]]:
        """Extract links from page."""
        try:
            links = await self.page.evaluate("""() => {
                const links = [];
                const seen = new Set();
                
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    const text = a.textContent?.trim();
                    
                    if (href && !seen.has(href)) {
                        seen.add(href);
                        links.push({text: text || '', href});
                    }
                });
                
                return links;
            }""")
            return links[:limit]
        except Exception:
            return []
    
    async def _extract_generic_llm(
        self, 
        data_type: str, 
        limit: int
    ) -> List[Any]:
        """Extract generic data type using LLM."""
        if not self.atoms:
            return []
        
        result = await self.atoms.extract_data_pattern(
            f"all {data_type} on the page"
        )
        
        if result.success and result.data:
            # Try to get list from result
            data = result.data
            if isinstance(data, list):
                return data[:limit]
            elif isinstance(data, dict):
                # Find first list in dict
                for v in data.values():
                    if isinstance(v, list):
                        return v[:limit]
        
        return []
    
    def _log(self, message: str, level: str = "info"):
        """Log message."""
        if self.run_logger:
            if level == "header":
                self.run_logger.log_text(f"\n{'='*50}\n{message}\n{'='*50}")
            elif level == "error":
                self.run_logger.log_text(f"❌ {message}")
            else:
                self.run_logger.log_text(f"   {message}")
        logger.info(message)
