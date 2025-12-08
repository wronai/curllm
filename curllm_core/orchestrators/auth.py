"""
Authentication Orchestrator - Specialized orchestrator for login/authentication tasks

Architecture:
- LLM-first element finding for dynamic detection
- Selector hints used only as fallback suggestions
- LLM analyzes page structure to find login elements

Handles:
- Standard login flows (email/password)
- Multi-factor authentication (2FA, OTP)
- CAPTCHA detection and solving
- Session management and persistence
- Social login (OAuth)
- Password recovery flows
"""



import warnings
warnings.warn(
    "This module is deprecated. Use curllm_core.v2.LLMAuthOrchestrator instead.",
    DeprecationWarning,
    stacklevel=2
)



import json
import re
from typing import Any, Dict, List, Optional
from enum import Enum


class AuthMethod(Enum):
    """Authentication methods"""
    STANDARD = "standard"       # Email/password
    TWO_FACTOR = "2fa"          # 2FA with code
    OAUTH = "oauth"             # Social login
    SSO = "sso"                 # Single sign-on
    MAGIC_LINK = "magic_link"   # Email link


class AuthStep(Enum):
    """Authentication workflow steps"""
    NAVIGATE = "navigate"
    ENTER_CREDENTIALS = "enter_credentials"
    CAPTCHA = "captcha"
    TWO_FACTOR = "two_factor"
    SUBMIT = "submit"
    VERIFY = "verify"


