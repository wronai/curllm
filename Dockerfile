FROM python:3.11-slim

# Install minimal system dependencies; Playwright will install browser deps
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    tesseract-ocr \
    libtesseract-dev \
    fonts-liberation \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy application files
COPY curllm_server.py .
COPY curllm /usr/local/bin/curllm
RUN chmod +x /usr/local/bin/curllm

# Create necessary directories
RUN mkdir -p /app/screenshots /app/logs /app/workspace/storage

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    CURLLM_SCREENSHOT_DIR=/app/screenshots

# Run the server
CMD ["python", "curllm_server.py"]
