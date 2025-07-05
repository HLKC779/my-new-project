.PHONY: help install start stop restart test clean lint format db-up db-down db-migrate db-reset logs

# Show help
help:
	@echo "Available commands:"
	@echo "  install     Install all dependencies"
	@echo "  start       Start all services"
	@echo "  stop        Stop all services"
	@echo "  restart     Restart all services"
	@echo "  test        Run all tests"
	@echo "  test-backend  Run backend tests"
	@echo "  test-frontend Run frontend tests"
	@echo "  lint        Run linters"
	@echo "  format      Format code"
	@echo "  db-up       Start database services"
	@echo "  db-down     Stop database services"
	@echo "  db-migrate  Run database migrations"
	@echo "  db-reset    Reset database (WARNING: deletes all data!)"
	@echo "  logs        View logs"

# Install all dependencies
install:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml build
	@echo "Installation complete! Run 'make start' to start the application."

# Start all services
start:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Stop all services
stop:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml down

# Restart all services
restart: stop start

# Run all tests
test: test-backend test-frontend

# Run backend tests
test-backend:
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit test-backend

# Run frontend tests
test-frontend:
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit test-frontend

# Run linters
lint:
	docker-compose -f docker-compose.override.yml exec backend black --check app tests
	docker-compose -f docker-compose.override.yml exec backend isort --check-only app tests
	docker-compose -f docker-compose.override.yml exec backend flake8 app tests
	docker-compose -f docker-compose.override.yml exec backend mypy app

# Format code
format:
	docker-compose -f docker-compose.override.yml exec backend black app tests
	docker-compose -f docker-compose.override.yml exec backend isort app tests

# Start database services
db-up:
	docker-compose -f docker-compose.yml up -d db pgadmin

# Stop database services
db-down:
	docker-compose -f docker-compose.yml stop db pgadmin

# Run database migrations
db-migrate:
	docker-compose -f docker-compose.override.yml exec backend alembic upgrade head

# Reset database (WARNING: deletes all data!)
db-reset:
	@echo "WARNING: This will delete all data in the database!"
	@read -p "Are you sure you want to continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose -f docker-compose.override.yml exec backend bash -c "rm -f /app/alembic/versions/*.py && \
		alembic revision --autogenerate -m 'Initial migration' && \
		alembic upgrade head"; \
	fi

# View logs
logs:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml logs -f
