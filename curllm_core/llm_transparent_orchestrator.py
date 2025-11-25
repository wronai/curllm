#!/usr/bin/env python3
"""
Transparent LLM Orchestrator - Multi-step form filling with full LLM control.

LLM widzi KAŻDY krok:
1. Detection → LLM planuje mapowanie
2. Mapping → LLM weryfikuje
3. Filling → LLM kontroluje każde pole
4. Validation → LLM decyduje czy submit
5. Submit → LLM widzi rezultat

Każda decyzja algorytmu jest transparentna dla LLM.
"""

import json
from typing import Dict, List, Any, Optional


class TransparentOrchestrator:
    """
    Orkiestrator z pełną transparentnością dla LLM.
    LLM widzi każdą decyzję i może ją modyfikować.
    """
    
    def __init__(self, llm, run_logger=None):
        self.llm = llm
        self.run_logger = run_logger
        self.conversation_history = []
        self.decisions_log = []
    
    def log(self, message: str, level: str = "info"):
        """Log message with level."""
        if self.run_logger:
            prefix = {
                "info": "   ℹ️ ",
                "llm": "   🧠 ",
                "action": "   ⚡ ",
                "result": "   📊 ",
                "decision": "   🎯 "
            }.get(level, "   ")
            self.run_logger.log_text(f"{prefix}{message}")
    
    def add_decision(self, phase: str, decision: Dict[str, Any]):
        """Track decision for transparency."""
        self.decisions_log.append({
            "phase": phase,
            "decision": decision,
            "timestamp": self._get_timestamp()
        })
    
    def _get_timestamp(self):
        """Get current timestamp."""
        import time
        return time.time()
    
    async def orchestrate_form_fill(
        self,
        instruction: str,
        page,
        user_data: Dict[str, str],
        detected_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Main orchestration flow with full LLM transparency.
        
        Returns:
            Dict with execution results and LLM decisions
        """
        self.log("🎭 TRANSPARENT LLM ORCHESTRATION - Starting", "info")
        self.log(f"User instruction: {instruction}", "info")
        
        result = {
            "phases": [],
            "decisions": [],
            "filled_fields": {},
            "submitted": False,
            "success": False
        }
        
        # ============================================================
        # PHASE 1: FIELD DETECTION & MAPPING
        # ============================================================
        self.log("━━━ PHASE 1: Field Detection & Mapping ━━━", "info")
        
        phase1_result = await self._phase1_field_mapping(
            instruction, user_data, detected_fields
        )
        result["phases"].append(phase1_result)
        
        if not phase1_result.get("success"):
            self.log("❌ Phase 1 failed - cannot proceed", "info")
            return result
        
        field_mapping = phase1_result.get("mapping", {})
        
        # ============================================================
        # PHASE 2: MAPPING VERIFICATION
        # ============================================================
        self.log("━━━ PHASE 2: Mapping Verification ━━━", "info")
        
        phase2_result = await self._phase2_verify_mapping(
            page, field_mapping, detected_fields
        )
        result["phases"].append(phase2_result)
        
        if phase2_result.get("needs_adjustment"):
            # LLM suggested adjustments
            field_mapping = phase2_result.get("adjusted_mapping", field_mapping)
        
        # ============================================================
        # PHASE 3: FILLING PLAN
        # ============================================================
        self.log("━━━ PHASE 3: Create Filling Plan ━━━", "info")
        
        phase3_result = await self._phase3_create_plan(
            field_mapping, user_data
        )
        result["phases"].append(phase3_result)
        
        filling_plan = phase3_result.get("plan", [])
        
        # ============================================================
        # PHASE 4: EXECUTION WITH FEEDBACK
        # ============================================================
        self.log("━━━ PHASE 4: Execute with Feedback ━━━", "info")
        
        phase4_result = await self._phase4_execute_with_feedback(
            page, filling_plan, field_mapping
        )
        result["phases"].append(phase4_result)
        result["filled_fields"] = phase4_result.get("filled", {})
        
        # ============================================================
        # PHASE 5: FINAL VALIDATION & SUBMIT DECISION
        # ============================================================
        self.log("━━━ PHASE 5: Validation & Submit Decision ━━━", "info")
        
        phase5_result = await self._phase5_validate_and_decide(
            page, field_mapping, result["filled_fields"]
        )
        result["phases"].append(phase5_result)
        
        if phase5_result.get("ready_to_submit"):
            # LLM decided to submit
            submit_result = await self._execute_submit(page, field_mapping)
            result["submitted"] = submit_result.get("success", False)
            result["success"] = result["submitted"]
        
        result["decisions"] = self.decisions_log
        
        self.log("✅ ORCHESTRATION COMPLETE", "info")
        return result
    
    async def _phase1_field_mapping(
        self,
        instruction: str,
        user_data: Dict[str, str],
        detected_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Phase 1: LLM creates field mapping plan.
        
        LLM sees:
        - User instruction
        - Detected fields (raw data from browser)
        - User data to fill
        
        LLM decides:
        - Which field should contain which value
        - Mapping strategy (split name, etc.)
        """
        self.log("Asking LLM to plan field mapping...", "llm")
        
        prompt = self._create_mapping_prompt(instruction, user_data, detected_fields)
        
        llm_response = await self.llm.generate(prompt, max_tokens=1000, temperature=0.1)
        
        self.log(f"LLM response ({len(llm_response)} chars)", "result")
        
        # Parse LLM mapping decision
        mapping = self._parse_mapping_response(llm_response)
        
        if mapping:
            self.log(f"✅ Mapping plan created: {len(mapping)} fields", "decision")
            for field_id, config in mapping.items():
                self.log(f"   {field_id} ← {config.get('value')} (reason: {config.get('reasoning', 'N/A')})", "decision")
            
            self.add_decision("field_mapping", {
                "mapping": mapping,
                "llm_response": llm_response[:500]
            })
            
            return {
                "phase": "field_mapping",
                "success": True,
                "mapping": mapping
            }
        else:
            self.log("❌ Failed to parse LLM mapping", "result")
            return {
                "phase": "field_mapping",
                "success": False,
                "error": "Could not parse LLM mapping"
            }
    
    def _create_mapping_prompt(
        self,
        instruction: str,
        user_data: Dict[str, str],
        detected_fields: List[Dict[str, Any]]
    ) -> str:
        """Create prompt for field mapping phase."""
        return f"""You are a form field mapping expert. Your task is to map user data to form fields.

USER INSTRUCTION:
{instruction}

USER DATA TO FILL:
{json.dumps(user_data, indent=2)}

DETECTED FORM FIELDS:
{json.dumps(detected_fields, indent=2)}

YOUR TASK:
Create a mapping plan that specifies which value should go into which field.

MAPPING RULES:
1. Match fields by: hints, label, type, name, id (in that order)
2. For split name fields (first_name + last_name): split the full name
3. For email: ALWAYS use type="email" field
4. For message/textarea: use textarea or field with message hints
5. If unsure, use field hints as primary guide

RESPONSE FORMAT (JSON only):
```json
{{
  "mapping": {{
    "field_id_1": {{
      "value": "value to fill",
      "reasoning": "why this field for this value",
      "confidence": 0.9
    }},
    "field_id_2": {{
      "value": "another value",
      "reasoning": "explanation",
      "confidence": 0.95
    }}
  }}
}}
```

CRITICAL:
- Use ACTUAL field IDs from detected_fields
- Provide reasoning for EVERY mapping
- If split name needed, create TWO mappings (first + last)
- Return ONLY JSON, no other text

Generate the mapping NOW:"""
    
    def _parse_mapping_response(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM mapping response."""
        try:
            import re
            # Try to find JSON in response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return data.get("mapping", {})
            
            # Try direct JSON
            data = json.loads(llm_response)
            return data.get("mapping", {})
        except Exception as e:
            self.log(f"Parse error: {str(e)}", "result")
            return None
    
    async def _phase2_verify_mapping(
        self,
        page,
        mapping: Dict[str, Any],
        detected_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Phase 2: Verify mapping by checking actual DOM.
        
        LLM sees:
        - Proposed mapping
        - Actual field states in DOM
        
        LLM decides:
        - Is mapping correct?
        - Any adjustments needed?
        """
        self.log("Verifying mapping against DOM...", "action")
        
        # Check if fields exist and are fillable
        verification_results = await self._verify_fields_in_dom(page, mapping)
        
        self.log("Asking LLM to verify mapping...", "llm")
        
        prompt = self._create_verification_prompt(mapping, verification_results, detected_fields)
        
        llm_response = await self.llm.generate(prompt, max_tokens=800, temperature=0.1)
        
        # Parse verification decision
        verification = self._parse_verification_response(llm_response)
        
        if verification.get("approved"):
            self.log("✅ LLM approved mapping", "decision")
            return {
                "phase": "mapping_verification",
                "success": True,
                "needs_adjustment": False,
                "verification": verification_results
            }
        else:
            self.log(f"⚠️  LLM suggested adjustments: {verification.get('reason')}", "decision")
            adjusted_mapping = verification.get("adjusted_mapping", mapping)
            return {
                "phase": "mapping_verification",
                "success": True,
                "needs_adjustment": True,
                "adjusted_mapping": adjusted_mapping,
                "reason": verification.get("reason")
            }
    
    async def _verify_fields_in_dom(
        self,
        page,
        mapping: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if fields exist in DOM and are fillable."""
        results = {}
        
        for field_id, config in mapping.items():
            try:
                # Try to locate field
                selector = f"#{field_id}"
                element = await page.query_selector(selector)
                
                if element:
                    # Check if visible and enabled
                    is_visible = await element.is_visible()
                    is_enabled = await element.is_enabled()
                    
                    results[field_id] = {
                        "exists": True,
                        "visible": is_visible,
                        "enabled": is_enabled,
                        "fillable": is_visible and is_enabled
                    }
                else:
                    results[field_id] = {
                        "exists": False,
                        "fillable": False
                    }
            except Exception as e:
                results[field_id] = {
                    "exists": False,
                    "error": str(e)
                }
        
        return results
    
    def _create_verification_prompt(
        self,
        mapping: Dict[str, Any],
        verification_results: Dict[str, Any],
        detected_fields: List[Dict[str, Any]]
    ) -> str:
        """Create prompt for mapping verification."""
        return f"""Verify the field mapping against actual DOM state.

PROPOSED MAPPING:
{json.dumps(mapping, indent=2)}

DOM VERIFICATION RESULTS:
{json.dumps(verification_results, indent=2)}

DETECTED FIELDS (reference):
{json.dumps(detected_fields, indent=2)}

YOUR TASK:
Check if the mapping is correct. If any field doesn't exist or isn't fillable, suggest adjustments.

RESPONSE FORMAT (JSON only):
```json
{{
  "approved": true/false,
  "reason": "explanation if not approved",
  "adjusted_mapping": {{
    // Only if adjustments needed
  }}
}}
```

Respond NOW:"""
    
    def _parse_verification_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse verification response."""
        try:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return json.loads(llm_response)
        except:
            return {"approved": True}  # Default to approved if can't parse
    
    async def _phase3_create_plan(
        self,
        mapping: Dict[str, Any],
        user_data: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Phase 3: LLM creates step-by-step filling plan.
        
        LLM sees:
        - Verified mapping
        - User data
        
        LLM decides:
        - Order of filling
        - Dependencies (e.g., fill name before email if validation depends on it)
        """
        self.log("Asking LLM to create filling plan...", "llm")
        
        prompt = f"""Create a step-by-step plan to fill the form fields.

VERIFIED MAPPING:
{json.dumps(mapping, indent=2)}

USER DATA:
{json.dumps(user_data, indent=2)}

YOUR TASK:
Create an ordered list of filling operations. Consider dependencies and logical order.

RESPONSE FORMAT (JSON only):
```json
{{
  "plan": [
    {{"step": 1, "field_id": "...", "value": "...", "reasoning": "why this order"}},
    {{"step": 2, "field_id": "...", "value": "...", "reasoning": "..."}}
  ]
}}
```

Generate plan NOW:"""
        
        llm_response = await self.llm.generate(prompt, max_tokens=800, temperature=0.1)
        
        plan = self._parse_plan_response(llm_response)
        
        if plan:
            self.log(f"✅ Filling plan created: {len(plan)} steps", "decision")
            for step in plan:
                self.log(f"   Step {step.get('step')}: {step.get('field_id')} ← {step.get('value')}", "decision")
            
            return {
                "phase": "create_plan",
                "success": True,
                "plan": plan
            }
        else:
            # Fallback: create simple plan from mapping
            plan = [
                {"step": i+1, "field_id": fid, "value": cfg.get("value")}
                for i, (fid, cfg) in enumerate(mapping.items())
            ]
            return {
                "phase": "create_plan",
                "success": True,
                "plan": plan,
                "fallback": True
            }
    
    def _parse_plan_response(self, llm_response: str) -> Optional[List[Dict[str, Any]]]:
        """Parse plan response."""
        try:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return data.get("plan", [])
            data = json.loads(llm_response)
            return data.get("plan", [])
        except:
            return None
    
    async def _phase4_execute_with_feedback(
        self,
        page,
        plan: List[Dict[str, Any]],
        mapping: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 4: Execute plan step-by-step with LLM feedback.
        
        After each step:
        - Execute fill
        - Check result
        - Show to LLM
        - LLM decides: continue / adjust / retry
        """
        self.log("Executing plan with LLM feedback...", "action")
        
        filled = {}
        errors = []
        
        for step in plan:
            field_id = step.get("field_id")
            value = step.get("value")
            step_num = step.get("step", 0)
            
            self.log(f"Step {step_num}: Filling {field_id} with '{value}'", "action")
            
            # Execute fill
            success = await self._fill_field(page, field_id, value)
            
            if success:
                filled[field_id] = value
                self.log(f"   ✅ Success", "result")
            else:
                errors.append({"field_id": field_id, "error": "Fill failed"})
                self.log(f"   ❌ Failed", "result")
                
                # Ask LLM for decision
                decision = await self._ask_llm_on_error(field_id, value, step_num, len(plan))
                
                if decision.get("action") == "retry":
                    self.log(f"   🔄 LLM decided: Retry", "decision")
                    success = await self._fill_field(page, field_id, value)
                    if success:
                        filled[field_id] = value
                        errors.pop()  # Remove error
                elif decision.get("action") == "skip":
                    self.log(f"   ⏭️  LLM decided: Skip", "decision")
                elif decision.get("action") == "adjust":
                    self.log(f"   🔧 LLM decided: Adjust value", "decision")
                    new_value = decision.get("new_value", value)
                    success = await self._fill_field(page, field_id, new_value)
                    if success:
                        filled[field_id] = new_value
        
        return {
            "phase": "execute_with_feedback",
            "success": len(errors) == 0,
            "filled": filled,
            "errors": errors
        }
    
    async def _fill_field(self, page, field_id: str, value: str) -> bool:
        """Fill a single field."""
        try:
            selector = f"#{field_id}"
            await page.fill(selector, value, timeout=3000)
            # Trigger events
            await page.evaluate(f"""
                document.querySelector('{selector}')?.dispatchEvent(new Event('input', {{bubbles:true}}));
                document.querySelector('{selector}')?.dispatchEvent(new Event('change', {{bubbles:true}}));
            """)
            return True
        except Exception as e:
            return False
    
    async def _ask_llm_on_error(
        self,
        field_id: str,
        value: str,
        step_num: int,
        total_steps: int
    ) -> Dict[str, Any]:
        """Ask LLM what to do on fill error."""
        prompt = f"""Fill operation failed for field.

FIELD: {field_id}
VALUE: {value}
STEP: {step_num}/{total_steps}

OPTIONS:
1. retry - Try again
2. skip - Skip this field
3. adjust - Change value

RESPONSE (JSON only):
```json
{{"action": "retry/skip/adjust", "new_value": "if adjust", "reasoning": "why"}}
```

Decide NOW:"""
        
        try:
            llm_response = await self.llm.generate(prompt, max_tokens=200, temperature=0.1)
            return self._parse_decision_response(llm_response)
        except:
            return {"action": "skip"}  # Default to skip on error
    
    def _parse_decision_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse decision response."""
        try:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return json.loads(llm_response)
        except:
            return {"action": "skip"}
    
    async def _phase5_validate_and_decide(
        self,
        page,
        mapping: Dict[str, Any],
        filled_fields: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Phase 5: LLM validates and decides if ready to submit.
        
        LLM sees:
        - What was filled
        - What was supposed to be filled
        - Current form state
        
        LLM decides:
        - Ready to submit? Yes/No
        - If no: what's missing/wrong
        """
        self.log("Asking LLM for final validation...", "llm")
        
        # Get current form state
        form_state = await self._get_form_state(page, mapping)
        
        prompt = f"""Validate the form and decide if ready to submit.

EXPECTED (mapping):
{json.dumps(mapping, indent=2)}

ACTUALLY FILLED:
{json.dumps(filled_fields, indent=2)}

CURRENT FORM STATE:
{json.dumps(form_state, indent=2)}

YOUR TASK:
Validate if all required fields are filled correctly. Decide if ready to submit.

RESPONSE (JSON only):
```json
{{
  "ready_to_submit": true/false,
  "reasoning": "why ready or not",
  "missing_fields": ["if any"],
  "incorrect_fields": ["if any"]
}}
```

Decide NOW:"""
        
        llm_response = await self.llm.generate(prompt, max_tokens=500, temperature=0.1)
        
        decision = self._parse_validation_response(llm_response)
        
        if decision.get("ready_to_submit"):
            self.log("✅ LLM approved: Ready to submit", "decision")
        else:
            self.log(f"⚠️  LLM blocked submit: {decision.get('reasoning')}", "decision")
        
        return {
            "phase": "validate_and_decide",
            "success": True,
            "ready_to_submit": decision.get("ready_to_submit", False),
            "reasoning": decision.get("reasoning"),
            "missing_fields": decision.get("missing_fields", []),
            "incorrect_fields": decision.get("incorrect_fields", [])
        }
    
    async def _get_form_state(self, page, mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Get current state of form fields."""
        state = {}
        
        for field_id in mapping.keys():
            try:
                selector = f"#{field_id}"
                value = await page.input_value(selector)
                state[field_id] = value
            except:
                state[field_id] = None
        
        return state
    
    def _parse_validation_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse validation response."""
        try:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return json.loads(llm_response)
        except:
            return {"ready_to_submit": True}  # Default to submit if can't parse
    
    async def _execute_submit(self, page, mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Execute form submission."""
        self.log("Submitting form...", "action")
        
        try:
            # Find submit button (assuming it's in mapping or look for it)
            submit_selector = None
            for field_id, config in mapping.items():
                if 'submit' in field_id.lower():
                    submit_selector = f"#{field_id}"
                    break
            
            if not submit_selector:
                # Try common submit button selectors
                submit_selector = "button[type='submit'], input[type='submit']"
            
            await page.click(submit_selector, timeout=3000)
            await page.wait_for_timeout(2000)  # Wait for submission
            
            self.log("✅ Form submitted", "result")
            return {"success": True}
        except Exception as e:
            self.log(f"❌ Submit failed: {str(e)}", "result")
            return {"success": False, "error": str(e)}
