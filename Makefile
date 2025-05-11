.PHONY: format lint lint-fix help

format:
	ruff format .
	ruff check --fix .

lint:
	ruff check .
	ruff format --diff

help:
	@echo "Available commands:"
	@echo "  make format    - Format code with ruff"
	@echo "  make lint      - Check code with ruff"
	@echo "  make lint-fix  - Fix linting issues with ruff"
