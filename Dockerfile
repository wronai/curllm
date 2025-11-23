FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    tesseract-ocr \
    libtesseract-dev \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    libxtst6 \
    xdg-utils \
    fonts-liberation \
    libgbm1 \
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
RUN mkdir -p ./screenshots /var/log/curllm

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Run the server
CMD ["python", "curllm_server.py"]
