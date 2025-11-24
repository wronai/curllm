#!/usr/bin/env python3
import os
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


def _ensure_base() -> Path:
    base = Path(os.getenv("CURLLM_WORKSPACE", "./workspace")) / "results"
    candidates = [
        base,
        Path(os.path.expanduser("~")) / ".cache" / "curllm" / "results",
        Path("/tmp/curllm/results"),
    ]
    for cand in candidates:
        try:
            cand.mkdir(parents=True, exist_ok=True)
            test = cand / ".writetest"
            with open(test, "w") as f:
                f.write("ok")
            try:
                test.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                pass
            return cand
        except Exception:
            continue
    return base


def _sanitize_key(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "default"
    s2 = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in s)
    if len(s2) > 100:
        h = hashlib.sha1(s.encode("utf-8")).hexdigest()
        s2 = s2[:60] + "_" + h
    return s2


def compute_key(url: Optional[str], instruction: Optional[str], result_key: Optional[str]) -> str:
    if result_key and str(result_key).strip():
        return _sanitize_key(str(result_key).strip())
    u = (url or "").strip()
    i = (instruction or "").strip()
    h = hashlib.sha1(i.encode("utf-8")).hexdigest()[:12]
    safe = _sanitize_key(u.replace("://", "_").replace("/", "_"))
    if not safe:
        safe = "run"
    return f"{safe}__{h}"


def _store_dir_for(key: str) -> Path:
    base = _ensure_base()
    d = base / _sanitize_key(key)
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d


def save_snapshot(key: str, result_obj: Any, keep_history: int = 10) -> Path:
    d = _store_dir_for(key)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    p = d / f"{ts}.json"
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"timestamp": ts, "result": result_obj}, f, ensure_ascii=False, indent=2)
        latest = d / "latest.json"
        try:
            with open(latest, "w", encoding="utf-8") as f:
                json.dump({"timestamp": ts, "result": result_obj}, f, ensure_ascii=False)
        except Exception:
            pass
        files = sorted([x for x in d.glob("*.json") if x.name != "latest.json"], reverse=True)
        if keep_history and keep_history > 0 and len(files) > keep_history:
            for old in files[keep_history:]:
                try:
                    old.unlink()
                except Exception:
                    pass
    except Exception:
        pass
    return p


def load_latest(key: str) -> Optional[Dict[str, Any]]:
    d = _store_dir_for(key)
    latest = d / "latest.json"
    if latest.exists():
        try:
            with open(latest, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    files = sorted([x for x in d.glob("*.json") if x.name != "latest.json"], reverse=True)
    if files:
        try:
            with open(files[0], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _extract_array(res: Any) -> List[Any]:
    if isinstance(res, dict):
        for k in ("links", "articles", "products"):
            v = res.get(k)
            if isinstance(v, list):
                return v
        try:
            pg = res.get("page")
            if isinstance(pg, dict) and isinstance(pg.get("links"), list):
                return pg.get("links")  # type: ignore[return-value]
        except Exception:
            pass
        if isinstance(res.get("result"), list):
            return res.get("result")  # type: ignore[return-value]
    if isinstance(res, list):
        return res
    return []


def _key_for_item(it: Any, fields: List[str]) -> str:
    if isinstance(it, dict):
        parts = []
        for f in fields:
            v = it.get(f)
            if v is None:
                parts.append("")
            else:
                parts.append(str(v))
        return "|".join(parts)
    return json.dumps(it, ensure_ascii=False, sort_keys=True)


def diff(prev: List[Any], curr: List[Any], fields: List[str]) -> Tuple[List[Any], List[Tuple[Any, Any]], List[Any]]:
    prev_map = {}
    for it in prev:
        prev_map[_key_for_item(it, fields)] = it
    curr_map = {}
    for it in curr:
        curr_map[_key_for_item(it, fields)] = it
    new_items: List[Any] = []
    changed: List[Tuple[Any, Any]] = []
    for k, v in curr_map.items():
        if k not in prev_map:
            new_items.append(v)
        else:
            pv = prev_map[k]
            try:
                if json.dumps(pv, sort_keys=True, ensure_ascii=False) != json.dumps(v, sort_keys=True, ensure_ascii=False):
                    changed.append((pv, v))
            except Exception:
                pass
    removed: List[Any] = []
    for k, v in prev_map.items():
        if k not in curr_map:
            removed.append(v)
    return new_items, changed, removed


def previous_for_context(url: Optional[str], instruction: Optional[str], result_key: Optional[str], key_fields: List[str]) -> Dict[str, Any]:
    key = compute_key(url, instruction, result_key)
    prev_obj = load_latest(key)
    prev_list: List[Any] = []
    if isinstance(prev_obj, dict):
        prev_list = _extract_array(prev_obj.get("result"))
    return {"key": key, "items": prev_list, "fields": key_fields}


def apply_diff_and_store(url: Optional[str], instruction: Optional[str], result_key: Optional[str], result_obj: Any, key_fields: List[str], keep_history: int, mode: str) -> Tuple[Any, Dict[str, Any]]:
    key = compute_key(url, instruction, result_key)
    prev_obj = load_latest(key)
    prev_list: List[Any] = []
    if isinstance(prev_obj, dict):
        prev_list = _extract_array(prev_obj.get("result"))
    curr_list = _extract_array(result_obj)
    new_items, changed_items, removed_items = diff(prev_list, curr_list, key_fields)
    meta = {
        "store_key": key,
        "prev_count": len(prev_list),
        "curr_count": len(curr_list),
        "new_count": len(new_items),
        "changed_count": len(changed_items),
        "removed_count": len(removed_items),
    }
    out_obj = result_obj
    try:
        if isinstance(result_obj, dict):
            if mode == "new" and curr_list is not None:
                if "links" in result_obj and isinstance(result_obj.get("links"), list):
                    out_obj = {**result_obj, "links": new_items}
                elif "articles" in result_obj and isinstance(result_obj.get("articles"), list):
                    out_obj = {**result_obj, "articles": new_items}
                elif "products" in result_obj and isinstance(result_obj.get("products"), list):
                    out_obj = {**result_obj, "products": new_items}
                else:
                    out_obj = new_items
            elif mode == "changed":
                out_obj = {
                    "changed": [{"previous": a, "current": b} for a, b in changed_items]
                }
            elif mode == "delta":
                out_obj = {
                    "new": new_items,
                    "changed": [{"previous": a, "current": b} for a, b in changed_items],
                    "removed": removed_items,
                }
        else:
            if mode == "new":
                out_obj = new_items
            elif mode == "changed":
                out_obj = [{"previous": a, "current": b} for a, b in changed_items]
            elif mode == "delta":
                out_obj = {
                    "new": new_items,
                    "changed": [{"previous": a, "current": b} for a, b in changed_items],
                    "removed": removed_items,
                }
    except Exception:
        out_obj = result_obj
    save_snapshot(key, result_obj, keep_history=keep_history)
    return out_obj, meta
