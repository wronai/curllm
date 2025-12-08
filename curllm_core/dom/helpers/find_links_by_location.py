import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .link_info import LinkInfo
from .extract_all_links import extract_all_links

async def find_links_by_location(
    page,
    locations: List[str]
) -> List[LinkInfo]:
    """
    Find links in specific page locations (header, footer, nav, etc).
    """
    all_links = await extract_all_links(page)
    return [l for l in all_links if l.location in locations]
