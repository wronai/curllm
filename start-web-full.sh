#!/bin/bash
#============================================================================
# start-web-full.sh - Uruchamia curllm API + Web Client
#============================================================================

echo "🚀 Uruchamianie curllm w trybie webowym..."
echo ""

# Kolory
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Sprawdź czy Ollama działa
echo -e "${BLUE}[1/3]${NC} Sprawdzam Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Ollama działa"
else
    echo -e "${YELLOW}⚠${NC} Ollama nie działa. Uruchamiam..."
    ollama serve > /dev/null 2>&1 &
    sleep 2
fi

# Uruchom serwer API w tle
echo -e "${BLUE}[2/3]${NC} Uruchamiam serwer API (curllm_server.py)..."
python curllm_server.py > logs/api-server.log 2>&1 &
API_PID=$!
echo -e "${GREEN}✓${NC} Serwer API uruchomiony (PID: $API_PID)"
echo "   Logi: logs/api-server.log"
sleep 3

# Sprawdź czy API odpowiada
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API odpowiada na http://localhost:8000"
else
    echo -e "${YELLOW}⚠${NC} API nie odpowiada, może potrzebować więcej czasu..."
fi

# Uruchom klienta webowego
echo -e "${BLUE}[3/3]${NC} Uruchamiam klienta webowego..."
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     curllm Web Client jest gotowy!         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "🌐 Otwórz przeglądarkę: ${BLUE}http://localhost:5000${NC}"
echo ""
echo -e "📊 API Server: ${BLUE}http://localhost:8000${NC}"
echo -e "📋 API Health: ${BLUE}http://localhost:8000/health${NC}"
echo ""
echo -e "${YELLOW}Aby zatrzymać, naciśnij Ctrl+C${NC}"
echo ""

# Uruchom klienta webowego (blokujący)
curllm-web

# Cleanup po Ctrl+C
echo ""
echo "Zatrzymywanie serwerów..."
kill $API_PID 2>/dev/null
echo "Zakończono"
