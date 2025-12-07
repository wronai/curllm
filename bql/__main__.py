"""BQL module entry point for testing"""

import json

from bql.parser.bql_parser import BQLParser
from bql.examples import EXAMPLE_QUERIES


def main():
    """Test parser with example queries"""
    parser = BQLParser()
    
    for name, query in EXAMPLE_QUERIES.items():
        print(f"\n=== {name} ===")
        try:
            parsed = parser.parse(query)
            print(json.dumps(parsed, indent=2))
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
