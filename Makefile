.PHONY: help dev prod build up down logs clean migrate backup restore health

# Default target
help:
	@echo "Multi-Platform Video Scheduler - Make Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Start development environment"
	@echo "  make dev-logs         - View development logs"
	@echo "  make dev-down         - Stop development environment"
	@echo ""
	@echo "Production:"
	@echo "  make prod             - Start production environment"
	@echo "  make prod-build       - Build production containers"
	@echo "  make prod-logs        - View production logs"
	@echo "  make prod-down        - Stop production environment"
	@echo "  make prod-restart     - Restart production services"
	@echo ""
	@echo "Database:"
	@echo "  make migrate          - Run database migrations"
	@echo "  make migrate-create   - Create new migration"
	@echo "  make backup           - Backup database"
	@echo "  make restore          - Restore database from backup"
	@echo ""
	@echo "Monitoring:"
	@echo "  make health           - Check service health"
	@echo "  make logs             - View all logs"
	@echo "  make stats            - View container stats"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            - Remove stopped containers"
	@echo "  make clean-all        - Remove containers and volumes (CAUTION)"
	@echo "  make scale-workers    - Scale Celery workers (N=number)"

# Development commands
dev:
	docker-compose up -d
	@echo "Development environment started"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"

dev-logs:
	docker-compose logs -f

dev-down:
	docker-compose down

# Production commands
prod:
	docker-compose -f docker-compose.prod.yml up -d
	@echo "Production environment started"
	@echo "Run 'make health' to check service status"

prod-build:
	docker-compose -f docker-compose.prod.yml build --no-cache

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

prod-down:
	docker-compose -f docker-compose.prod.yml down

prod-restart:
	docker-compose -f docker-compose.prod.yml restart

# Database commands
migrate:
	docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	docker-compose -f docker-compose.prod.yml exec backend alembic revision --autogenerate -m "$$msg"

backup:
	@mkdir -p backups
	docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres video_scheduler > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in backups/"

restore:
	@read -p "Enter backup file path: " file; \
	docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres video_scheduler < $$file

# Monitoring commands
health:
	@echo "Checking service health..."
	@docker-compose -f docker-compose.prod.yml ps
	@echo ""
	@echo "Backend health:"
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "Backend not responding"

logs:
	docker-compose -f docker-compose.prod.yml logs --tail=100 -f

stats:
	docker stats

# Maintenance commands
clean:
	docker-compose -f docker-compose.prod.yml down
	docker system prune -f

clean-all:
	@echo "WARNING: This will remove all containers and volumes!"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker-compose -f docker-compose.prod.yml down -v; \
		docker system prune -af; \
	fi

scale-workers:
	@read -p "Enter number of workers: " n; \
	docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=$$n

# Quick deployment
deploy: prod-build migrate prod
	@echo "Deployment complete!"
	@make health

# Update application
update:
	git pull origin main
	docker-compose -f docker-compose.prod.yml build
	docker-compose -f docker-compose.prod.yml up -d --no-deps backend celery-worker frontend
	docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
	@echo "Application updated!"
