# STR QC Platform — developer entrypoints
# Usage: make <target>

PY := python3
WEB := apps/web
DB_PATH ?= ./str_qc.sqlite

.PHONY: help install install-web migrate seed test lint api web dev clean

help: ## List targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install published Strands packages + editable project packages
	pip install "strands-agents==1.48.0" "strands-agents-tools==0.8.4" "strands-fun-tools==0.4.0" "strands-google==0.1.0"
	pip install -e "packages/shared[dev]"
	pip install -e "packages/db[dev]"
	pip install -e "apps/api[dev]"

install-web: ## Install web app dependencies
	cd $(WEB) && pnpm install

migrate: ## Apply database migrations
	$(PY) -m strqc_db.migrate --db-path $(DB_PATH)

seed: ## Load local dev fixtures (small Big Bear cluster)
	$(PY) -m strqc_db.seed --db-path $(DB_PATH)

test: ## Run all Python unit tests
	$(PY) -m pytest packages/shared/tests packages/db/tests apps/api/tests -q

lint: ## Lint all Python packages
	$(PY) -m ruff check packages apps/api

api: ## Run the API service (dev)
	$(PY) -m uvicorn strqc_api.main:app --reload --port 8000

web: ## Run the Next.js dev server
	cd $(WEB) && pnpm dev

dev: ## API + web together (requires two shells; convenience hint)
	@echo "run 'make api' and 'make web' in separate shells"

clean: ## Remove local dev database and caches
	rm -f $(DB_PATH) $(DB_PATH)-wal $(DB_PATH)-shm
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
