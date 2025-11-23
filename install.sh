#!/bin/bash
#============================================================================
# install.sh - curllm Installation Script
# Automated setup for browser automation with local LLM
#============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       curllm Installation Script           ║${NC}"
echo -e "${BLUE}║   Browser Automation with Local LLM        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
fi

echo -e "${BLUE}[1/7] Checking system requirements...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Check GPU (optional)
GPU_AVAILABLE=false
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1)
    echo -e "${GREEN}✓ GPU detected: $GPU_INFO${NC}"
    GPU_AVAILABLE=true
else
    echo -e "${YELLOW}⚠ No NVIDIA GPU detected (CPU mode will be slower)${NC}"
fi

# Check Docker (optional)
DOCKER_AVAILABLE=false
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker is installed${NC}"
    DOCKER_AVAILABLE=true
else
    echo -e "${YELLOW}⚠ Docker not found (Browserless features unavailable)${NC}"
fi

echo ""
echo -e "${BLUE}[2/7] Installing Ollama...${NC}"

# Install Ollama
if ! command -v ollama &> /dev/null; then
    echo "Downloading Ollama installer..."
    if [[ "$OS" == "linux" ]]; then
        curl -fsSL https://ollama.ai/install.sh | sh
    elif [[ "$OS" == "macos" ]]; then
        echo "Please download Ollama from: https://ollama.ai/download/mac"
        echo "Press Enter when installation is complete..."
        read
    else
        echo "Please download Ollama from: https://ollama.ai/download/windows"
        echo "Press Enter when installation is complete..."
        read
    fi
else
    echo -e "${GREEN}✓ Ollama is already installed${NC}"
fi

echo ""
echo -e "${BLUE}[3/7] Setting up Python environment...${NC}"

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python packages..."
pip install -r requirements.txt
echo -e "${GREEN}✓ Python packages installed${NC}"

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium > /dev/null 2>&1
playwright install-deps chromium > /dev/null 2>&1 || true
echo -e "${GREEN}✓ Playwright browsers installed${NC}"

echo ""
echo -e "${BLUE}[4/7] Downloading LLM models...${NC}"

# Start Ollama service
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama service..."
    ollama serve > /tmp/ollama_install.log 2>&1 &
    sleep 3
fi

# Select and download model based on available VRAM
if [ "$GPU_AVAILABLE" = true ]; then
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    echo "Detected VRAM: ${VRAM}MB"
    
    if [ "$VRAM" -ge 8000 ]; then
        echo "Pulling qwen2.5:7b (recommended for 8GB+ VRAM)..."
        ollama pull qwen2.5:7b
        DEFAULT_MODEL="qwen2.5:7b"
    elif [ "$VRAM" -ge 6000 ]; then
        echo "Pulling mistral:7b-instruct-q4_0 (for 6GB VRAM)..."
        ollama pull mistral:7b-instruct-q4_0
        DEFAULT_MODEL="mistral:7b-instruct-q4_0"
    else
        echo "Pulling phi3:mini (for <6GB VRAM)..."
        ollama pull phi3:mini
        DEFAULT_MODEL="phi3:mini"
    fi
else
    echo "Pulling llama3.2:3b (CPU-optimized)..."
    ollama pull llama3.2:3b
    DEFAULT_MODEL="llama3.2:3b"
fi

echo -e "${GREEN}✓ Model $DEFAULT_MODEL downloaded${NC}"

echo ""
echo -e "${BLUE}[5/7] Setting up configuration...${NC}"

# Create config directory
mkdir -p ~/.config/curllm

# Create configuration file
cat > ~/.config/curllm/config.yml << EOF
# curllm Configuration
model: $DEFAULT_MODEL
ollama_host: http://localhost:11434
api_port: 8000
max_steps: 20
screenshot_dir: ./screenshots

# Features
visual_mode: false
stealth_mode: false
captcha_solver: false

# Browserless (if Docker available)
use_browserless: $DOCKER_AVAILABLE
browserless_url: ws://localhost:3000

# Performance
num_ctx: 8192
num_predict: 512
temperature: 0.3
top_p: 0.9
EOF

echo -e "${GREEN}✓ Configuration file created${NC}"

echo ""
echo -e "${BLUE}[6/7] Installing curllm command...${NC}"

# Make scripts executable
chmod +x curllm
chmod +x curllm_server.py

