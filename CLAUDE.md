# therapy-note-bench — Agent Notes

A reproducible benchmark of LLM-generated psychotherapy session notes, run
against whatever models e-INFRA CZ has deployed. Generation refreshes from a
button; scoring is run by hand, because CI has no judge credential.

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

Phases 0 to 5 are done. 16 models have written notes on both tracks — 50 AnnoMI
conversations for TN-Eval SOAP, 40 iHOPE sessions for iCARE — and both tracks
are scored by two independent judges, `gemini-3.1-pro-preview` and
`gpt-5.6-terra`. `tnb report` writes four artefacts from `results/rows.jsonl`:
`docs/index.html` (the tables), `docs/methods.html` (the instrument),
`docs/leaderboard.json` and the README block.

**Two pages, on purpose.** The tables answer "which model" and the panels
answer "why believe the tables", and both were on one page until eight panels
had grown above the thing a reader came for. The leaderboard draws **one**
comparability group at a time with a switch for the track and the judge; every
ordering decision is made in Python and the page only draws it.

**The Actions button generates and does not score.** It has only ever held the
e-INFRA token, and the README used to promise it "commits the new results and
regenerates the table" while its one step called a stub that exits 2. Wiring a
judge into CI is undecided, and `tests/test_workflow.py` holds the button to
what it actually does.

Read `docs/limitations.md` before adding a number to any view. Three findings
bound what a table may claim: the two judges agree on the *shape* of the
ranking and not on the order, the three TN-Eval columns do not predict each
other, and **each judge scores its own vendor about 0.02 completeness higher**
— +0.017 for `gemini-3.1-pro-preview` and +0.016 for `gpt-5.6-terra` after the
re-ask of 2026-09-02, neither interval clearing zero once the models are
resampled as well as the conversations. The rows it applies to are marked in the table. A published
"detected" verdict came from resampling conversations only, which treats four
models as the whole of OpenAI.

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
- **An absence is never a measurement.** Every number here is a fraction, and
  for each one the question "what happens when something is missing" has three
  answers and one is right: counting it as zero invents a measurement nobody
  made; dropping it from the denominator is biased, because what goes missing
  clusters on the hard cases; **omitting the number and naming the gap** is the
  only honest one. Two code reviews found this same shape sixteen times —
  `gemma4` published with a perfect temporal score for writing "Nil" four ways,
  `glm-5` accused of failing a session e-INFRA refused to answer, a conciseness
  of 1.00 from one answered sentence of four.
- **Measure before deciding, and re-measure after.** The plan to raise the
  judge's thinking budget was held until the truncation rate was counted (0.50%
  at 128) and confirmed after (0.05% at 256 — revised to 0.15% on 2026-09-02 by
  an answer test that refuses an echo of the prompt; the 78 behind it were
  re-asked). A first attempt at that
  measurement classified TRACE ratings with the yes/no parser and reported the
  opposite conclusion; the numbers were re-derived rather than reported.
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
- Every result row carries `track`, `harness_version`, `prompt_version`,
  `judge_model`, `judge_prompt_version`, `judge_settings` and dataset
  revisions. **The leaderboard only combines rows that agree on all six of
  `results.COMPARABILITY_KEYS`.** Changing the judge — or the budget it thinks
  with — starts a new table. A group that names a judge and records no settings
  for it is withdrawn, not drawn: two rows that both say nothing are not
  thereby the same instrument.
- `harness_version` is **not a release number**: it is the claim "these measures
  mean what they meant last time". Bump it whenever a measure's definition
  changes even if no interface does — 0.2.0 was the ROUGE-L, temporal,
  `is_filled` and conciseness repairs. Older groups are named on the page rather
  than drawn beside the new ones.
- A cached answer is tied to **what was asked**: the judge cache records the
  prompt's digest, as the generation cache always has. Re-generating a note and
  re-scoring it used to reuse the judgement of the text it replaced.
- **The ranking is a shape, not an order.** Two judges place most systems
  differently. The only claim about "better" that survives is dominance —
  at least as good on every measure under both judges.
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
  goes on thinking. They are not broken. **A truncated answer is a failure on
  both sides**: `finish_reason` decides `ok`, which is what lets the generator
  escalate and the judge re-ask.
- BERTScore is cached under `scores/bertscore.json`, keyed on the pair it
  measures. Without it every run spent half an hour before its first question.
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
uv run tnb generate         # write notes; re-asks only what is missing
uv run tnb score            # TN-Eval rubric, one judge per run
uv run tnb score --cache-only   # publish what is answered, ask the judge nothing
uv run tnb score --thinking-budget N  # a budget is part of the instrument
uv run tnb score-icare      # ROUGE-L, BERTScore, TRACE, the two temporal columns
uv run tnb judges           # every candidate judge against the two therapists
uv run tnb saturation       # is there anything left to measure?
uv run tnb preference       # does either judge favour its own family?
uv run tnb report           # rebuild both pages, the JSON and the README table
```

Secrets live in `.env` and `secrets/`, both gitignored, and appear in no
tracked file: `EINFRA_BASE_URL`, `EINFRA_API_TOKEN`, `OPENAI_API_KEY`,
`VERTEX_PROJECT`, `VERTEX_LOCATION`, `GOOGLE_APPLICATION_CREDENTIALS`. Which
name each provider reads is in `models.yaml`, which is public and holds no
values.
