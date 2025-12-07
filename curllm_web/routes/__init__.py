"""Routes module for curllm_web"""

from curllm_web.routes.main import main_bp
from curllm_web.routes.prompts import prompts_bp
from curllm_web.routes.execute import execute_bp
from curllm_web.routes.upload import upload_bp
from curllm_web.routes.logs import logs_bp
from curllm_web.routes.static import static_bp
from curllm_web.routes.health import health_bp

__all__ = [
    'main_bp', 'prompts_bp', 'execute_bp', 
    'upload_bp', 'logs_bp', 'static_bp', 'health_bp'
]
