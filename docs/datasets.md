# Datasets: provenance, licensing, and why nothing is vendored here

## The rule

**This repository never redistributes a corpus.** No transcript, no gold note,
no annotation is committed. `data/` is in `.gitignore`. Every dataset is fetched
from its original source at run time, checksummed, and cited.

This is not caution for its own sake. Checked repository by repository on
2026-08-24 — the GitHub licence field, the file tree, and the README of each:

| Source | What we take | `LICENSE` file | Stated elsewhere |
|---|---|---|---|
| `amazon-science/TN-Eval` | SOAP prompt, scoring prompts, 23-item rubric | **Apache-2.0** | — |
| `amazon-science/TN-Eval-Data` | 150 notes, ratings from 2 annotators | **none** | README says only "data for the TN-Eval project" |
| `uccollab/AnnoMI` | 133 transcripts | **none** | "we release AnnoMI … to benefit research community"; citation requested |
| `proadhikary/iCARE` | the 17 section instructions | **none** | nothing at all |
| `ai4mhx/TheraFuse` | iHOPE transcripts and gold notes | **none** | an **MIT badge** in the README |
| medRxiv 2025.06.25.25330252 | citation only | — | **CC-BY** (confirmed via the medRxiv API) |

Two corrections to what this page used to say:

- **TN-Eval's *data* is not Apache-2.0.** The licence is on the code repository.
  The annotations we calibrate the judge against live in a separate repository
  with no licence file and no statement in its README. That was written here as
  a fact when it was an assumption.
- **TheraFuse displays an MIT badge**, which is the only positive licence
  signal anywhere on the iHOPE side. It is weak in two ways: there is no
  `LICENSE` file behind the badge, and a badge on a code repository conventionally
  covers the code. The corpus was collected at AIIMS and TheraFuse redistributes
  it; nobody can license somebody else's data under MIT.

The rule does not change, and the reason for it gets stronger: publishing a
public repository that mirrors unlicensed clinical-adjacent data would be the one
avoidable mistake in this project. So we do not. Prompts we reproduce in source
are Apache-2.0 (TN-Eval); the iCARE instructions are fetched at run time and this
repository shows only field names.

## What gets fetched, and from where

### AnnoMI (TN-Eval track)

    https://github.com/uccollab/AnnoMI/raw/refs/heads/main/AnnoMI-full.csv

133 expert-annotated motivational-interviewing transcripts, transcribed from
public YouTube demonstration videos.

**The 50 conversations are taken from TN-Eval's released ids, not reconstructed
by a rule.** Their paper describes the set as "the first 50 conversations from
the high-quality split", but the released ids are
`0, 1, 2, 3, 5, 6, … 117, 122, 129` — they skip several and run to 129, so
sorting the high-quality split and slicing the first 50 produces a different set
and would pair therapist notes with the wrong transcripts. The ids are in the
data; the loader uses them and raises if AnnoMI cannot supply one.

Two properties of AnnoMI-full that matter to the loader:

- **One row per (utterance, annotator).** Seven of the 133 transcripts are
  annotated by all ten annotators, so every utterance in them appears ten times.
  TN-Eval deduplicates before grouping and so do we — otherwise those
  transcripts would be sent to the model with every line repeated ten times.
  Transcript 7 is one of the seven and is in the benchmark set.
- **It has not changed since 2023-03-14.** The only commit ever to touch
  `AnnoMI-full.csv` predates TN-Eval, so the transcripts we score are the ones
  they scored. It is also the newest commit the repository has: nothing has been pushed
since (checked 2026-08-31).

One unexplained discrepancy, recorded rather than smoothed over: the paper
reports a median conversation length of 1067 words and 42 turns. Measured over
the 50 released ids we get **793 words and 48 turns**; over all 110 high-quality
transcripts, 951 words and 52 turns. Neither matches, and collapsing consecutive
same-speaker utterances does not close the gap. Since pairing was verified
independently — a note's vocabulary overlaps its own transcript about twice as
much as a neighbour's, for 44 of 50 sessions, and the six exceptions are
near-ties on short notes — the likely explanation is a different definition of
"word" or "turn" rather than a different corpus.

Cite: Wu, Balloccu, Kumar, Helaoui, Reiter, Reforgiato Recupero, Riboni.
*Anno-MI: A Dataset of Expert-Annotated Counselling Dialogues.* ICASSP 2022.

### TN-Eval notes and human annotations

    https://github.com/amazon-science/TN-Eval-Data (data/notes_part1..10.json)

50 conversations × 3 notes (therapist-written, Llama 3.1 70B, Mistral Large V2),
each with rubric and Likert scores from two human annotators and two LLM judges.
**No licence published** — see the correction at the top of this page; the
Apache-2.0 licence is on TN-Eval's *code* repository, not on this one. This is
the **calibration anchor** described in
[methodology.md](methodology.md) — without it there would be no way to check the
judge against a human.

### iHOPE (iCARE track)

    https://github.com/ai4mhx/TheraFuse/raw/main/data/graph_test_aiims.json
    https://github.com/ai4mhx/TheraFuse/raw/main/data/graph_train_aiims.json
    https://github.com/proadhikary/iCARE (instructions.json)

174 sessions total; we score the 40 held-out test sessions. The 17 section
prompts come from `instructions.json` under `doctors_prompts` and are used
verbatim.