class AuthOrchestrator:
    """
    Specialized orchestrator for authentication tasks.
    
    Features:
    - LLM-driven element finding (primary)
    - Multiple authentication method support
    - CAPTCHA detection and solving
    - 2FA handling with OTP/TOTP
    - Session persistence
    - Error recovery and retry logic
    
    Architecture:
    1. LLM analyzes login form and finds elements by PURPOSE
    2. Selector hints used only as statistical fallback
    3. No hardcoded selectors in production flow
    """
    
    # Element purpose descriptions for LLM
    ELEMENT_PURPOSES = {
        'email': 'email, username, or login input field',
        'password': 'password input field',
        'submit': 'login, sign in, or submit button',
        '2fa_code': 'verification code or OTP input',
        'remember': 'remember me or stay signed in checkbox',
        'forgot': 'forgot password or reset password link'
    }
    
    # Fallback selector hints (used when LLM unavailable)
    # These are scored by statistical matching, not used directly
    SELECTOR_HINTS = {
        'generic': {
            'email': [
                'input[type="email"]',
                'input[name="email"]',
                'input[name="username"]',
                'input[name="login"]',
                '#email', '#username', '#login',
                'input[placeholder*="email"]',
                'input[placeholder*="Email"]'
            ],
            'password': [
                'input[type="password"]',
                'input[name="password"]',
                '#password',
                'input[placeholder*="password"]'
            ],
            'submit': [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'button:has-text("Zaloguj")'
            ],
            '2fa_code': [
                'input[name="otp"]',
                'input[name="code"]',
                'input[name="totp"]',
                'input[autocomplete="one-time-code"]',
                '#otp', '#code'
            ]
        },
        'wordpress': {
            'email': ['#user_login'],
            'password': ['#user_pass'],
            'submit': ['#wp-submit'],
            'remember': ['#rememberme']
        },
        'google': {
            'email': ['input[type="email"]'],
            'password': ['input[type="password"]'],
            'next': ['#identifierNext', '#passwordNext']
        }
    }
    
    def __init__(self, llm=None, page=None, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
        self._session_data = {}
    
    async def _find_auth_element(
        self, 
        element_type: str,
        platform: str = 'generic'
    ) -> Optional[str]:
        """
        Find authentication element using LLM-driven analysis.
        
        Args:
            element_type: Type of element (email, password, submit, etc.)
            platform: Platform hint for context
        
        Returns:
            CSS selector or None
        """
        purpose = self.ELEMENT_PURPOSES.get(element_type, element_type)
        
        # Try LLM first
        if self.llm and self.page:
            try:
                from curllm_core.llm_dsl.selector_generator import LLMSelectorGenerator
                
                generator = LLMSelectorGenerator(llm=self.llm)
                result = await generator.generate_field_selector(
                    self.page,
                    purpose=f"{purpose} for login on {platform}"
                )
                if result.confidence > 0.5 and result.selector:
                    self._log(f"LLM found {element_type}: {result.selector}")
                    return result.selector
            except Exception as e:
                self._log(f"LLM element finding failed: {e}", "debug")
        
        # Fallback: try selector hints with statistical matching
        hints = self.SELECTOR_HINTS.get(platform, self.SELECTOR_HINTS.get('generic', {}))
        selectors = hints.get(element_type, [])
        
        if self.page:
            for selector in selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        is_visible = await el.is_visible()
                        if is_visible:
                            return selector
                except Exception:
                    continue
        
        return None
    
    async def orchestrate(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute authentication workflow.
        
        Args:
            instruction: User's login instruction with credentials
            page_context: Current page state
            
        Returns:
            Authentication result with status and session info
        """
        self._log("🔐 AUTHENTICATION ORCHESTRATOR", "header")
        
        result = {
            'success': False,
            'auth_method': None,
            'steps_completed': [],
            'session': None
        }
        
        try:
            # Phase 1: Parse credentials from instruction
            credentials = self._parse_credentials(instruction)
            self._log(f"Credentials parsed: {list(credentials.keys())}")
            
            if not credentials.get('email') and not credentials.get('username'):
                result['error'] = 'No username/email provided'
                return result
            
            # Phase 2: Detect authentication method
            auth_method = await self._detect_auth_method(page_context)
            result['auth_method'] = auth_method.value
            self._log(f"Auth method: {auth_method.value}")
            
            # Phase 3: Detect platform for selector optimization
            platform = self._detect_platform(page_context)
            self._log(f"Platform: {platform}")
            
            # Phase 4: Execute authentication flow
            if auth_method == AuthMethod.STANDARD:
                auth_result = await self._standard_login(credentials, platform)
            elif auth_method == AuthMethod.TWO_FACTOR:
                auth_result = await self._two_factor_login(credentials, platform)
            elif auth_method == AuthMethod.OAUTH:
                auth_result = await self._oauth_login(credentials, instruction)
            else:
                auth_result = await self._standard_login(credentials, platform)
            
            result.update(auth_result)
            
            # Phase 5: Verify login success
            if result.get('login_attempted'):
                verified = await self._verify_login()
                result['verified'] = verified
                result['success'] = verified
                
                if verified:
                    # Save session info
                    result['session'] = await self._capture_session()
                    self._log("✅ Login verified successfully")
                else:
                    self._log("❌ Login verification failed", "error")
            
        except Exception as e:
            result['error'] = str(e)
            self._log(f"Authentication failed: {e}", "error")
        
        return result
    
    def _parse_credentials(self, instruction: str) -> Dict[str, str]:
        """Extract credentials from instruction"""
        creds = {}
        
        # Email/username patterns
        patterns = {
            'email': [
                r'(?:email|e-mail|mail)[=:]\s*["\']?([^\s,\'"]+)',
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ],
            'username': [
                r'(?:user|username|login)[=:]\s*["\']?([^\s,\'"]+)'
            ],
            'password': [
                r'(?:pass|password|hasło)[=:]\s*["\']?([^\s,\'"]+)'
            ],
            'otp': [
                r'(?:otp|code|kod|2fa)[=:]\s*["\']?(\d{4,8})["\']?'
            ]
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, instruction, re.I)
                if match:
                    creds[field] = match.group(1)
                    break
        
        return creds
    
    async def _detect_auth_method(
        self,
        page_context: Optional[Dict[str, Any]]
    ) -> AuthMethod:
        """Detect which authentication method is needed"""
        if not self.page:
            return AuthMethod.STANDARD
        
        try:
            page_text = await self.page.inner_text('body')
            page_text_lower = page_text.lower()
            
            # Check for 2FA indicators
            if any(kw in page_text_lower for kw in [
                '2fa', 'two-factor', 'verification code', 'kod weryfikacyjny',
                'authenticator', 'otp', 'one-time'
            ]):
                return AuthMethod.TWO_FACTOR
            
            # Check for OAuth buttons
            oauth_buttons = await self.page.query_selector_all(
                'button:has-text("Google"), button:has-text("Facebook"), '
                'button:has-text("Apple"), a[href*="oauth"]'
            )
            if len(oauth_buttons) > 0:
                return AuthMethod.OAUTH
            
            # Check for SSO
            if 'sso' in page_text_lower or 'single sign' in page_text_lower:
                return AuthMethod.SSO
            
        except Exception:
            pass
        
        return AuthMethod.STANDARD
    
    def _detect_platform(
        self,
        page_context: Optional[Dict[str, Any]]
    ) -> str:
        """Detect platform for selector optimization"""
        if not page_context:
            return 'generic'
        
        url = page_context.get('url', '').lower()
        
        if 'wp-login' in url or 'wordpress' in url:
            return 'wordpress'
        elif 'accounts.google' in url:
            return 'google'
        elif 'facebook.com' in url:
            return 'facebook'
        elif 'linkedin.com' in url:
            return 'linkedin'
        
        return 'generic'
    
    async def _standard_login(
        self,
        credentials: Dict[str, str],
        platform: str
    ) -> Dict[str, Any]:
        """Execute standard email/password login"""
        if not self.page:
            return {'success': False, 'error': 'No page'}
        
        result = {
            'steps_completed': [],
            'login_attempted': False
        }
        
        selectors = self.PLATFORM_SELECTORS.get(platform, {})
        if not selectors:
            selectors = self.PLATFORM_SELECTORS['generic']
        
        try:
            # Step 1: Fill email/username
            email = credentials.get('email') or credentials.get('username')
            if email:
                filled = await self._fill_field(selectors.get('email', []), email)
                if filled:
                    result['steps_completed'].append(AuthStep.ENTER_CREDENTIALS.value)
                    self._log(f"Filled email/username")
            
            # Step 2: Check for CAPTCHA before password
            captcha_detected = await self._detect_captcha()
            if captcha_detected.get('detected'):
                self._log("CAPTCHA detected, attempting to solve...", "warning")
                solved = await self._solve_captcha(captcha_detected)
                result['captcha'] = {'detected': True, 'solved': solved}
                if solved:
                    result['steps_completed'].append(AuthStep.CAPTCHA.value)
            
            # Step 3: Fill password
            password = credentials.get('password')
            if password:
                filled = await self._fill_field(selectors.get('password', []), password)
                if filled:
                    self._log("Filled password")
            
            # Step 4: Check "Remember me" if available
            try:
                remember_selectors = selectors.get('remember', []) or ['#remember', '[name="remember"]']
                for sel in remember_selectors:
                    try:
                        await self.page.check(sel, timeout=1000)
                        self._log("Checked 'Remember me'")
                        break
                    except Exception:
                        continue
            except Exception:
                pass
            
            # Step 5: Submit login form
            submitted = await self._click_element(selectors.get('submit', []))
            if submitted:
                result['steps_completed'].append(AuthStep.SUBMIT.value)
                result['login_attempted'] = True
                self._log("Login form submitted")
                
                # Wait for navigation/response
                await self.page.wait_for_timeout(3000)
                
                # Check for 2FA prompt after submission
                needs_2fa = await self._check_2fa_prompt()
                if needs_2fa:
                    self._log("2FA required after login")
                    result['needs_2fa'] = True
                    
                    otp = credentials.get('otp')
                    if otp:
                        otp_result = await self._handle_2fa(otp)
                        result.update(otp_result)
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _two_factor_login(
        self,
        credentials: Dict[str, str],
        platform: str
    ) -> Dict[str, Any]:
        """Handle two-factor authentication flow"""
        # First do standard login
        result = await self._standard_login(credentials, platform)
        
        # Then handle 2FA if not already done
        if not result.get('2fa_completed') and credentials.get('otp'):
            otp_result = await self._handle_2fa(credentials['otp'])
            result.update(otp_result)
        
        return result
    
    async def _oauth_login(
        self,
        credentials: Dict[str, str],
        instruction: str
    ) -> Dict[str, Any]:
        """Handle OAuth/social login"""
        result = {
            'steps_completed': [],
            'login_attempted': False
        }
        
        instr_lower = instruction.lower()
        
        # Determine OAuth provider
        provider = None
        if 'google' in instr_lower:
            provider = 'google'
        elif 'facebook' in instr_lower:
            provider = 'facebook'
        elif 'apple' in instr_lower:
            provider = 'apple'
        elif 'github' in instr_lower:
            provider = 'github'
        
        if not provider:
            result['error'] = 'OAuth provider not specified'
            return result
        
        try:
            # Click OAuth button
            oauth_selectors = [
                f'button:has-text("{provider.capitalize()}")',
                f'a:has-text("{provider.capitalize()}")',
                f'[data-provider="{provider}"]',
                f'.{provider}-login'
            ]
            
            clicked = await self._click_element(oauth_selectors)
            if clicked:
                result['steps_completed'].append('oauth_click')
                result['login_attempted'] = True
                
                # Wait for OAuth flow
                await self.page.wait_for_timeout(5000)
                
                # OAuth usually opens popup or redirects
                # Would need to handle popup in real implementation
                result['note'] = f'{provider.capitalize()} OAuth flow initiated'
            else:
                result['error'] = f'Could not find {provider} login button'
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _handle_2fa(self, otp: str) -> Dict[str, Any]:
        """Handle 2FA code entry"""
        result = {'2fa_completed': False}
        
        if not self.page:
            return result
        
        try:
            selectors = self.PLATFORM_SELECTORS['generic']['2fa_code']
            filled = await self._fill_field(selectors, otp)
            
            if filled:
                self._log(f"Entered 2FA code")
                
                # Submit 2FA code
                submit_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Verify")',
                    'button:has-text("Submit")',
                    'button:has-text("Potwierdź")'
                ]
                
                await self._click_element(submit_selectors)
                await self.page.wait_for_timeout(2000)
                
                result['2fa_completed'] = True
                result['steps_completed'] = [AuthStep.TWO_FACTOR.value]
            
        except Exception as e:
            result['2fa_error'] = str(e)
        
        return result
    
    async def _check_2fa_prompt(self) -> bool:
        """Check if page is showing 2FA prompt"""
        if not self.page:
            return False
        
        try:
            page_text = await self.page.inner_text('body')
            page_text_lower = page_text.lower()
            
            return any(kw in page_text_lower for kw in [
                'verification code', 'kod weryfikacyjny',
                'two-factor', 'authenticator',
                'enter code', 'wpisz kod'
            ])
        except Exception:
            return False
    
    async def _detect_captcha(self) -> Dict[str, Any]:
        """Detect CAPTCHA on page"""
        if not self.page:
            return {'detected': False}
        
        try:
            # Common CAPTCHA indicators
            captcha_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[src*="hcaptcha"]',
                '.g-recaptcha',
                '.h-captcha',
                '[data-sitekey]',
                '#captcha'
            ]
            
            for selector in captcha_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        return {
                            'detected': True,
                            'type': 'recaptcha' if 'recaptcha' in selector else 'other',
                            'selector': selector
                        }
                except Exception:
                    continue
            
            # Check for slider CAPTCHA
            slider = await self.page.query_selector('.slider-captcha, .slide-verify')
            if slider:
                return {
                    'detected': True,
                    'type': 'slider',
                    'selector': '.slider-captcha'
                }
            
        except Exception:
            pass
        
        return {'detected': False}
    
    async def _solve_captcha(self, captcha_info: Dict[str, Any]) -> bool:
        """Attempt to solve CAPTCHA"""
        captcha_type = captcha_info.get('type')
        
        if captcha_type == 'slider':
            # Use slider solver
            try:
                from ..captcha_slider import attempt_slider_challenge
                return await attempt_slider_challenge(self.page)
            except ImportError:
                pass
        
        # For other types, would integrate with CAPTCHA solving service
        # For now, return False (manual intervention needed)
        self._log("CAPTCHA requires manual solving or API integration", "warning")
        return False
    
    async def _verify_login(self) -> bool:
        """Verify that login was successful"""
        if not self.page:
            return False
        
        try:
            url = self.page.url.lower()
            
            # Check for login failure indicators
            failure_indicators = ['login', 'signin', 'error', 'failed', 'incorrect']
            if any(ind in url for ind in failure_indicators):
                # Still on login page - might have failed
                page_text = await self.page.inner_text('body')
                page_text_lower = page_text.lower()
                
                error_messages = [
                    'invalid', 'incorrect', 'wrong', 'error',
                    'nieprawidłowe', 'błędne', 'nie udało'
                ]
                
                if any(err in page_text_lower for err in error_messages):
                    return False
            
            # Check for success indicators
            success_indicators = [
                'dashboard', 'home', 'profile', 'account',
                'panel', 'konto', 'pulpit'
            ]
            
            if any(ind in url for ind in success_indicators):
                return True
            
            # Check for logged-in elements
            logged_in_selectors = [
                '[aria-label*="profile"]',
                '[aria-label*="account"]',
                '.user-menu',
                '.logged-in',
                '#logout',
                'a:has-text("Logout")',
                'a:has-text("Wyloguj")'
            ]
            
            for selector in logged_in_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        return True
                except Exception:
                    continue
            
            # If not on login page anymore, assume success
            if 'login' not in url and 'signin' not in url:
                return True
            
        except Exception:
            pass
        
        return False
    
    async def _capture_session(self) -> Dict[str, Any]:
        """Capture session information"""
        session = {}
        
        if not self.page:
            return session
        
        try:
            # Get cookies
            cookies = await self.page.context.cookies()
            session['cookies'] = [
                {'name': c['name'], 'domain': c['domain']}
                for c in cookies[:10]  # Limit for safety
            ]
            
            # Get current URL
            session['url'] = self.page.url
            
            # Get storage state
            try:
                storage = await self.page.context.storage_state()
                session['has_storage'] = bool(storage)
            except Exception:
                pass
            
        except Exception:
            pass
        
        return session
    
    async def _fill_field(self, selectors: List[str], value: str) -> bool:
        """Fill field with fallback selectors"""
        if not self.page:
            return False
        
        for selector in selectors:
            try:
                await self.page.fill(selector, value, timeout=3000)
                return True
            except Exception:
                continue
        
        return False
    
    async def _click_element(self, selectors: List[str]) -> bool:
        """Click element with fallback selectors"""
        if not self.page:
            return False
        
        for selector in selectors:
            try:
                await self.page.click(selector, timeout=3000)
                return True
            except Exception:
                continue
        
        return False
    
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
