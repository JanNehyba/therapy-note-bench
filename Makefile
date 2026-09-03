.PHONY: help install lint test models prompts smoke bench score score-icare analyse report figures brief pdf

help:
	@echo "install     install dependencies (uv)"
	@echo "lint        ruff check + format check"
	@echo "test        pytest (offline, no API calls)"
	@echo "models      print what e-INFRA has deployed right now"
	@echo "prompts     show the generation prompts; --verify checks them upstream"
	@echo "smoke       3 sessions x 2 models, cheap end-to-end check"
	@echo "bench       generate over every discovered model (no judge, no money)"
	@echo "score       judge the TN-Eval notes with both judges"
	@echo "score-icare judge the iCARE notes with both judges"
	@echo "analyse     saturation and self-preference, from cached answers"
	@echo "report      regenerate both pages, docs/leaderboard.json and the README table"
	@echo "figures     redraw docs/figures/*.svg from the published payload"
	@echo "brief       rebuild docs/brief.html from the payload and the figures"
	@echo "pdf         print the brief to docs/therapy-note-bench.pdf (needs Chrome)"

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

# Generation only: 3 sessions x (1 SOAP + 17 iCARE) calls, 2 models PER
# CREDENTIALLED PROVIDER. `--max-models` caps inside the loop over providers and
# `Policy.resolve(None)` returns every provider with a token, so with
# OPENAI_API_KEY or Vertex credentials in `.env` this spends their money too.
# Add `--providers einfra` to keep it inside the e-INFRA quota.
smoke:
	uv run tnb generate --limit 3 --max-models 2

# Every discovered model, both tracks: ~730 calls each, hours at concurrency 2.
# Generation only -- scoring is a separate target because it costs money and
# should be an explicit decision rather than something `bench` does on the way
# past.
bench:
	uv run tnb generate

# Both judges, because one judge cannot say how much to trust its own ranking.
# Answers are cached, so a repeat run asks only what is new.
score:
	uv run tnb score --judge-model gemini-3.1-pro-preview
	uv run tnb score --judge-model gpt-5.6-terra

score-icare:
	uv run tnb score-icare --judge-model gemini-3.1-pro-preview
	uv run tnb score-icare --judge-model gpt-5.6-terra

# Free: both of these read answers the judges have already given.
analyse:
	uv run tnb saturation
	uv run tnb preference
	uv run tnb orders

report:
	uv run tnb report

figures:
	uv run python tools/figures.py

brief: figures
	uv run python tools/brief.py

pdf: brief
	uv run python tools/pdf.py
