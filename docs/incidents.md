# Data events

What happened to confidential data in this repository's runs, from the
artefacts that record it: commit messages, the docstrings written as the record
at the time, and the names, counts and timestamps of the gitignored caches. No
transcript, no note and no session identifier appears here. The generation log
and the judge caches behind these counts are not in this repository.

## 2026-08-29: ten real sessions sent to two external providers by generation

**What.** `tnb generate --tasks deepsy-real,deepsy-translated` was run without
`--providers`. The default was every provider with a token, so all ten real
sessions of the corpus went to OpenAI and to Google Vertex: 150 calls, each
answered, between 01:09 and 03:39 (the times the commit recording the event
states). The generation prompt carries the transcript, so the disclosure was
the request itself. The transcripts were the de-identified form the track reads
(`data/czech/anonymised`); whether that de-identification is enough for the
text to stop being personal data is a question for the controller, not for
this file.

**Recorded where.** Commit c140d9f (2026-08-29), the docstring of
`tests/test_corpus_confinement.py`, and `tasks.Task.confined_to`. The commit
reports that the 300 answers were quarantined in gitignored
`local/incident-2026-08-29/` rather than deleted, and that ten result rows
scored from them stayed in the append-only record. On 2026-09-14 that directory
is not present on the machine this record was written on, and the results file
carries no rows of the Czech track: they left with the Czech branch on
2026-09-01 (commits d5a3330 and 9a9cb47). Where the quarantined answers are now
is not known from the repository; the generation log is not in this repository.

**Fix at the time.** `Task.confined_to` names the providers a task's corpus may
reach, and `cmd_generate` refuses to build a job outside it, before a job
exists.

## 2026-08-29 to 2026-09-01: notes written from the real sessions were judged by two external judges, by design

This was not an accident and was not recorded as an event. It is recorded here
because the counts were never written down, and because the design has since
changed.

**The design as stated then.** The methodology said the transcripts are
de-identified, read only by the note-writing model on e-INFRA, and never shown
to the judge: the Czech scoring module's questions took a note and had no
parameter a transcript could arrive through, and "what does reach one is the
note a model wrote from an already de-identified session". It called this a
deliberate narrowing of the earlier commitment that the judge moves inside the
infrastructure holding the data, made because an e-INFRA judge would have had
no calibration and no second judge to disagree with it.

**What the caches hold.** Counting only the sessions marked real, the judge
caches under `scores/deepsy-3section-v1/` hold, for each of
`gemini-3.1-pro-preview` (Google Vertex) and `gpt-5.6-terra` (OpenAI): on
2026-08-29, 2 424 cached answers per judge about 168 notes written for the ten
sessions by 17 systems, 12 of them on e-INFRA, 3 on OpenAI and 2 on Vertex,
between 03:39 and 13:07, across three answer-room settings; overnight
2026-08-31 to 2026-09-01, on the PDSQI-9 instrument, 714 answers per judge
about 119 notes from 12 systems, the two attributes that need a transcript not
asked; and on 2026-09-01, 19 and 7 further answers. That is 6 302 cached
answers about notes of the real sessions across the two judges. Each answer is
one request that carried one note; nothing in these caches carried a
transcript. The caches behind these counts are gitignored and not in this
repository.

**What changed on 2026-09-14.** `judge.Judge` is built for named tasks and
refuses to exist for a confined task on a backend the task does not allow
(commit ed12f30); Gen-2 confines both generation and judging through
`Case.allowed_providers`, and a case from a real session admits only `local`
and `einfra`. Under either, the runs above could not be repeated as they were:
a confined Czech task can be generated for on e-INFRA and not judged at all,
until a judge inside e-INFRA exists as its own instrument.

## Decisions this record does not make

- Whether de-identified transcripts, and notes written from them, are personal
  data of the client under the GDPR, and on what legal basis they were
  processed. No consent, ethics opinion or processing agreement is recorded in
  this repository.
- Whether the event of 2026-08-29 was a personal data breach under the GDPR
  that had to be notified to the supervisory authority within 72 hours of
  awareness (Article 33) and to the data subject (Article 34). Awareness was
  2026-08-29; this file was written on 2026-09-14.
- What happens to the quarantined answers, if they still exist, and to the
  judge caches named above.
- Whether the note-only judging of 2026-08-29 to 2026-09-01 falls under the
  same assessment.

These are the controller's decisions. The repository's part, that neither path
can be taken again without a decision written in code, is done.
