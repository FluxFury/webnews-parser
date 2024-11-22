SOURCES := $(shell find . -name '*.py')

.DEFAULT_GOAL := help
.PY = poetry run

help: ## Display this help screen
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
.PHONY: help

install: ## Install project dependencies
	poetry install --with dev --no-interaction --no-ansi --no-root
.PHONY: install

lint: ## Lint the source code
	$(.PY) ruff check --config pyproject.toml --no-fix $(SOURCES)
.PHONY: lint

format: ## Format the source code
	$(.PY) ruff check --config pyproject.toml --fix $(SOURCES)
	$(.PY) ruff format --config pyproject.toml $(SOURCES)
.PHONY: format