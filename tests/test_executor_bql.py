from curllm_core import CurllmExecutor


def test_parse_bql_to_instruction():
    ex = CurllmExecutor()
    bql = 'query { page(url: "https://example.com") { title links { href text } } }'
    parsed = ex._parse_bql(bql)
    assert isinstance(parsed, str)
    assert parsed.startswith("Extract the following fields from the page:")


def test_parse_plain_text_passthrough():
    ex = CurllmExecutor()
    plain = "extract all links"
    parsed = ex._parse_bql(plain)
    assert parsed == plain
