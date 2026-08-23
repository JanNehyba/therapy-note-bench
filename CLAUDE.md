# therapy-note-bench — Agent Notes

A reproducible benchmark of LLM-generated psychotherapy session notes, run
against whatever models e-INFRA CZ has deployed, refreshed from a button.

This repository is **not** part of `destilo` (a separate project in a sibling
directory). No shared code, no shared conventions beyond the language rule.

Talk with Jan in Czech; keep code, docstrings, tests, commit messages and all
documentation in English. Jan is not a software engineer — explain plainly, skip
jargon, and prove things in small verified steps rather than large ones.

## Source Of Truth

- What exists in this field and what does not: `docs/landscape.md` — read first
- How scoring works and why: `docs/methodology.md`
- Corpora, licensing, and the traps in them: `docs/datasets.md`
- What a result cannot claim: `docs/limitations.md`
- What e-INFRA had deployed when: `docs/models-snapshot.md`
- Roadmap and phase status: `README.md`

## Where We Are

Phases 0 and 1 are done: the survey, model discovery, and both dataset loaders.
`tnb models` works against the live endpoint. No notes have been generated yet.

**Phase 2 is next — generation.** An OpenAI-compatible client against
`EINFRA_BASE_URL`, driven by `models.yaml`, writing one note per
(model, task, session) into a content-addressed cache so adding a model
re-generates only that model. Two tasks: TN-Eval's SOAP prompt over 50 sessions,
and iCARE's 17 section prompts over 40. Then phases 3-6 per the README.

## Working Rules

- **Verify, do not trust.** The endpoint's metadata is nearly empty, its
  documentation is stale, and model names lie — `command-a` returns `gemma4`'s
  output. `tnb models --probe` establishes identity by asking. Apply the same
  standard to papers: TN-Eval's stated conversation selection does not match the
  ids they released, and following the prose would have paired notes with the
  wrong transcripts.
- **Record negative and unexplained findings, do not smooth them over.** The
  TRACE ratings are not published and the docs say where that was checked. The
  paper's median conversation length does not reproduce and the docs say so.
- **Never vendor a corpus.** Two of the three upstream sources publish no
  licence. Everything is fetched at run time into a gitignored `data/` and
  checksummed.
- Read nearby code before editing; follow existing boundaries and naming.
- One logical change per commit. Commit messages say what would have broken.
- No `git reset --hard`, `git checkout .`, force push, or broad restores without
  Jan's explicit instruction.
- Do not add planning or status documents unless Jan asks for a repo artifact.

## Invariants

- Models are **discovered at run time**, never hard-coded. Unversioned aliases
  are excluded: they point somewhere else after the next deployment.
- Every result row carries `harness_version`, `prompt_version`, `judge_model`,
  `judge_prompt_version` and dataset revisions. **The leaderboard only combines
  rows that agree on all four.** Changing the judge starts a new table.
- Generation and scoring prompts are reproduced **verbatim** from TN-Eval and
  iCARE. Measure models on their task, not on ours.
- The judge is calibrated against TN-Eval's two human annotators before any
  leaderboard number is published, and the agreement figure goes in the README
  even if it is bad. The TRACE scorer has no human anchor and is labelled as
  such everywhere it appears.
- The iCARE track reports automatic metrics and TRACE **side by side**; the
  source paper found they disagree, and that disagreement is a result.
- `results/` is append-only.

## Cost And Safety

- The benchmark workflow has **only** `workflow_dispatch`. The `schedule:` block
  is commented out on purpose and no `pull_request` trigger exists, so secrets
  are unreachable from forks. Do not add triggers without asking.
- `--max-judge-usd` is a hard ceiling; a run stops rather than exceeding it.
- e-INFRA rate-limits per API key, not per model: six concurrent requests drew
  429 on a third of calls. Keep `concurrency: 2` and retry 429 with backoff.
- Reasoning models return empty content when `max_tokens` is small — the budget
  goes on thinking. They are not broken.
- Judging is grouped **by session, not by model**, so one transcript is sent as
  a cached prefix and reused across roughly a hundred calls.

## Commands

```sh
make install   # uv sync --all-groups --all-extras
make lint      # ruff check + format check
make test      # pytest, fully offline
make models    # what e-INFRA has deployed right now
make smoke     # cheap end-to-end run
make bench     # everything
uv run tnb models --probe   # which ids are secretly the same model
```

Secrets live in `.env` (gitignored): `EINFRA_API_TOKEN`, `ANTHROPIC_API_KEY`.
