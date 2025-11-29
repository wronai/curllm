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
"""

from .master import MasterOrchestrator, TaskType
from .form import FormOrchestrator
from .extraction import ExtractionOrchestrator
from .ecommerce import ECommerceOrchestrator
from .social import SocialMediaOrchestrator
from .live import LiveInteractionOrchestrator
from .auth import AuthOrchestrator

__all__ = [
    'MasterOrchestrator',
    'TaskType',
    'FormOrchestrator',
    'ExtractionOrchestrator',
    'ECommerceOrchestrator',
    'SocialMediaOrchestrator',
    'LiveInteractionOrchestrator',
    'AuthOrchestrator'
]

