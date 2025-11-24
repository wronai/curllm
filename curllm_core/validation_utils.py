from typing import Any, Optional


def should_validate(instruction: Optional[str], data: Optional[Any]) -> bool:
    try:
        low = (instruction or "").lower()
        # product-related
        if any(k in low for k in ["product", "produkt", "price", "zł", "pln"]):
            return True
        # article/title-related
        if any(k in low for k in ["title", "titles", "article", "artyku", "wpis", "blog", "news", "headline", "articl"]):
            return True
        if isinstance(data, dict):
            if "products" in data:
                return True
            if "articles" in data:
                return True
            try:
                pg = data.get("page")
                if isinstance(pg, dict) and isinstance(pg.get("links"), list):
                    # Looks like page.links extraction
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False
