import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse


@dataclass
class LinkInfo:
    """Information about a found link"""
    url: str
    text: str
    aria_label: Optional[str]
    title: Optional[str]
    location: str  # header, footer, nav, main, sidebar
    context: str  # surrounding text
    score: float
    method: str  # how it was found

