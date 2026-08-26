# What exists for benchmarking psychotherapy note generation

*Surveyed 2026-08-23. Every claim below was checked against the primary source —
the paper, the repository tree, or the API — not against a search snippet. Where
something could not be verified, it says so.*

## Short version

For the specific task of **generating a clinical note from a psychotherapy
session transcript**, there are exactly two public resources, both from the last
eighteen months, and neither is an established standard:

| | iCARE / iHOPE | TN-Eval |
|---|---|---|
| Venue | medRxiv preprint (v2, 2026-08-19) | ACL 2025, Industry Track |
| Peer reviewed | No | Yes |
| Corpus | 174 sessions (HOPE / YouTube, re-transcribed) | 50 conversations (AnnoMI) |
| Gold notes | Yes — expert-written, 17 sections | Yes — therapist-written, SOAP |
| Evaluation | Reference-based + TRACE human framework | Rubric, **reference-free** |
| Licence on data | **None published** | **None published** (Apache-2.0 covers the code) |
| Models benchmarked | 11 (2025-era) | 7 (2024-era) |

Nobody has re-run either of them on current models. That is the gap this
repository fills.

Two more corpora from the iCARE group cover the adjacent task of *counseling
summarization* — **MentalCLOUDS** (191 sessions, JMIR Mental Health 2024) and
**MEMO** (KDD 2022, released on request) — and a third, **TheraFuse** (IEEE JBHI
2026), republishes the iHOPE corpus in a more usable form. None of them appears
in any existing survey of this task. See
[What the search did turn up](#what-the-search-did-turn-up).

## iCARE / iHOPE

- Code and data: <https://github.com/proadhikary/iCARE>
- Preprint: <https://www.medrxiv.org/content/10.1101/2025.06.25.25330252>

**The naming is confusing because it changed between versions.** Version 1
(2025-06-25, *"Towards Richer AI-Assisted Psychotherapy Note-Making and
Performance Benchmarking"*) calls the corpus **PATH**. Version 2 (2026-08-19,
*"Clinically Grounded AI-Scribing in Psychotherapy: Benchmarking LLMs Against
Expert Documentation in the iCARE Framework"*) renames it **iHOPE**. Both names
refer to the same thing. Throughout this repository the v2 naming is used:

- **iCARE** — the documentation *format*: 17 sections grouped as Identifying
  information, Chief concerns and clinical history, Assessment and analysis,
  Risk identification, Evaluation of progress and action plan. Developed by
  iterative review with psychiatrists and clinical psychologists at AIIMS Delhi.
- **iHOPE** — the *corpus*: 174 therapy sessions re-transcribed and
  speaker-diarised (WhisperX) from the older public **HOPE** dataset of YouTube
  counselling demonstrations, with expert-written gold-standard notes in the
  iCARE format.

Verified from the repository tree: `Data/train` holds 134 session directories,
`Data/test` holds 40 — 174 total. Each session directory contains the transcript
and the expert gold note as two CSV files. The 17 section prompts live in
`instructions.json` under the `doctors_prompts` key.

Eleven models were benchmarked (nine open-weight, two proprietary) in zero-shot
and one-shot settings, scored with BLEU, METEOR, ROUGE-L, BERTScore, BLEURT and
InfoLM, plus **TRACE** — a five-domain human evaluation framework
(Trustworthiness, Relevance, Accuracy, Comprehensiveness, Expression) introduced
in v2.

**Three caveats that shaped this benchmark's design.**

1. *The TRACE annotations are not published anywhere.* This was searched for
   rather than assumed — see [Where the TRACE data is not](#where-the-trace-data-is-not).
   Our TRACE implementation is therefore a re-implementation with no human
   anchor, and is labelled as such everywhere it appears.
2. *The authors report that automatic metrics disagree with clinical judgement.*
   From the v2 abstract: "clinical preference did not always mirror automatic
   benchmarks, with Mistral, a smaller open model, emerging as a surprise
   favourite", and "lexical overlap with human notes was low despite strong
   semantic alignment". A leaderboard built on ROUGE alone would rank models by
   a measure the source paper says misses the point. See
   [methodology.md](methodology.md) for how this track is scored instead.
3. *Every model failed at temporal reasoning* — "past-session and next-session
   details". This is reported as its own column rather than averaged away.

The corpus carries **no licence file**. The spreadsheet of published scores
referenced by the repository README is absent from the tree, so the paper's
numbers can only be transcribed from the PDF, not re-derived.

### Where the TRACE data is not

The TRACE human ratings are the one artefact that would let an automated TRACE
scorer be calibrated against clinicians. Searched on 2026-08-23, in this order:

1. **The paper's own Data Availability statement** (v2 full text, JATS XML). It
   reads: *"All conversation transcripts used in this study and all source code
   for benchmarking experiments are publicly available in
   https://github.com/ai4mhx/iCARE (accessed April 26, 2025)."* Transcripts and
   code — human ratings are not claimed to be published.
2. **`ai4mhx/iCARE`**, the repository that statement names, is a fork of
   `proadhikary/iCARE` with identical content: same six commits, same size, last
   pushed 2025-04-28. Two URLs, one repository.
3. **All seven repositories of the `ai4mhx` organisation** ("AI for Mental Health
   Experts", the authors' group, recently rebranded as *Manashi*).
4. **All 112 repositories of `LCS2-IIITD`**, the group's earlier lab org.
5. **Hugging Face** — the first author's account holds three datasets, none
   related; searches for iHOPE, iCARE, MentalCLOUDS and AIIMS return nothing.
6. **The group's own publication list** (20 entries on their site) — no dataset
   link for TRACE.

The finding is negative and it is a real finding: the ratings are not public.
The likely route is a request, which is how this group releases data elsewhere —
see MEMO below.

### What the search did turn up

Three datasets and one instrument from the same lab, none of which appear in any
survey of this task:

- **TheraFuse** — [ai4mhx/TheraFuse](https://github.com/ai4mhx/TheraFuse), IEEE
  Journal of Biomedical and Health Informatics 2026. Its `data/` directory ships
  `graph_train_aiims.json` and `graph_test_aiims.json`: **134 + 40 = 174
  sessions**, ids matching the iCARE split directories exactly, each with the
  dialogue and the gold note already joined. This is the iHOPE corpus in a far
  more usable form than 174 directories of CSV pairs, published openly with no
  request needed. One session has an empty summary. Median dialogue 9020
  characters, median note 1263.
- **MentalCLOUDS** — *Exploring the Efficacy of LLMs in Summarizing Mental Health
  Counseling Sessions*, [JMIR Mental Health 2024](https://mental.jmir.org/2024/1/e57306).
  191 counseling sessions with component-guided gold summaries across three
  counseling aspects, eleven LLMs benchmarked, expert qualitative assessment.
  Not on GitHub or Hugging Face.
- **MEMO** — [LCS2-IIITD/MEMO](https://github.com/LCS2-IIITD/MEMO), KDD 2022. A
  counseling summarization dataset released **on request**: a consent form plus
  an email. The repository contains nothing but those instructions. This is the
  precedent for how the group shares data.
- **MASES** — *Development of a Standardized Clinician-Oriented Scale for
  Evaluating AI-Generated Medical Summaries*, Indian Journal of Medical Research
  2026. A clinician-facing evaluation scale from the same authors, plausibly
  TRACE's published sibling.

Aspect-based *counseling summarization* (MEMO, MentalCLOUDS) is a near neighbour
of *note generation in a documentation format*, not the same task: the target is
a summary organised by counseling component rather than a clinical record
organised by a documentation standard. They are listed here because any survey
that misses them is incomplete, not because this benchmark scores on them.

## TN-Eval

- Code: <https://github.com/amazon-science/TN-Eval> (Apache-2.0)
- Data: <https://github.com/amazon-science/TN-Eval-Data>
- Paper: <https://aclanthology.org/2025.acl-industry.14/>

Built by Amazon with licensed therapists over the **first 50 conversations from
the high-quality split of AnnoMI** (median length 1067 words / 42 turns). For
each conversation the data repository ships three notes — one therapist-written,
one from Llama 3.1 70B, one from Mistral Large V2 — together with ratings from
**two human annotators** and two LLM judges. Twenty-two therapists took part
overall: five co-designing the rubric, thirteen writing notes, nine evaluating.

The rubric covers the four SOAP sections with **23 completeness criteria**
(subjective 6, objective 5, assessment 8, plan 4), scores conciseness
**sentence by sentence**, and adds 1–5 Likert ratings for completeness,
conciseness and faithfulness.

**Its central result is the reason this repository scores the way it does.**
Krippendorff's alpha between human annotators:

| | Rubric protocol | Likert 1–5 |
|---|---|---|
| Completeness | 0.52 | **0.08** |
| Conciseness | 0.49 | **0.16** |
| Faithfulness | 0.62 | **0.18** |

A 1–5 scale produces near-zero agreement between trained therapists on this
task. Criterion checklists produce usable agreement. Any leaderboard in this
area that rests on Likert scores is measuring noise.

The paper also finds that LLM judges track humans well on completeness and
conciseness but **struggle on faithfulness**, and that in blind comparison
therapists preferred LLM-written notes to therapist-written ones.

Crucially for us, the protocol is **reference-free** — it needs the transcript
and the candidate note, not a gold note. Any new model can be measured on it.

The evaluation code targets AWS Bedrock; this repository swaps the backend for
an OpenAI-compatible client while keeping the prompt wording unchanged. AnnoMI
itself (133 transcripts) publishes **no licence file**, only a citation request.

## Has anyone already done this?

No. Checked five ways on 2026-08-23:

| Check | Result |
|---|---|
| Forks of `amazon-science/TN-Eval` | 1 — a mirroring bot, no commits beyond upstream |
| Forks of `proadhikary/iCARE` | 1 — `ai4mhx/iCARE`, push timestamp identical to upstream, i.e. unchanged |
| GitHub search: `therapy notes benchmark`, `SOAP note generation evaluation`, `psychotherapy notes LLM evaluation` | zero results (a control query returned results, so search was working) |
| Hugging Face | no leaderboard or Space for therapy note generation |
| Literature 2025–2026 | frontier models are being benchmarked on note generation, but in **general medicine** |

### Closely related work worth knowing about

- **[Omi-Health/medical-note-eval](https://github.com/Omi-Health/medical-note-eval)**
  — MIT, actively maintained (last update 2026-08-19). A maintained leaderboard
  over eight frontier models on 300 synthetic ambulatory primary-care dialogues,
  measuring hallucinations against omitted safety facts. Its headline result —
  omissions were 43× more common than hallucinations — is worth reading before
  designing any note metric. **It states explicitly that mental-health notes are
  not tested.** If you want general medicine, go there; this repository covers
  the ground they exclude.
- **[arXiv:2605.24902](https://arxiv.org/abs/2605.24902)** — source-aware
  evaluation of frontier LLMs on SOAP note generation across OMI Health,
  ACI-Bench and PriMock57. General medicine, and a one-off study rather than a
  maintained leaderboard.
- `justlab-ai/oss-20b-aci-bench` — a single evaluation run of gpt-oss on
  ACI-Bench.

### The instrument this field uses to mean "quality"

**[PDSQI-9](https://arxiv.org/abs/2501.08977)** — the Provider Documentation
Summarization Quality Instrument, published January 2025. It is the successor
to PDQI-9, which was written for provider-authored notes, and it exists because
that older instrument does not address what LLM summarisation gets wrong:
hallucination, omission, relevance.

Nine attributes: **accurate, citation, comprehensible, organized, succinct,
stigmatizing, synthesized, thorough, useful**. Five-point scales and binary
scales, depending on the attribute. Validated on real EHR data — 200 patients
with 3–5 prior encounters each, across 11 specialties — reaching an ICC of
0.867 between raters.

**This benchmark measures two of those nine**, and reports a third under a name
that means something else:

| PDSQI-9 attribute | Here |
|---|---|
| Thorough | `completeness` — **the column the leaderboard is ordered by** |
| Accurate | `faithfulness`, on which two therapists reach an alpha of 0.18 |
| Succinct | not measured. `conciseness` counts sentences that fit a rubric item, and its own definition says it "does not mean the note is short" |
| Organized, synthesized, useful, comprehensible, citation, stigmatizing | not measured at all |

**Why it is not simply adopted.** PDSQI-9 was validated with *physicians* doing
the rating; the authors state they did not compare LLM raters against human
ones. Scoring these notes on it with an LLM judge would produce nine columns
with no human anchor for any of them — which is exactly what this repository
already labels TRACE as, and labels it everywhere it appears. Adopting the
instrument properly needs clinicians rating the notes in `generations/`, which
is a study rather than a code change.

The closest thing here is TRACE, whose five dimensions (trustworthiness,
relevance, accuracy, comprehensiveness, expression) overlap PDSQI-9's
construct more than the rubric does — and which has no human anchor and,
measured on 2026-08-26, separates the sixteen models across 5.6% of its scale.

## Adjacent, but a different task

These come up in searches for "therapy benchmark" and are not about notes:

- **TherapyGym** (Stanford) — clinical fidelity and safety of therapy
  *chatbots*, via an automated CTRS pipeline plus a safety annotation scheme.
  Its TherapyJudgeBench holds 116 dialogues and 1270 expert ratings. Measures
  the quality of the therapist, not the documentation.
- **CounselBench, PsychEval, MentalBench, PsychiatryBench, MentalChat16K** —
  counselling quality, patient simulation, or psychiatric question answering.
- **ACI-Bench, PriMock57, MTS-Dialog, NoteChat** — note generation, but general
  medicine. ACI-Bench is the largest; PriMock57 has 57 encounters; MTS-Dialog
  holds roughly 1700 dialogue snippets rather than full encounters.

## What does not exist at all

Nothing in Czech. Nothing on real clinical sessions — the entire field runs on
YouTube demonstration videos and role-play. Nothing on payer or insurer
compliance requirements. And human agreement is either low or openly fragile
everywhere you look. That is the state of the field, not a gap in this survey.
