# Methodology

## What is measured

Given a therapy session transcript, a model must produce a clinical note. The
note is scored. That is the whole task. Nothing here measures a model's ability
to *conduct* therapy — see [landscape.md](landscape.md) for benchmarks that do.

Two corpora run side by side because they measure different things and disagree
in interesting ways, and the SOAP notes written on the first are scored by two
instruments rather than one. Three tracks, then: the TN-Eval rubric and PDSQI-9
over the same notes, and the iCARE form over the other corpus.

## Track 1 — TN-Eval SOAP rubric (reference-free)

50 AnnoMI conversations. The model writes a SOAP note using TN-Eval's prompt,
unchanged in wording. Scoring reproduces TN-Eval's reference-free protocol:

- **Completeness** — 23 binary criteria across the four SOAP sections
  (subjective 6, objective 5, assessment 8, plan 4). One judge call per
  criterion: does this note segment contain this item?
- **Conciseness** — one judge call per sentence: does this sentence fit any
  rubric item? Per section, the score is the fraction that do; the note's figure averages its section fractions, every section counting once. **What counts as a sentence
  is part of the measure**, because it is the denominator. TN-Eval used
  `nltk.sent_tokenize`; this repository splits on `.!?` followed by whitespace,
  holding back common abbreviations ("Dr.") and list markers ("1."). The list
  markers were added in harness `0.4.0`: before that, a numbered plan was cut
  into pieces that were bare numerals, each one a question the judge was asked
  and a numeral cannot pass. Measured before the repair it was 65% of one
  model's conciseness failures and 0% for the models that write prose, so the
  column was partly measuring markdown — a figure recorded at the time and not
  reproducible now, because applying the repair re-asked the answers it was
  computed from. The effect is in `results/` and is checkable: conciseness rose
  by 0.090, 0.078 and 0.059 under `gemini-3.1-pro-preview` and by 0.087, 0.075
  and 0.055 under `gpt-5.6-terra` for the three models that write numbered
  plans -- `qwen3.5-122b`, `gpt-oss-120b` and `google_gemini-3.7-flash` -- and
  did not move at all under either judge for `qwen3.8-27b`, `gpt-5.6-sol`,
  `gpt-5.6-luna`, `mistral-large-v2` and the therapist notes.
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
| `rouge_l` / `bertscore` | The paper's own metrics, over the **field values** of the sections the expert answered | See below: not directly comparable with their published table |
| `trace` | Trustworthiness, Relevance, Accuracy, Comprehensiveness, Expression, as an LLM judge over the note | The paper's own human framework — the thing the metrics above were found to miss |
| `temporal_past` | Section 5 alone (what happened last session) | The paper reports that *all* models fail on time; one of these two shows they do not |
| `temporal_next` | Section 17 alone (what happens next session) | And this is the one they fail. Averaged together the finding disappears -- see below |

**The gap between the first two columns is a published result, not an error.**
It is reported, not smoothed over.

**Why the two temporal columns are not one.** They were, and the average lied.
Looking back is something every model does (0.97-1.00); looking forward is
something almost none of them does (0.00-0.73, `gpt-oss-120b` at 0.00). The
expert notes answer section 5 in 34 of 40 cases and section 17 in 11, so the
mean is weighted 3:1 towards the easy half and turned 1.00 and 0.09 into 0.78 --
publishing the *opposite* of the finding this track exists to reproduce.

**Why ROUGE-L is not comparable with their table.** Their score is computed over
the whole rendered note, which means both sides share our 17 field labels and
every `Nil` the expert wrote. Measured: a note where the model wrote **nothing
at all** scored 0.379 that way, higher than most real notes. Ours compares the
field values only, over the sections the expert answered -- the same empty note
now scores 0.000. The cost is that the number no longer lines up with the
published one, and that is the smaller of the two evils.

