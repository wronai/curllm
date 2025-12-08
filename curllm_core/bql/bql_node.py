import json
import re
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
from enum import Enum

from .query_type import QueryType

@dataclass
class BQLNode:
    type: QueryType
    selector: Optional[str] = None
    attributes: Dict[str, Any] = None
    children: List['BQLNode'] = None

    def __post_init__(self):
        self.attributes = self.attributes or {}
        self.children = self.children or []

