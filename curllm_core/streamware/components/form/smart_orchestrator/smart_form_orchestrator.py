import json
import re
from typing import Dict, List, Any, Optional
from pathlib import Path


class SmartFormOrchestrator:
    """
    Intelligent form filling orchestrator with LLM verification.
    
    Workflow:
    1. Detect form fields and types
    2. Map user data to fields (LLM-assisted)
    3. Fill each field with verification
    4. Handle missing required fields (LLM generation)
    5. Detect and handle CAPTCHA
    6. Submit with success evaluation
    7. Retry on failures
    """
    
    def __init__(self, page, llm, instruction: str, run_logger=None):
        self.page = page
        self.llm = llm
        self.instruction = instruction
        self.run_logger = run_logger
        self.state = {
            "fields_detected": [],
            "fields_filled": {},
            "fields_verified": {},
            "errors": [],
            "warnings": [],
            "retries": 0,
            "captcha_detected": False,
            "submitted": False,
            "success": False
        }
    
    def _log(self, msg: str):
        """Log message."""
        if self.run_logger:
            self.run_logger.log_text(msg)
    
    def _log_json(self, label: str, data: Any):
        """Log JSON data."""
        if self.run_logger:
            self.run_logger.log_text(f"**{label}:**")
            self.run_logger.log_code("json", json.dumps(data, indent=2, ensure_ascii=False))
    
    async def orchestrate(self, user_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute smart form filling.
        
        Args:
            user_data: User data to fill (email, name, message, etc.)
            
        Returns:
            Result dict with success, filled fields, errors
        """
        self._log("\n🤖 ═══ SMART FORM ORCHESTRATOR ═══\n")
        
        try:
            # Step 1: Detect and analyze form fields
            fields = await self._detect_fields()
            if not fields:
                return self._result(False, "No form fields detected")
            
            # Step 2: Smart field mapping with LLM
            mapping = await self._smart_map_fields(fields, user_data)
            if not mapping:
                return self._result(False, "Field mapping failed")
            
            # Step 3: Fill fields with verification
            fill_result = await self._fill_with_verification(mapping)
            
            # Step 4: Handle missing required fields
            if fill_result.get("missing"):
                await self._handle_missing_fields(fill_result["missing"], user_data)
            
            # Step 5: Detect CAPTCHA
            captcha = await self._detect_captcha()
            if captcha.get("found"):
                await self._handle_captcha(captcha)
            
            # Step 6: Submit with evaluation
            submit_result = await self._submit_with_evaluation()
            
            # Step 7: Retry if needed
            if not submit_result.get("success") and self.state["retries"] < 2:
                self._log("\n⚠️ Submit failed, analyzing and retrying...")
                retry_result = await self._retry_with_llm_guidance(submit_result)
                if retry_result.get("success"):
                    return self._result(True, "Success after retry")
            
            return self._result(
                submit_result.get("success", False),
                submit_result.get("reason", "Unknown")
            )
            
        except Exception as e:
            self._log(f"❌ Orchestrator error: {e}")
            return self._result(False, str(e))
    
    async def _detect_fields(self) -> List[Dict]:
        """Detect form fields with type analysis."""
        self._log("\n## Step 1: Field Detection\n")
        
        fields = await self.page.evaluate("""
            () => {
                const fields = [];
                const form = document.querySelector('form');
                if (!form) return fields;
                
                const inputs = form.querySelectorAll('input, textarea, select');
                for (const input of inputs) {
                    const type = input.type || input.tagName.toLowerCase();
                    const name = input.name || input.id || '';
                    
                    // Skip hidden and file inputs for text mapping
                    const isTextFillable = !['hidden', 'file', 'submit', 'button', 'image'].includes(type);
                    
                    fields.push({
                        tag: input.tagName.toLowerCase(),
                        type: type,
                        name: name,
                        id: input.id,
                        placeholder: input.placeholder || '',
                        required: input.required || input.hasAttribute('aria-required'),
                        visible: input.offsetParent !== null && input.offsetWidth > 0,
                        isTextFillable: isTextFillable,
                        selector: input.id ? `#${input.id}` : 
                                  input.name ? `[name="${input.name}"]` : null
                    });
                }
                return fields;
            }
        """)
        
        self._log_json("Fields detected", fields)
        self.state["fields_detected"] = fields
        
        # Filter to only text-fillable fields
        fillable = [f for f in fields if f.get("isTextFillable") and f.get("visible")]
        self._log(f"✅ Found {len(fillable)} fillable fields (excluding file/hidden)")
        
        return fillable
    
    async def _smart_map_fields(
        self,
        fields: List[Dict],
        user_data: Dict[str, str]
    ) -> List[Dict]:
        """
        Smart field mapping using LLM with validation.
        """
        self._log("\n## Step 2: Smart Field Mapping\n")
        
        # Prepare data with name splitting
        data = dict(user_data)
        if "name" in data and " " in data["name"]:
            parts = data["name"].split(" ", 1)
            data["first_name"] = parts[0]
            data["last_name"] = parts[1] if len(parts) > 1 else ""
        
        # Build field descriptions
        field_desc = []
        for i, f in enumerate(fields):
            desc = f"[{i}] {f['type']}: name='{f['name']}'"
            if f.get('placeholder'):
                desc += f" placeholder='{f['placeholder']}'"
            if f.get('tag') == 'textarea':
                desc += " (TEXTAREA - for long text/message)"
            field_desc.append(desc)
        
        # Ask LLM for mapping
        prompt = f"""Map user data to form fields. CRITICAL RULES:

1. email → field with type="email"
2. message/content → field with tag="textarea" (NOT file input!)
3. phone → field with type="tel" or name contains "phone"
4. first_name → field name contains "first"
5. last_name → field name contains "last"
6. NEVER map text data to file/upload fields!

FIELDS:
{chr(10).join(field_desc)}

USER DATA KEYS: {list(data.keys())}
USER DATA: {json.dumps(data, ensure_ascii=False)}

Output JSON array:
[{{"field_index": 0, "data_key": "email"}}, ...]

ONLY return fields that have matching data. JSON:"""

        try:
            response = await self._llm_generate(prompt)
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                mappings = json.loads(match.group())
                
                result = []
                for m in mappings:
                    idx = m.get("field_index", -1)
                    data_key = m.get("data_key")
                    
                    if 0 <= idx < len(fields) and data_key in data:
                        field = fields[idx]
                        
                        # SAFETY: Never map text to file input!
                        if field.get("type") == "file":
                            self._log(f"⚠️ Skipping file field for text data: {data_key}")
                            continue
                        
                        result.append({
                            "selector": field["selector"],
                            "value": data[data_key],
                            "type": field["type"],
                            "name": field["name"],
                            "data_key": data_key
                        })
                
                self._log_json("Mapping result", result)
                return result
                
        except Exception as e:
            self._log(f"❌ LLM mapping failed: {e}")
        
        # Fallback: simple rule-based mapping
        return self._fallback_mapping(fields, data)
    
    def _fallback_mapping(
        self,
        fields: List[Dict],
        data: Dict[str, str]
    ) -> List[Dict]:
        """
        Dynamic rule-based fallback mapping.
        
        Uses semantic matching instead of hardcoded patterns.
        Matches field attributes against data keys using similarity scoring.
        """
        result = []
        used_data_keys = set()
        
        # Build semantic mapping rules dynamically from data keys
        for f in fields:
            # Skip non-fillable fields
            if f.get("type", "").lower() in ["file", "hidden", "submit", "button"]:
                continue
            
            if not f.get("selector"):
                continue
            
            # Get field identifiers
            field_name = f.get("name", "").lower()
            field_type = f.get("type", "").lower()
            field_tag = f.get("tag", "").lower()
            field_placeholder = f.get("placeholder", "").lower()
            field_id = f.get("id", "").lower()
            
            # Combine all field identifiers for matching
            field_text = f"{field_name} {field_type} {field_placeholder} {field_id}"
            
            best_match = None
            best_score = 0
            
            for data_key, data_value in data.items():
                if data_key in used_data_keys:
                    continue
                
                score = self._compute_field_match_score(
                    data_key=data_key,
                    field_name=field_name,
                    field_type=field_type,
                    field_tag=field_tag,
                    field_text=field_text
                )
                
                if score > best_score:
                    best_score = score
                    best_match = (data_key, data_value)
            
            # Accept match if score is high enough
            if best_match and best_score >= 0.5:
                data_key, value = best_match
                used_data_keys.add(data_key)
                result.append({
                    "selector": f["selector"],
                    "value": value,
                    "type": field_type,
                    "name": f["name"],
                    "data_key": data_key,
                    "match_score": best_score
                })
        
        return result
    
    def _compute_field_match_score(
        self,
        data_key: str,
        field_name: str,
        field_type: str,
        field_tag: str,
        field_text: str
    ) -> float:
        """
        Compute semantic match score between data key and field.
        
        Returns score 0.0-1.0 based on:
        - Type match (email type -> email key)
        - Name containment (field contains key or vice versa)
        - Semantic similarity (message -> textarea, phone -> tel)
        """
        score = 0.0
        key_lower = data_key.lower()
        
        # Exact type match (highest priority)
        if field_type == key_lower:
            score = 1.0
        elif field_type == "email" and key_lower == "email":
            score = 1.0
        elif field_type == "tel" and key_lower in ["phone", "tel", "telephone", "mobile"]:
            score = 1.0
        
        # Tag-based semantic match
        elif field_tag == "textarea" and key_lower in ["message", "content", "description", "comment", "body", "text"]:
            score = 0.95
        
        # Name containment (bidirectional)
        elif key_lower in field_name or field_name in key_lower:
            score = 0.8
        elif key_lower in field_text:
            score = 0.7
        
        # Semantic synonyms
        elif self._are_semantically_related(key_lower, field_name):
            score = 0.75
        
        return score
    
    def _are_semantically_related(self, key: str, field: str) -> bool:
        """
        Check if key and field are semantically related.
        
        Uses semantic concept groups for matching.
        These are language-agnostic concepts, NOT hardcoded selectors.
        
        In LLM-driven mode, the LLM would determine semantic similarity
        directly. These groups serve as statistical fallback.
        """
        # Semantic concept groups (language-agnostic)
        # LLM would determine these dynamically in production
        semantic_groups = [
            {"email", "mail", "e-mail", "correo", "poczta"},
            {"phone", "tel", "telephone", "mobile", "cell", "telefon", "komórka"},
            {"message", "msg", "content", "body", "text", "wiadomość", "treść", "komentarz"},
            {"name", "nombre", "imię", "nazwisko", "fullname"},
            {"first", "firstname", "fname", "imię"},
            {"last", "lastname", "lname", "surname", "nazwisko"},
            {"address", "addr", "street", "ulica", "adres"},
            {"city", "miasto", "town"},
            {"zip", "postal", "postcode", "kod"},
            {"country", "kraj", "nation", "państwo"},
            {"company", "firma", "organization", "org", "przedsiębiorstwo"},
            {"subject", "temat", "title", "tytuł", "topic"},
        ]
        
        for group in semantic_groups:
            key_matches = any(k in key for k in group)
            field_matches = any(k in field for k in group)
            if key_matches and field_matches:
                return True
        
        return False
    
    async def _fill_with_verification(
        self,
        mapping: List[Dict]
    ) -> Dict[str, Any]:
        """Fill fields with per-field verification."""
        self._log("\n## Step 3: Fill with Verification\n")
        
        filled = []
        failed = []
        
        for field in mapping:
            selector = field["selector"]
            value = field["value"]
            data_key = field.get("data_key", "unknown")
            
            try:
                # Fill the field
                await self.page.fill(selector, value)
                await self.page.wait_for_timeout(200)
                
                # Verify the fill
                actual = await self.page.evaluate(f"""
                    () => {{
                        const el = document.querySelector('{selector}');
                        return el ? el.value : null;
                    }}
                """)
                
                if actual == value:
                    self._log(f"✅ {data_key}: filled and verified")
                    filled.append(data_key)
                    self.state["fields_filled"][data_key] = True
                    self.state["fields_verified"][data_key] = True
                else:
                    self._log(f"⚠️ {data_key}: filled but verification mismatch")
                    self._log(f"   Expected: {value[:30]}... Got: {str(actual)[:30]}...")
                    filled.append(data_key)
                    self.state["fields_filled"][data_key] = True
                    self.state["fields_verified"][data_key] = False
                    
            except Exception as e:
                self._log(f"❌ {data_key}: fill failed - {e}")
                failed.append({"field": data_key, "error": str(e)})
                self.state["errors"].append(f"Fill {data_key}: {e}")
        
        return {
            "filled": filled,
            "failed": failed,
            "missing": self._find_missing_required()
        }
    
    def _find_missing_required(self) -> List[Dict]:
        """Find required fields that weren't filled."""
        missing = []
        for f in self.state["fields_detected"]:
            if f.get("required") and f.get("isTextFillable"):
                name = f.get("name", "")
                if name not in self.state["fields_filled"]:
                    missing.append(f)
        return missing
    
    async def _handle_missing_fields(
        self,
        missing: List[Dict],
        user_data: Dict
    ):
        """Generate values for missing required fields using LLM."""
        self._log("\n## Step 4: Handle Missing Fields\n")
        
        if not missing:
            return
        
        self._log(f"⚠️ {len(missing)} required fields not filled")
        
        # Ask LLM to generate values
        fields_desc = [f"{f['name']} ({f['type']})" for f in missing]
        
        prompt = f"""Generate realistic values for these required form fields:

Missing fields: {fields_desc}
Context (existing data): {json.dumps(user_data, ensure_ascii=False)}
Form purpose: {self.instruction}

Generate appropriate values based on the context.
Output JSON: {{"field_name": "value", ...}}

JSON:"""

        try:
            response = await self._llm_generate(prompt)
            match = re.search(r'\{[^}]+\}', response)
            if match:
                generated = json.loads(match.group())
                
                for field in missing:
                    name = field.get("name", "")
                    if name in generated and field.get("selector"):
                        value = generated[name]
                        await self.page.fill(field["selector"], value)
                        self._log(f"✅ Generated and filled: {name} = {value[:30]}...")
                        
        except Exception as e:
            self._log(f"❌ Failed to generate missing fields: {e}")
    
    async def _detect_captcha(self) -> Dict[str, Any]:
        """Detect CAPTCHA on the page."""
        self._log("\n## Step 5: CAPTCHA Detection\n")
        
        # Import captcha detection
        try:
            from ..captcha.detect import detect_captcha
            result = await detect_captcha(self.page)
            
            if result.get("found"):
                self._log(f"⚠️ CAPTCHA detected: {result.get('type')}")
                self.state["captcha_detected"] = True
            else:
                self._log("✅ No CAPTCHA detected")
            
            return result
        except Exception as e:
            self._log(f"⚠️ CAPTCHA detection failed: {e}")
            return {"found": False}
    
    async def _handle_captcha(self, captcha: Dict[str, Any]):
        """Handle CAPTCHA using visual solver."""
        self._log("\n### Handling CAPTCHA\n")
        
        try:
            from ..captcha.vision_solve import VisualCaptchaSolver
            
            solver = VisualCaptchaSolver(
                page=self.page,
                llm=self.llm,
                run_logger=self.run_logger
            )
            
            result = await solver.solve(captcha)
            
            if result.get("solved"):
                self._log("✅ CAPTCHA solved!")
            else:
                self._log(f"⚠️ CAPTCHA not solved: {result.get('reason')}")
                self.state["warnings"].append("CAPTCHA may not be solved")
                
        except Exception as e:
            self._log(f"❌ CAPTCHA handling failed: {e}")
            self.state["errors"].append(f"CAPTCHA: {e}")
    
    async def _submit_with_evaluation(self) -> Dict[str, Any]:
        """Submit form and evaluate success with LLM."""
        self._log("\n## Step 6: Submit with Evaluation\n")
        
        # Capture pre-submit state
        pre_url = self.page.url
        pre_screenshot = await self._take_screenshot("pre_submit")
        
        # Find and click submit
        submit_clicked = False
        for selector in [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Wyślij")',
            'button:has-text("Send")',
            '.submit-button',
            'form button'
        ]:
            try:
                btn = await self.page.query_selector(selector)
                if btn:
                    await btn.click()
                    submit_clicked = True
                    self._log(f"✅ Clicked submit: {selector}")
                    break
            except Exception:
                continue
        
        if not submit_clicked:
            return {"success": False, "reason": "Submit button not found"}
        
        # Wait for response
        await self.page.wait_for_timeout(3000)
        
        # Capture post-submit state
        post_url = self.page.url
        post_screenshot = await self._take_screenshot("post_submit")
        
        # Get page text for success indicators
        page_text = await self.page.evaluate("() => document.body.innerText")
        
        # Evaluate success with LLM
        success_result = await self._evaluate_success_with_llm(
            pre_url=pre_url,
            post_url=post_url,
            page_text=page_text[:2000],
            pre_screenshot=pre_screenshot,
            post_screenshot=post_screenshot
        )
        
        self.state["submitted"] = True
        self.state["success"] = success_result.get("success", False)
        
        return success_result
    
    async def _evaluate_success_with_llm(
        self,
        pre_url: str,
        post_url: str,
        page_text: str,
        pre_screenshot: str,
        post_screenshot: str
    ) -> Dict[str, Any]:
        """Use LLM to evaluate if form submission was successful."""
        self._log("\n### Evaluating Success with LLM\n")
        
        # Check obvious indicators
        url_changed = pre_url != post_url
        
        # Success patterns
        success_patterns = [
            r'thank\s*you', r'dziękuj', r'sukces', r'success',
            r'sent\s*successfully', r'wysłan', r'otrzymali',
            r'message\s*sent', r'wiadomość.*wysłana'
        ]
        has_success_text = any(
            re.search(p, page_text, re.I) for p in success_patterns
        )
        
        # Error patterns
        error_patterns = [
            r'error', r'błąd', r'failed', r'nie udało',
            r'required', r'wymagane', r'invalid', r'nieprawidłow'
        ]
        has_error_text = any(
            re.search(p, page_text, re.I) for p in error_patterns
        )
        
        # Quick decision if obvious
        if has_success_text and not has_error_text:
            self._log("✅ Success indicators found in page text")
            return {"success": True, "reason": "Success message detected", "confidence": 0.9}
        
        if has_error_text and not has_success_text:
            self._log("❌ Error indicators found in page text")
            return {"success": False, "reason": "Error message detected", "confidence": 0.8}
        
        # Ask LLM for uncertain cases
        prompt = f"""Analyze if this form submission was successful.

URL changed: {url_changed}
Pre-URL: {pre_url}
Post-URL: {post_url}

Page text (excerpt):
{page_text[:1000]}

Signs to look for:
- Success: "thank you", "sent", "received", "dziękujemy", "wysłano"
- Failure: "error", "required", "invalid", "błąd", "wymagane"
- Form still visible = likely not submitted

Output JSON:
{{"success": true/false, "confidence": 0.0-1.0, "reason": "brief explanation"}}

JSON:"""

        try:
            response = await self._llm_generate(prompt)
            match = re.search(r'\{[^}]+\}', response)
            if match:
                result = json.loads(match.group())
                self._log_json("LLM evaluation", result)
                return result
        except Exception as e:
            self._log(f"⚠️ LLM evaluation failed: {e}")
        
        # Fallback
        return {
            "success": url_changed or has_success_text,
            "confidence": 0.5,
            "reason": "Heuristic evaluation"
        }
    
    async def _retry_with_llm_guidance(
        self,
        failed_result: Dict
    ) -> Dict[str, Any]:
        """Retry with LLM guidance based on failure analysis."""
        self._log("\n## Step 7: Retry with LLM Guidance\n")
        
        self.state["retries"] += 1
        
        # Take screenshot for analysis
        screenshot = await self._take_screenshot("retry_analysis")
        
        # Ask LLM what went wrong
        prompt = f"""The form submission failed. Analyze why and suggest fix.

Previous result: {json.dumps(failed_result, ensure_ascii=False)}
Fields filled: {list(self.state['fields_filled'].keys())}
Errors: {self.state['errors']}

Look at the current page state and identify:
1. What fields might be missing or incorrectly filled
2. Any error messages visible
3. What action to take

Output JSON:
{{"issue": "description", "fix_action": "retry_field/add_field/solve_captcha/none", "field_name": "...", "suggested_value": "..."}}

JSON:"""

        try:
            response = await self._llm_generate(prompt)
            match = re.search(r'\{[^}]+\}', response)
            if match:
                guidance = json.loads(match.group())
                self._log_json("LLM guidance", guidance)
                
                action = guidance.get("fix_action")
                
                if action == "retry_field":
                    field = guidance.get("field_name")
                    value = guidance.get("suggested_value")
                    if field and value:
                        # Try to fill the field
                        selector = self._find_field_selector(field)
                        if selector:
                            await self.page.fill(selector, value)
                            return await self._submit_with_evaluation()
                
                elif action == "solve_captcha":
                    captcha = await self._detect_captcha()
                    if captcha.get("found"):
                        await self._handle_captcha(captcha)
                        return await self._submit_with_evaluation()
                        
        except Exception as e:
            self._log(f"❌ Retry guidance failed: {e}")
        
        return {"success": False, "reason": "Retry failed"}
    
    def _find_field_selector(self, field_name: str) -> Optional[str]:
        """Find selector for field by name."""
        for f in self.state["fields_detected"]:
            if f.get("name") == field_name or field_name in f.get("name", ""):
                return f.get("selector")
        return None
    
    async def _take_screenshot(self, label: str) -> str:
        """Take and save screenshot."""
        try:
            from ...config import config
            path = config.screenshot_dir / f"smart_form_{label}_{int(self.page.url.__hash__() % 10000)}.png"
            await self.page.screenshot(path=str(path))
            return str(path)
        except Exception:
            return ""
    
    async def _llm_generate(self, prompt: str) -> str:
        """Generate text from LLM."""
        if hasattr(self.llm, 'ainvoke'):
            result = await self.llm.ainvoke(prompt)
            return result.get('text', str(result))
        elif hasattr(self.llm, 'generate'):
            return await self.llm.generate(prompt)
        else:
            return str(await self.llm(prompt))
    
    def _result(self, success: bool, reason: str) -> Dict[str, Any]:
        """Build result dict."""
        return {
            "success": success,
            "reason": reason,
            "filled": self.state["fields_filled"],
            "verified": self.state["fields_verified"],
            "submitted": self.state["submitted"],
            "errors": self.state["errors"],
            "warnings": self.state["warnings"],
            "retries": self.state["retries"],
            "captcha_detected": self.state["captcha_detected"]
        }
