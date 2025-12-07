"""
Tests for DOM Toolkit Patterns and Algorithms

These tests verify that pattern matching works correctly
without needing a browser - using regex and string matching.
"""

import pytest
import re


class TestPricePatterns:
    """Test price detection patterns."""
    
    PRICE_PATTERNS = [
        # Polish formats
        (r"(\d+[\d\s]*[,\.]\d{2})\s*(?:zł|PLN)", "1 234,56 zł", "1 234,56"),
        (r"(\d+[\d\s]*[,\.]\d{2})\s*(?:zł|PLN)", "PLN 999.99", None),  # PLN before
        (r"(\d+)\s*(?:zł|PLN)", "500 zł", "500"),
        (r"od\s*(\d+[\d\s]*[,\.]\d{2})\s*(?:zł|PLN)", "od 1234,56 zł", "1234,56"),
        
        # Euro
        (r"(\d+[\d\s]*[,\.]\d{2})\s*€", "99,99 €", "99,99"),
        (r"€\s*(\d+[\d\s]*[,\.]\d{2})", "€ 99.99", "99.99"),
        
        # Dollar
        (r"\$\s*(\d+[\d\s]*[,\.]\d{2})", "$199.99", "199.99"),
        (r"(\d+[\d\s]*[,\.]\d{2})\s*(?:USD|\$)", "199.99 USD", "199.99"),
    ]
    
    @pytest.mark.parametrize("pattern,text,expected", PRICE_PATTERNS)
    def test_price_pattern(self, pattern, text, expected):
        """Test individual price patterns."""
        match = re.search(pattern, text, re.IGNORECASE)
        if expected:
            assert match is not None, f"Pattern {pattern} should match {text}"
            assert match.group(1) == expected
        else:
            # Pattern might not match, that's expected for some cases
            pass
    
    def test_universal_price_pattern(self):
        """Test universal price pattern that catches most formats."""
        universal_pattern = r"(\d+[\d\s]*[,\.]\d{2})\s*(?:zł|PLN|€|\$|EUR|USD)"
        
        test_cases = [
            ("1 234,56 zł", True),
            ("999.99 PLN", True),
            ("50,00 €", True),
            ("$99.99", False),  # $ before number
            ("bez ceny", False),
        ]
        
        for text, should_match in test_cases:
            match = re.search(universal_pattern, text, re.IGNORECASE)
            if should_match:
                assert match is not None, f"Should match: {text}"
            else:
                assert match is None, f"Should not match: {text}"
    
    def test_price_extraction_normalization(self):
        """Test price normalization (string to float)."""
        def normalize_price(price_str: str) -> float:
            # Remove spaces
            price_str = price_str.replace(" ", "")
            # Replace comma with dot
            price_str = price_str.replace(",", ".")
            return float(price_str)
        
        test_cases = [
            ("1 234,56", 1234.56),
            ("999.99", 999.99),
            ("1234,00", 1234.0),
            ("50,00", 50.0),
        ]
        
        for input_str, expected in test_cases:
            result = normalize_price(input_str)
            assert result == expected, f"{input_str} -> {result} != {expected}"


class TestProductLinkPatterns:
    """Test product link detection patterns."""
    
    PRODUCT_PATTERNS = [
        # Ceneo patterns
        (r"^/\d{6,}$", "/179521263", True),
        (r"^/\d{6,}$", "/12345", False),  # Too short
        (r"^/offers/\d+/\d+", "/offers/123/456", True),
        (r"^/offers/\d+/\d+", "/offers/abc/456", False),
        
        # HTML product pages
        (r"[_/-]\d{3,}\.html?$", "/product_12345.html", True),
        (r"[_/-]\d{3,}\.html?$", "/Product-Name_98765.htm", True),
        (r"[_/-]\d{3,}\.html?$", "/about.html", False),
        
        # Common e-commerce patterns
        (r"/(?:product|produkt|item|towar)/", "/product/shoes-nike", True),
        (r"/(?:product|produkt|item|towar)/", "/produkt/buty", True),
        (r"/(?:product|produkt|item|towar)/", "/category/shoes", False),
        
        # ID-based patterns
        (r"/[pi]/\d+", "/p/12345", True),
        (r"/[pi]/\d+", "/i/67890", True),
        (r"/[pi]/\d+", "/c/12345", False),
    ]
    
    @pytest.mark.parametrize("pattern,path,expected", PRODUCT_PATTERNS)
    def test_product_link_pattern(self, pattern, path, expected):
        """Test individual product link patterns."""
        match = re.search(pattern, path, re.IGNORECASE)
        result = match is not None
        assert result == expected, f"Pattern {pattern} on {path}: got {result}, expected {expected}"
    
    def test_combined_product_detector(self):
        """Test combined product link detection function."""
        def is_product_link(pathname: str) -> bool:
            patterns = [
                r"/\d{6,}$",  # Pure numeric ID
                r"/offers/\d+/\d+",  # Offers
                r"[_/-]\d{3,}\.html?$",  # HTML with ID
                r"/(?:product|produkt|item|towar)/",  # Product path
                r"/[pi]/\d+",  # Short ID paths
                r";\d{4,}",  # Semicolon ID
            ]
            return any(re.search(p, pathname, re.IGNORECASE) for p in patterns)
        
        product_links = [
            "/179521263",
            "/offers/123/456",
            "/product/nike-shoes_12345.html",
            "/produkt/buty-sportowe",
            "/p/98765",
            "/item;12345678",
        ]
        
        non_product_links = [
            "/",
            "/kontakt",
            "/category/shoes",
            "/about-us",
            "/privacy-policy",
            "/cart",
        ]
        
        for link in product_links:
            assert is_product_link(link), f"Should be product: {link}"
        
        for link in non_product_links:
            assert not is_product_link(link), f"Should NOT be product: {link}"


