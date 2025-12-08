from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from curllm_core.llm_dsl import AtomicFunctions

from .auth_credentials import AuthCredentials
from .auth_result import AuthResult

class LLMAuthOrchestrator:
    """
    LLM-driven authentication orchestrator.
    
    NO HARDCODED:
    - Platform selectors
    - Field patterns
    - Button texts
    
    Everything detected by LLM from context.
    """
    
    def __init__(self, llm=None, page=None, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
        self.atoms = None
        
        if page and llm:
            self.atoms = AtomicFunctions(page=page, llm=llm)
    
    async def authenticate(
        self,
        instruction: str,
        credentials: Optional[Dict[str, str]] = None
    ) -> AuthResult:
        """
        Perform authentication using LLM-driven detection.
        
        Args:
            instruction: Auth instruction with credentials
            credentials: Optional explicit credentials dict
            
        Returns:
            AuthResult with status
        """
        self._log("🔐 LLM AUTH ORCHESTRATOR", "header")
        
        if not self.atoms:
            return AuthResult(
                success=False, method='unknown',
                error="No LLM/page available"
            )
        
        try:
            # Phase 1: Parse credentials from instruction
            creds = await self._parse_credentials_llm(instruction, credentials)
            self._log(f"Email: {creds.email[:3] if creds.email else 'N/A'}***")
            
            # Phase 2: Analyze page for auth type
            auth_analysis = await self._analyze_auth_page()
            self._log(f"Auth type: {auth_analysis.get('type', 'unknown')}")
            
            # Phase 3: Fill credentials
            if creds.email:
                await self._fill_email_llm(creds.email)
            
            if creds.password:
                await self._fill_password_llm(creds.password)
            
            # Phase 4: Submit
            submitted = await self._submit_login_llm()
            
            if not submitted:
                return AuthResult(
                    success=False, method='standard',
                    error="Could not submit login form"
                )
            
            # Phase 5: Check result
            await self.page.wait_for_timeout(2000)
            
            # Check for 2FA
            needs_2fa = await self._check_2fa_required()
            if needs_2fa:
                if creds.otp_code:
                    await self._fill_2fa_code(creds.otp_code)
                    await self._submit_login_llm()
                else:
                    return AuthResult(
                        success=False, method='2fa',
                        needs_2fa=True,
                        message="2FA code required"
                    )
            
            # Check for CAPTCHA
            needs_captcha = await self._check_captcha_required()
            if needs_captcha:
                return AuthResult(
                    success=False, method='standard',
                    needs_captcha=True,
                    message="CAPTCHA required"
                )
            
            # Check for errors
            error_msg = await self._check_auth_error()
            if error_msg:
                return AuthResult(
                    success=False, method='standard',
                    error=error_msg
                )
            
            return AuthResult(
                success=True, method='standard',
                message="Authentication successful"
            )
            
        except Exception as e:
            self._log(f"Error: {e}", "error")
            return AuthResult(
                success=False, method='unknown',
                error=str(e)
            )
    
    async def _parse_credentials_llm(
        self,
        instruction: str,
        explicit_creds: Optional[Dict[str, str]]
    ) -> AuthCredentials:
        """Parse credentials using LLM."""
        
        creds = AuthCredentials()
        
        # Use explicit if provided
        if explicit_creds:
            creds.email = explicit_creds.get('email') or explicit_creds.get('username')
            creds.password = explicit_creds.get('password')
            creds.otp_code = explicit_creds.get('otp') or explicit_creds.get('code')
            return creds
        
        # Parse from instruction using LLM
        if not self.llm:
            return creds
        
        prompt = f"""Extract login credentials from this instruction.

Instruction: "{instruction}"

Return JSON:
{{
    "email": "email or username if found",
    "password": "password if found",
    "otp_code": "2FA code if found",
    "remember": true/false
}}

Return ONLY valid JSON, null for missing values."""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip()
            
            import json
            import re
            if '```' in answer:
                answer = re.sub(r'```\w*\n?', '', answer)
            
            data = json.loads(answer)
            creds.email = data.get('email')
            creds.password = data.get('password')
            creds.otp_code = data.get('otp_code')
            creds.remember = data.get('remember', False)
        except Exception:
            pass
        
        return creds
    
    async def _analyze_auth_page(self) -> Dict[str, Any]:
        """Analyze page to understand auth type."""
        if not self.atoms:
            return {}
        
        result = await self.atoms.analyze_page_structure()
        
        analysis = {
            'type': 'unknown',
            'has_form': False,
            'has_social_login': False,
        }
        
        if result.success and result.data:
            stats = result.data.get('stats', {})
            analysis['has_form'] = stats.get('forms', 0) > 0
            analysis['type'] = 'standard' if analysis['has_form'] else 'unknown'
        
        return analysis
    
    async def _fill_email_llm(self, email: str) -> bool:
        """Fill email field using LLM detection."""
        if not self.atoms:
            return False
        
        result = await self.atoms.find_input_by_context(
            "login form field for email address or username"
        )
        
        if result.success and result.data:
            selector = result.data.get('selector')
            try:
                await self.page.fill(selector, email)
                self._log(f"Filled email: {selector}")
                return True
            except Exception as e:
                self._log(f"Failed to fill email: {e}", "error")
        
        return False
    
    async def _fill_password_llm(self, password: str) -> bool:
        """Fill password field using LLM detection."""
        if not self.atoms:
            return False
        
        result = await self.atoms.find_input_by_context(
            "login form field for password"
        )
        
        if result.success and result.data:
            selector = result.data.get('selector')
            try:
                await self.page.fill(selector, password)
                self._log(f"Filled password: {selector}")
                return True
            except Exception as e:
                self._log(f"Failed to fill password: {e}", "error")
        
        return False
    
    async def _submit_login_llm(self) -> bool:
        """Submit login form using LLM detection."""
        if not self.atoms:
            return False
        
        result = await self.atoms.find_clickable_by_intent(
            "submit login form / sign in button / log in button"
        )
        
        if result.success and result.data:
            selector = result.data.get('selector')
            try:
                await self.page.click(selector)
                self._log(f"Clicked submit: {selector}")
                return True
            except Exception as e:
                self._log(f"Failed to submit: {e}", "error")
        
        return False
    
    async def _check_2fa_required(self) -> bool:
        """Check if 2FA is required using LLM."""
        if not self.atoms:
            return False
        
        result = await self.atoms.find_input_by_context(
            "2FA verification code input / OTP input / one-time password field"
        )
        
        return result.success
    
    async def _fill_2fa_code(self, code: str) -> bool:
        """Fill 2FA code using LLM detection."""
        if not self.atoms:
            return False
        
        result = await self.atoms.find_input_by_context(
            "2FA verification code input / OTP input"
        )
        
        if result.success and result.data:
            selector = result.data.get('selector')
            try:
                await self.page.fill(selector, code)
                self._log(f"Filled 2FA code: {selector}")
                return True
            except Exception:
                pass
        
        return False
    
    async def _check_captcha_required(self) -> bool:
        """Check if CAPTCHA is required using LLM."""
        if not self.llm:
            return False
        
        # Get page content
        try:
            page_text = await self.page.evaluate(
                "() => document.body.innerText.substring(0, 2000)"
            )
        except Exception:
            return False
        
        prompt = f"""Does this page show a CAPTCHA challenge or robot verification?

Page text: {page_text[:1000]}

Answer ONLY: yes or no"""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip().lower()
            return 'yes' in answer
        except Exception:
            return False
    
    async def _check_auth_error(self) -> Optional[str]:
        """Check for authentication errors using LLM."""
        if not self.atoms:
            return None
        
        result = await self.atoms.detect_message_type()
        
        if result.success and result.data:
            if result.data.get('type') == 'error':
                return result.data.get('text', 'Authentication failed')
        
        return None
    
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
