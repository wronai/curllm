"""
BQL - Browser Query Language module
GraphQL-like syntax for browser automation and data extraction
"""

from bql.types.query_type import QueryType
from bql.types.bql_node import BQLNode
from bql.parser.bql_parser import BQLParser
from bql.executor.bql_executor import BQLExecutor
from bql.examples import EXAMPLE_QUERIES

__all__ = [
    'QueryType',
    'BQLNode',
    'BQLParser',
    'BQLExecutor',
    'EXAMPLE_QUERIES',
]