Our TRACE is a **re-implementation without a human anchor.** The authors'
TRACE annotations and blinded expert review are not in the public repository, so
we cannot calibrate it the way we calibrate the TN-Eval judge. Every table and
column that carries a TRACE score says so.

## Track 3 — PDSQI-9 over the same SOAP notes

This page described two tracks until 2026-09-03 and the payload has held three
since 2026-08-27. The section is here because the document every page links as
"the method" has to describe the instrument a published table is ordered by.

**Why a second instrument on the same notes.** The rubric that anchors the
leaderboard reaches two of the nine things a clinician means by note quality
(see [limitations.md](limitations.md)). PDSQI-9 is the field's instrument for
that count — nine attributes, validated on real records with physicians doing
the rating — and eight of the nine are run here over the notes the rubric
already scored. `cited` is dropped: a note written from one transcript has no
source documents to cite. Two wordings are substituted, both named in
`src/tnb/scoring/pdsqi.py` and in `NOTICE`.

**It is never averaged with the rubric.** They are separate instruments, they
are drawn as separate tables, and each table is ordered by the mean of a
system's places over *its own* columns. A number scored on one is not comparable
with a number scored on the other, and the second does not fill the gap the
first leaves — it is wider, not sharper.

**No human anchor, and two traps.** No therapist rated these notes on PDSQI-9,
so unlike the rubric there is nothing to calibrate the judge against, and every
table says so. The first trap is the ceiling: an empty SOAP note beats the
therapist on *accurate* and on *succinct*, because a note that asserts nothing
has nothing untrue in it and says what it says in the fewest possible words.
[limitations.md](limitations.md) has the figures, and they are stated once,
there. Read those two columns as things a note can fail, never as things it can
win. The second is that under `gemini-3.1-pro-preview` four of
the eight columns — *comprehensible*, *organized*, *synthesized* and *useful* —
give the same number to twenty of the twenty-one systems, so no ordering exists
on them and the table's order is decided by the four that vary. Under
`gpt-5.6-terra` only *organized* is flat. That makes the count a fact about the
pair of judges rather than about the instrument, and it is one more reason the
two tables are never averaged.

## How the tables are ordered

Every table is ordered the same way. On each column of its instrument every
system is placed first, second and so on, at the precision the table prints —
rows that print the same figure share a place, because a reader checks a place
against the digits in front of them. The places are averaged with every column
counting once, and the rows are ordered by that mean, competition-style: a tie
on the mean is a tie, and the next place is skipped.

Places rather than values, for a measured reason. A mean of places agrees with
a mean win rate almost exactly on these tables — the same order by a longer
route — while a min-max mean of the values reverses many pairs of models when
the reference rows are removed, because it is rescaled by whoever sits at the
extremes. A place has no unit, so a fraction and a rating weigh the same, and
removing a row moves every place below it and nothing else.

The one convention the rule embeds is that every column counts equally, and
the page treats that as a claim to be tested rather than a fact. Under every
table it says who is first when each column is counted twice and when the
reference rows are removed, how many systems change place and how far; the
full table is on the methods page. A place is a statement about the table,
never about a note: it is not a measure, it never enters a headline, and the
two judges are never averaged into one order.

Beside the order, where `docs/edges-<track>.json` exists, a Group column draws
what the evidence separates: the layers of the dominance graph after every
"beats outright" claim was resampled whole over the conversations the pair
shares, kept at the band analysis's threshold. The first group is beaten by no
kept claim, the second only by the first, and nothing breaks a tie. The column
exists only where that artefact does, by construction: a Group drawn from an
untested relation was built and taken down once.

## What the instruments do to each other

Each table publishes an order of its own. The leaderboard opens with all of
them side by side: a row per model, its rank in every published table, and no
total. A total would have to price the instruments against each other, which is
a clinical judgement and not something these numbers can be asked for.

