# Atomic Query & Export System

## 🎯 Overview

System atomowych zapytań i multi-format exportu:
- **Atomic Queries**: Małe, composable funkcje wyszukiwania
- **Multi-Format Export**: JSON, CSV, XML, Excel, Markdown, HTML, YAML, SQLite
- **Fluent API**: Chainable operations
- **Type-Safe**: TypeScript-like experience w Pythonie

## 🔍 Atomic Query System

### Basic Usage

```python
from curllm_core.atomic_query import AtomicQuery

# Create query
query = AtomicQuery(page)

# Chain operations
result = await (
    query
    .find(".product-box")
    .filter("el => el.classList.contains('available')")
    .map("el => ({name: el.querySelector('h3').innerText, price: el.querySelector('.price').innerText})")
    .limit(20)
    .execute()
)

# Access data
products = result.data
metadata = result.metadata
```

### Product Query (Specialized)

```python
from curllm_core.atomic_query import ProductQuery

query = ProductQuery(page)

products = await (
    query
    .find(".product")
    .extract_product(
        name_sel="h3.title",
        price_sel=".price",
        url_sel="a.link"
    )
    .filter_by_price(max_price=150)
    .limit(50)
    .execute()
)
```

### Quick Functions

```python
from curllm_core.atomic_query import (
    quick_find,
    quick_extract_text,
    quick_extract_products
)

# Quick find
elements = await quick_find(page, ".product", limit=20)

# Quick text extraction
names = await quick_extract_text(page, ".product", "h3.name")

# Quick product extraction
products = await quick_extract_products(
    page,
    container_selector=".product-box",
    name_selector="h3",
    price_selector=".price",
    url_selector="a",
    max_price=150,
    limit=50
)
```

## 📊 Export System

### JSON Export

```python
from curllm_core.data_export import DataExporter

exporter = DataExporter(products)

# Pretty JSON
exporter.to_json("products.json", pretty=True)

# Compact JSON
exporter.to_json("products.compact.json", pretty=False)

# JSONL (one JSON per line)
exporter.to_jsonl("products.jsonl")
```

### CSV Export

```python
# Basic CSV
exporter.to_csv("products.csv")

# Custom delimiter
exporter.to_csv("products.tsv", delimiter="\t")

# Specific columns
exporter.to_csv("products.csv", columns=["name", "price", "url"])
```

### Excel Export

```python
# Requires: pip install openpyxl

exporter.to_excel("products.xlsx", sheet_name="Products")
```

### Markdown Export

```python
exporter.to_markdown("products.md")

# Output:
# | name | price | url |
# | --- | --- | --- |
# | Product 1 | 99.99 | https://... |
# | Product 2 | 149.99 | https://... |
```

### HTML Export

```python
exporter.to_html("products.html", include_style=True)
```

### XML Export

```python
exporter.to_xml("products.xml", root_tag="products", item_tag="product")
```

### SQLite Export

```python
exporter.to_sqlite("products.db", table_name="products")
```

### Quick Export Functions

```python
from curllm_core.data_export import (
    export_json,
    export_csv,
    export_excel,
    export_markdown
)

# Quick exports
export_json(products, "output.json", pretty=True)
export_csv(products, "output.csv")
export_excel(products, "output.xlsx")
export_markdown(products, "output.md")
```

## 🔗 Complete Example

```python
from playwright.async_api import async_playwright
from curllm_core.atomic_query import ProductQuery
from curllm_core.data_export import DataExporter

async def scrape_and_export():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://example.com/products")
        
        # Query products with atomic operations
        query = ProductQuery(page)
        result = await (
            query
            .find(".product-card")
            .extract_product(
                name_sel="h3.product-name",
                price_sel=".price",
                url_sel="a.product-link"
            )
            .filter_by_price(max_price=500)
            .limit(100)
            .execute()
        )
        
        # Export to multiple formats
        exporter = DataExporter(result.data, metadata=result.metadata)
        
        exporter.to_json("output/products.json", pretty=True)
        exporter.to_csv("output/products.csv")
        exporter.to_excel("output/products.xlsx")
        exporter.to_markdown("output/products.md")
        exporter.to_html("output/products.html")
        
        await browser.close()
        
        print(f"Exported {len(result.data)} products to multiple formats!")
```

## 🎨 Advanced Patterns

### Custom Transformers

```python
query = AtomicQuery(page)

# Complex transformation
result = await (
    query
    .find(".product")
    .map("""
        el => {
            const name = el.querySelector('h3')?.innerText || '';
            const priceText = el.querySelector('.price')?.innerText || '';
            const price = parseFloat(priceText.replace(/[^0-9.]/g, ''));
            const inStock = !el.classList.contains('out-of-stock');
            const rating = el.querySelector('.rating')?.getAttribute('data-rating') || 0;
            
            return {name, price, inStock, rating: parseFloat(rating)};
        }
    """)
    .filter("item => item.inStock && item.rating >= 4.0")
    .execute()
)
```

