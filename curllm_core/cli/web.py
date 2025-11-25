#!/usr/bin/env python3
"""Web client CLI for curllm."""

import sys
import os

def main():
    """Main entry point for curllm-web command."""
    # Import the actual web module
    try:
        from curllm_web import main as web_main
        sys.exit(web_main())
    except ImportError as e:
        print(f"Error: Could not import curllm_web: {e}", file=sys.stderr)
        print("\nMake sure curllm is properly installed:", file=sys.stderr)
        print("  pip install -e .", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error starting curllm-web: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
