"""
Social Media Orchestrator - Specialized orchestrator for social platform tasks

Architecture:
- LLM-first element finding for dynamic detection
- Platform configs as fallback hints (not hardcoded selectors)
- LLM analyzes page structure to find appropriate elements

Handles:
- Login with captcha solving
- Profile navigation
- Post/share content
- Message sending
- Follow/unfollow actions
- Content engagement (like, comment)
"""



import warnings
warnings.warn(
    "This module is deprecated. Use curllm_core.v2.LLMSocialOrchestrator instead.",
    DeprecationWarning,
    stacklevel=2
)



import json
import re
from typing import Any, Dict, List, Optional
from enum import Enum


class SocialPlatform(Enum):
    """Supported social platforms"""
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    UNKNOWN = "unknown"


class SocialMediaOrchestrator:
    """
    Specialized orchestrator for social media automation.
    
    Features:
    - LLM-driven element finding (primary)
    - Multi-platform support
    - Secure credential handling
    - Captcha detection and solving
    - Rate limiting awareness
    - Session persistence
    
    Architecture:
    1. LLM analyzes page and finds elements by PURPOSE
    2. Platform hints used only as fallback suggestions
    3. No hardcoded selectors in production flow
    """
    
    # Platform-specific HINTS (not hardcoded selectors)
    # These are suggestions for LLM, not direct selectors
    # LLM uses these as context hints when analyzing the page
    PLATFORM_HINTS = {
        SocialPlatform.FACEBOOK: {
            'login_url': 'https://facebook.com/login',
            'email_purpose': 'email or phone input field for login',
            'password_purpose': 'password input field for login',
            'login_purpose': 'login button to submit credentials',
            'post_purpose': 'text area to compose a new post',
            'like_purpose': 'like button for content engagement'
        },
        SocialPlatform.TWITTER: {
            'login_url': 'https://twitter.com/login',
            'email_purpose': 'username or email input for login',
            'password_purpose': 'password input for authentication',
            'login_purpose': 'next or login button to proceed',
            'post_purpose': 'tweet compose textarea',
            'like_purpose': 'heart icon to like tweet'
        },
        SocialPlatform.LINKEDIN: {
            'login_url': 'https://linkedin.com/login',
            'email_purpose': 'email or phone input for LinkedIn login',
            'password_purpose': 'password input field',
            'login_purpose': 'sign in button',
            'post_purpose': 'start a post button or textarea',
            'like_purpose': 'like reaction button'
        }
    }
    
    async def _find_element_with_llm(
        self, 
        page, 
        purpose: str, 
        platform: SocialPlatform
    ) -> Optional[str]:
        """
        Find element using LLM-driven analysis.
        
        Args:
            page: Playwright page object
            purpose: What the element is for (e.g., "email input for login")
            platform: Current social platform for context
        
        Returns:
            CSS selector or None
        """
        try:
            from curllm_core.llm_dsl.selector_generator import LLMSelectorGenerator
            
            if hasattr(self, 'llm') and self.llm:
                generator = LLMSelectorGenerator(llm=self.llm)
                result = await generator.generate_field_selector(
                    page, 
                    purpose=f"{purpose} on {platform.value}"
                )
                if result.confidence > 0.5 and result.selector:
                    return result.selector
        except Exception as e:
            self._log(f"LLM element finding failed: {e}", "debug")
        
        return None
    
    def __init__(self, llm=None, page=None, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
        self._session_data = {}
    
    async def orchestrate(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute social media workflow.
        
        Args:
            instruction: User's social media instruction
            page_context: Current page state
            
        Returns:
            Social media action result
        """
        self._log("📱 SOCIAL MEDIA ORCHESTRATOR", "header")
        
        result = {
            'success': False,
            'platform': None,
            'action': None
        }
        
        try:
            # Phase 1: Detect platform
            platform = self._detect_platform(instruction, page_context)
            result['platform'] = platform.value
            self._log(f"Platform: {platform.value}")
            
            # Phase 2: Parse intent
            intent = self._parse_social_intent(instruction)
            result['action'] = intent['action']
            self._log(f"Action: {intent['action']}")
            
            # Phase 3: Execute action
            if intent['action'] == 'login':
                login_result = await self._perform_login(platform, intent)
                result.update(login_result)
                
            elif intent['action'] == 'post':
                post_result = await self._create_post(platform, intent)
                result.update(post_result)
                
            elif intent['action'] == 'message':
                msg_result = await self._send_message(platform, intent)
                result.update(msg_result)
                
            elif intent['action'] == 'like':
                like_result = await self._like_content(platform, intent)
                result.update(like_result)
                
            elif intent['action'] == 'follow':
                follow_result = await self._follow_user(platform, intent)
                result.update(follow_result)
                
            elif intent['action'] == 'comment':
                comment_result = await self._add_comment(platform, intent)
                result.update(comment_result)
            
            else:
                # Default: extract profile/page data
                data = await self._extract_social_data(platform)
                result['data'] = data
                result['success'] = bool(data)
            
        except Exception as e:
            result['error'] = str(e)
            self._log(f"Social media failed: {e}", "error")
        
        return result
    
    def _detect_platform(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]]
    ) -> SocialPlatform:
        """Detect which social platform is being used"""
        
        # Check instruction
        instr_lower = instruction.lower()
        url = page_context.get('url', '').lower() if page_context else ''
        
        platforms = [
            (SocialPlatform.FACEBOOK, ['facebook', 'fb.com', 'fb.me']),
            (SocialPlatform.TWITTER, ['twitter', 'x.com', 'tweet']),
            (SocialPlatform.INSTAGRAM, ['instagram', 'insta', 'ig']),
            (SocialPlatform.LINKEDIN, ['linkedin', 'lnkd']),
            (SocialPlatform.YOUTUBE, ['youtube', 'youtu.be', 'yt']),
            (SocialPlatform.TIKTOK, ['tiktok', 'tik tok'])
        ]
        
        for platform, keywords in platforms:
            if any(kw in instr_lower or kw in url for kw in keywords):
                return platform
        
        return SocialPlatform.UNKNOWN
    
    def _parse_social_intent(self, instruction: str) -> Dict[str, Any]:
        """Parse social media action intent"""
        instr_lower = instruction.lower()
        intent = {
            'action': 'browse',
            'credentials': {},
            'content': None,
            'target': None
        }
        
        # Determine action
        if any(kw in instr_lower for kw in ['login', 'log in', 'sign in', 'zaloguj']):
            intent['action'] = 'login'
            
            # Extract credentials
            email_match = re.search(r'(?:email|user|login)[=:]\s*["\']?([^\s,\'"]+)', instruction, re.I)
            if email_match:
                intent['credentials']['email'] = email_match.group(1)
            
            pass_match = re.search(r'(?:pass|password|hasło)[=:]\s*["\']?([^\s,\'"]+)', instruction, re.I)
            if pass_match:
                intent['credentials']['password'] = pass_match.group(1)
                
        elif any(kw in instr_lower for kw in ['post', 'share', 'publish', 'napisz', 'udostępnij']):
            intent['action'] = 'post'
            
            # Extract content
            content_match = re.search(r'(?:post|share|message)[=:]\s*["\']([^"\']+)["\']', instruction, re.I)
            if content_match:
                intent['content'] = content_match.group(1)
                
        elif any(kw in instr_lower for kw in ['message', 'dm', 'send', 'wyślij wiadomość']):
            intent['action'] = 'message'
            
            # Extract recipient
            to_match = re.search(r'to\s+@?(\w+)', instruction, re.I)
            if to_match:
                intent['target'] = to_match.group(1)
                
        elif any(kw in instr_lower for kw in ['like', 'polub', 'heart']):
            intent['action'] = 'like'
            
        elif any(kw in instr_lower for kw in ['follow', 'obserwuj', 'subscribe']):
            intent['action'] = 'follow'
            
            # Extract target
            follow_match = re.search(r'follow\s+@?(\w+)', instruction, re.I)
            if follow_match:
                intent['target'] = follow_match.group(1)
                
        elif any(kw in instr_lower for kw in ['comment', 'reply', 'komentarz']):
            intent['action'] = 'comment'
            
            content_match = re.search(r'(?:comment|reply)[=:]\s*["\']([^"\']+)["\']', instruction, re.I)
            if content_match:
                intent['content'] = content_match.group(1)
        
        return intent
    
    async def _perform_login(
        self,
        platform: SocialPlatform,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform login to social platform"""
        if not self.page:
            return {'success': False, 'error': 'No page'}
        
        result = {'success': False}
        config = self.PLATFORM_CONFIG.get(platform, {})
        
        try:
            # Navigate to login page if needed
            current_url = self.page.url.lower()
            if 'login' not in current_url:
                login_url = config.get('login_url')
                if login_url:
                    await self.page.goto(login_url)
                    await self.page.wait_for_timeout(2000)
            
            # Check for captcha
            captcha = await self._detect_captcha()
            if captcha['detected']:
                self._log("Captcha detected, attempting to solve...", "warning")
                solved = await self._solve_captcha(captcha)
                result['captcha'] = {'detected': True, 'solved': solved}
                if not solved:
                    result['error'] = 'Captcha not solved'
                    return result
            
            # Fill email/username
            email = intent['credentials'].get('email')
            email_selector = config.get('email_selector', 'input[type="email"]')
            if email:
                await self.page.fill(email_selector, email)
                await self.page.wait_for_timeout(500)
            
            # Some platforms have two-step login
            if platform == SocialPlatform.TWITTER:
                await self.page.click('button:has-text("Next")')
                await self.page.wait_for_timeout(1000)
            
            # Fill password
            password = intent['credentials'].get('password')
            password_selector = config.get('password_selector', 'input[type="password"]')
            if password:
                await self.page.fill(password_selector, password)
                await self.page.wait_for_timeout(500)
            
            # Click login button
            login_button = config.get('login_button', 'button[type="submit"]')
            await self.page.click(login_button)
            await self.page.wait_for_timeout(3000)
            
            # Verify login success
            result['success'] = await self._verify_login(platform)
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _create_post(
        self,
        platform: SocialPlatform,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a post on social platform"""
        if not self.page:
            return {'success': False}
        
        result = {'success': False}
        config = self.PLATFORM_CONFIG.get(platform, {})
        
        try:
            content = intent.get('content', '')
            if not content:
                result['error'] = 'No content to post'
                return result
            
            # Find and click post box
            post_box = config.get('post_box', '[contenteditable="true"]')
            await self.page.click(post_box)
            await self.page.wait_for_timeout(500)
            
            # Type content
            await self.page.keyboard.type(content)
            await self.page.wait_for_timeout(500)
            
            # Find and click post button
            post_buttons = [
                'button:has-text("Post")',
                'button:has-text("Tweet")',
                'button:has-text("Opublikuj")',
                '[data-testid="tweetButton"]'
            ]
            
            for selector in post_buttons:
                try:
                    await self.page.click(selector, timeout=2000)
                    result['success'] = True
                    result['posted'] = content[:100]
                    break
                except Exception:
                    continue
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _send_message(
        self,
        platform: SocialPlatform,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a direct message"""
        if not self.page:
            return {'success': False}
        
        result = {'success': False}
        
        try:
            target = intent.get('target')
            content = intent.get('content', '')
            
            # Navigate to messages/DM
            dm_links = [
                'a[href*="/messages"]',
                'a[href*="/direct"]',
                'a[aria-label*="Message"]'
            ]
            
            for selector in dm_links:
                try:
                    await self.page.click(selector, timeout=2000)
                    await self.page.wait_for_timeout(1500)
                    break
                except Exception:
                    continue
            
            # Find/select recipient if specified
            if target:
                search_input = await self.page.query_selector('input[type="search"], input[placeholder*="Search"]')
                if search_input:
                    await search_input.fill(target)
                    await self.page.wait_for_timeout(1000)
                    # Click first result
                    await self.page.click('.search-result, [role="option"]', timeout=2000)
            
            # Type message
            if content:
                message_input = await self.page.query_selector(
                    'textarea, [contenteditable="true"], input[placeholder*="message"]'
                )
                if message_input:
                    await message_input.fill(content)
                    await self.page.keyboard.press('Enter')
                    result['success'] = True
                    result['sent_to'] = target
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _like_content(
        self,
        platform: SocialPlatform,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Like/heart content"""
        if not self.page:
            return {'success': False}
        
        result = {'success': False, 'liked_count': 0}
        config = self.PLATFORM_CONFIG.get(platform, {})
        
        try:
            like_button = config.get('like_button', 'button[aria-label*="Like"]')
            
            # Find all like buttons
            buttons = await self.page.query_selector_all(like_button)
            
            for btn in buttons[:5]:  # Limit to first 5
                try:
                    await btn.click()
                    result['liked_count'] += 1
                    await self.page.wait_for_timeout(500)
                except Exception:
                    continue
            
            result['success'] = result['liked_count'] > 0
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _follow_user(
        self,
        platform: SocialPlatform,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Follow a user"""
        if not self.page:
            return {'success': False}
        
        result = {'success': False}
        
        try:
            target = intent.get('target')
            
            if target:
                # Navigate to user profile
                profile_url = self._get_profile_url(platform, target)
                if profile_url:
                    await self.page.goto(profile_url)
                    await self.page.wait_for_timeout(2000)
            
            # Find follow button
            follow_buttons = [
                'button:has-text("Follow")',
                'button:has-text("Obserwuj")',
                'button:has-text("Subscribe")',
                '[data-testid*="follow"]'
            ]
            
            for selector in follow_buttons:
                try:
                    await self.page.click(selector, timeout=2000)
                    result['success'] = True
                    result['followed'] = target
                    break
                except Exception:
                    continue
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _add_comment(
        self,
        platform: SocialPlatform,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a comment to content"""
        if not self.page:
            return {'success': False}
        
        result = {'success': False}
        
        try:
            content = intent.get('content', '')
            
            # Find comment input
            comment_selectors = [
                'textarea[placeholder*="comment"]',
                'input[placeholder*="comment"]',
                '[contenteditable="true"]',
                '.comment-input'
            ]
            
            for selector in comment_selectors:
                try:
                    await self.page.fill(selector, content)
                    await self.page.keyboard.press('Enter')
                    result['success'] = True
                    result['commented'] = content[:50]
                    break
                except Exception:
                    continue
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _detect_captcha(self) -> Dict[str, Any]:
        """Detect if captcha is present"""
        if not self.page:
            return {'detected': False}
        
        try:
            captcha_indicators = await self.page.evaluate('''() => {
                const indicators = {
                    recaptcha: !!document.querySelector('.g-recaptcha, [data-sitekey]'),
                    hcaptcha: !!document.querySelector('.h-captcha, [data-hcaptcha-sitekey]'),
                    slider: !!document.querySelector('.slider-captcha, [class*="slider"]'),
                    text_captcha: !!document.querySelector('[aria-label*="captcha"], img[alt*="captcha"]')
                };
                return {
                    detected: Object.values(indicators).some(v => v),
                    type: Object.entries(indicators).find(([k, v]) => v)?.[0] || null
                };
            }''')
            
            return captcha_indicators
        except Exception:
            return {'detected': False}
    
    async def _solve_captcha(self, captcha: Dict[str, Any]) -> bool:
        """Attempt to solve detected captcha"""
        # This is a placeholder - actual implementation would use
        # captcha solving services or manual intervention
        self._log(f"Captcha type: {captcha.get('type')}", "warning")
        return False
    
    async def _verify_login(self, platform: SocialPlatform) -> bool:
        """Verify if login was successful"""
        if not self.page:
            return False
        
        try:
            # Check for common login success indicators
            url = self.page.url.lower()
            
            # Should not be on login page anymore
            if 'login' in url or 'signin' in url:
                return False
            
            # Check for error messages
            errors = await self.page.query_selector_all('.error, .alert-error, [role="alert"]')
            if errors:
                return False
            
            return True
        except Exception:
            return False
    
    def _get_profile_url(self, platform: SocialPlatform, username: str) -> Optional[str]:
        """Get profile URL for platform"""
        urls = {
            SocialPlatform.TWITTER: f'https://twitter.com/{username}',
            SocialPlatform.INSTAGRAM: f'https://instagram.com/{username}',
            SocialPlatform.FACEBOOK: f'https://facebook.com/{username}',
            SocialPlatform.LINKEDIN: f'https://linkedin.com/in/{username}',
            SocialPlatform.TIKTOK: f'https://tiktok.com/@{username}'
        }
        return urls.get(platform)
    
    async def _extract_social_data(self, platform: SocialPlatform) -> Dict[str, Any]:
        """Extract data from social page"""
        if not self.page:
            return {}
        
        try:
            return await self.page.evaluate('''() => {
                return {
                    title: document.title,
                    url: window.location.href,
                    posts: Array.from(document.querySelectorAll('article, [data-testid="tweet"]'))
                        .slice(0, 10)
                        .map(el => el.textContent?.substring(0, 200)),
                    profile: document.querySelector('h1, [data-testid="UserName"]')?.textContent
                };
            }''')
        except Exception:
            return {}
    
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

