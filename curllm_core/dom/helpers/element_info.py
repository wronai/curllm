import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse


@dataclass 
class ElementInfo:
    """Information about a DOM element"""
    selector: str
    tag: str
    text: str
    attributes: Dict[str, str]
    visible: bool
    location: str

