from curllm_core.bql import BQLParser


def test_bql_query_parse_structure():
    q = 'query Q { page(url: "https://example.com") { title links: select(css: "a") { text href: attr(name: "href") } } }'
    p = BQLParser()
    parsed = p.parse(q)
    assert parsed["type"] == "query"
    assert isinstance(parsed.get("operations"), list)
    assert parsed["operations"][0]["operation"] == "page"
    assert parsed["operations"][0]["arguments"]["url"] == "https://example.com"


def test_bql_plain_instruction_fallback():
    q = "extract all links"
    parsed = BQLParser().parse(q)
    assert parsed["type"] == "instruction"
    assert "operations" in parsed
