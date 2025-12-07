"""BQL query type enumeration"""

from enum import Enum


class QueryType(Enum):
    """BQL query types"""
    PAGE = "page"
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    EXTRACT = "extract"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
