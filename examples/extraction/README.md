# Data Extraction Examples

Examples for extracting structured data from web pages.

## Projects

### [products/](products/) - Product Extraction
Extract product data (names, prices, images) from e-commerce sites.

```bash
# CLI
curllm "https://ceneo.pl" -d "Extract all products with prices"

# Python
python examples/extraction/products/extract_products.py
```

### [links/](links/) - Link Extraction
Extract and filter links from any webpage.

```bash
# CLI
curllm "https://example.com" -d "Extract all links"

# Python
python examples/extraction/links/extract_links.py
```

## Features Demonstrated

- **LLM-guided extraction** - LLM analyzes DOM to find data
- **Price filtering** - Filter products by price constraints
- **Structured output** - JSON output format
- **BQL queries** - Browser Query Language for precise extraction

## Related Documentation

- [Iterative Extractor](../../docs/v2/features/ITERATIVE_EXTRACTOR.md)
- [Extraction Architecture](../../docs/v2/features/EXTRACTION_ARCHITECTURE.md)
- [Examples Guide](../../docs/v2/guides/EXAMPLES.md)
