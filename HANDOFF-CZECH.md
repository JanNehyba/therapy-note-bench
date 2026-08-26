# Handoff: does an English leaderboard say anything about clinical Czech?

Paste this whole file as the first message of a new session, working in
`c:\Users\Nehyba\therapy-note-bench`. Read `CLAUDE.md` first — its rules apply
unchanged, and the two that matter most here are **verify, do not trust** and
**never vendor a corpus**.

---

## The question

`therapy-note-bench` measures how well 16 models write psychotherapy notes.
Both corpora are English. `kimi-k3` is **1st of 19 on completeness under all
three judges** — the column the leaderboard is ordered by.

Jan then had three models write notes from real Czech sessions and had the
Czech rated on eight language dimensions. The order came out close to
**reversed**:

| Model | English (this benchmark) | Czech (Jan's rating, 0-10) |
|---|---|---|
| `kimi` | 1st cluster — top | **5.6 — worst** |
| `glm-5.2` | 3rd cluster — middle | **8.8 — best** |
| `deepseek` | 4th–5th cluster — bottom | 7.1 — middle |

**But that comparison is not valid yet**: each model was given a *different*
session, one each. Model quality and session difficulty moved together, so
neither can be blamed. The rater said so themselves.

**The job is to settle it properly.** If the reversal survives, it is a
publishable finding: *an English benchmark can say the opposite of the truth
about clinical Czech.*

---

## Non-negotiable: the Czech transcripts must never leave the machine

Jan has **10 real Czech session transcripts from one client** in a local
folder. They are real clinical material.

- Put them under `data/`, which is **gitignored** — the same place the fetched
  English corpora live. Never anywhere else.
- **Never** commit them, quote them in a doc, paste them into a commit message,
  or put a sentence of them on the leaderboard page.
- Scores and aggregates are fine to publish. Text is not.
- `results/rows.jsonl` is committed. Check that nothing text-shaped reaches it —
  `failure_reasons` keys are provider error bodies kept verbatim, and
  `results.normalise_reason` masks secrets but not content.
- Ask Jan before any run that would send them anywhere new.

---

## Design: two corpora, because that is what separates the two explanations

Jan's own worry, and it is the right one: with translated transcripts you
cannot tell whether clumsy Czech came from the translation or from the model.

Use both, and the ambiguity resolves:

| | 10 real Czech transcripts | AnnoMI transcripts translated to Czech |
|---|---|---|
| Input language | genuine spoken Czech | possibly translationese |
| Links to the English scores | ✗ none | ✓ same session, English numbers already exist |
| Sample | **one client, one therapist** | 50 different clients |

- Bad on **both** → the model.
- Bad on **translations only** → the input.
- Bad on **real only** → look at what real Czech has that the translation lost.

**Who translates.** Claude, and this is deliberate: every tested model is from
the gemma / glm / qwen / deepseek / kimi / gpt-oss / gpt-5.6 / gemini families,
and both judges are `gemini-3.1-pro-preview` and `gpt-5.6-terra`. Claude is
outside all of them, so no tested model is on home ground. Translate into
**spoken** Czech, not written Czech — a session transcript is speech. Have Jan
read one before running anything on the rest.

The translation is the same for every model, so it **cancels when comparing
models**. It does **not** cancel for the absolute claim "models write bad
Czech". Say that wherever the absolute claim appears.

---

## The one thing that makes this valid

**Every model gets every transcript.** That is the whole fix for the confound
in Jan's first pass. Nothing else about the design matters as much.

Suggested scope, small on purpose:

- **Models (5):** `glm-5.2`, `deepseek-v4-flash`, `deepseek-v4-flash-thinking`,
  `kimi-k3`, `qwen3.5-int4`.
  - Jan's three, plus the second deepseek (the two sit in different clusters,
    so "does thinking help Czech" comes free), plus `qwen3.5-int4` — the other
    model at the top in English, and Chinese like kimi. If it falls too, that
    is a pattern rather than one model.
  - Jan tested `deepseek-v3.2` and `kimi-k2.6`; e-INFRA now serves **newer**
    generations. Decide with Jan whether the question is "was Jan right about
    those versions" or "is it true of what is deployed today", and say which in
    the write-up.
- **Transcripts:** 10 real + 5 translated AnnoMI = 15.
- **Total:** 75 notes. Small and cheap.

---

## The rubric: reuse Jan's, do not invent one

Jan already has an eight-dimension rubric, 0–10, and has applied it once, so
the two runs can be compared. Ask him for the full text. The dimensions:

