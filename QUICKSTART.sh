#!/bin/bash
# QUICK START - curllm
# Copy and run these commands to get started immediately

echo "================================================"
echo "       curllm - Quick Start Guide"
echo "   Browser Automation with Local LLM (8GB GPU)"
echo "================================================"
echo ""

# 1. Basic Installation (5 minutes)
echo "[Step 1] Installing Ollama..."
curl -fsSL https://ollama.ai/install.sh | sh

echo "[Step 2] Installing Python dependencies..."
pip3 install browser-use langchain langchain-ollama playwright flask flask-cors

echo "[Step 3] Installing Playwright browser..."
playwright install chromium

echo "[Step 4] Pulling optimized model for 8GB GPU..."
ollama pull qwen2.5:7b

# 2. Start Services
echo "[Step 5] Starting services..."
ollama serve &
sleep 3
python3 curllm_server.py &
sleep 3

# 3. Test Examples
echo ""
echo "================================================"
echo "READY! Try these examples:"
echo "================================================"
echo ""

echo "1. Simple extraction:"
echo '   curllm "https://example.com" -d "extract all links"'
echo ""

echo "2. Form filling with stealth mode:"
echo '   curllm --visual --stealth \\'
echo '     -d "fill contact form: name=John, email=john@test.com" \\'
echo '     https://example.com/contact'
echo ""

echo "3. Login with 2FA:"
echo '   curllm -X POST --visual --captcha \\'
echo '     -d "{"task":"login","user":"john","pass":"secret","2fa":"123456"}" \\'
echo '     https://secure-app.com'
echo ""

echo "4. BQL structured extraction:"
echo '   curllm --bql -d "query { page(url: \"https://news.site.com\") {'
echo '     articles: select(css: \".article\") {'
echo '       title: text(css: \"h2\")'
echo '       summary: text(css: \".summary\")'
echo '     }}}"'
echo ""

echo "================================================"
echo "For GPU status: nvidia-smi"
echo "For service status: curllm --status"
echo "For help: curllm --help"
echo "================================================"