**The transcripts and gold notes are read from TheraFuse, not from the iCARE
repository**, even though the iCARE repository is what the paper cites. Both hold
the same corpus, but TheraFuse ships it as two JSON files with `dialogue` and
`summary` already joined per session, while iCARE spreads it over 174
directories of CSV pairs. Verified equivalent on 2026-08-23: 134 train + 40 test
= 174, and the test ids match the iCARE `Data/test/` directory names exactly.

TheraFuse is *Discourse-Guided Summarisation of Psychotherapy Dialogues via
Graph-Fused Language Models* (IEEE JBHI 2026), from the same authors. Its
`graph_*_aiims.json` files also carry discourse graph edges, which this
benchmark ignores.

Known defect: one of the 174 sessions has an empty gold summary. The loader
drops it and records the drop rather than scoring a model against nothing.

**18 of the 40 gold notes do not carry all 17 labels.** Measured on 2026-08-25 across
the 40 held-out notes: 22 carry all seventeen and 18 carry between seven and
twelve. The sparsest fields are Clinical identifiers, Assessments and
Reflections by the therapist, each labelled in 22 of 40. This is not the same as
a field answered `Nil` -- one is a clinician writing "nothing to report", the
other is a field that was never written down at all -- and 524 labelled parts
across the corpus parse with **zero** the matcher cannot place, so it is a fact
about the notes rather than about our splitter.

It has one direct consequence for scoring: the temporal measures take their
denominator from what the expert answered, not from what the form asks. A model
is not marked down for leaving blank a field the expert left blank too.

And "answered" is structural, not a word list. A model that writes

    Date: Nil
    Place: Nil
    Time: Nil
    Accompanying Person: Nil

has said nothing, and reading only the whole string counted it as content
because it is not literally "Nil". `gemma4` wrote exactly that into *what
happens next* in 36 of 40 sessions — the four-field template appears in all 40,
but in 36 every sub-value is Nil-ish — and was published with a perfect temporal
score. Counted on 2026-08-31 against a written definition — a value where no
sub-field carries content and yet the whole string is not the bare marker, so a
reader checking only "is this literally Nil?" calls it content — there are **88
distinct such strings over 486 model-written sections**, out of 10 879 sections
read. Counted by `tools/count_dressed_up_empties.py` over a local `generations/`
tree, which is gitignored and not redistributed: unlike every other figure on
this page, a fresh checkout cannot re-derive it without generating the notes
again — and three of the sixteen models generate at a non-zero temperature, so
a re-run would not return exactly this count either. No amount of adding phrases to the marker list would catch them: the shape
is structural, not lexical.

**It is entirely a model habit.** Of the 524 expert fields, 208 say nothing and
**not one** of them is dressed up: the clinicians write the bare marker. The
earlier figure here, "150 distinct composite strings over 534 records", stated no
definition and matched neither population; it is replaced rather than
reinterpreted.

**The sessions are not Indian; the note format is.** This was checked in the
data on 2026-08-24 rather than taken from the paper. Across the 40 test
sessions, the strings `AIIMS`, `OPD`, `Delhi` and `India` appear **zero times**,
and every patient name is Western — Sherry, Jessica, Sam, Judy, Sarah, Tim,
Emma, Tommy. (One apparent hit for `Rs.` was `Dr. Evers.`) The transcripts are
the same kind of published counselling demonstration as AnnoMI.

What is Indian is the **form** — 17 fields including Hospital ID, bed number,
OPD/inpatient/telepsychiatry status — and the clinicians who filled it in. The
benchmark therefore measures models filling an Indian hospital intake form from
a Western demonstration video, and that mismatch is visible in the gold notes
themselves: see [limitations.md](limitations.md#the-form-does-not-fit-the-material).

Cite: Adhikary et al. *Clinically Grounded AI-Scribing in Psychotherapy:
Benchmarking LLMs Against Expert Documentation in the iCARE Framework.*
medRxiv 2025.06.25.25330252, v2 (2026-08-19).

## A version mismatch to be aware of

The iCARE repository's last commit is **2025-04-28**. Preprint v2, which
introduces the name *iHOPE* and the TRACE evaluation framework, is dated
**2026-08-19** — sixteen months later. The published code and data therefore
predate the paper that describes them, and v2's Data Availability statement
still cites the repository "accessed April 26, 2025".

What this means in practice:

- The 174-session corpus with expert gold notes **is** present and matches v2's
  description, so the generation and reference-scoring tracks are sound.
- The **TRACE annotations are not published anywhere.** This was established by
  search, not assumption — see
  [landscape.md](landscape.md#where-the-trace-data-is-not) for what was checked.
  Our TRACE scorer is a re-implementation with no human anchor.
- The corpus counts agree across two independently published copies (iCARE's CSV
  directories and TheraFuse's JSON), which is weak but real evidence that it did
  not change between v1 and v2.

The authors release data on request elsewhere — MEMO ships nothing but a consent
form and an email address — so a request is the likely route for the TRACE
ratings. If they arrive, the TRACE column gets a human anchor and affected runs
are re-tagged.

## Ethics and scope

Both corpora are transcripts of **publicly published YouTube videos** —
counselling demonstrations and role-play, not clinical practice. No patient
consented to a therapy session; there is no protected health information in
either corpus. That is why the judge can be an external API here, and it is also
the ceiling on what any result from this benchmark can claim. See
[limitations.md](limitations.md).