1. Spelling and diacritics
2. Grammar, agreement, complete sentences
3. Lexical accuracy — calques, anglicisms
4. Czech clinical terminology
5. Register and stylistic consistency
6. Readability, flow, degree of nominalisation
7. Typography — Czech quotation marks, dashes
8. Internal and cross-document consistency

Concrete errors he found, useful as anchors: `pres` for *tlak*, `sebepeče` for
*sebepéče*, untranslated `behavioral avoidance coping`, colloquial `Ségra` in a
field where `Sestra` belongs, straight `"` instead of Czech `„ "`.

**This rubric needs no expert note to compare against.** That is why this is
cheap: the main benchmark is expensive because it needs gold notes, and Czech
gold notes do not exist. Language quality is judged from the note alone.

---

## What to reuse in the repo

The generation pipeline, the judge, the caching, the result schema and the page
all work and are tested (458 tests, all passing). A Czech run is a **new track**
alongside `tneval-soap` and `icare`:

- `src/tnb/tasks/` — the note prompt, in Czech
- `src/tnb/scoring/` — the language rubric as a scorer, with its own
  `MEASURES`, `RANKING_MEASURE` and `JUDGE_MEASURES`
- `src/tnb/results.py` — add the track constant
- `src/tnb/report.py` — `COLUMNS`, `MEASURE_TABLES`, `RANKING_MEASURES`,
  `JUDGE_MEASURES`, `TRACK_TITLES`

Copy the shape of the iCARE track; it is the more recent of the two and its
scorer is the cleaner example.

---

## Rules this repository learned the hard way — do not relearn them

Every one of these was a live bug found and fixed on 2026-08-26.

1. **An absence is never a measurement.** Every number is a fraction. When
   something is missing, the only honest answer is *omit the number and name
   the gap* — never count it as zero, never quietly shrink the denominator.
   This shape was found sixteen times in two reviews.
2. **An instrument is its settings, not its name.** The same judge at thinking
   budget 128 and 256 moved **every one of 19 systems** on completeness
   (+0.017 mean) and reordered **16 of 19** on conciseness. `judge_settings` is
   part of the comparability key; two settings never share a table.
3. **Bump `harness_version` when a measure changes meaning**, even if no
   interface does. It is not a release number.
4. **A cached answer is tied to what was asked** — the judge cache records the
   prompt's digest. Re-generating a note and re-scoring it used to reuse the
   judgement of the text it replaced.
5. **One instrument at a time when reading the answer cache.**
   `saturation.load_answers` picks one fingerprint and reports what it ignored.
6. **A number that is computed must be drawn, or it is not a number.** Three
   analyses were written, tested, documented and rendered nowhere.
7. **Do not put a non-comparable number in a comparable column.** Reasoning
   tokens are reported as ~1600 by e-INFRA models and ~13–100 by GPT-5.6 at
   every effort level. Whether that is behaviour or bookkeeping is unknown from
   outside, so it does not belong beside the scores.
8. Prove a test by putting the bug back and watching it fail. Every fix in this
   repository was checked that way.

---

## First steps

1. Ask Jan for the folder with the 10 Czech transcripts and for the full rubric
   text. Confirm the folder is inside `data/` or move it there.
2. Read one transcript end to end. Check the loader can read the format before
   writing anything else.
3. Translate 5 AnnoMI transcripts into spoken Czech. Have Jan read one and say
   whether it sounds like a session or like subtitles. **Do not proceed until
   he has.**
4. Write the Czech note prompt. It is a new `prompt_version`.
5. Generate: 5 models × 15 transcripts = 75 notes. e-INFRA concurrency stays
   at **2** — it is Jan's personal academic quota.
6. Score with the language rubric, both judges. Report per model, and report
   real transcripts and translations **separately** — that separation is the
   point of the design.
7. Join to the English numbers for the 5 translated AnnoMI sessions and answer
   the question directly: **does a model's English rank predict its Czech?**

---

## Repository state as of this handoff

- Both English tracks generated and scored by two judges, harness `0.2.0`.
- 458 tests pass; `ruff` clean.
- `docs/index.html`, `docs/leaderboard.json` and the README table are current.
- Leaderboard tables now show a **shared rank**: systems the evidence cannot
  tell apart share a rank rather than being numbered 1, 2, 3.
- One long job may still be running: `tnb judges`, re-measuring the seven judge
  candidates at current settings. Harmless; it only rewrites
  `docs/judges-*.json`.
- Open item, agreed with Jan and not yet done: the measured reasoning-token
  figure should move out of the main table into the expanded row, with the
  caveat in rule 7 above.
