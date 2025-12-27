.PHONY: all build run stop dev clean test lint format help

APP_NAME := sub-grabber
PORT := 8000

# Default target
all: help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the Docker image (production ready)
	docker build -t $(APP_NAME) .

run: ## Run the Docker container
	docker run -d --name $(APP_NAME) -p $(PORT):8000 $(APP_NAME)
	@echo "\n🚀 API is running at http://localhost:$(PORT)"
	@echo "📝 Swagger UI: http://localhost:$(PORT)/docs"

stop: ## Stop and remove the Docker container
	docker stop $(APP_NAME) || true
	docker rm $(APP_NAME) || true

logs: ## Show logs from the running container
	docker logs -f $(APP_NAME)

dev: ## Run locally with uv (hot reload)
	uv run uvicorn main:app --app-dir src --host 0.0.0.0 --port $(PORT) --reload

test: ## Run tests
	uv run pytest

lint: ## Run linter
	uv run ruff check src/

format: ## Format code
	uv run ruff format src/

clean: ## Clean up temporary files
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +

update-dict: ## Download the latest JMdict dictionary
	./scripts/update_jmdict.sh
