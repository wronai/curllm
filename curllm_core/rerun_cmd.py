import json
from typing import Any, Dict, Optional
from .config import config


def build_rerun_curl(instruction: Optional[str], url: str, params: Dict[str, Any], top_level: Optional[Dict[str, Any]] = None) -> str:
    try:
        inner = {"instruction": instruction or "", "params": params}
        instr_json = json.dumps(inner, ensure_ascii=False)
        payload = {
            "data": instr_json,
            "url": url,
            "visual_mode": False,
            "stealth_mode": False,
            "captcha_solver": False,
            "use_bql": False,
        }
        if isinstance(top_level, dict):
            try:
                payload.update({k: v for k, v in top_level.items() if k in ("visual_mode","stealth_mode","captcha_solver","use_bql","url")})
            except Exception:
                pass
        payload_text = json.dumps(payload, ensure_ascii=False)
        api_url = f"http://localhost:{config.api_port}/api/execute"
        return f"curl -s -X POST '{api_url}' -H 'Content-Type: application/json' -d '{payload_text}'"
    except Exception:
        return ""
