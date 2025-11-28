"""
BQL Component - Browser Query Language

A GraphQL-inspired query language for browser automation and data extraction.

Usage:
    from curllm_core.streamware.components.bql import BQLParser, BQLExecutor

    parser = BQLParser()
    parsed = parser.parse('''
        query {
            page(url: "https://example.com") {
                title
                select(css: ".product") {
                    name: text(css: ".title")
                    price: text(css: ".price")
                }
            }
        }
    ''')
    
    executor = BQLExecutor(browser_context)
    result = await executor.execute(query)
"""

from .parser import BQLParser, BQLNode, QueryType
from .executor import BQLExecutor
from .utils import parse_bql, normalize_query

__all__ = [
    'BQLParser',
    'BQLExecutor',
    'BQLNode',
    'QueryType',
    'parse_bql',
    'normalize_query'
]
