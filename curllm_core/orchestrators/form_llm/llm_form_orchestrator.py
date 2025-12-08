from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import AtomicFunctions

from .form_result import FormResult

class LLMFormOrchestrator:
    """
    LLM-driven form orchestrator.
    
    NO HARDCODED:
    - Field keywords
    - Type mappings
    - Label patterns
    """
    
    def __init__(self, llm=None, page=None, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
        self.atoms = None
        
        if page and llm:
            self.atoms = AtomicFunctions(page=page, llm=llm)
    
    async def orchestrate(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> FormResult:
        """Execute form filling using LLM."""
        self._log("📝 LLM FORM ORCHESTRATOR", "header")
        
        if not self.atoms:
            return FormResult(
                success=False, filled={}, submitted=False,
                errors=["No LLM/page available"]
            )
        
        filled = {}
        errors = []
        
        try:
            # Phase 1: LLM parses form data
            form_data = await self._parse_form_data_llm(instruction)
            self._log(f"Parsed data: {list(form_data.keys())}")
            
            # Phase 2: For each value, LLM finds matching field
            for purpose, value in form_data.items():
                field_result = await self.atoms.find_input_by_context(
                    f"form field for {purpose}"
                )
                
                if field_result.success and field_result.data:
                    selector = field_result.data.get('selector')
                    try:
                        await self.page.fill(selector, value)
                        await self._trigger_events(selector)
                        filled[purpose] = value
                        self._log(f"Filled {purpose}: {selector}")
                    except Exception as e:
                        errors.append(f"Failed to fill {purpose}: {e}")
                else:
                    errors.append(f"No field found for: {purpose}")
            
            # Phase 3: Handle consents
            await self._handle_consents_llm()
            
            # Phase 4: Submit form
            submitted = await self._submit_form_llm()
            
            # Phase 5: Verify
            verification = None
            if submitted:
                await self.page.wait_for_timeout(2000)
                msg_result = await self.atoms.detect_message_type()
                if msg_result.success:
                    verification = msg_result.data.get('text')
                    msg_type = msg_result.data.get('type')
                    self._log(f"Verification: {msg_type} - {verification}")
            
            return FormResult(
                success=len(filled) > 0 and len(errors) == 0,
                filled=filled,
                submitted=submitted,
                verification=verification,
                errors=errors if errors else None,
            )
            
        except Exception as e:
            self._log(f"Error: {e}", "error")
            return FormResult(
                success=False, filled=filled, submitted=False,
                errors=[str(e)]
            )
    
    async def _parse_form_data_llm(self, instruction: str) -> Dict[str, str]:
        """Parse form data using LLM."""
        if not self.llm:
            return {}
        
        prompt = f"""Extract form field values from this instruction.

Instruction: "{instruction}"

Return JSON with field purposes as keys and values to fill:
{{"email": "email@example.com", "name": "John Doe", ...}}

Return ONLY valid JSON."""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip()
            
            import json
            import re
            if '```' in answer:
                answer = re.sub(r'```\w*\n?', '', answer)
            
            return json.loads(answer)
        except Exception:
            return {}
    
    async def _handle_consents_llm(self) -> bool:
        """Handle consent checkboxes using LLM."""
        if not self.atoms:
            return False
        
        # Find consent/terms checkbox
        consent_result = await self.atoms.find_input_by_context(
            "consent checkbox / terms agreement / privacy policy acceptance / GDPR checkbox"
        )
        
        if consent_result.success and consent_result.data:
            selector = consent_result.data.get('selector')
            try:
                # Check if already checked
                is_checked = await self.page.evaluate(
                    f"() => document.querySelector('{selector}')?.checked"
                )
                if not is_checked:
                    await self.page.click(selector)
                    self._log(f"Checked consent: {selector}")
                return True
            except Exception:
                pass
        
        return False
    
    async def _submit_form_llm(self) -> bool:
        """Submit form using LLM."""
        if not self.atoms:
            return False
        
        submit_result = await self.atoms.find_clickable_by_intent(
            "submit form button / send message / confirm"
        )
        
        if submit_result.success and submit_result.data:
            selector = submit_result.data.get('selector')
            try:
                await self.page.click(selector)
                self._log(f"Clicked submit: {selector}")
                return True
            except Exception:
                pass
        
        return False
    
    async def _trigger_events(self, selector: str):
        """Trigger form events after filling."""
        await self.page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            if (el) {
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }""", selector)
    
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