class TestSelectorPatterns:
    """Test CSS selector patterns."""
    
    def test_product_class_patterns(self):
        """Test detection of product-related class names."""
        product_keywords = [
            "product", "produkt", "item", "card", "tile",
            "offer", "listing", "result"
        ]
        
        penalty_keywords = [
            "nav", "menu", "header", "footer", "sidebar",
            "banner", "ad", "cookie", "modal"
        ]
        
        def score_selector(selector: str) -> int:
            score = 0
            lower = selector.lower()
            
            for kw in product_keywords:
                if kw in lower:
                    score += 20
                    
            for kw in penalty_keywords:
                if kw in lower:
                    score -= 40
                    
            return score
        
        # Good selectors
        assert score_selector("div.product-card") > 0
        assert score_selector("li.product-item") > 0
        assert score_selector("article.offer-tile") > 0
        
        # Bad selectors
        assert score_selector("nav.main-menu") < 0
        assert score_selector("div.header-banner") < 0
        assert score_selector("footer.site-footer") < 0


class TestContainerScoring:
    """Test container scoring logic."""
    
    def test_scoring_factors(self):
        """Test that scoring weights are reasonable."""
        def score_container(metrics: dict) -> int:
            score = 0
            
            # Count bonus
            count = metrics.get("count", 0)
            if count >= 10:
                score += 30
            elif count >= 5:
                score += 20
            
            # Has links
            if metrics.get("link_ratio", 0) >= 0.8:
                score += 25
            
            # Has prices
            if metrics.get("price_ratio", 0) >= 0.5:
                score += 35
            
            # Has images
            if metrics.get("image_ratio", 0) >= 0.5:
                score += 15
            
            # Text quality
            avg_text = metrics.get("avg_text_len", 0)
            if 30 < avg_text < 500:
                score += 20
            elif avg_text > 2000:
                score -= 30
            
            return score
        
        # Good product container
        good_container = {
            "count": 15,
            "link_ratio": 0.9,
            "price_ratio": 0.8,
            "image_ratio": 0.9,
            "avg_text_len": 150,
        }
        
        # Navigation container
        nav_container = {
            "count": 20,
            "link_ratio": 1.0,
            "price_ratio": 0.0,
            "image_ratio": 0.1,
            "avg_text_len": 20,
        }
        
        # Too large content
        article_container = {
            "count": 3,
            "link_ratio": 0.3,
            "price_ratio": 0.0,
            "image_ratio": 0.3,
            "avg_text_len": 3000,
        }
        
        good_score = score_container(good_container)
        nav_score = score_container(nav_container)
        article_score = score_container(article_container)
        
        assert good_score > nav_score, "Product container should score higher than nav"
        assert good_score > article_score, "Product container should score higher than article"
        assert good_score > 100, f"Good container should have high score: {good_score}"


class TestFieldExtraction:
    """Test field extraction logic."""
    
    def test_name_cleanup(self):
        """Test product name cleanup."""
        def cleanup_name(name: str) -> str:
            # Remove price patterns
            name = re.sub(r"\d+[\d\s]*[,\.]\d{2}\s*(?:zł|PLN|€|\$)", "", name)
            # Remove extra whitespace
            name = " ".join(name.split())
            # Truncate
            return name[:200].strip()
        
        test_cases = [
            ("iPhone 15 Pro Max 256GB", "iPhone 15 Pro Max 256GB"),
            ("Laptop 999,00 zł", "Laptop"),
            ("Samsung Galaxy   S24   Ultra", "Samsung Galaxy S24 Ultra"),
        ]
        
        for input_name, expected in test_cases:
            result = cleanup_name(input_name)
            assert result == expected, f"{input_name} -> {result} != {expected}"
    
    def test_url_validation(self):
        """Test URL validation."""
        def is_valid_product_url(url: str) -> bool:
            if not url:
                return False
            if not url.startswith(("http://", "https://", "/")):
                return False
            if url in ("#", "javascript:", "javascript:void(0)"):
                return False
            return True
        
        valid = [
            "https://shop.pl/product/123",
            "/product/123",
            "http://example.com/item",
        ]
        
        invalid = [
            "",
            "#",
            "javascript:void(0)",
            "not-a-url",
        ]
        
        for url in valid:
            assert is_valid_product_url(url), f"Should be valid: {url}"
        
        for url in invalid:
            assert not is_valid_product_url(url), f"Should be invalid: {url}"
