def parse_bql(query: str) -> str:
    if "query" in query and "{" in query:
        return f"Extract the following fields from the page: {query}"
    return query
