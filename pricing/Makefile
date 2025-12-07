# Price Comparator - Makefile
# Convenience commands for development and deployment

.PHONY: help build up down logs shell clean dev test

# Default target
help:
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║           🏷️  Price Comparator - Commands                    ║"
	@echo "╠══════════════════════════════════════════════════════════════╣"
	@echo "║  make build     - Build Docker image                         ║"
	@echo "║  make up        - Start service (Docker)                     ║"
	@echo "║  make up-ollama - Start with local Ollama                    ║"
	@echo "║  make down      - Stop service                               ║"
	@echo "║  make logs      - View logs                                  ║"
	@echo "║  make shell     - Open shell in container                    ║"
	@echo "║  make dev       - Run locally (development)                  ║"
	@echo "║  make clean     - Remove containers and images               ║"
	@echo "║  make test      - Test the API                               ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"

# Build Docker image
build:
	docker compose build

# Start service
up:
	docker compose up --build -d
	@echo ""
	@echo "✅ Price Comparator started!"
	@echo "   Open: http://localhost:8080"
	@echo ""

# Start with Ollama
up-ollama:
	docker compose --profile with-ollama up --build -d
	@echo ""
	@echo "✅ Price Comparator + Ollama started!"
	@echo "   Open: http://localhost:8080"
	@echo ""
	@echo "   Pull a model: docker exec ollama ollama pull llama3.2"
	@echo ""

# Stop service
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# Open shell in container
shell:
	docker compose exec price-comparator /bin/bash

# Run locally for development
dev:
	@echo "Starting development server..."
	cd .. && python pricing/app.py

# Clean up
clean:
	docker compose down -v --rmi local
	@echo "✅ Cleaned up containers and images"

# Test the API
test:
	@echo "Testing health endpoint..."
	curl -s http://localhost:8080/health | python -m json.tool
	@echo ""
	@echo "Testing extraction (example)..."
	@echo "Use: make test-compare to run a full comparison test"

test-compare:
	@echo "Running comparison test..."
	curl -X POST http://localhost:8080/api/compare \
		-H "Content-Type: application/json" \
		-d '{ \
			"urls": ["https://example.com"], \
			"extraction_prompt": "Extract the main heading and any links", \
			"comparison_prompt": "Summarize the content", \
			"stealth": false \
		}' | python -m json.tool

# Install dependencies locally
install:
	cd .. && pip install -r requirements.txt
	pip install -r requirements.txt
	playwright install chromium

# Create .env from example
env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env from .env.example"; \
		echo "   Edit .env to configure your settings"; \
	else \
		echo "⚠️  .env already exists"; \
	fi
