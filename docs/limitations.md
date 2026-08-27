# What this benchmark does not measure

Read this before quoting a number from the leaderboard.

## The sessions are not real

Both corpora are transcripts of **public YouTube videos** — counselling
demonstrations and role-play. AnnoMI sessions run around seven minutes. iHOPE
sessions come from the HOPE dataset of pre-recorded demonstration videos.
Neither is a real clinical encounter with a real patient, real ambivalence, real
silences, or real risk.

A model that writes good notes here has demonstrated that it writes good notes
*about demonstration videos*. That is a genuine signal and it is not the same
thing as clinical readiness.

## Human agreement is fragile, and it is fragile in the source data too

TN-Eval measured Krippendorff's alpha of **0.08** between trained therapists
rating note completeness on a 1–5 scale. The rubric protocol reaches 0.52. Even
the good number is moderate agreement, not consensus. When the humans who
designed the task agree this weakly, no downstream ranking should be read as
precise.

Small differences between adjacent models on this leaderboard are noise. Treat
the table as a coarse ordering.

## The judges also sit the exam

Two of the models being scored are also the two doing the scoring:
`gemini-3.1-pro-preview` and `gpt-5.6-terra` both write notes here. A model
asked to grade text tends to grade its own output higher than a neutral rater
would, which would inflate exactly the two systems a reader is most likely to
be curious about.

This is measured rather than disclaimed. Both judges score every system, the
two resulting tables are published side by side, and the difference between
them estimates the effect with a bootstrap interval. Read that panel before
reading either table. If the interval spans zero, the effect was not detected
in this data — which is not the same as it being absent, only that a run this
size could not see it.

Cells where a judge scored a model from its own family are marked in the table
where they sit. They are never dropped: a missing row would be a worse
distortion than a marked one.

## The ranking is a shape, not an order

