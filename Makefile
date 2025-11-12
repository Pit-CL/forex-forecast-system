# ==========================================
# FOREX FORECAST SYSTEM - MAKEFILE
# ==========================================
# Common development and deployment tasks
# ==========================================

.PHONY: help install install-dev test test-unit test-integration test-e2e \
        test-pdf lint format clean docker-build docker-up docker-down \
        run-7d run-12m run-importer

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
DOCKER_COMPOSE := docker-compose

# Help target
help:  ## Show this help message
	@echo "Forex Forecast System - Available Commands"
	@echo "==========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ==========================================
# INSTALLATION
# ==========================================

install:  ## Install production dependencies
	$(PIP) install -r requirements.txt

install-dev:  ## Install development dependencies
	$(PIP) install -r requirements-dev.txt

install-all: install install-dev  ## Install all dependencies

# ==========================================
# TESTING
# ==========================================

test:  ## Run all tests
	$(PYTEST)

test-unit:  ## Run unit tests only
	$(PYTEST) -m unit tests/unit/

test-integration:  ## Run integration tests only
	$(PYTEST) -m integration tests/integration/

test-e2e:  ## Run end-to-end tests only
	$(PYTEST) -m e2e tests/e2e/

test-pdf:  ## Run PDF generation tests
	$(PYTEST) -m pdf tests/e2e/test_pdf_generation.py

test-fast:  ## Run fast tests only (skip slow tests)
	$(PYTEST) -m "not slow"

test-critical:  ## Run critical tests only
	$(PYTEST) -m critical

test-coverage:  ## Run tests with coverage report
	$(PYTEST) --cov-report=html --cov-report=term

# ==========================================
# CODE QUALITY
# ==========================================

lint:  ## Run linters (ruff, mypy)
	$(PYTHON) -m ruff check src/ tests/
	$(PYTHON) -m mypy src/

format:  ## Format code with black and isort
	$(PYTHON) -m black src/ tests/
	$(PYTHON) -m isort src/ tests/

format-check:  ## Check code formatting without changes
	$(PYTHON) -m black --check src/ tests/
	$(PYTHON) -m isort --check-only src/ tests/

# ==========================================
# DOCKER
# ==========================================

docker-build:  ## Build Docker images
	$(DOCKER_COMPOSE) build

docker-up:  ## Start all services
	$(DOCKER_COMPOSE) up -d

docker-down:  ## Stop all services
	$(DOCKER_COMPOSE) down

docker-logs:  ## Show Docker logs
	$(DOCKER_COMPOSE) logs -f

docker-test:  ## Run tests in Docker
	$(DOCKER_COMPOSE) run --rm forecaster-7d pytest

# ==========================================
# RUN SERVICES
# ==========================================

run-7d:  ## Run 7-day forecast
	$(PYTHON) -m services.forecaster_7d.cli run

run-12m:  ## Run 12-month forecast
	$(PYTHON) -m services.forecaster_12m.cli run

run-importer:  ## Run importer report
	$(PYTHON) -m services.importer_report.cli run

# ==========================================
# CLEANUP
# ==========================================

clean:  ## Clean build artifacts and cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf build

clean-all: clean  ## Clean everything including outputs
	rm -rf output/
	rm -rf data/cache/
	rm -rf logs/

# ==========================================
# DOCUMENTATION
# ==========================================

docs:  ## Build documentation
	cd docs && mkdocs build

docs-serve:  ## Serve documentation locally
	cd docs && mkdocs serve

# ==========================================
# UTILITIES
# ==========================================

check-env:  ## Check if .env file exists
	@if [ ! -f .env ]; then \
		echo "ERROR: .env file not found. Copy .env.example to .env and configure."; \
		exit 1; \
	else \
		echo ".env file found ✓"; \
	fi

setup:  ## Initial setup (copy .env.example, install deps)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file. Please edit it with your credentials."; \
	fi
	$(MAKE) install-all
	@echo "Setup complete! Edit .env and run 'make run-7d' to test."

validate:  ## Run all validation checks
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) test

# ==========================================
# CI/CD
# ==========================================

ci:  ## Run CI pipeline (format, lint, test)
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) test-coverage

pre-commit:  ## Run pre-commit checks
	pre-commit run --all-files