# Create symlink for global access
sudo -n ln -sf $(pwd)/curllm /usr/local/bin/curllm 2>/dev/null || \
    ln -sf $(pwd)/curllm ~/.local/bin/curllm 2>/dev/null || \
    echo -e "${YELLOW}⚠ Could not create global symlink. Add $(pwd) to PATH${NC}"

echo -e "${GREEN}✓ curllm command installed${NC}"

# Create .env from example if missing and set defaults
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        touch .env
    fi
fi

# Ensure CURLLM_MODEL is set to the downloaded default model
if grep -q '^CURLLM_MODEL=' .env; then
    sed -i "s/^CURLLM_MODEL=.*/CURLLM_MODEL=${DEFAULT_MODEL}/" .env
else
    echo "CURLLM_MODEL=${DEFAULT_MODEL}" >> .env
fi

# Optional: Setup Docker services
if [ "$DOCKER_AVAILABLE" = true ]; then
    echo ""
    echo -e "${BLUE}[7/7] Setting up Docker services...${NC}"
    
    if [ -t 0 ]; then
        read -p "Would you like to start Browserless container? (y/n) " -n 1 -r || true
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            BROWSERLESS_PORT_ENV=${BROWSERLESS_PORT:-3000}
            while ss -ltn | grep -q ":$BROWSERLESS_PORT_ENV\\b"; do BROWSERLESS_PORT_ENV=$((BROWSERLESS_PORT_ENV+1)); done
            REDIS_PORT_ENV=${REDIS_PORT:-6379}
            while ss -ltn | grep -q ":$REDIS_PORT_ENV\\b"; do REDIS_PORT_ENV=$((REDIS_PORT_ENV+1)); done
            echo $BROWSERLESS_PORT_ENV > /tmp/curllm_browserless_port
            echo $REDIS_PORT_ENV > /tmp/curllm_redis_port
            # Persist selected ports to .env
            if grep -q '^BROWSERLESS_PORT=' .env; then
                sed -i "s/^BROWSERLESS_PORT=.*/BROWSERLESS_PORT=${BROWSERLESS_PORT_ENV}/" .env
            else
                echo "BROWSERLESS_PORT=${BROWSERLESS_PORT_ENV}" >> .env
            fi
            if grep -q '^REDIS_PORT=' .env; then
                sed -i "s/^REDIS_PORT=.*/REDIS_PORT=${REDIS_PORT_ENV}/" .env
            else
                echo "REDIS_PORT=${REDIS_PORT_ENV}" >> .env
            fi
            if grep -q '^BROWSERLESS_URL=' .env; then
                sed -i "s#^BROWSERLESS_URL=.*#BROWSERLESS_URL=ws://localhost:${BROWSERLESS_PORT_ENV}#" .env
            else
                echo "BROWSERLESS_URL=ws://localhost:${BROWSERLESS_PORT_ENV}" >> .env
            fi
            BROWSERLESS_PORT=$BROWSERLESS_PORT_ENV REDIS_PORT=$REDIS_PORT_ENV docker compose up -d browserless redis 2>/dev/null || \
            BROWSERLESS_PORT=$BROWSERLESS_PORT_ENV REDIS_PORT=$REDIS_PORT_ENV docker-compose up -d browserless redis
            echo -e "${GREEN}✓ Docker services started on ports browserless:$BROWSERLESS_PORT_ENV redis:$REDIS_PORT_ENV${NC}"
        fi
    else
        echo -e "${YELLOW}Non-interactive shell, skipping Docker setup${NC}"
    fi
else
    echo ""
    echo -e "${BLUE}[7/7] Skipping Docker setup (not installed)${NC}"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}        Installation Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Quick Start:${NC}"
echo "1. Start services:    curllm --start-services"
echo "2. Check status:      curllm --status"
echo "3. Run example:       curllm 'https://example.com' -d 'extract all links'"
echo ""
echo -e "${BLUE}Model:${NC} $DEFAULT_MODEL"
echo -e "${BLUE}Config:${NC} ~/.config/curllm/config.yml"
echo -e "${BLUE}Logs:${NC} /tmp/curllm.log"
echo ""
echo -e "${YELLOW}For GPU acceleration, ensure CUDA is properly configured${NC}"
echo -e "${YELLOW}For CAPTCHA solving, set CAPTCHA_API_KEY environment variable${NC}"
