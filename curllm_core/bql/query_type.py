import json
import re
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
from enum import Enum


class QueryType(Enum):
    PAGE = "page"
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    EXTRACT = "extract"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
