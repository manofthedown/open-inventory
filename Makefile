.PHONY: dev test lint types run help

help:
	@echo "open-inventory development commands:"
	@echo "  make dev      - Install dev dependencies in .venv"
	@echo "  make test     - Run pytest suite"
	@echo "  make lint     - Run ruff linter"
	@echo "  make types    - Run mypy type checker"
	@echo "  make run      - Run dev server with --reload"
	@echo "  make init     - Initialize database"

dev:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check inv tests

types:
	uv run mypy inv

run:
	uv run inventory run --reload

init:
	uv run inventory init
