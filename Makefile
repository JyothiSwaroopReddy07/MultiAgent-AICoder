.PHONY: help build up down restart logs clean scale-workers deploy

help:
	@echo "AI Coder - Docker Commands"
	@echo ""
	@echo "Development:"
	@echo "  make build          - Build all Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs from all services"
	@echo "  make logs-api       - View backend API logs"
	@echo "  make logs-worker    - View agent worker logs"
	@echo "  make clean          - Remove all containers and volumes"
	@echo ""
	@echo "Scaling:"
	@echo "  make scale-workers N=5    - Scale agent workers to N instances"
	@echo "  make scale-api N=3        - Scale backend API to N instances"
	@echo ""
	@echo "Production:"
	@echo "  make prod-up        - Start production environment"
	@echo "  make prod-down      - Stop production environment"
	@echo "  make deploy         - Deploy with zero-downtime"
	@echo ""
	@echo "Monitoring:"
	@echo "  make status         - Check service status"
	@echo "  make health         - Check health of all services"
	@echo "  make monitor-up     - Start with monitoring tools"

# Development commands
build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "Frontend: http://localhost:3002"
	@echo "Backend API: http://localhost:8500"
	@echo "API Docs: http://localhost:8500/docs"
	@echo "Nginx Gateway: http://localhost:9080"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f backend-api

logs-worker:
	docker-compose logs -f agent-worker

logs-nginx:
	docker-compose logs -f nginx-gateway

# Scaling commands
scale-workers:
	@if [ -z "$(N)" ]; then echo "Usage: make scale-workers N=5"; exit 1; fi
	docker-compose up -d --scale agent-worker=$(N)

scale-api:
	@if [ -z "$(N)" ]; then echo "Usage: make scale-api N=3"; exit 1; fi
	docker-compose up -d --scale backend-api=$(N)

# Production commands
prod-up:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

deploy:
	@echo "Deploying with zero-downtime..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --scale backend-api=3 --scale agent-worker=5

# Monitoring commands
monitor-up:
	docker-compose --profile monitoring up -d
	@echo "Redis Commander: http://localhost:8082"

status:
	docker-compose ps

health:
	@echo "Checking service health..."
	@curl -s http://localhost:9080/health || echo "Gateway: DOWN"
	@curl -s http://localhost:8500/ || echo "Backend: DOWN"

# Cleanup
clean:
	docker-compose down -v
	docker system prune -f

clean-all:
	docker-compose down -v --rmi all
	docker system prune -af --volumes

# Development helpers
shell-api:
	docker-compose exec backend-api /bin/bash

shell-worker:
	docker-compose exec agent-worker /bin/bash

shell-redis:
	docker-compose exec redis redis-cli

# Testing
test:
	docker-compose exec backend-api pytest tests/

# Build for specific services
build-backend:
	docker-compose build backend-api

build-worker:
	docker-compose build agent-worker

build-frontend:
	docker-compose build frontend

