"""
Built-in Streamware components

Components:
- form/       - Form detection, filling, submission
- extraction/ - Data extraction from pages
- navigation/ - Browser navigation and actions
- captcha/    - CAPTCHA detection and solving
- screenshot/ - Page and element screenshots
- curllm      - CurLLM integration
- web         - HTTP requests
- file        - File operations
- transform   - Data transformation
- decision    - LLM decision making
- dom_fix     - DOM analysis and fixes
"""

from .curllm import CurLLMComponent, CurLLMStreamComponent
from .web import WebComponent, HTTPComponent
from .file import FileComponent
from .transform import TransformComponent, JSONPathComponent
from .decision import (
    DOMAnalyzeComponent,
    ActionPlanComponent,
    ActionValidateComponent,
    DecisionTreeComponent
)
from .dom_fix import (
    DOMSnapshotComponent,
    DOMDiffComponent,
    DOMValidateComponent,
    FieldMapperComponent
)

# New atomic components
from . import form
from . import extraction
from . import navigation
from . import captcha
from . import screenshot
from . import dom
from . import bql
from . import llm
from . import vision
from . import browser
from . import page
from . import data
from . import config as config_component

__all__ = [
    # Core components
    "CurLLMComponent",
    "CurLLMStreamComponent",
    "WebComponent",
    "HTTPComponent",
    "FileComponent",
    "TransformComponent",
    "JSONPathComponent",
    # Decision components
    "DOMAnalyzeComponent",
    "ActionPlanComponent",
    "ActionValidateComponent",
    "DecisionTreeComponent",
    # DOM fix components
    "DOMSnapshotComponent",
    "DOMDiffComponent",
    "DOMValidateComponent",
    "FieldMapperComponent",
    # Atomic component modules
    "form",
    "extraction",
    "navigation",
    "captcha",
    "screenshot",
    "dom",
    "bql",
    "llm",
    "vision",
    "browser",
    "page",
    "data",
    "config_component",
]
