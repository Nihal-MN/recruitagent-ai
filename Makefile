.DEFAULT_GOAL := help
SHELL := /bin/bash

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Build + start the full stack (db, api, web)
	docker compose up --build -d

down: ## Stop the stack (keeps the database volume)
	docker compose down

seed: ## (Re)seed the synthetic demo dataset — 20 candidates / 5 jobs
	docker compose exec api uv run --no-dev python -m app.seed --reset

reset: ## Stop the stack and DELETE the database volume
	docker compose down -v

logs: ## Tail all service logs
	docker compose logs -f --tail=50

health: ## Print the health endpoint
	curl -s localhost:$${API_PORT:-8000}/api/v1/health | python3 -m json.tool

test: ## Backend tests (incl. evals + MCP smoke)
	cd backend && uv run pytest

test-frontend: ## Frontend unit tests
	cd frontend && npm test

lint: ## Lint backend + frontend
	cd backend && uv run ruff check app tests
	cd frontend && npm run lint && npm run typecheck

mcp: ## Run the MCP server locally (stdio transport)
	cd backend && uv run python -m app.mcp_server
