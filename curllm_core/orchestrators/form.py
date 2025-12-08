"""
Form Orchestrator - Specialized orchestrator for form filling tasks

Handles:
- Form detection and analysis
- Field mapping (instruction values to form fields)
- Smart field filling with validation
- GDPR/consent handling
- Submit and verification
"""



import warnings
warnings.warn(
    "This module is deprecated. Use curllm_core.v2.LLMFormOrchestrator instead.",
    DeprecationWarning,
    stacklevel=2
)



import json
import re
from typing import Any, Dict, List, Optional


class FormOrchestrator:
    """
    Specialized orchestrator for form filling tasks.
    
    Workflow:
    1. Detect forms on page
    2. Analyze form structure (fields, types, labels)
    3. Map user data to form fields
    4. Fill fields with validation
    5. Handle consents/checkboxes
    6. Submit and verify
    """
    
    def __init__(self, llm=None, page=None, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
    
    async def orchestrate(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute form filling workflow.
        
        Args:
            instruction: User's instruction with form data
            page_context: Current page state
            
        Returns:
            Result with filled fields, submission status, and validation
        """
        self._log("📝 FORM ORCHESTRATOR", "header")
        
        result = {
            'filled': {},
            'errors': {},
            'submitted': False
        }
        
        try:
            # Phase 1: Parse user data from instruction
            user_data = self._parse_form_data(instruction)
            self._log(f"Parsed data: {list(user_data.keys())}")
            
            # Phase 2: Detect form fields
            form_analysis = await self._analyze_form()
            if not form_analysis:
                result['errors']['form'] = 'No form detected'
                return result
            
            self._log(f"Found {len(form_analysis.get('fields', []))} fields")
            
            # Phase 3: Map data to fields
            field_mapping = await self._map_fields(user_data, form_analysis)
            self._log(f"Mapped {len(field_mapping)} fields")
            
            # Phase 4: Fill fields
            for field_id, value in field_mapping.items():
                success = await self._fill_field(field_id, value, form_analysis)
                if success:
                    result['filled'][field_id] = value
                else:
                    result['errors'][field_id] = 'Fill failed'
            
            # Phase 5: Handle consents
            consent_result = await self._handle_consents(form_analysis)
            result['consents'] = consent_result
            
            # Phase 6: Submit form
            submit_result = await self._submit_form(form_analysis)
            result['submitted'] = submit_result.get('success', False)
            result['submit_details'] = submit_result
            
            # Phase 7: Verify submission
            if result['submitted']:
                verification = await self._verify_submission()
                result['verification'] = verification
            
        except Exception as e:
            result['errors']['exception'] = str(e)
            self._log(f"Form orchestration failed: {e}", "error")
        
        return result
    
    def _parse_form_data(self, instruction: str) -> Dict[str, str]:
        """Extract form field values from instruction"""
        data = {}
        
        # Pattern: field=value or field: value
        patterns = [
            r'(\w+)\s*=\s*["\']?([^,\'"]+)["\']?',
            r'(\w+)\s*:\s*["\']?([^,\'"]+)["\']?'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, instruction):
                field = match.group(1).lower().strip()
                value = match.group(2).strip()
                data[field] = value
        
        # Extract common fields by keyword
        keywords = {
            'name': ['name', 'imię', 'nazwisko', 'full name'],
            'email': ['email', 'e-mail', 'mail'],
            'phone': ['phone', 'telefon', 'tel', 'mobile'],
            'message': ['message', 'wiadomość', 'comment', 'komentarz'],
            'subject': ['subject', 'temat', 'tytuł']
        }
        
        instr_lower = instruction.lower()
        for field, kws in keywords.items():
            if field not in data:
                for kw in kws:
                    pattern = rf'{kw}\s*[=:]\s*["\']?([^,\'"]+)["\']?'
                    match = re.search(pattern, instr_lower)
                    if match:
                        data[field] = match.group(1).strip()
                        break
        
        return data
    
    async def _analyze_form(self) -> Optional[Dict[str, Any]]:
        """Detect and analyze form on page"""
        if not self.page:
            return None
        
        try:
            form_data = await self.page.evaluate('''() => {
                const forms = Array.from(document.querySelectorAll('form'));
                if (forms.length === 0) {
                    // Look for input fields without form wrapper
                    const inputs = document.querySelectorAll('input, textarea, select');
                    if (inputs.length === 0) return null;
                    
                    return {
                        id: 'virtual_form',
                        fields: Array.from(inputs).map(el => ({
                            id: el.id || el.name,
                            type: el.type || el.tagName.toLowerCase(),
                            name: el.name,
                            placeholder: el.placeholder,
                            required: el.required,
                            label: el.labels?.[0]?.textContent?.trim() || '',
                            selector: el.id ? `#${el.id}` : `[name="${el.name}"]`
                        })).filter(f => f.id || f.name)
                    };
                }
                
                const form = forms[0];
                return {
                    id: form.id || 'form_0',
                    action: form.action,
                    method: form.method,
                    fields: Array.from(form.querySelectorAll('input, textarea, select')).map(el => ({
                        id: el.id || el.name,
                        type: el.type || el.tagName.toLowerCase(),
                        name: el.name,
                        placeholder: el.placeholder,
                        required: el.required,
                        label: el.labels?.[0]?.textContent?.trim() || '',
                        selector: el.id ? `#${el.id}` : `[name="${el.name}"]`,
                        value: el.value || ''
                    })).filter(f => f.id || f.name),
                    submitButton: (() => {
                        const btn = form.querySelector('button[type="submit"], input[type="submit"], button:not([type])');
                        return btn ? (btn.id ? `#${btn.id}` : 'button[type="submit"]') : null;
                    })()
                };
            }''')
            
            return form_data
        except Exception as e:
            self._log(f"Form analysis failed: {e}", "error")
            return None
    
    async def _map_fields(
        self,
        user_data: Dict[str, str],
        form_analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """Map user data to form field selectors"""
        mapping = {}
        fields = form_analysis.get('fields', [])
        
        for data_key, value in user_data.items():
            best_match = None
            best_score = 0
            
            for field in fields:
                score = self._calculate_field_match(data_key, field)
                if score > best_score:
                    best_score = score
                    best_match = field
            
            if best_match and best_score >= 0.5:
                selector = best_match.get('selector')
                if selector:
                    mapping[selector] = value
        
        return mapping
    
    def _calculate_field_match(self, data_key: str, field: Dict[str, Any]) -> float:
        """Calculate match score between data key and form field"""
        score = 0.0
        data_key_lower = data_key.lower()
        
        # Exact ID/name match
        if field.get('id', '').lower() == data_key_lower:
            score += 1.0
        if field.get('name', '').lower() == data_key_lower:
            score += 0.9
        
        # Partial matches
        if data_key_lower in field.get('id', '').lower():
            score += 0.5
        if data_key_lower in field.get('name', '').lower():
            score += 0.5
        if data_key_lower in field.get('placeholder', '').lower():
            score += 0.4
        if data_key_lower in field.get('label', '').lower():
            score += 0.4
        
        # Type-based matching
        type_mappings = {
            'email': ['email'],
            'phone': ['tel', 'phone'],
            'message': ['textarea'],
            'name': ['text']
        }
        
        if data_key_lower in type_mappings:
            if field.get('type') in type_mappings[data_key_lower]:
                score += 0.3
        
        return min(1.0, score)
    
    async def _fill_field(
        self,
        selector: str,
        value: str,
        form_analysis: Dict[str, Any]
    ) -> bool:
        """Fill a single form field"""
        if not self.page:
            return False
        
        try:
            # Clear existing value
            await self.page.fill(selector, '')
            await self.page.wait_for_timeout(100)
            
            # Fill new value
            await self.page.fill(selector, value)
            await self.page.wait_for_timeout(100)
            
            # Trigger events
            await self.page.evaluate(f'''(selector) => {{
                const el = document.querySelector(selector);
                if (el) {{
                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    el.dispatchEvent(new Event('change', {{bubbles: true}}));
                    el.dispatchEvent(new Event('blur', {{bubbles: true}}));
                }}
            }}''', selector)
            
            return True
        except Exception as e:
            self._log(f"Failed to fill {selector}: {e}", "warning")
            # Try alternative method
            try:
                await self.page.type(selector, value, delay=50)
                return True
            except Exception:
                return False
    
    async def _handle_consents(self, form_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GDPR/consent checkboxes"""
        if not self.page:
            return {'checked': []}
        
        result = {'checked': [], 'failed': []}
        
        try:
            # Find consent checkboxes
            checkboxes = await self.page.evaluate('''() => {
                const checks = Array.from(document.querySelectorAll('input[type="checkbox"]'));
                return checks.map(el => ({
                    id: el.id || el.name,
                    selector: el.id ? `#${el.id}` : `input[name="${el.name}"]`,
                    required: el.required,
                    label: el.labels?.[0]?.textContent?.trim() || ''
                })).filter(c => 
                    c.label.toLowerCase().includes('consent') ||
                    c.label.toLowerCase().includes('gdpr') ||
                    c.label.toLowerCase().includes('zgod') ||
                    c.label.toLowerCase().includes('privacy') ||
                    c.label.toLowerCase().includes('terms') ||
                    c.label.toLowerCase().includes('regulamin') ||
                    c.required
                );
            }''')
            
            for cb in checkboxes:
                try:
                    await self.page.check(cb['selector'])
                    result['checked'].append(cb['id'])
                except Exception:
                    try:
                        await self.page.click(cb['selector'])
                        result['checked'].append(cb['id'])
                    except Exception:
                        result['failed'].append(cb['id'])
            
        except Exception as e:
            self._log(f"Consent handling failed: {e}", "warning")
        
        return result
    
    async def _submit_form(self, form_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Submit the form"""
        if not self.page:
            return {'success': False, 'error': 'No page'}
        
        result = {'success': False}
        
        try:
            # Try form's submit button
            submit_selector = form_analysis.get('submitButton')
            
            if submit_selector:
                await self.page.click(submit_selector)
                result['success'] = True
                result['method'] = 'button_click'
            else:
                # Try common submit selectors
                selectors = [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Submit")',
                    'button:has-text("Send")',
                    'button:has-text("Wyślij")',
                    '.submit-btn',
                    '#submit'
                ]
                
                for sel in selectors:
                    try:
                        await self.page.click(sel, timeout=2000)
                        result['success'] = True
                        result['method'] = 'selector_fallback'
                        result['selector'] = sel
                        break
                    except Exception:
                        continue
            
            if result['success']:
                # Wait for response
                await self.page.wait_for_timeout(2000)
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _verify_submission(self) -> Dict[str, Any]:
        """Verify form was submitted successfully"""
        if not self.page:
            return {'verified': False}
        
        try:
            # Check for success indicators
            success_indicators = await self.page.evaluate('''() => {
                const body = document.body.textContent.toLowerCase();
                const indicators = {
                    thank_you: body.includes('thank you') || body.includes('dziękujemy'),
                    success: body.includes('success') || body.includes('sukces'),
                    sent: body.includes('message sent') || body.includes('wiadomość wysłana'),
                    confirmation: body.includes('confirmation') || body.includes('potwierdzenie')
                };
                
                // Check for error indicators
                const errors = {
                    error: body.includes('error') && !body.includes('404'),
                    failed: body.includes('failed') || body.includes('niepowodzenie'),
                    invalid: body.includes('invalid') || body.includes('nieprawidłow')
                };
                
                return {
                    success_found: Object.values(indicators).some(v => v),
                    error_found: Object.values(errors).some(v => v),
                    indicators,
                    errors
                };
            }''')
            
            return {
                'verified': success_indicators['success_found'] and not success_indicators['error_found'],
                'details': success_indicators
            }
            
        except Exception as e:
            return {'verified': False, 'error': str(e)}
    
    def _log(self, message: str, level: str = "info"):
        """Log message"""
        if self.run_logger:
            if level == "header":
                self.run_logger.log_text(f"\n{'='*50}")
                self.run_logger.log_text(message)
                self.run_logger.log_text(f"{'='*50}\n")
            elif level == "error":
                self.run_logger.log_text(f"❌ {message}")
            elif level == "warning":
                self.run_logger.log_text(f"⚠️  {message}")
            else:
                self.run_logger.log_text(f"   {message}")

