.PHONY: help install lint test models smoke bench report

help:
	@echo "install  install dependencies (uv)"
	@echo "lint     ruff check + format check"
	@echo "test     pytest (offline, no API calls)"
	@echo "models   print what e-INFRA has deployed right now"
	@echo "smoke    3 sessions x 2 models, cheap end-to-end check"
	@echo "bench    full run over every discovered model"
	@echo "report   regenerate leaderboard.md and the README table"

install:
	uv sync --all-groups --all-extras

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

test:
	uv run pytest -q

models:
	uv run tnb models

smoke:
	uv run tnb run --limit 3 --max-judge-usd 5

bench:
	uv run tnb run --max-judge-usd 150

report:
	uv run tnb report
