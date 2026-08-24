# therapy-note-bench

**A reproducible benchmark of LLM-written psychotherapy session notes, scored
on two published protocols and re-run as models change.**

Two datasets exist for turning a therapy transcript into a clinical note. Both
were benchmarked once, on models from 2024 and 2025, and never re-run. This
repository re-runs them from a button — so the table stays true as models
change.

Which models is a question of configuration, not of design. Providers are a
swappable backend: today the harness measures what is deployed on
[e-INFRA CZ](https://www.e-infra.cz/en), and adding another provider adds rows
rather than a second benchmark.

> **Status: notes written, nothing scored yet.** The 31 model ids currently
> reachable reduce to **11 distinct benchmarkable models**. All eleven have
> written the TN-Eval SOAP track — 542 of 550 notes; the eight misses are one
> model that will not produce a flat dictionary. The judge runs next, and until
> it does every score column below is a dash. See [Roadmap](#roadmap).

---

## The leaderboard

Full version, with per-section detail, the reference systems and the papers' own
published numbers: **<https://jannehyba.github.io/therapy-note-bench/>**

<!-- LEADERBOARD:BEGIN -->
**TN-Eval SOAP · AnnoMI conversations**

| Model | Completeness | Conciseness | Faithfulness* | Sessions |
|---|---|---|---|---|
| `deepseek-v4-flash` | — | — | — | 50/50 |
| `deepseek-v4-flash-thinking` | — | — | — | 50/50 |
| `gemma4` | — | — | — | 50/50 |
| `glm-5` | — | — | — | 50/50 |
| `glm-5.2` | — | — | — | 50/50 |
| `gpt-oss-120b` | — | — | — | 42/50 (8 unusable) |
| `kimi-k3` | — | — | — | 50/50 |
| `mistral-medium-3.5` | — | — | — | 50/50 |
| `qwen3.5-122b` | — | — | — | 50/50 |
| `qwen3.5-int4` | — | — | — | 50/50 |
| `qwen3.8-27b` | — | — | — | 50/50 |

**iCARE / iHOPE · 17 sections per session**

| Model | ROUGE-L | BERTScore | TRACE† | Temporal | Sessions |
|---|---|---|---|---|---|
| `deepseek-v4-flash` | — | — | — | — | 3/3 |
| `deepseek-v4-flash-thinking` | — | — | — | — | 3/3 |

See the [full leaderboard](https://jannehyba.github.io/therapy-note-bench/) for per-section detail, the reference systems and the published numbers.
<!-- LEADERBOARD:END -->

Numbers are only ever combined across runs that agree on harness version,
prompt version, judge model and judge prompt version. Changing the referee
starts a new table rather than rewriting the old one — see
[docs/methodology.md](docs/methodology.md#comparability-over-time).

## Judge calibration

<!-- CALIBRATION:BEGIN -->
Judge **`gemini-2.5-pro`** (prompts `tneval-rubric-v1`) against the two therapists TN-Eval had rate the same notes.

| Measure | Statistic | Judge vs therapist | Therapist vs therapist | n |
|---|---|---|---|---|
| rubric completeness | Cohen's kappa | 0.58 | 0.50 | 3450 |
| likert completeness | Spearman rho | 0.32 | 0.13 | 600 |
| likert conciseness | Spearman rho | 0.03 | 0.19 | 600 |
| likert faithfulness | Spearman rho | 0.06 | 0.18 | 600 |

**The right-hand column is the ceiling, not a target to beat.** Two trained therapists disagree with each other about these notes; a judge that agrees with a therapist as often as the other therapist does has done as well as the task allows.

The judge reproduces TN-Eval's central finding: criterion checklists agree far better than 1–5 scales. That is why the leaderboard ranks on the rubric and reports the Likert columns with a caveat.
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

No provider guarantees that a model version stays available — e-INFRA's
documentation says so outright. A hard-coded list would therefore be wrong
within weeks, so there is none: every run queries the provider's `/v1/models`
and filters it through rules in [`models.yaml`](models.yaml). When `glm-5.2`
becomes `glm-5.3`, the next run picks it up without anyone editing anything.

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
make smoke                # 3 sessions x 2 models, e-INFRA quota only
make bench                # everything
```

An e-INFRA token comes from <https://chat.ai.e-infra.cz> → Account → API keys
and needs a MetaCentrum account or Masaryk University affiliation.

## Roadmap

| Phase | | |
|---|---|---|
| 0 | Repository, survey, model discovery | **done** |
| 1 | Dataset adapters (AnnoMI + iHOPE → common schema) | **done** |
| 2 | Generation against every discovered model | **SOAP done**, iCARE next |
| 3 | Scoring: rubric, reference metrics, TRACE, temporal | |
| 4 | Judge calibration against TN-Eval's human annotators | |
| 5 | Leaderboard generation | **done** |
| 6 | One-click workflow | |

## Data and licensing

The MIT licence covers **this repository's code only.** No corpus is
redistributed here. Checked repository by repository on 2026-08-24 — licence
field, file tree and README — **one of the five inputs carries a licence:**

| Source | Used for | Licence |
|---|---|---|
| [TN-Eval](https://github.com/amazon-science/TN-Eval) (code) | SOAP prompt, scoring prompts, 23-item rubric | **Apache-2.0** |
| [TN-Eval-Data](https://github.com/amazon-science/TN-Eval-Data) | 150 notes, two annotators' ratings | none published |
| [AnnoMI](https://github.com/uccollab/AnnoMI) | 133 transcripts, 50 scored | none published, citation requested |
| [iCARE](https://github.com/proadhikary/iCARE) | the 17 section instructions | none published |
| [TheraFuse](https://github.com/ai4mhx/TheraFuse) | iHOPE transcripts and expert notes | MIT badge, no `LICENSE` file |

So: prompts under Apache-2.0 are reproduced in source with attribution;
everything else is fetched from its origin when a run needs it, checksummed, and
cited. The published page shows scores and field names — never a transcript, a
note, or somebody else's prompt. Detail and the two corrections this table
records: [docs/datasets.md](docs/datasets.md), [NOTICE](NOTICE).

### The two tracks are annotated differently, and it changes what they can claim

| | TN-Eval | iCARE |
|---|---|---|
| Expert-written reference note | 50, by therapists | 174, by named clinicians |
| **Human ratings of what a model wrote** | **2 annotators × 150 notes** | **none published** |

That second row is why the judge can be calibrated on one track and not the
other. TN-Eval's annotators disagree with each other — Cohen's kappa 0.50 on the
rubric, and *negative* correlation on some Likert scales — and our judge is
measured against that ceiling rather than against an imagined truth. The iCARE
TRACE column has no such anchor and is labelled as a re-implementation
everywhere it appears.

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
