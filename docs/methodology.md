# Methodology

## What is measured

Given a therapy session transcript, a model must produce a clinical note. The
note is scored. That is the whole task. Nothing here measures a model's ability
to *conduct* therapy — see [landscape.md](landscape.md) for benchmarks that do.

Two tracks run side by side because they measure different things and disagree
in interesting ways.

## Track 1 — TN-Eval SOAP rubric (reference-free)

50 AnnoMI conversations. The model writes a SOAP note using TN-Eval's prompt,
unchanged in wording. Scoring reproduces TN-Eval's reference-free protocol:

- **Completeness** — 23 binary criteria across the four SOAP sections
  (subjective 6, objective 5, assessment 8, plan 4). One judge call per
  criterion: does this note segment contain this item?
- **Conciseness** — one judge call per sentence: does this sentence fit any
  rubric item? The score is the fraction that do.
- **Faithfulness** — a Likert rating against the full transcript.

Likert completeness and conciseness are also recorded, but **only for
comparison with the rubric**, never as headline numbers. TN-Eval measured
Krippendorff's alpha of 0.08 and 0.16 between trained therapists on those two
scales. They do not carry a signal worth ranking on. Faithfulness has no
criterion-based alternative in the protocol, so it stays Likert and is reported
with that caveat attached — TN-Eval also found LLM judges track humans worst on
exactly this dimension.

This track is the backbone: reference-free means any new model can be measured
without anyone writing a new gold note.

## Track 2 — iCARE / iHOPE, 17 sections

40 held-out sessions from the iHOPE corpus. The model fills the 17 iCARE
sections using the original AIIMS-approved prompts, unchanged in wording.

**This track deliberately reports three columns that can disagree**, because the
source paper found that they do. From the v2 abstract: clinical preference "did
not always mirror automatic benchmarks", with a smaller Mistral model preferred
by experts over the model that led on automatic scores.

| Column | What it is | Why it is here |
|---|---|---|
| `rouge_l` / `bertscore` | The paper's own metrics against expert gold notes | Lets our numbers be compared with the published table |
| `trace` | Trustworthiness, Relevance, Accuracy, Comprehensiveness, Expression, as an LLM judge over the note | The paper's own human framework — the thing the metrics above were found to miss |
| `temporal` | Sections 5 and 17 only (session details, next-session details) | The paper reports that *all* models fail here; averaging it away hides the finding |

**The gap between the first two columns is a published result, not an error.**
It is reported, not smoothed over.

Our TRACE is a **re-implementation without a human anchor.** The authors'
TRACE annotations and blinded expert review are not in the public repository, so
we cannot calibrate it the way we calibrate the TN-Eval judge. Every table and
column that carries a TRACE score says so.

## The judge

`claude-opus-5`, pinned. Scoring prompts are TN-Eval's, verbatim.

**Why an external model.** Both corpora are transcripts of public YouTube
videos. There are no patient data involved, so keeping inference inside e-INFRA
buys nothing here. If real session data are ever added to this benchmark, the
judge must move inside the infrastructure that holds them — which is why the
provider layer is swappable from the start.

### Calibration comes before the leaderboard

TN-Eval published ratings from two human annotators over 150 notes (50
therapist-written, 50 Llama 3.1 70B, 50 Mistral Large V2). Before any leaderboard
number is trusted, the judge is run over those same notes and compared with the
humans:

- Cohen's kappa per rubric criterion
- Spearman correlation on the aggregate section scores
- Whether the judge reproduces TN-Eval's own finding that rubric agreement beats
  Likert agreement

Those numbers go in the README, above the leaderboard. **If the judge disagrees
with therapists, that is published too.** A leaderboard whose referee has never
been checked against a human is a table of numbers, not a measurement.

## Comparability over time

The point of this repository is a table that stays meaningful as models change.
That only works if the measuring instrument does not drift silently.

Every result row carries:

- `harness_version` — this repository's version
- `prompt_version` — generation prompt revision
- `judge_model` and `judge_prompt_version`
- `dataset_revision` — upstream commit SHA for each corpus
- `model_id` exactly as the provider reported it, plus the raw `/v1/models` entry

**The leaderboard only ever combines rows that agree on all four version
fields.** Changing the judge produces a new table alongside the old one; it never
rewrites history in place. Without this rule the table quietly becomes
meaningless within a couple of model generations and nobody notices.

## Model discovery

No provider guarantees that a model version stays available — e-INFRA's
documentation says so outright. A hard-coded model list would therefore be wrong
within weeks. Each run queries every configured provider's `GET /v1/models` and
filters the result through [`models.yaml`](../models.yaml), which holds only
rules — exclude embeddings, exclude speech models, exclude the moving aliases
(`glm`, `kimi`, `deepseek`) because the model behind an alias changes without
notice.

The consequence is the property this repository exists for: when a provider
swaps `glm-5.2` for `glm-5.3`, the next run picks it up on its own.

### The provider is part of a model's identity

A model id is only unique inside one endpoint. The same name served by two
providers can be two different things — a different quantisation, different
weights, a different system prompt — so every result row carries its provider,
every cached note is filed under it, and the leaderboard shows it. Two providers
share a table, because comparing them is the point; they never share a row.

`tnb models --probe` answers the question directly: run it against both and
compare the fingerprints. It is the same check that caught `command-a` returning
`gemma4`'s exact output, one level up.

## Cost control

Generation runs on e-INFRA and costs quota, not money. Judging costs money, so:

- Scoring is grouped **by session, not by model** — the transcript is identical
  across every model and every prompt for a given session, so it is sent once as
  a cached prefix and reused across roughly a hundred calls.
- The Batch API is used where latency does not matter.
- `--max-judge-usd` is a hard ceiling. The run stops rather than exceeding it.
- Results are content-addressed on `(provider, model, task, session, prompt_version)`,
  so adding one model re-generates and re-scores only that model.
