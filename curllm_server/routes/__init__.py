"""Routes module for Flask endpoints"""

from curllm_server.routes.health import health_bp
from curllm_server.routes.execute import execute_bp
from curllm_server.routes.models import models_bp
from curllm_server.routes.screenshot import screenshot_bp

__all__ = ['health_bp', 'execute_bp', 'models_bp', 'screenshot_bp']
