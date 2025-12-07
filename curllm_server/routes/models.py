"""Models endpoint for listing Ollama models"""

from flask import Blueprint, jsonify

from curllm_server.config import config

models_bp = Blueprint('models', __name__)


@models_bp.route('/api/models', methods=['GET'])
def list_models():
    """List available Ollama models"""
    try:
        import requests
        response = requests.get(f"{config.ollama_host}/api/tags")
        return jsonify(response.json())
    except Exception:
        return jsonify({"error": "Failed to fetch models"}), 500
