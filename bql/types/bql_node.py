"""BQL node dataclass"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from bql.types.query_type import QueryType


@dataclass
class BQLNode:
    """Represents a node in BQL query tree"""
    type: QueryType
    selector: Optional[str] = None
    attributes: Dict[str, Any] = None
    children: List['BQLNode'] = None
    
    def __post_init__(self):
        self.attributes = self.attributes or {}
        self.children = self.children or []
