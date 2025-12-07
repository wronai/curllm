"""Form instruction parser - extracts key=value pairs from instructions"""

import json
import re
from typing import Dict


def parse_form_pairs(instruction: str | None) -> Dict[str, str]:
    """Parse key=value pairs from instruction string.
    
    Supports formats like:
    - name=John, email=john@example.com
    - name=John; email=john@example.com
    - JSON wrapper with instruction field
    """
    pairs: Dict[str, str] = {}
    text = instruction or ""
    
    # If JSON-like wrapper is used, parse to get inner instruction
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and isinstance(obj.get("instruction"), str):
            text = obj.get("instruction") or text
    except Exception:
        pass
    
    # Extract key=value pairs separated by commas/semicolons/newlines
    for m in re.finditer(r"([A-Za-ząćęłńóśźż\- ]+)\s*=\s*([^,;\n]+)", text, flags=re.IGNORECASE):
        k = (m.group(1) or "").strip().lower()
        v = (m.group(2) or "").strip()
        if k and v:
            pairs[k] = v
    
    return pairs


def normalize_field_key(key: str) -> str:
    """Normalize a field key to canonical form (name, email, message, etc.)"""
    lk = key.lower()
    
    if any(x in lk for x in ["email", "e-mail", "mail"]):
        return "email"
    elif any(x in lk for x in ["name", "imi", "nazw", "full name", "fullname", "first name", "last name"]):
        return "name"
    elif any(x in lk for x in ["message", "wiadomo", "treść", "tresc", "content", "komentarz"]):
        return "message"
    elif any(x in lk for x in ["subject", "temat"]):
        return "subject"
    elif any(x in lk for x in ["phone", "telefon", "tel"]):
        return "phone"
    
    return key
