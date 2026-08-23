# therapy-note-bench

**A reproducible benchmark of LLM-generated psychotherapy session notes, run
against the models actually deployed on [e-INFRA CZ](https://www.e-infra.cz/en).**

Two published datasets exist for turning a therapy transcript into a clinical
note. Both were benchmarked once, on models from 2024 and 2025, and never
re-run. This repository re-runs them on whatever is deployed today, and does it
from a button — so the table stays true as models change.

> **Status: no results yet.** The survey, the design and model discovery are
> done — 31 ids on e-INFRA reduce to **11 distinct benchmarkable models**, and
> `glm-5.3` is not among them. Generation and scoring are next.
> See [Roadmap](#roadmap).

---

## The leaderboard

<!-- LEADERBOARD:BEGIN -->
*No runs yet. The first run will populate this section automatically.*
<!-- LEADERBOARD:END -->

Numbers are only ever combined across runs that agree on harness version,
prompt version, judge model and judge prompt version. Changing the referee
starts a new table rather than rewriting the old one — see
[docs/methodology.md](docs/methodology.md#comparability-over-time).

## Judge calibration

<!-- CALIBRATION:BEGIN -->
*Not yet measured.* Before any leaderboard number is published, the judge is
scored against the two human annotators TN-Eval released, and the agreement
figures appear here — including if they are bad.
<!-- CALIBRATION:END -->

---

## What is measured

| Track | Corpus | Protocol | Reference needed |
|---|---|---|---|
| **TN-Eval SOAP** | 50 AnnoMI conversations | 23 completeness criteria, per-sentence conciseness, faithfulness | No |
| **iCARE / iHOPE** | 40 held-out sessions, 17 sections | ROUGE-L + BERTScore, TRACE, and a separate temporal-reasoning column | Yes |

The iCARE track reports automatic metrics and a TRACE judge **side by side
because the source paper found they disagree** — experts preferred a smaller
Mistral model over the automatic-score leader. That disagreement is a result, and
it is reported rather than averaged away.

Full detail: [docs/methodology.md](docs/methodology.md).

## What is *not* measured

Both corpora are transcripts of public YouTube demonstration videos, not real
clinical sessions. Human agreement in the source data is weak (Krippendorff's
alpha of 0.08 on Likert completeness between trained therapists). Nothing here is
in Czech, and nothing here measures payer compliance. Small gaps between adjacent
models are noise.

Read [docs/limitations.md](docs/limitations.md) before quoting a number.

For **general medicine** rather than therapy, see
[Omi-Health/medical-note-eval](https://github.com/Omi-Health/medical-note-eval) —
a well-built maintained leaderboard that states explicitly that mental-health
notes are not tested. This repository covers the ground they exclude.

## Why the model list is not in this repository

e-INFRA's own documentation says "no specific model version is guaranteed to
stay available". So there is no hard-coded model list: every run queries
`GET /v1/models` and filters it through rules in
[`models.yaml`](models.yaml). When `glm-5.2` becomes `glm-5.3`, the next run
picks it up without anyone editing anything.

Names cannot be trusted either. `command-a` sounds like Cohere Command A and
returns `gemma4`'s exact output; four other ids turned out to be second names
for models already in the set. `tnb models --probe` establishes identity by
asking each model a fixed question and comparing answers, rather than by
reading its name.

Last captured snapshot: [docs/models-snapshot.md](docs/models-snapshot.md).

## Running it

### One click

Actions → **Benchmark** → *Run workflow*. Inputs: which models (blank means
every discovered model), which tracks, an optional session limit, and a hard
dollar ceiling on judge spend. The workflow commits the new results and
regenerates the table above.

There is **no scheduled run.** The `schedule:` trigger sits commented out in
[`.github/workflows/benchmark.yml`](.github/workflows/benchmark.yml); uncomment
two lines to enable it. Nothing spends anything without a click.

### Locally

```sh
uv sync --all-groups
cp .env.example .env      # add EINFRA_API_TOKEN and ANTHROPIC_API_KEY
make models               # what is deployed right now
uv run tnb models --probe # which ids are secretly the same model
make smoke                # 3 sessions x 2 models, under $2
make bench                # everything
```

An e-INFRA token comes from <https://chat.ai.e-infra.cz> → Account → API keys
and needs a MetaCentrum account or Masaryk University affiliation.

## Roadmap

| Phase | | |
|---|---|---|
| 0 | Repository, survey, model discovery | **done** |
| 1 | Dataset adapters (AnnoMI + iHOPE → common schema) | |
| 2 | Generation against every discovered model | |
| 3 | Scoring: rubric, reference metrics, TRACE, temporal | |
| 4 | Judge calibration against TN-Eval's human annotators | |
| 5 | Leaderboard generation | |
| 6 | One-click workflow | |

## Data and licensing

The MIT licence covers **this repository's code only**. No corpus is
redistributed here — two of the three upstream sources publish no licence at
all, so everything is fetched from its origin at run time and cited. See
[docs/datasets.md](docs/datasets.md) and [NOTICE](NOTICE).

## Credits

This benchmark is a harness around other people's work. The rubric, the prompts
and the human annotations are theirs.

- **TN-Eval** — Shah, Xu, Liu, Burnsky, Bertagnolli, Shivade. *TN-Eval: Rubric
  and Evaluation Protocols for Measuring the Quality of Behavioral Therapy
  Notes.* ACL 2025, Industry Track.
- **AnnoMI** — Wu, Balloccu, Kumar, Helaoui, Reiter, Reforgiato Recupero,
  Riboni. *Anno-MI: A Dataset of Expert-Annotated Counselling Dialogues.*
  ICASSP 2022.
- **iCARE / iHOPE** — Adhikary et al. *Clinically Grounded AI-Scribing in
  Psychotherapy: Benchmarking LLMs Against Expert Documentation in the iCARE
  Framework.* medRxiv 2025.06.25.25330252.
