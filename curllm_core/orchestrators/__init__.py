"""
Specialized Orchestrators for CurLLM

Provides domain-specific orchestrators for different task types:
- MasterOrchestrator - Routes to appropriate specialized orchestrator
- FormOrchestrator - Form filling and submission
- ExtractionOrchestrator - Data extraction tasks
- ECommerceOrchestrator - Shopping cart, checkout, payments
- SocialMediaOrchestrator - Login, captcha, social actions
- LiveInteractionOrchestrator - Real-time GUI interactions
- AuthOrchestrator - Authentication, login, 2FA, CAPTCHA solving

LLM-Driven Orchestrators (no hardcoded selectors):
- LLMFormOrchestrator - LLM-driven form filling
- LLMAuthOrchestrator - LLM-driven authentication
- LLMSocialOrchestrator - LLM-driven social media
- LLMECommerceOrchestrator - LLM-driven e-commerce
"""

from .master import MasterOrchestrator, TaskType
from .form import FormOrchestrator
from .extraction import ExtractionOrchestrator
from .ecommerce import ECommerceOrchestrator
from .social import SocialMediaOrchestrator
from .live import LiveInteractionOrchestrator
from .auth import AuthOrchestrator

# LLM-driven orchestrators (no hardcoded selectors)
from .form_llm import LLMFormOrchestrator
from .auth_llm import LLMAuthOrchestrator
from .social_llm import LLMSocialOrchestrator
from .ecommerce_llm import LLMECommerceOrchestrator

__all__ = [
    # Legacy orchestrators
    'MasterOrchestrator',
    'TaskType',
    'FormOrchestrator',
    'ExtractionOrchestrator',
    'ECommerceOrchestrator',
    'SocialMediaOrchestrator',
    'LiveInteractionOrchestrator',
    'AuthOrchestrator',
    # LLM-driven orchestrators
    'LLMFormOrchestrator',
    'LLMAuthOrchestrator',
    'LLMSocialOrchestrator',
    'LLMECommerceOrchestrator',
]

