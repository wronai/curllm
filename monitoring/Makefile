# Makefile for website monitoring with curllm

.PHONY: help run install remove edit-env

help:
	@echo "Monitoring with curllm"
	@echo "Targets:"
	@echo "  make run        - Run monitoring once (uses monitoring/.env)"
	@echo "  make install    - Install cron job (every 3 hours)"
	@echo "  make remove     - Remove cron job"
	@echo "  make edit-env   - Create/open monitoring/.env"

run:
	@chmod +x website_monitor.sh
	@./website_monitor.sh run

install:
	@chmod +x website_monitor.sh
	@./website_monitor.sh install

remove:
	@chmod +x website_monitor.sh
	@./website_monitor.sh remove

edit-env:
	@[ -f .env ] || cp .env.example .env
	@${EDITOR:-nano} .env
