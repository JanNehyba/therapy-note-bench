.PHONY: help install lint test models prompts smoke bench report

help:
	@echo "install  install dependencies (uv)"
	@echo "lint     ruff check + format check"
	@echo "test     pytest (offline, no API calls)"
	@echo "models   print what e-INFRA has deployed right now"
	@echo "prompts  show the generation prompts; --verify checks them upstream"
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

prompts:
	uv run tnb prompts --verify

# Generation only until the judge lands in phase 3, so this spends e-INFRA
# quota and no money: 2 models x 3 sessions x (1 SOAP + 17 iCARE) calls.
smoke:
	uv run tnb generate --limit 3 --max-models 2

# Every discovered model, both tracks: ~730 calls each, hours at concurrency 2.
# Scoring joins this target in phase 3; until then it generates and stops.
bench:
	uv run tnb generate

report:
	uv run tnb report