### Nested Data

```python
query = AtomicQuery(page)

result = await (
    query
    .find(".product")
    .map("""
        el => ({
            name: el.querySelector('h3').innerText,
            price: parseFloat(el.querySelector('.price').innerText),
            specs: Array.from(el.querySelectorAll('.spec')).map(spec => ({
                key: spec.querySelector('.key').innerText,
                value: spec.querySelector('.value').innerText
            })),
            reviews: {
                count: parseInt(el.querySelector('.review-count').innerText),
                rating: parseFloat(el.querySelector('.rating').innerText)
            }
        })
    """)
    .execute()
)
```

### Conditional Export

```python
exporter = DataExporter(products)

# Export based on count
if len(products) < 100:
    exporter.to_json("small_dataset.json")
else:
    exporter.to_csv("large_dataset.csv")  # CSV better for large datasets

# Export with timestamp
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
exporter.to_excel(f"products_{timestamp}.xlsx")
```

## 📈 Performance Tips

### 1. Limit Early

```python
# Good - limit before complex operations
query.find(".product").limit(100).map(complex_transformer)

# Bad - limit after (processes all then limits)
query.find(".product").map(complex_transformer).limit(100)
```

### 2. Filter Before Map

```python
# Good - filter first
query.find(".product").filter(simple_check).map(complex_extractor)

# Bad - map then filter
query.find(".product").map(complex_extractor).filter(check)
```

### 3. Use Quick Functions for Simple Cases

```python
# Good for simple extractions
names = await quick_extract_text(page, ".product", "h3")

# Overkill for simple cases
query = AtomicQuery(page)
result = await query.find(".product").extract_text("h3").execute()
names = result.data
```

## 🔧 Integration with Existing System

### Use in Extractors

```python
from curllm_core.llm_guided_extractor import LLMGuidedExtractor
from curllm_core.atomic_query import ProductQuery

class ImprovedExtractor(LLMGuidedExtractor):
    async def extract_products_atomic(self, container_sel, name_sel, price_sel, url_sel):
        """Use atomic query for extraction"""
        query = ProductQuery(self.page, self.run_logger)
        return await (
            query
            .find(container_sel)
            .extract_product(name_sel, price_sel, url_sel)
            .filter_by_price(max_price=150)  # From instruction
            .execute()
        )
```

### Export from Task Runner

```python
# In task_runner.py
from curllm_core.data_export import DataExporter

# After extraction
if result.get("data") and result["data"].get("products"):
    products = result["data"]["products"]
    exporter = DataExporter(products)
    
    # Auto-export to multiple formats
    exporter.to_json("output/products.json")
    exporter.to_csv("output/products.csv")
    exporter.to_markdown("output/products.md")
```

## 🎯 Benefits

### Atomization
- **Small functions**: Each does one thing well
- **Composable**: Chain operations
- **Reusable**: Use across projects
- **Testable**: Easy to unit test

### Multi-Format Export
- **Flexibility**: Choose format per use case
- **No vendor lock-in**: Data portable
- **Tool integration**: CSV for Excel, JSON for APIs
- **Human readable**: Markdown for docs

### Developer Experience
- **Fluent API**: Easy to read and write
- **Type hints**: Better IDE support
- **Quick functions**: Common cases covered
- **Metadata**: Track operations

## 📝 API Reference

### AtomicQuery

- `.find(selector)` - Find elements
- `.filter(predicate_js)` - Filter with JS function
- `.map(transformer_js)` - Transform with JS function
- `.extract_text(child_selector?)` - Extract text
- `.extract_attr(attr, child_selector?)` - Extract attribute
- `.limit(count)` - Limit results
- `.execute()` - Execute and return QueryResult

### ProductQuery (extends AtomicQuery)

- `.extract_product(name_sel, price_sel, url_sel)` - Extract product data
- `.filter_by_price(min_price?, max_price?)` - Filter by price range

### DataExporter

- `.to_json(file_path?, **kwargs)` - Export to JSON
- `.to_jsonl(file_path?)` - Export to JSONL
- `.to_csv(file_path?, **kwargs)` - Export to CSV
- `.to_xml(file_path?, **kwargs)` - Export to XML
- `.to_markdown(file_path?, **kwargs)` - Export to Markdown
- `.to_html(file_path?, **kwargs)` - Export to HTML
- `.to_yaml(file_path?)` - Export to YAML
- `.to_excel(file_path, **kwargs)` - Export to Excel (requires openpyxl)
- `.to_sqlite(db_path, table_name?)` - Export to SQLite

## 🚀 Next Steps

1. **Use atomic queries** w extractors
2. **Add export** do task runner
3. **Create presets** for common sites
4. **Add more formats** (Parquet, Avro, etc.)
5. **Stream processing** for large datasets
