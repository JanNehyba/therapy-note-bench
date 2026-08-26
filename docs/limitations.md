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
different position, on both tracks. The current figures are on the leaderboard,
in the panel above the tables, where a run keeps them right; repeating them
here would only guarantee that one of the two copies is wrong.

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

Ordering by completeness says little about conciseness (−0.18 and −0.33 under
the two judges) and something the judges cannot agree on about faithfulness
(+0.72 and +0.04). A model that answers every question satisfies more criteria
and invents more; the two columns measure that trade, and collapsing them into
one number means deciding which matters more.

That decision is clinical, not statistical, so this benchmark does not make it.
What it would take to settle it is a clinician reading two notes and saying
which they would sign — which is a different study.

## The judge is a model

For the TN-Eval track each judge is calibrated against two human annotators and
that calibration is published above the leaderboard. Calibrated is not the same
as correct. Nor does newer mean better: on this task `gemini-2.5-flash` agreed
with the therapists slightly *more* than `gemini-3.7-flash` did, which is the
reverse of what any general benchmark would predict, and is why every candidate
is measured rather than assumed. TN-Eval's own finding is that LLM judges track humans acceptably on
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

## A rubric rewards coverage, not judgement

The first scored run put both 2025 models **above** the therapist on rubric
completeness — 0.45 and 0.41 against 0.34 — and above on conciseness and
faithfulness too. TN-Eval reported the same direction from blinded expert
comparison, so this is a reproduction, not an anomaly.

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
