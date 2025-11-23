import json

from curllm_core.runtime import parse_runtime_from_instruction, DEFAULT_RUNTIME
from curllm_core.headers import normalize_headers


def test_parse_runtime_plain_string():
    instr = "Find links on the page"
    new_instr, runtime = parse_runtime_from_instruction(instr)
    assert new_instr == instr
    assert isinstance(runtime, dict)
    # defaults preserved
    for k, v in DEFAULT_RUNTIME.items():
        assert k in runtime


def test_parse_runtime_with_json_params():
    obj = {
        "instruction": "Do something",
        "params": {
            "include_dom_html": True,
            "action_timeout_ms": 12000,
        },
    }
    s = json.dumps(obj)
    new_instr, runtime = parse_runtime_from_instruction(s)
    assert new_instr == "Do something"
    assert runtime["include_dom_html"] is True
    assert runtime["action_timeout_ms"] == 12000
    # default keys still present
    assert "no_click" in runtime
    assert "scroll_load" in runtime


ess_obj = {"task": "Hello world", "params": {"no_click": True}}

def test_parse_runtime_task_key():
    s = json.dumps(ess_obj)
    new_instr, runtime = parse_runtime_from_instruction(s)
    assert new_instr == "Hello world"
    assert runtime["no_click"] is True


def test_normalize_headers_dict():
    res = normalize_headers({"User-Agent": "UA", "Accept-Language": "pl-PL"})
    assert res["User-Agent"] == "UA"
    assert res["Accept-Language"] == "pl-PL"


def test_normalize_headers_list():
    res = normalize_headers(["X-Foo: bar", "Accept: */*"])
    assert res["X-Foo"] == "bar"
    assert res["Accept"] == "*/*"


def test_normalize_headers_none():
    res = normalize_headers(None)
    assert res == {}
