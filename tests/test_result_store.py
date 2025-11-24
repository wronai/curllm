import os
import json
import tempfile
from pathlib import Path

from curllm_core.result_store import diff, compute_key, save_snapshot, previous_for_context


def test_diff_new_changed_removed():
    prev = [
        {"href": "https://x/a", "title": "A"},
        {"href": "https://x/b", "title": "B"},
    ]
    curr = [
        {"href": "https://x/a", "title": "A!"},  # changed
        {"href": "https://x/c", "title": "C"},   # new
    ]
    new_items, changed, removed = diff(prev, curr, ["href"])
    assert any(it["href"] == "https://x/c" for it in new_items)
    assert any(pv["href"] == "https://x/a" and cv["title"] == "A!" for pv, cv in changed)
    assert any(it["href"] == "https://x/b" for it in removed)


def test_compute_key_stable_and_sanitized():
    k1 = compute_key("https://example.com/path", "instr text", None)
    k2 = compute_key("https://example.com/path", "instr text", None)
    assert k1 == k2
    assert "__" in k1


def test_previous_for_context_reads_latest(tmp_path: Path, monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setenv("CURLLM_WORKSPACE", td)
        key = "series-1"
        sample = {"result": {"links": [{"href": "https://x/a"}]}}
        # Save as latest
        d = Path(td) / "results" / key
        d.mkdir(parents=True, exist_ok=True)
        (d / "latest.json").write_text(json.dumps(sample), encoding="utf-8")
        prev = previous_for_context("https://x/", "instr", key, ["href"])
        assert prev["key"] == key
        assert prev["fields"] == ["href"]
        assert any(it["href"] == "https://x/a" for it in prev["items"])  # type: ignore[index]
