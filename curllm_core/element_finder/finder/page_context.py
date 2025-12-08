import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PageContext:
    """Context extracted from page for LLM"""
    url: str
    title: str
    visible_text: str
    form_fields: List[Dict[str, str]]
    buttons: List[Dict[str, str]]
    links: List[Dict[str, str]]
    inputs: List[Dict[str, str]]

