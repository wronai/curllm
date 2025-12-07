"""Main entry point for curllm server"""

import logging
import os

from curllm_server.config import config
from curllm_server.app import app

logger = logging.getLogger(__name__)


def main():
    """Run the curllm API server"""
    try:
        from curllm_core.server import run_server as _run_server
        _run_server()
    except Exception:
        # Fallback to legacy in-file server start if package import fails
        import requests
        try:
            requests.get(f"{config.ollama_host}/api/tags")
            logger.info(f"✓ Connected to Ollama at {config.ollama_host}")
        except Exception:
            logger.warning(f"✗ Cannot connect to Ollama at {config.ollama_host}")
            logger.warning("  The API server will start, but requests may fail until Ollama is running (run: 'ollama serve').")
        logger.info(f"Starting curllm API server on port {config.api_port}...")
        logger.info(f"Model: {config.ollama_model}")
        logger.info(f"Visual mode: Available")
        logger.info(f"Stealth mode: Available")
        logger.info(f"CAPTCHA solver: {'Enabled' if os.getenv('CAPTCHA_API_KEY') else 'Local OCR only'}")
        app.run(host='0.0.0.0', port=config.api_port, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
