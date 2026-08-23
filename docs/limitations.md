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

## The judge is a model

For the TN-Eval track the judge is calibrated against two human annotators and
that calibration is published above the leaderboard. Calibrated is not the same
as correct. TN-Eval's own finding is that LLM judges track humans acceptably on
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
- iHOPE's expert notes come from a single institution (AIIMS Delhi) in an Indian
  clinical context. Documentation conventions are not universal.
- One generation prompt per track, at temperature 0. This measures models under
  one prompting strategy, not their ceiling under prompt engineering.

## What it is good for

Tracking, over time and across model releases, whether a given model can turn a
therapy transcript into a structured clinical note that a rubric designed by
therapists recognises as complete, concise and faithful — and doing so on a
measuring instrument whose version, judge and calibration are all recorded.

That is a narrow claim. It is also the claim nobody was making before.