The two judges agree on where a model sits roughly and disagree on exactly
where. The rank correlations are high and most systems still land in a
different position, on both tracks. The current figures are on
[the methods page](https://jannehyba.github.io/therapy-note-bench/methods.html), under *Do the two judges agree?*, where a run keeps them right — and
one sentence of them sits under the leaderboard's table, because it changes how
that table should be read. Repeating them here would only guarantee that one of
the copies is wrong.

**So the table supports "near the top" and "near the bottom". It does not
support "ninth rather than tenth".** A comparison between two adjacent rows is
not a result of this benchmark.

The one claim that survives is dominance: a system at least as good on *every*
measure under *both* judges is better however a reader weights the measures.
Most systems are beaten outright by nobody, which is why no single winner is
named.

**And it is not only two judges disagreeing — one judge disagrees with
itself.** Gemini's thinking budget was raised from 128 to 256 tokens and all
51 000 questions were asked again. Nothing else changed: same model, same
prompts, same notes. Every one of the nineteen systems scored higher on
completeness (mean +0.017) and on conciseness (mean +0.048) and slightly lower
on faithfulness (mean −0.021). Six systems changed position on completeness,
sixteen on conciseness; the conciseness top three changed and so did the leader
on faithfulness.

A setting a reader never sees moved the table more than most of the differences
printed in it. That is why the judge's settings are part of what a table is
compared on, and why each table's heading names them.

## The columns do not agree with each other either

Ordering by completeness says little about conciseness — the correlation is
negative under both judges — and something the two judges cannot agree on about
faithfulness, where one sees a moderate positive relationship and the other
sees none. The current figures are on [the methods page](https://jannehyba.github.io/therapy-note-bench/methods.html), under *Do the columns agree
with each other?*, where a run keeps them right.

They are not repeated here, for the reason given two sections above and
demonstrated by this paragraph: it used to carry four numbers copied by hand,
two of them wrong by more than the difference they were describing, and all
four stale within a fortnight.

A model that answers every question satisfies more criteria and invents more;
the two columns measure that trade, and collapsing them into one number means
deciding which matters more.

That decision is clinical, not statistical, so this benchmark does not make it.
What it would take to settle it is a clinician reading two notes and saying
which they would sign — which is a different study.

## How much a model "thought" is partly bookkeeping

Each row records how many tokens its model spent reasoning before writing.
Measured over the notes: `qwen3.8-27b` 1620, `glm-5.2` 1552,
`gemini-3.1-pro-preview` 1244, `kimi-k3` 670, `gpt-5.6-terra` 13 — and six
models report nothing at all.

**Do not read that as "GPT thinks a hundred times less".** Two things make the
figure incomparable across providers:

- **vLLM**, which serves the e-INFRA models, documents that it reports
  `reasoning_tokens: 0` for models whose reasoning is text-delimited — Qwen3
  and DeepSeek R1 among them — *even when the model reasons*. It counts
  normally for others. So "reports nothing" and "reasoned nothing" look
  identical here and are not the same.
- **OpenAI** counts differently again: its output-token count can exceed the
  visible tokens while `reasoning_tokens` reads 0.

Checked directly rather than assumed: the `reasoning_effort` parameter *is*
sent and *does* move the number — on one note, `gpt-5.6-sol` went 0 / 32 / 103
at low / medium / high. But published GPT-5 figures at the same three levels
are roughly 172 / 437 / 1087, an order of magnitude higher, and those were
measured on reasoning-heavy question answering. Writing a note from a
transcript is extraction, not reasoning, so a low figure here is expected — but
that explanation cannot also account for the open models spending 1500 on the
same task.

Which is why the figure sits in the expanded row and not in a sortable column:
it is real, and a gap in it can be accounting rather than behaviour.

## The judge is a model

For the TN-Eval track each judge is calibrated against two human annotators and
that calibration is published on [the methods page](https://jannehyba.github.io/therapy-note-bench/methods.html). Calibrated is not the same
as correct. Nor does newer or dearer mean better: measured at one setting, the
seven candidates span 0.089 in agreement with the therapists, and of the 21
pairs among them only 7 are separated by more than the 0.05 this repository
treats as the smallest real difference. The three `flash` candidates cannot be
told apart from each other, and neither can the $20 GPT from the $12 one. That
is why every candidate is measured rather than assumed — and why the panel
reports bands rather than an order. TN-Eval's own finding is that LLM judges track humans acceptably on
completeness and conciseness and **struggle on faithfulness** — which is the
dimension that matters most clinically, because it is where hallucinations show
up.

For the iCARE track, the TRACE scorer has **no human anchor at all**, because
the authors' TRACE annotations are not public. It is a re-implementation. Weigh
it accordingly.

## Automatic metrics and clinical preference disagree

This is not a caveat we are adding; it is a published result from the iCARE
paper. Experts preferred a smaller Mistral model over the model that led on
automatic scores, and lexical overlap with human notes was low even where
semantic alignment was strong.

This benchmark reports both and shows the disagreement rather than picking a
winner. If you need one number, you are asking the wrong question of this data.

**And our ROUGE-L is not their ROUGE-L.** Theirs compares the whole rendered
note, which puts our own 17 field labels and every `Nil` the expert wrote on
both sides of the comparison: measured here, a note where the model wrote
*nothing at all* scores **0.379** that way — higher than most real notes. Ours
compares the field values of the sections the expert answered, and the same
empty note scores **0.000**. Every model's figure fell by roughly a third as a
result. The number can no longer be lined up against their published table, and
that is the smaller of the two costs.

**The forward-looking temporal column rests on eleven sessions.** The experts
answered "what happens at the next session" in 11 of 40 notes and "what happened
last session" in 34, which is why those are two columns rather than one. Eleven
is a small denominator: a score of 0.09 there is one session, and the gap
between two models a few tenths apart is not evidence.

## Nothing here is in Czech

Both corpora are English. A model that performs well on this leaderboard has
told you nothing about how it handles a Czech therapy session — a different
language, different clinical vocabulary, different documentation conventions,
and a training-data distribution where Czech clinical text barely exists.

## Nothing here measures compliance

No payer requirements, no insurer documentation standards, no legal
record-keeping obligations in any jurisdiction. Completeness against a research
rubric is not completeness against a reimbursement requirement.

## Coverage is bounded

- TN-Eval track: 50 conversations. iCARE track: 40 held-out sessions.
- Motivational interviewing (AnnoMI) and the HOPE demonstration corpus are two
  narrow slices of psychotherapy. No CBT-specific, DBT-specific, psychodynamic
  or family-therapy corpus with gold notes exists publicly.
- iHOPE's expert notes were written at a single institution (AIIMS Delhi).
  Documentation conventions are not universal — and see below: the sessions
  those notes describe are not Indian, only the form is.
- One generation prompt per track, at temperature 0. This measures models under
  one prompting strategy, not their ceiling under prompt engineering.
- **A model can lose sessions to the output format rather than to the note.**
  TN-Eval ask for a flat four-key dictionary and recover it by slicing from the
  first `{` to the first `}`, re-asking up to five times when that fails. On the
  first full generation run `gpt-oss-120b` answered 37 of 50 conversations with
  a nested `Plan` (sub-headings and lists), which that slice truncates. The
  repair loop recovered 29; **8 conversations stayed unrecoverable**, so that
  model is scored on 42 notes and the other ten on 50.

  The notes themselves were good. What failed was instruction-following on the
  output shape — which is part of the task as TN-Eval defined it, so it is not
  patched away with a cleverer parser: doing that would score our extraction
  rather than theirs. But a lower score for `gpt-oss-120b` partly measures
  formatting, not clinical content, and **any table showing it must show its
  session count next to it.**

## The form does not fit the material

The iCARE note is a 17-field clinical form — hospital ID, bed number,
OPD/inpatient/telepsychiatry status, referring clinician — and the sessions it
is filled in from are published counselling demonstrations, checked in the data
and not Indian in any respect (see
[datasets.md](datasets.md)). Most of those fields have no answer in a YouTube
counselling video, and the gold notes show it. Across the 40 held-out sessions:

| Section | Blank in the expert's own note |
|---|---|
| Reflections by the therapist | **40 of 40** |
| Referral information | 38 of 40 |
| Crisis markers | 37 of 40 |
| Assessments | 37 of 40 |
| Clinical identifiers | 36 of 40 |

**Only 46% of the form is filled in at all** — 316 of 17 x 40 fields — and one
section was never filled in once.

The denominator was checked rather than assumed, because it decides the number.
An earlier revision said 60%: it counted a field only in the notes that printed
its label, so a field a note omitted entirely fell out of the denominator
instead of counting as unanswered. Three things settle it:

- **The label matcher is not the problem.** Every label in every gold note maps
  to one of the 17 fields; there are zero unrecognised labels, so a field that
  is missing is genuinely absent from the text.
- **The absences are scattered, not truncated.** Thirteen of the seventeen
  fields go missing in some notes; the four that never do — presenting
  complaints, mental status, issues discussed, clinical diagnosis — are exactly
  the four that are almost always filled. The annotators dropped the row when
  they had nothing to write, where others wrote `Nil`. Both mean the same thing.
- **The two readings can be told apart, and they agree.** Twenty-two of the 40
  notes carry all seventeen rows, so every field was demonstrably presented in
  them. Their fill rate is **44%** — the same as the 46% measured over all forty
  against a denominator of 17 x 40. If an omitted row meant "not asked", the
  complete notes would score far higher. They do not. Since the protocol's instruction is to write `Nil` when the transcript
does not say, a model can score well on those sections by staying quiet — and a
model that tries to be helpful is penalised. Read the iCARE numbers as
"fills the form correctly, including knowing when not to", not as "writes a good
clinical note". The sections that carry real signal are the ones the transcripts
can actually answer: presenting complaints, mental status, and what was
discussed, which the experts filled in 37, 39 and 39 times out of 40.

## Seven of nine things a clinician means by "quality" are not measured

The field has an instrument for this: [PDSQI-9](https://arxiv.org/abs/2501.08977),
validated on real EHR data with physicians doing the rating. It has nine
attributes. **This benchmark measures two of them.**

| PDSQI-9 attribute | Measured here? |
|---|---|
| **Thorough** — covers all pertinent issues | **Yes.** `completeness`, and the leaderboard is ordered by it |
| **Accurate** — true, free of incorrect information | **Yes.** `faithfulness` — on which two trained therapists reach an alpha of 0.18 |
| **Succinct** — brief, to the point, without redundancy | **No.** `conciseness` counts sentences that fit a rubric item; a note twice as long scores the same |
| **Organized** — structured so the reader follows the clinical course | No |
| **Synthesized** — shows understanding and an ability to plan care | No |
| **Useful** — relevant, provides value | No |
| **Comprehensible** — clear, unambiguous | No |
| **Citation** — sources present and appropriate | No |
| **Stigmatizing** — free of stigmatising language | No |

So the ranking column is the one attribute of nine that most rewards writing
more, and the seven it does not measure are the ones that separate a good note
from a complete one. That is not a flaw in the protocol — TN-Eval's rubric is
reproduced here exactly and it never claimed to measure the rest. It is a limit
on the sentence "this model writes better notes", which no number here
supports.

**Adopting PDSQI-9 helps, and less than it looks.** The instrument was
validated with physicians doing the rating, and its authors state they did not
compare LLM raters against human ones. So scoring these notes on it with a
judge gives columns that are *better anchored than TRACE and still not
calibrated here*, and the difference between those two sentences is the whole
point:

- TRACE has **no human agreement figure at all**. Nobody has rated anything on
  it that this repository can cite, which is why it is labelled that way
  wherever it appears.
- PDSQI-9 publishes one: trained physicians agree with each other at
  Krippendorff's alpha **0.575** — against the 0.18 two therapists reach on
  faithfulness. That is a **ceiling** a judge can be held against, and it is not
  nothing.
- Neither is a measurement of how well *our* judge agrees with *people* about
  *these* notes. That still needs clinicians rating what is in `generations/`,
  and that is a study rather than a configuration change.

`src/tnb/scoring/pdsqi.py` implements the instrument with three adaptations
named rather than absorbed — the "cited" attribute dropped because a note
written from one transcript has no source documents, the wording moved from
"summary" to "note", and the stigmatising item asked as published and reported
flipped so that every column runs the same way. It has not been run: no row in
`results/` carries a PDSQI figure, and nothing on the site reports one. **When
it is run, the ceiling belongs beside every column it produces**, exactly as
the rubric's does.

## Two of the twenty-three criteria are on the floor for every system

AnnoMI is motivational-interviewing demonstrations. There is no medication to
adjust, no formal diagnosis, no assessment instrument administered. The rubric
asks about all of them anyway, of every note, and the denominator is always 23.

**What decides that a criterion cannot apply.** `saturation`'s `unreachable`
verdict, which is already in the code and already published per judge in
`docs/saturation-<judge>.json`: **nobody** reaches it — every one of the
nineteen systems at or below 0.10, the therapist among them as one system and
not as the authority on it. Two criteria meet that under both judges:

| Criterion | Best of the nineteen, `gemini-3.1-pro-preview` | `gpt-5.6-terra` |
|---|---|---|
| Treatment goals, SMART (assessment) | 0.04 | 0.02 |
| Homework from previous sessions (subjective) | 0.08 | 0.06 |

A third — **assessment tools** — is on the floor under `gpt-5.6-terra` (best
0.10) and a hair off it under `gemini-3.1-pro-preview` (best 0.12). The entire
difference is one note out of fifty in one model, so it is named here rather
than counted: **2 of 23 is what both judges support**, and that is the count the
briefing's panel prints. Excluding the third as well would move the leader a
further +0.029 under judge A and +0.015 under judge B.

**What this does to the number, and to the ordering.** Recomputed over the
twenty-one criteria somebody reaches, on the notes whose completeness the judge
answered in full — the saturation panel's denominator, which is why the baseline
below is 0.550 and the leaderboard's headline for the same model is 0.546, and
the note set is held to what was complete under all 23 so that the only thing
changing is the criterion list:

| | `gemini-3.1-pro-preview` | `gpt-5.6-terra` |
|---|---|---|
| Leader, `kimi-k3` | 0.550 → 0.598 | 0.514 → 0.564 |
| Weakest model, `llama-3.1-70b` | 0.364 → 0.396 | 0.315 → 0.348 |
| Therapist | 0.325 → 0.355 | 0.273 → 0.303 |
| Mean model gain | +0.041 | +0.044 |
| The therapist's gain | +0.030, 0.74× the models' | +0.030, 0.68× |
| Weakest model minus therapist | +0.039 → +0.040 | +0.042 → +0.045 |
| Ordering | Spearman +0.996; four systems move, none by more than one place | +1.000; nothing moves at all |

**The correction is small and it is not neutral between the parties.** The
therapist gains about seven tenths of what the average model gains, so the gap
between her and the weakest model widens — by 4% under one judge and 7% under
the other. Small, and said out loud, because the version of this section it
replaces did not say it at all.

### The rule this replaces

Until 2026-08-27 the exclusion was five criteria, chosen as those the therapist
writes in at most 10% of her notes. Two things are wrong with that, and both are
measured rather than argued.

**It settles the comparison with the quantity being compared.** The
most-quoted result here is that every model covers more of the rubric than the
therapist, and the mechanism the next section documents is that models fill
boxes she leaves empty. A rule that then defines "inapplicable" as "the boxes
she leaves empty" is not independent of the finding it adjusts. Its effect was
correspondingly larger and ran one way: the leader went 0.550 → 0.676, and the
therapist-to-weakest-model gap widened by **42%** under judge A and 41% under
judge B — which the section never reported, because the therapist was left out
of the loop that produced its table. (Its published pair, "0.554 to 0.681", is
also not either of these: it came from an aggregation the scoring pipeline never
performs, the mean over sections of per-criterion rates across sessions, rather
than the mean over notes of each note's completeness.)

**And its answer depends on which judge is asked.** The rule reads a therapist
rate, and a therapist rate is a judge's opinion about her notes. Recomputed on
`gpt-5.6-terra`'s answers, the same rule keeps a *different* five:
`plan-adjustment` leaves, because she reaches 0.12 there, and
**`objective-mental-status` arrives** at 0.02 — the criterion the next section
names as the clearest case of the coverage mechanism, and where the best model
reaches 0.52. Excluding that set moves ten of eighteen systems and one of them
by **seven places**, Spearman +0.934, against the published claim that nothing
moved by more than two. The `unreachable` rule does not behave like this: its
two criteria are the same two under both judges.

### Three of the five it dropped are kept on purpose

`assessment-diagnosis` is the clearest. Nobody diagnoses in a
motivational-interviewing demonstration and the therapist writes one in 6% of her
notes — but under `gemini-3.1-pro-preview`, `gpt-oss-120b` writes one in **41%**
of its notes. If the criterion genuinely cannot apply, that is a model inventing
a diagnosis in four sessions out of ten, which is evidence about the models and
the strongest of its kind in this repository. Excluding the criterion deletes
the evidence rather than reading it.

It is also a column the two judges do not agree about — under `gpt-5.6-terra`
the same model sits at 0.02 and the whole field's maximum is 0.12 — and a
disagreement that size is a result about the instrument, so it is reported
rather than removed. `plan-adjustment` is the same shape with the judges
swapped: judge B puts `gpt-5.6-terra` at 0.54 there and judge A puts the field's
maximum at 0.16.

Quote completeness as a fraction of the whole 23-item rubric, which is what it
is, and not as a proportion of what a note could have contained.

## How a model beats a therapist: by filling boxes she leaves empty

The mechanism is visible per criterion. Models exceed the therapist on 15 of
the 23, by a mean of +0.15, and the largest gaps are where a note either has a
section or does not:

| Criterion | Therapist | Models (median) |
|---|---|---|
| Mental status examination | 0.26 | 0.96 |
| Interventions (plan) | 0.36 | 0.97 |
| Behaviour (objective) | 0.44 | 1.00 |
| Client's own words, quoted | 0.24 | 0.66 |

A model writes a mental status section in almost every note; the therapist
writes one in a quarter of them. **Whether what the model wrote there is true
is checked by exactly one measure** — faithfulness — **and that is the measure
two therapists agree on least.** Coverage is verified against a checklist;
what fills the coverage is verified against the weakest instrument in the set.

## A rubric rewards coverage, not judgement

Every judge that has scored this corpus puts both 2025 models **above** the
therapist on rubric completeness, and above on conciseness — all three judges,
no exception. TN-Eval reported the same direction from blinded expert
comparison, so this is a reproduction, not an anomaly.

**Faithfulness is the exception, and it is the informative one.** Llama 3.1
70B scores *below* the therapist there under both panel judges and above her
under the third. That is the measure with near-zero agreement between the two
therapists who rated these notes, and it behaves like it: a column that
reverses when the referee changes is not measuring what the other two are.

The figures are in the tables rather than here. The three this paragraph used
to quote came from a run that has since been withdrawn, so a reader could not
have checked them against anything published — and the first attempt at
replacing them claimed the pattern held on all three measures, which the check
written to verify it disproved in one line.

It does not mean a model writes a better clinical note than a therapist. It
means a model is better at covering a checklist. A therapist writes what matters
for the next session and leaves out what does not; the rubric counts what is
present and cannot see why something was left out. Quote the number with that
sentence attached, or do not quote it.

## What it is good for

Tracking, over time and across model releases, whether a given model can turn a
therapy transcript into a structured clinical note that a rubric designed by
therapists recognises as complete, concise and faithful — and doing so on a
measuring instrument whose version, judge and calibration are all recorded.

That is a narrow claim. It is also the claim nobody was making before.