The ranks there are not the Place a table prints. Place counts the reference
rows; those rows sit at different heights on each instrument, and the iCARE
tables carry none at all, so a place among all rows means a different thing per
table. The profile re-derives each order over the models alone, through the
same `composite.order` the tables use — the `models_only` variant already
reported under every table's sensitivity — so no new ordering rule is
introduced.

What it measures is the Spearman correlation between every pair of those
orders, grouped by what the pair has in common: the same instrument under both
judges, or different instruments. The figures are on the leaderboard, where a
run keeps them right, and they are not repeated here for the reason
`docs/limitations.md` gives.

Sensitivity is a jackknife over the models. Every band is recomputed with each
model left out in turn, and a claim is published only if it survives all of
those, which answers whether a band rests on a single system. **It does not
answer whether a correlation is distinguishable from zero.** Nothing here
resamples the conversations the scores came from, and the page says so rather
than leaving the gap to be assumed closed.

Two things the section may not say, each because a measurement contradicts it.
That every pair inside an instrument sits above every pair across instruments:
true of the published figures, false as soon as a model is removed. And that
the instruments measure different things: between individual columns, where no
ordering convention is involved, columns of different instruments predict each
other about as well as columns of the same instrument. Whatever separates the
orders happens in the averaging of places, not in the measurements. That is
unexplained, and it is printed beside the finding it qualifies rather than
filed away here.

The artefact is `docs/orders.json`, written by `tnb orders`. It is arithmetic
over the published rows — no answer cache, no seed, no draw count — so the page
refuses it as soon as it stops describing the tables being drawn, down to a
single rank out of place.

## The judges

**Two of them, and they mark each other's homework.** Scoring prompts are
TN-Eval's, verbatim.

| Role | Model | Setting |
|---|---|---|
| Judge A | `gemini-3.1-pro-preview` | thinking budget 256 |
| Judge B | `gpt-5.6-terra` | reasoning effort `medium` |

Each scores every system, its own family included, and the two produce separate
tables — the leaderboard never mixes rows that disagree on `judge_model`.

**Why two.** Both of these models also *write* notes in this benchmark, and a
model asked to score text tends to score its own output higher than a neutral
rater would. Judging only with one of them would leave that as a caveat. With
two, the difference between the tables measures it: for each system take
`score_A − score_B`; the average over one judge's own family minus the average
over the systems **neither judge wrote** is the self-preference effect, in the
units of the leaderboard, with a bootstrap interval. If the interval spans zero
the page says the effect was not detected. If it does not, the number is a
result.

**Neither judge wrote, not "everything else".** This document said "everything
else" and the code does not, because that version does not work with two
judges. There is only one difference `d` and it is antisymmetric, so A's
comparison group would contain B's family and B favouring its own would show up
as A favouring its own: with A favouring Gemini by *x* and B favouring GPT by
*y*, it returns `x + y/2` for A. Comparing against the neutral systems returns
*x*, and the two effects can be read apart. It also means the panel needs at
least one neutral system to say anything, and it refuses to report a number
otherwise.

The obvious alternative — each judge scores only the *other* family — was
rejected: it would put two instruments with two calibrations in one column, and
leave every system with a single score and no way to check it.

**"Its own family" means the vendor, not the name.** `gemma4` is Google
DeepMind's and `gpt-oss-120b` is OpenAI's, and both were in the comparison
group until 2026-08-26 because the table that assigns families was keyed on the
judges' own model names. Both pulled the estimate toward zero, in the one group
the whole estimate is measured against. Whether self-preference carries across
an open-weight sibling is genuinely open; leaving them in the control group
answered it "no" with no evidence, so they are now counted with the vendor that
built them and the panel names its comparison group on the page. Correcting it
moved the estimates of that day from +0.005 to +0.018 for `gemini-3.1-pro-preview`
and from +0.005 to +0.027 for `gpt-5.6-terra`; the figures after the re-ask of
2026-09-02 are below.

