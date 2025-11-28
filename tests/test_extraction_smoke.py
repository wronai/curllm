import asyncio
import pytest

from curllm_core.extraction import generic_fastpath, direct_fastpath, product_heuristics, fallback_extract


class FakePage:
    def __init__(self):
        self._text = (
            "Welcome. Contact: foo@example.com, Phone: +48 123 456 789. "
            "Product A 99 PLN\nProduct B 199 PLN"
        )
        self._anchors = [
            {"text": "Home", "href": "https://example.com/"},
            {"text": "Mail", "href": "mailto:bar@example.com"},
            {"text": "Tel", "href": "tel:+48111222333"},
        ]

    async def evaluate(self, script, *args):
        s = str(script)
        # Body innerText
        if "document.body.innerText" in s:
            return self._text
        # All anchors
        if "querySelectorAll('a')" in s and 'href^="mailto:"' not in s and 'href^="tel:"' not in s:
            return self._anchors
        # mailto anchors
        if 'querySelectorAll(\'a[href^="mailto:"]\')' in s or 'querySelectorAll("a[href^=\"mailto:\"]")' in s:
            return [
                "mailto:baz@example.com?subject=x",
            ]
        # tel anchors
        if 'querySelectorAll(\'a[href^="tel:"]\')' in s or 'querySelectorAll("a[href^=\"tel:\"]")' in s:
            return [
                "tel:+48 600-700-800",
            ]
        # product heuristics placeholder
        if "const asNumber" in s and "cards = Array.from(document.querySelectorAll" in s:
            return [
                {"name": "Product A", "price": 99.0, "url": "https://e/pA"},
                {"name": "Product B", "price": 120.0, "url": "https://e/pB"},
            ]
        # Minimal context
        if "({ title: document.title, url: window.location.href })" in s:
            return {"title": "t", "url": "https://example.com"}
        return None


def test_generic_fastpath():
    page = FakePage()
    res = asyncio.run(generic_fastpath("extract info", page))
    assert isinstance(res, dict)
    assert res["links"][0]["href"].startswith("https://example.com")
    assert any("@" in e for e in res["emails"])  # email present
    assert any(p for p in res["phones"])  # phone present


def test_direct_fastpath_links_only():
    page = FakePage()
    res = asyncio.run(direct_fastpath("links", page))
    assert isinstance(res, dict)
    assert "links" in res and res["links"]


@pytest.mark.skip(reason="product_heuristics is deprecated and redirects to iterative_extract which needs LLM")
def test_product_heuristics():
    page = FakePage()
    res = asyncio.run(product_heuristics("find product under 150", page))
    assert res and "products" in res and res["products"][0]["price"] < 150


def test_fallback_extract():
    page = FakePage()
    res = asyncio.run(fallback_extract("emails and phones only", page))
    assert "emails" in res or "phones" in res
