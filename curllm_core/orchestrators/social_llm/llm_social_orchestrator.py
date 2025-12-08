from typing import Any, Dict, Optional
from curllm_core.llm_dsl import DSLExecutor, AtomicFunctions

from .social_platform import SocialPlatform
from .social_intent import SocialIntent
from .social_result import SocialResult

class LLMSocialOrchestrator:
    """
    LLM-driven social media orchestrator.
    
    NO HARDCODED:
    - Platform selectors
    - Keyword lists
    - URL patterns
    
    Everything is detected by LLM from context.
    """
    
    def __init__(self, llm=None, page=None, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
        self.atoms = None
        self.executor = None
        
        if page and llm:
            self.atoms = AtomicFunctions(page=page, llm=llm)
            self.executor = DSLExecutor(page=page, llm=llm)
    
    async def orchestrate(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> SocialResult:
        """
        Execute social media workflow using LLM.
        """
        self._log("📱 LLM SOCIAL ORCHESTRATOR", "header")
        
        try:
            # Phase 1: LLM detects platform from page
            platform = await self._detect_platform_llm(page_context)
            self._log(f"Platform: {platform.value}")
            
            # Phase 2: LLM parses intent from instruction
            intent = await self._parse_intent_llm(instruction)
            self._log(f"Action: {intent.action} (confidence: {intent.confidence:.0%})")
            
            # Phase 3: Execute action using LLM-driven element finding
            if intent.action == 'login':
                return await self._perform_login_llm(platform, intent)
            elif intent.action == 'post':
                return await self._create_post_llm(platform, intent)
            elif intent.action == 'message':
                return await self._send_message_llm(platform, intent)
            elif intent.action == 'like':
                return await self._like_content_llm(platform)
            elif intent.action == 'follow':
                return await self._follow_user_llm(platform, intent)
            elif intent.action == 'comment':
                return await self._add_comment_llm(platform, intent)
            else:
                # Browse/extract data
                data = await self._extract_data_llm(platform)
                return SocialResult(
                    success=True,
                    platform=platform.value,
                    action='browse',
                    data=data,
                )
                
        except Exception as e:
            self._log(f"Error: {e}", "error")
            return SocialResult(
                success=False,
                platform='unknown',
                action='error',
                error=str(e),
            )
    
    async def _detect_platform_llm(
        self, 
        page_context: Optional[Dict[str, Any]]
    ) -> SocialPlatform:
        """
        Detect platform using LLM - no hardcoded URL/keyword matching.
        """
        if not self.llm:
            return SocialPlatform.UNKNOWN
        
        # Get current page info
        url = page_context.get('url', '') if page_context else ''
        title = page_context.get('title', '') if page_context else ''
        
        if self.page:
            try:
                url = await self.page.evaluate("() => location.href")
                title = await self.page.evaluate("() => document.title")
            except Exception:
                pass
        
        prompt = f"""Identify which social media platform this page belongs to.

URL: {url}
Title: {title}

Respond with ONLY one of: facebook, twitter, instagram, linkedin, youtube, tiktok, unknown"""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip().lower()
            
            platform_map = {
                'facebook': SocialPlatform.FACEBOOK,
                'twitter': SocialPlatform.TWITTER,
                'instagram': SocialPlatform.INSTAGRAM,
                'linkedin': SocialPlatform.LINKEDIN,
                'youtube': SocialPlatform.YOUTUBE,
                'tiktok': SocialPlatform.TIKTOK,
            }
            return platform_map.get(answer, SocialPlatform.UNKNOWN)
        except Exception:
            return SocialPlatform.UNKNOWN
    
    async def _parse_intent_llm(self, instruction: str) -> SocialIntent:
        """
        Parse user intent using LLM - no hardcoded keyword lists.
        """
        if not self.llm:
            return SocialIntent(
                action='browse',
                credentials={},
                content=None,
                target=None,
                confidence=0.5,
            )
        
        prompt = f"""Parse this social media instruction.

Instruction: "{instruction}"

Return JSON:
{{
    "action": "login|post|message|like|follow|comment|browse",
    "credentials": {{"email": "...", "password": "..."}},
    "content": "text to post if any",
    "target": "username to message/follow if any",
    "confidence": 0.0-1.0
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
            return SocialIntent(
                action=data.get('action', 'browse'),
                credentials=data.get('credentials', {}),
                content=data.get('content'),
                target=data.get('target'),
                confidence=data.get('confidence', 0.7),
            )
        except Exception:
            return SocialIntent(
                action='browse',
                credentials={},
                content=None,
                target=None,
                confidence=0.3,
            )
    
    async def _perform_login_llm(
        self, 
        platform: SocialPlatform, 
        intent: SocialIntent
    ) -> SocialResult:
        """
        Perform login using LLM to find fields - no hardcoded selectors.
        """
        if not self.atoms:
            return SocialResult(
                success=False, platform=platform.value, action='login',
                error="No LLM/page available"
            )
        
        # LLM finds email/username field
        email_result = await self.atoms.find_input_by_context(
            "login form field for email address or username"
        )
        
        if email_result.success and intent.credentials.get('email'):
            selector = email_result.data.get('selector')
            await self.page.fill(selector, intent.credentials['email'])
            self._log(f"Filled email: {selector}")
        
        # LLM finds password field
        pass_result = await self.atoms.find_input_by_context(
            "login form field for password"
        )
        
        if pass_result.success and intent.credentials.get('password'):
            selector = pass_result.data.get('selector')
            await self.page.fill(selector, intent.credentials['password'])
            self._log(f"Filled password: {selector}")
        
        # LLM finds login button
        button_result = await self.atoms.find_clickable_by_intent(
            "submit login form / sign in button"
        )
        
        if button_result.success:
            selector = button_result.data.get('selector')
            await self.page.click(selector)
            self._log(f"Clicked login: {selector}")
            
            await self.page.wait_for_timeout(3000)
            
            # Check result
            msg_result = await self.atoms.detect_message_type()
            if msg_result.success:
                msg_type = msg_result.data.get('type', '')
                if msg_type == 'error':
                    return SocialResult(
                        success=False, platform=platform.value, action='login',
                        error=msg_result.data.get('text', 'Login failed')
                    )
            
            return SocialResult(
                success=True, platform=platform.value, action='login',
                message="Login submitted"
            )
        
        return SocialResult(
            success=False, platform=platform.value, action='login',
            error="Could not find login button"
        )
    
    async def _create_post_llm(
        self, 
        platform: SocialPlatform, 
        intent: SocialIntent
    ) -> SocialResult:
        """Create post using LLM to find elements."""
        if not self.atoms or not intent.content:
            return SocialResult(
                success=False, platform=platform.value, action='post',
                error="No content to post"
            )
        
        # Find post input
        post_input = await self.atoms.find_input_by_context(
            "text area or input for creating a new post / status update / tweet"
        )
        
        if post_input.success:
            selector = post_input.data.get('selector')
            await self.page.fill(selector, intent.content)
            self._log(f"Entered post content: {selector}")
            
            # Find post button
            post_btn = await self.atoms.find_clickable_by_intent(
                "publish / post / tweet / submit the new post"
            )
            
            if post_btn.success:
                await self.page.click(post_btn.data.get('selector'))
                return SocialResult(
                    success=True, platform=platform.value, action='post',
                    message="Post created"
                )
        
        return SocialResult(
            success=False, platform=platform.value, action='post',
            error="Could not find post input"
        )
    
    async def _send_message_llm(
        self, 
        platform: SocialPlatform, 
        intent: SocialIntent
    ) -> SocialResult:
        """Send message using LLM to find elements."""
        if not self.atoms:
            return SocialResult(
                success=False, platform=platform.value, action='message',
                error="No LLM available"
            )
        
        # Find message input
        msg_input = await self.atoms.find_input_by_context(
            "text input for composing a direct message"
        )
        
        if msg_input.success and intent.content:
            await self.page.fill(msg_input.data.get('selector'), intent.content)
            
            # Find send button
            send_btn = await self.atoms.find_clickable_by_intent(
                "send the message"
            )
            
            if send_btn.success:
                await self.page.click(send_btn.data.get('selector'))
                return SocialResult(
                    success=True, platform=platform.value, action='message',
                    message="Message sent"
                )
        
        return SocialResult(
            success=False, platform=platform.value, action='message',
            error="Could not send message"
        )
    
    async def _like_content_llm(self, platform: SocialPlatform) -> SocialResult:
        """Like content using LLM to find like button."""
        if not self.atoms:
            return SocialResult(
                success=False, platform=platform.value, action='like',
                error="No LLM available"
            )
        
        like_btn = await self.atoms.find_clickable_by_intent(
            "like button / heart button / upvote"
        )
        
        if like_btn.success:
            await self.page.click(like_btn.data.get('selector'))
            return SocialResult(
                success=True, platform=platform.value, action='like',
                message="Content liked"
            )
        
        return SocialResult(
            success=False, platform=platform.value, action='like',
            error="Could not find like button"
        )
    
    async def _follow_user_llm(
        self, 
        platform: SocialPlatform, 
        intent: SocialIntent
    ) -> SocialResult:
        """Follow user using LLM to find follow button."""
        if not self.atoms:
            return SocialResult(
                success=False, platform=platform.value, action='follow',
                error="No LLM available"
            )
        
        follow_btn = await self.atoms.find_clickable_by_intent(
            "follow button / subscribe button"
        )
        
        if follow_btn.success:
            await self.page.click(follow_btn.data.get('selector'))
            return SocialResult(
                success=True, platform=platform.value, action='follow',
                message=f"Followed {intent.target or 'user'}"
            )
        
        return SocialResult(
            success=False, platform=platform.value, action='follow',
            error="Could not find follow button"
        )
    
    async def _add_comment_llm(
        self, 
        platform: SocialPlatform, 
        intent: SocialIntent
    ) -> SocialResult:
        """Add comment using LLM to find elements."""
        if not self.atoms:
            return SocialResult(
                success=False, platform=platform.value, action='comment',
                error="No LLM available"
            )
        
        # Find comment input
        comment_input = await self.atoms.find_input_by_context(
            "input field for writing a comment"
        )
        
        if comment_input.success and intent.content:
            await self.page.fill(comment_input.data.get('selector'), intent.content)
            
            # Find submit
            submit_btn = await self.atoms.find_clickable_by_intent(
                "post comment / submit comment"
            )
            
            if submit_btn.success:
                await self.page.click(submit_btn.data.get('selector'))
                return SocialResult(
                    success=True, platform=platform.value, action='comment',
                    message="Comment added"
                )
        
        return SocialResult(
            success=False, platform=platform.value, action='comment',
            error="Could not add comment"
        )
    
    async def _extract_data_llm(self, platform: SocialPlatform) -> Dict[str, Any]:
        """Extract social data using LLM."""
        if not self.atoms:
            return {}
        
        result = await self.atoms.extract_data_pattern(
            "profile information: username, bio, follower count, post count"
        )
        
        if result.success:
            return result.data
        
        return {}
    
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
