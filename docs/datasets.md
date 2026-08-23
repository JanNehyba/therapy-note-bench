# Datasets: provenance, licensing, and why nothing is vendored here

## The rule

**This repository never redistributes a corpus.** No transcript, no gold note,
no annotation is committed. `data/` is in `.gitignore`. Every dataset is fetched
from its original source at run time, checksummed, and cited.

This is not caution for its own sake. Of the three upstream sources, **two
publish no licence at all**:

| Source | Licence | What we do |
|---|---|---|
| TN-Eval code + rubric + annotations | Apache-2.0 | Reuse with attribution in `NOTICE` |
| AnnoMI transcripts | **none published**, citation requested | Fetch at run time, cite, never mirror |
| iCARE / iHOPE transcripts + gold notes | **none published** | Fetch at run time, cite, never mirror |

Publishing a public repository that mirrors unlicensed clinical-adjacent data
would be the one avoidable mistake in this project. So we do not.

## What gets fetched, and from where

### AnnoMI (TN-Eval track)

    https://github.com/uccollab/AnnoMI/raw/refs/heads/main/AnnoMI-full.csv

133 expert-annotated motivational-interviewing transcripts, transcribed from
public YouTube demonstration videos. TN-Eval uses the **first 50 conversations
of the high-quality split**; we use the same 50, selected the same way, so our
numbers line up with theirs.

Cite: Wu, Balloccu, Kumar, Helaoui, Reiter, Reforgiato Recupero, Riboni.
*Anno-MI: A Dataset of Expert-Annotated Counselling Dialogues.* ICASSP 2022.

### TN-Eval notes and human annotations

    https://github.com/amazon-science/TN-Eval-Data (data/notes_part1..10.json)

50 conversations × 3 notes (therapist-written, Llama 3.1 70B, Mistral Large V2),
each with rubric and Likert scores from two human annotators and two LLM judges.
Apache-2.0. This is the **calibration anchor** described in
[methodology.md](methodology.md) — without it there would be no way to check the
judge against a human.

### iHOPE (iCARE track)

    https://github.com/proadhikary/iCARE (Data/test/<id>/, instructions.json)

174 sessions total; we score the 40 held-out test sessions. Each session
directory holds a transcript CSV and an expert gold-note CSV. The 17 section
prompts come from `instructions.json` under `doctors_prompts` and are used
verbatim.

Cite: Adhikary et al. *Clinically Grounded AI-Scribing in Psychotherapy:
Benchmarking LLMs Against Expert Documentation in the iCARE Framework.*
medRxiv 2025.06.25.25330252, v2 (2026-08-19).

## A version mismatch to be aware of

The iCARE repository's last commit is **2025-04-28**. Preprint v2, which
introduces the name *iHOPE* and the TRACE evaluation framework, is dated
**2026-08-19** — sixteen months later. The published code and data therefore
predate the paper that describes them.

What this means in practice:

- The 174-session corpus with expert gold notes **is** present and matches v2's
  description, so the generation and reference-scoring tracks are sound.
- The **TRACE annotations are not published**, and neither is the blinded
  expert-review data behind v2's finding that clinicians preferred a smaller
  model. Our TRACE scorer is a re-implementation with no human anchor.
- It has not been confirmed whether the corpus itself changed between v1 and v2.
  If the authors respond and it did, this file gets updated and affected runs get
  re-tagged with the new `dataset_revision`.

An issue has been opened upstream asking about both.

## Ethics and scope

Both corpora are transcripts of **publicly published YouTube videos** —
counselling demonstrations and role-play, not clinical practice. No patient
consented to a therapy session; there is no protected health information in
either corpus. That is why the judge can be an external API here, and it is also
the ceiling on what any result from this benchmark can claim. See
[limitations.md](limitations.md).
