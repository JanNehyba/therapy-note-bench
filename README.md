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

> **Status: the TN-Eval track is measured.** All **11 benchmarkable models**
> have written and been scored on 50 AnnoMI conversations, against a judge
> checked against two therapists first. Every one of them scores above both
> 2025 models TN-Eval released *and* above the therapist-written note — on a
> rubric that rewards coverage, which is not the same as writing a better note.
> The top three cannot be told apart from each other. The iCARE track is still
> generating. See [Roadmap](#roadmap).

---

## The leaderboard

Full version, with per-section detail, the reference systems and the papers' own
published numbers: **<https://jannehyba.github.io/therapy-note-bench/>**

<!-- LEADERBOARD:BEGIN -->
**TN-Eval SOAP · AnnoMI conversations**

| Model | Completeness (0-1) | Conciseness (0-1) | Faithfulness (1-5) | Notes | Scored |
|---|---|---|---|---|---|
| `kimi-k3` | 0.654 | 0.961 | 4.98 | 50/50 | 50 |
| `qwen3.5-122b` | 0.644 | 0.871 | 4.75 | 50/50 | 50 |
| `qwen3.5-int4` | 0.643 | 0.925 | 4.88 | 50/50 | 50 |
| `glm-5` | 0.597 | 0.941 | 4.95 | 50/50 | 50 |
| `deepseek-v4-flash-thinking` | 0.578 | 0.965 | 4.81 | 50/50 | 50 |
| `qwen3.8-27b` | 0.578 | 0.946 | 4.92 | 50/50 | 50 |
| `gpt-oss-120b` | 0.575 | 0.898 | 4.39 | 42/50 (8 unusable) | 42 |
| `glm-5.2` | 0.574 | 0.939 | 4.99 | 50/50 | 50 |
| `mistral-medium-3.5` | 0.558 | 0.974 | 4.88 | 50/50 | 50 |
| `gemma4` | 0.556 | 0.944 | 4.99 | 50/50 | 50 |
| `deepseek-v4-flash` | 0.524 | 0.973 | 4.80 | 50/50 | 50 |

*Ordered by **Completeness**. Every other column is context.*
- **Completeness** (0-1) — Fraction of the section's rubric criteria the judge found present. 0.65 means about two thirds of the required items are in the note.
- **Conciseness** (0-1) — Fraction of the note's sentences that fit at least one rubric item. 1.00 means nothing is off-topic; it does not mean the note is short.
- **Faithfulness** (1-5) — Whether the note contradicts the transcript, rated 1 to 5, where 5 is no inaccuracies. TN-Eval's protocol has no criterion-based version of this one, so it stays a Likert scale. A different scale from the two columns beside it, and a weak one: TN-Eval measured Krippendorff's alpha of 0.18 between trained therapists on this rating. Read it as a flag for gross invention, not as a ranking.

**TN-Eval SOAP · AnnoMI conversations**

| Model | Provider | Completeness (0-1) | Conciseness (0-1) | Faithfulness (1-5) | Notes | Scored |
|---|---|---|---|---|---|---|
| `kimi-k3` | einfra | 0.525 | 0.835 | 5.00 | 50/50 | 50 |
| `qwen3.5-int4` | einfra | 0.518 | 0.809 | 4.97 | 50/50 | 50 |
| `google_gemini-3.1-pro-preview` | vertex | 0.514 | 0.822 | 4.99 | 50/50 | 50 |
| `google_gemini-3.7-flash` | vertex | 0.508 | 0.836 | 5.00 | 50/50 | 50 |
| `qwen3.5-122b` | einfra | 0.502 | 0.785 | 4.82 | 50/50 | 50 |
| `gpt-5.6-sol` | openai | 0.488 | 0.828 | 4.96 | 50/50 | 50 |
| `glm-5` | einfra | 0.482 | 0.807 | 4.97 | 50/50 | 50 |
| `glm-5.2` | einfra | 0.479 | 0.828 | 4.96 | 50/50 | 50 |
| `gpt-5.6-terra` | openai | 0.476 | 0.827 | 4.96 | 50/50 | 50 |
| `deepseek-v4-flash-thinking` | einfra | 0.467 | 0.831 | 4.87 | 50/50 | 50 |
| `gpt-oss-120b` | einfra | 0.465 | 0.783 | 4.35 | 42/50 (8 unusable) | 42 |
| `gpt-5.6-luna` | openai | 0.462 | 0.837 | 4.96 | 50/50 | 50 |
| `qwen3.8-27b` | einfra | 0.458 | 0.768 | 4.92 | 50/50 | 50 |
| `gemma4` | einfra | 0.454 | 0.857 | 4.96 | 50/50 | 50 |
| `mistral-medium-3.5` | einfra | 0.448 | 0.857 | 4.91 | 50/50 | 50 |
| `deepseek-v4-flash` | einfra | 0.431 | 0.881 | 4.88 | 50/50 | 50 |

*Ordered by **Completeness**. Every other column is context.*
- **Completeness** (0-1) — Fraction of the section's rubric criteria the judge found present. 0.65 means about two thirds of the required items are in the note.
- **Conciseness** (0-1) — Fraction of the note's sentences that fit at least one rubric item. 1.00 means nothing is off-topic; it does not mean the note is short.
- **Faithfulness** (1-5) — Whether the note contradicts the transcript, rated 1 to 5, where 5 is no inaccuracies. TN-Eval's protocol has no criterion-based version of this one, so it stays a Likert scale. A different scale from the two columns beside it, and a weak one: TN-Eval measured Krippendorff's alpha of 0.18 between trained therapists on this rating. Read it as a flag for gross invention, not as a ranking.

**TN-Eval SOAP · AnnoMI conversations**

| Model | Provider | Completeness (0-1) | Conciseness (0-1) | Faithfulness (1-5) | Notes | Scored |
|---|---|---|---|---|---|---|
| `kimi-k3` | einfra | 0.514 | 0.897 | 4.33 | 50/50 | 50 |
| `qwen3.5-122b` | einfra | 0.508 | 0.835 | 3.90 | 50/50 | 50 |
| `google_gemini-3.1-pro-preview` | vertex | 0.503 | 0.882 | 4.49 | 50/50 | 50 |
| `gpt-oss-120b` | einfra | 0.494 | 0.837 | 3.39 | 42/50 (8 unusable) | 42 |
| `qwen3.5-int4` | einfra | 0.490 | 0.845 | 4.37 | 50/50 | 50 |
| `gpt-5.6-terra` | openai | 0.487 | 0.892 | 4.73 | 50/50 | 50 |
| `gpt-5.6-sol` | openai | 0.478 | 0.887 | 4.76 | 50/50 | 50 |
| `google_gemini-3.7-flash` | vertex | 0.475 | 0.889 | 4.53 | 50/50 | 50 |
| `deepseek-v4-flash-thinking` | einfra | 0.473 | 0.905 | 4.09 | 50/50 | 50 |
| `glm-5` | einfra | 0.459 | 0.872 | 4.47 | 50/50 | 50 |
| `glm-5.2` | einfra | 0.459 | 0.886 | 4.41 | 50/50 | 50 |
| `gpt-5.6-luna` | openai | 0.449 | 0.866 | 4.69 | 50/50 | 50 |
| `deepseek-v4-flash` | einfra | 0.438 | 0.928 | 4.25 | 50/50 | 50 |
| `qwen3.8-27b` | einfra | 0.438 | 0.845 | 4.45 | 50/50 | 50 |
| `mistral-medium-3.5` | einfra | 0.429 | 0.917 | 4.25 | 50/50 | 50 |
| `gemma4` | einfra | 0.409 | 0.899 | 4.46 | 50/50 | 50 |

*Ordered by **Completeness**. Every other column is context.*
- **Completeness** (0-1) — Fraction of the section's rubric criteria the judge found present. 0.65 means about two thirds of the required items are in the note.
- **Conciseness** (0-1) — Fraction of the note's sentences that fit at least one rubric item. 1.00 means nothing is off-topic; it does not mean the note is short.
- **Faithfulness** (1-5) — Whether the note contradicts the transcript, rated 1 to 5, where 5 is no inaccuracies. TN-Eval's protocol has no criterion-based version of this one, so it stays a Likert scale. A different scale from the two columns beside it, and a weak one: TN-Eval measured Krippendorff's alpha of 0.18 between trained therapists on this rating. Read it as a flag for gross invention, not as a ranking.

**iCARE / iHOPE · 17 sections per session**

| Model | ROUGE-L (0-1) | BERTScore (0-1) | TRACE (1-5) | Temporal (0-1) | Notes | Scored |
|---|---|---|---|---|---|---|
| `deepseek-v4-flash` | 0.303 | 0.841 | 5.00 | 0.750 | 40/40 | 2 of 40 *(judging)* |

*Deliberately not ranked: these columns measure different things and the source paper found they disagree.*
- **ROUGE-L** (0-1) — Longest-common-subsequence overlap with the expert note. Rewards using the same words in the same order. Cannot tell a good paraphrase from a wrong answer. The source paper found it disagrees with what clinicians preferred.
- **BERTScore** (0-1) — Embedding similarity to the expert note. Tolerates paraphrase. A fluent note about the wrong session still scores well.
- **TRACE** (1-5) — Trustworthiness, relevance, accuracy, comprehensiveness and expression, averaged. A re-implementation with no human anchor: the authors never published their ratings, so unlike the TN-Eval track this number is not calibrated against anybody.
- **Temporal** (0-1) — Sections 5 and 17 only -- what happened last time, what happens next. Kept out of the average. The source paper reports every model it tested failing here, so a low number is the expected result, not a surprise.

**iCARE / iHOPE · 17 sections per session** — *waiting for the judge.* 15 system(s) have written their notes and none has been scored yet: `deepseek-v4-flash-thinking`, `gemma4`, `glm-5`, `glm-5.2`, `google_gemini-3.1-pro-preview`, `google_gemini-3.7-flash`, `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-oss-120b`, `kimi-k3`, `mistral-medium-3.5`, `qwen3.5-122b`, `qwen3.5-int4`, `qwen3.8-27b`.

See the [full leaderboard](https://jannehyba.github.io/therapy-note-bench/) for per-section detail, the reference systems and the published numbers.
<!-- LEADERBOARD:END -->

Numbers are only ever combined across runs that agree on harness version,
prompt version, judge model and judge prompt version. Changing the referee
starts a new table rather than rewriting the old one — see
[docs/methodology.md](docs/methodology.md#comparability-over-time).

## Judge calibration

<!-- CALIBRATION:BEGIN -->
Judge **`gemini-2.5-pro`** (prompts `tneval-rubric-v1`) against the two therapists TN-Eval had rate the same notes.

| Measure | Statistic | Judge vs therapist | Therapist vs therapist | Alpha, judge | Alpha, therapists | n |
|---|---|---|---|---|---|---|
| rubric completeness | Cohen's kappa | 0.58 | 0.50 | 0.57 | 0.50 | 3450 |
| likert completeness | Spearman rho | 0.32 | 0.13 | 0.19 | 0.13 | 600 |
| likert conciseness | Spearman rho | 0.03 | 0.19 | 0.02 | 0.19 | 600 |
| likert faithfulness | Spearman rho | 0.06 | 0.18 | 0.06 | 0.18 | 600 |

**The therapist-vs-therapist columns are the ceiling, not a target to beat.** Two trained therapists disagree with each other about these notes; a judge that agrees with a therapist as often as the other therapist does has done as well as the task allows.

**Why two statistics.** Cohen's kappa suits a yes/no criterion and Spearman suits a 1–5 scale, so each measure is reported under the one a reader expects. But those two are different quantities and an inequality between them means nothing, so the rubric-versus-Likert comparison below is made on **Krippendorff's alpha**, which is defined for both — nominal for the rubric, ordinal for the scales — and is the statistic TN-Eval used to reach the finding in the first place.

The judge reproduces TN-Eval's central finding: criterion checklists agree far better than 1–5 scales (alpha 0.57 against 0.19). That is why the leaderboard ranks on the rubric and reports the Likert columns with a caveat.
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
| 2 | Generation against every discovered model | **SOAP done**, iCARE 91% |
| 3 | Scoring: rubric, reference metrics, TRACE, temporal | **TN-Eval done**, iCARE next |
| 4 | Judge calibration against TN-Eval's human annotators | **done** |
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
