# Bulk Form Filler - Makefile

.PHONY: help build up down logs dev

help:
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║           📝 Bulk Form Filler - Commands                     ║"
	@echo "╠══════════════════════════════════════════════════════════════╣"
	@echo "║  make build  - Build Docker image                            ║"
	@echo "║  make up     - Start service (Docker)                        ║"
	@echo "║  make down   - Stop service                                  ║"
	@echo "║  make logs   - View logs                                     ║"
	@echo "║  make dev    - Run locally                                   ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"

build:
	docker compose build

up:
	docker compose up --build -d
	@echo "✅ Form Filler started: http://localhost:8081"

down:
	docker compose down

logs:
	docker compose logs -f

dev:
	cd .. && python forms/app.py