**Both intervals include zero, and a published one did not.** The bootstrap
resampled conversations and not systems, so the interval described three or
four models rather than a vendor — while the sentence it supported, and the
mark on each affected row, are about the vendor. Resampling both:
`gemini-3.1-pro-preview` +0.018 [−0.009, +0.046] and `gpt-5.6-terra` +0.017
[−0.007, +0.043]. Neither is detected, and asked directly whether the two
judges differ, they do not: −0.000 [−0.041, +0.042].

Two systems carry most of the estimate, and they are the two that the vendor
redefinition moved into these groups: without `gemma4` the Gemini figure is
about +0.006, without `gpt-oss-120b` the GPT figure about +0.011 — each of them
the drop that moves its estimate furthest, and both published per judge in
`docs/preference.json` under `leans_on` rather than computed by hand into a
sentence. That is why the page
still tells a reader to check the panel before reading either table — not
because an effect was proved, but because one this size cannot be ruled out.

**The budget is part of the instrument.** At 128 tokens Gemini spent its whole
allowance thinking on 0.50% of questions and returned a fragment of its own
reasoning, which `parse_yes_no` reads as a "No" charged to the model. At 256
it was first counted as 0.05%; counted again on 2026-09-02 with an answer test
that refuses an echo of the prompt, it was 0.15% (78 of 51 000) — a count from the
judge's answer cache, which is not in this repository — and those 78 were re-asked
at harness 0.7.0 (docs/limitations.md says what that changed). Re-asking all 51 000
questions at the higher budget raised
every system's completeness (mean +0.017) and conciseness (+0.048) and lowered
faithfulness slightly (−0.021), and moved six systems on completeness and
sixteen on conciseness. So a run at one budget and a run at another are two
instruments, they never share a table, and each table says which it is.

**Why external models.** Both published corpora are transcripts of public
YouTube videos. There are no patient data involved, so keeping inference inside
e-INFRA buys nothing there.

**And if that changes.** If real session data are ever added to this
benchmark, the judge must move inside the infrastructure that holds them. The
commitment is written here rather than assumed, because the enforcement is not:
`tasks.Task.confined_to` refuses to build a generation job for a provider a
corpus may not reach, and nothing equivalent stands between a confidential
transcript and a judge.

**Why not the newest one.** Judge quality here does not follow release order,
and mostly it does not follow anything: measured over the same 150 notes with
every candidate at one setting, the three `flash` models score 0.544, 0.537 and
0.537 on the rubric. They span 0.008. The rule this repository uses elsewhere —
two things closer than 0.05 are reported as inseparable rather than ranked —
says that ordering is not a finding, in either direction.

An earlier version of this page said the newest flash was the *worst* of the
three, with the numbers 0.550, 0.543 and 0.541. Those were measured at
different thinking budgets and the conclusion reversed when they were not.
What the calibration does support is narrower and is derived on the page
itself: `gemini-3.1-pro-preview` is separably above five of the six others,
`gemini-2.5-pro` above the two GPT candidates, and no other pair separates —
so the $20 judge is indistinguishable from the $2.50 one. The calibration is
not a formality; without it we would have picked by reputation.

### Calibration comes before the leaderboard

TN-Eval published ratings from two human annotators over 150 notes (50
therapist-written, 50 Llama 3.1 70B, 50 Mistral Large V2). Before any leaderboard
number is trusted, the judge is run over those same notes and compared with the
humans:

- Cohen's kappa per rubric criterion — the statistic a reader expects for a
  yes/no judgement
- Spearman correlation on the 1–5 section scores — likewise, for a rating
- **Krippendorff's alpha on both**, which is the only one of the three defined
  for both kinds of rating

That third one carries a decision rather than a description. Whether the judge
reproduces TN-Eval's own finding — that criterion checklists agree far better
than 1–5 scales — is the stated reason this leaderboard ranks on the rubric, and
that comparison can only be made on a statistic that means the same thing on
both sides. It was made on a kappa against a Spearman rho until 2026-08-25, when
the two were compared as though they were one quantity. They are not, and the
inequality between them said nothing. TN-Eval reached the finding with alpha, so
reproducing it means using alpha.

