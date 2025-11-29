# BQL (Browser Query Language) Examples

BQL provides a GraphQL-like syntax for precise web data extraction.

## Quick Start

```bash
# CLI with BQL
curllm --bql 'query { page(url: "https://example.com") { title: text(css: "h1") } }'
```

## BQL Syntax

```graphql
query ProductList {
    page(url: "https://shop.example.com") {
        products: select(css: ".product") {
            name: text(css: ".title")
            price: text(css: ".price")
            url: attr(css: "a", name: "href")
            image: attr(css: "img", name: "src")
        }
    }
}
```

## Files

| File | Description |
|------|-------------|
| `product_search.py` | Product extraction with BQL |
| `contact_form.py` | Form filling with BQL |
| `wordpress_login.py` | WordPress login with BQL |

## Python Example

```python
from curllm_core import CurllmExecutor

async def bql_extract():
    executor = CurllmExecutor()
    
    bql_query = '''
    query {
        page(url: "https://news.ycombinator.com") {
            items: select(css: ".titleline") {
                title: text(css: "a")
                url: attr(css: "a", name: "href")
            }
        }
    }
    '''
    
    result = await executor.execute_workflow(
        instruction=bql_query,
        use_bql=True
    )
    
    return result
```

## Related Documentation

- [BQL Guide](../../docs/v2/guides/Playwright_BQL.md)
- [Extraction Examples](../extraction/)
