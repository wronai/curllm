import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .analyze_page_type import analyze_page_type

async def has_content_type(page, content_type: str) -> bool:
    """
    Check if page contains specific type of content.
    """
    analysis = await analyze_page_type(page)
    return analysis['type'] == content_type