The verdict is refused, rather than rounded, when the two instruments land
within 0.05 of each other.

Those numbers go in the README and on the methods page. **If the judge disagrees
with therapists, that is published too.** A leaderboard whose referee has never
been checked against a human is a table of numbers, not a measurement.

### The judge does not drift with scoring order, and that was tested

Models are scored one after another in alphabetical order, so "scored first" and
"scored at 17:34" are the same fact: a reader who notices that three of the top
four were judged late cannot tell an order effect from a real difference by
looking. Checked on 2026-08-25, three ways:

- **The judge was asked again.** 120 rubric questions from the first-scored
  model, re-asked fourteen hours later: **98.3% identical answers**, and the
  yes-rate moved +1.7 points. The gap between the first- and last-scored models
  is 12 points, which a 1.7-point drift cannot produce.
- **The correlation is weak.** Spearman between scoring position and score is
  **+0.31** over eleven models — well inside what eleven points produce by
  chance.
- **The last model breaks the pattern.** `qwen3.8-27b` was judged last, ninety
  minutes after everyone else, and landed mid-table at 55.2%.
  `mistral-medium-3.5` was judged eighth and is near the bottom.

If a future run wants to re-check this, the method is the first bullet: re-ask a
sample of already-answered questions and compare, which costs cents because the
answers are all cached.

**That re-ask has since been run wider, and the first bullet is not the whole
picture.** On 2026-09-02 both judges were asked the same questions again
at the same settings, into a separate answer cache so no published table is
computed from the second asking: `gemini-3.1-pro-preview` repeated 326 of 333
answers and `gpt-5.6-terra` 293 of 334. The counts are in
`docs/repeatability.json` and the panel drawn from it is on the methods page.
Repeating an answer and drifting with scoring order are different questions —
nothing here says the second judge's disagreement with itself grows through a
run — but a section that quotes the first bullet's figure and stops leaves a
reader with the wrong idea of how far an answer moves when nothing else does. The
probe is narrow on purpose and says so where it is drawn: five notes per
instrument, all written by one system.

## Comparability over time

The point of this repository is a table that stays meaningful as models change.
That only works if the measuring instrument does not drift silently.

Every result row carries:

- `harness_version` — this repository's version
- `prompt_version` — generation prompt revision
- `judge_model` and `judge_prompt_version`
- `dataset_revision` — upstream commit SHA for each corpus
- `model_id` exactly as the provider reported it, plus the raw `/v1/models` entry

**The leaderboard only ever combines rows that agree on all six comparability
fields** — `track`, `harness_version`, `prompt_version`, `judge_model`,
`judge_prompt_version` and `judge_settings`. Changing the judge, or the
settings the judge ran at, produces a new table alongside the old one; it never
rewrites history in place. Without this rule the table quietly becomes
meaningless within a couple of model generations and nobody notices.

This page said "all four" while the tuple held six. The sixth is
`judge_settings`, which is the field the thinking-budget argument on this page
turns on — and a table did blend two instruments while three documents promised
it could not, because rows written before that field existed all record
nothing and nothing told them apart. A group that names a judge and cannot say
how the judge was set is now withdrawn rather than drawn.

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

- Scoring walks provider, then task, then **model**, then session. Grouping by
  session instead would send each transcript once as a cached prefix and reuse
  it across roughly a hundred calls; that is worth doing and is **not what the
  code does today**. This entry claimed the saving as though it were already
  made, which is exactly what stops anyone from making it.
- `--max-judge-usd` is a hard ceiling. The run stops rather than exceeding it.
- Results are content-addressed on `(provider, model, task, session, prompt_version)`,
  so adding one model re-generates and re-scores only that model.
