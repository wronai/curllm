#!/usr/bin/env python3
from typing import Any, Dict, Optional

def normalize_headers(headers: Optional[Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not headers:
        return out
    if isinstance(headers, dict):
        for k, v in headers.items():
            try:
                out[str(k)] = str(v)
            except Exception:
                continue
        return out
    if isinstance(headers, (list, tuple)):
        for item in headers:
            try:
                s = str(item)
                if ":" in s:
                    k, v = s.split(":", 1)
                    out[k.strip()] = v.strip()
            except Exception:
                continue
    return out
