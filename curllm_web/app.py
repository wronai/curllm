"""Flask application setup for curllm_web"""

import logging

from flask import Flask
from flask_cors import CORS

from curllm_web.config import UPLOAD_FOLDER, MAX_CONTENT_LENGTH
from curllm_web.routes.main import main_bp
from curllm_web.routes.prompts import prompts_bp
from curllm_web.routes.execute import execute_bp
from curllm_web.routes.upload import upload_bp
from curllm_web.routes.logs import logs_bp
from curllm_web.routes.static import static_bp
from curllm_web.routes.health import health_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(prompts_bp)
app.register_blueprint(execute_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(static_bp)
app.register_blueprint(health_bp)
