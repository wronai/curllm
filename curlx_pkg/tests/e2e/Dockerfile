FROM python:3.11-slim

# System deps and Python packages
RUN apt-get update && apt-get install -y --no-install-recommends curl git jq \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -U pip \
    && true

WORKDIR /app

# Copy repo
COPY . /app

# Install curllm and curlx in editable mode and test deps
RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir -e ./curlx_pkg \
    && pip install --no-cache-dir playwright proxy.py requests \
    && playwright install chromium \
    && playwright install-deps chromium

ENV CURLLM_HEADLESS=true \
    CURLLM_API_PORT=8000 \
    CURLLM_WORKSPACE=/app/workspace

# Start a minimal Ollama stub on port 11434 to satisfy curllm CLI checks, then run API server
CMD ["bash", "-lc", "python - <<'PY'\nimport http.server, socketserver, json\nclass H(http.server.BaseHTTPRequestHandler):\n    def do_GET(self):\n        if self.path == '/api/tags':\n            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers();\n            self.wfile.write(b'{\\"models\\": []}')\n        else:\n            self.send_response(404); self.end_headers()\nwith socketserver.TCPServer(('0.0.0.0', 11434), H) as httpd:\n    import threading\n    t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()\n    import time; time.sleep(0.2)\n    import os\n    os.system('python -c \"from curllm_core.server import run_server; run_server()\"')\nPY"]
