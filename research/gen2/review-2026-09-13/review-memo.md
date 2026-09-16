# Gen-2 scoping review, executed round of 2026-09-13

**Status: searches executed, screening and construct selection are AI proposals.
This is not a completed scoping review and must not be reported as one.**

The previous round (`local/gen2-literature-2026-09-13/`) could not reach the
network and produced a formative map from local instrument reproductions. That
round is preserved unchanged. This round had working network access and executed
the planned searches.

## What was actually done

1. Verified the methodological guidance before searching, as protocol 2.0.0
   requires. PRISMA-ScR (accepted manuscript from a repository, not the version
   of record), PRISMA-S (publisher PDF) and the JBI conduct guidance (Peters et
   al. 2020, the journal version of the manual chapter) were retrieved and read.
   The JBI wiki chapter itself is JavaScript-rendered and returned no text.
2. Ran a pre-search sensitivity check. **The planned queries missed known
   relevant work**: the PDSQI-9 validation paper that the protocol names as a
   retrieval seed was retrieved by neither planned query. Six amendments were
   recorded in `amendments.json` *before* the amended queries were executed.
3. Executed six PubMed searches through the E-utilities and three ACL Anthology
   searches against a checksummed download of the complete Anthology corpus.
   Every result set was downloaded in full. `search-log-pubmed.json` and
   `search-log-acl.json` hold the exact queries, dates, counts and export
   checksums.
4. Built one deduplicated pool of 10 223 records (10 059 until the DOI correction of
   2026-09-15, when the pool builder was found to take a cited reference's DOI for a
   third of the PubMed records), screened a 487-record priority stratum, and audited
   a random sample of 200 records from the remainder. The corrected stratum holds
   507 records: the 487 screened ones and 20 that entered it only through the
   correction and are listed as not screened, never as excluded; the remainder is
   9 716.
5. Sought 19 catalog reports: 12 evidence papers, 2 guidance documents and 5
   methodological guidance documents. Eighteen were retrieved and read by the
   assistant; one, the 2008 PDQI-9 preliminary paper, was not. Six evidence papers
   reached the full-text stage through the search and screening; the other thirteen
   reports entered through other routes (known sources, professional and
   methodological guidance, an author search from Keren 2026), which `reports.json`
   records per report and `flow.json` derives. Two attempts failed before a copy was
   obtained: the Walker paper was first fetched under a guessed PMID, and Keren 2026
   was supplied by the investigator after every open route failed.
6. Produced a 29-candidate registry, a 17-method inventory, a 13-level map of
   assessment units, 11 worked blind spots, a line-by-line comparison with the
   previous 26-candidate map, and a 14-measurement pilot proposal. The protocol's
   8-12 target came from the task brief, not from the review; it was withdrawn on
   2026-09-15 (decision of the investigator): every supported measurement is carried,
   and what the human budget cannot cover is reported as not measured.

## What could not be done

| Gap | Detail |
|---|---|
| **Scopus** | Not searched. `api.elsevier.com` returns HTTP 401 without a key. The sibling `destilo` project was checked at the user's suggestion: its `.env` and `.env.example` hold `CORE_API_KEY` and `NCBI_API_KEY` but **no Elsevier or Scopus credential**, and a repo-wide search found Scopus mentioned only in a design note recording that Taylor & Francis, APA and Elsevier paywalls return 404. |
| **APA PsycINFO** | Not searched. EBSCOhost requires an institutional login. PsycINFO was the only database planned for the requirements layer, so amendment AM-2 added a PubMed requirements query that recovers part, not all, of that coverage. |
| **9 716 records unscreened, and 20 more in the priority stratum** | The priority ordering is not a screen. The audit estimates **291 eligible records [95% CI 134-621]** below the threshold, or 534 [301-931] counting borderline cases (the judgement of 2026-09-13, recomputed over the remainder after the DOI correction). Two of the six clear finds were direct or requirements evidence, so the gap is not confined to NLP method papers. Twenty records entered the priority stratum only through the correction of 2026-09-15 and have no proposal yet. |
| **No human screening** | JBI asks for a minimum of two reviewers at selection and at least two at extraction. This round has one investigator and an AI assistant. Every include/exclude in `screening-decisions.json` is an AI proposal. |
| **One report not retrieved** | The 2008 PDQI-9 preliminary-development paper (S5). The Psychotherapy Research 2026 paper was supplied by the investigator on 2026-09-13 after every open route failed and is retrieved; `reports.json` keeps the failed attempt beside the supplied copy. Not retrieved is not an eligibility exclusion. |
| **Abstract-only sources** | 13 sources were judged relevant from title and abstract alone. Their instruments and validation are **not** verified, and the registry marks every candidate that leans on them. |
| **ACL recall** | Only 62.9% of Anthology records carry an abstract; the rest were searched on title alone. |

## Findings that change what we should build

### The rubric we reproduce has graded importance and we flattened it

TN-Eval annotates every rubric item with one of five importance levels —
*Mandatory, Mandatory in certain circumstances, Highly recommended, Good to have,
Optional* — agreed by five therapists (Fleiss' kappa 0.68, Krippendorff's alpha
0.73), and computes completeness as a micro average weighted by section. Our
reproduction treats the items as an equal-weight checklist. **A missed mandatory
safety item and a missed homework item currently cost the same.** This is the
single most consequential divergence found.

### PDSQI-9 was validated on a corpus that excluded psychotherapy

Verbatim from its methods: *"excluded psychiatry notes. Psychotherapy notes were
excluded due to their highly sensitive nature and additional regulatory
protections under HIPAA and 42 CFR Part 2."* Its Cronbach's alpha of 0.879 and
ICC of 0.867 are real, and they were earned on multi-document EHR summaries with
psychotherapy deliberately removed. Transfer to our task is an untested
extrapolation, and the source itself is evidence that these notes are treated as
a special category.

### The same instrument family has a published failure, and rater training is the likeliest difference

Walker et al. 2017 applied PDQI-9 to 220 emergency department notes and found
Cronbach's alpha 0.93 alongside **between-rater Pearson r = 0.07 (p = 0.270)**
and an inability to distinguish good from poor notes, F(3,34) = 1.15, p = 0.342.
Their methods say raters *"were not trained in the use of the tool and there was
no pre-study agreement between raters about standards."* PDSQI-9, which trained
its raters, reached ICC 0.867 — on a different instrument version, sample, rater
pool and statistic, so the pair motivates training without establishing its causal
effect or its size (audit A06). Two lessons: train raters before any use of the
instrument, and measure what the training does rather than assume it; and **high
internal consistency is not agreement** — 0.93 and 0.07 came from the same study.

### Rating format and task decomposition change the conclusion, but we cannot say which did it

In TN-Eval, Likert-rating experts judged LLM notes superior to human notes on
every dimension including overall acceptance. The rubric protocol reproduces that
order for completeness and conciseness but **reverses it for faithfulness**. The
rubric changed the unit, the task and the response format at the same time, so
this is not evidence that the response scale alone caused the difference. It is
evidence that the finding is fragile to how you ask.

### Automatic metrics and expert judgement disagree, in two independent direct-layer studies

MentalCLOUDS concludes that task-specific models win on ROUGE and BERTScore while
*"expert assessments indicate that these models are not yet reliable for clinical
application."* This replicates the disagreement iCARE reports. Reference overlap
metrics belong in the report as descriptive numbers, not as quality measures.

### The Czech audit specification exists, and the obvious source is repealed

Decree No. 98/2012 Coll. was **repealed by Decree No. 444/2024 Coll. with effect
from 1 January 2025**. The instrument in force is Decree No. 444/2024 Coll. on
medical documentation, whose Section 2 enumerates the required content of
medical documentation. (The exact Czech titles are carried in the registry.) Until now the
audit purpose had no Czech specification at all.

### The APA guidance we were pointed at has expired by its own terms

*"These guidelines are scheduled to expire 10 years from February 16, 2007."*
Whether a successor is in force was not established. It is US guidance and is not
a Czech requirement in any case.

### The client purpose has a literature we have not used

Nationwide surveys of mental health patients reading their own records, a Delphi
on the benefits and harms of open notes, and an existing scoping review on
sharing notes with people affected by mental health conditions. All were reached
by the amended searches and none has been read in full. The Swedish survey's
three categories — errors, omissions and offenses — map onto the client purpose
more directly than anything we currently measure.

### The most directly relevant paper is closed to open routes; the investigator supplied it

Keren, Klein, Bar-Shachar, Liakata and Atzil-Slonim, *A comparative evaluation of
LLM-generated and clinician-written psychotherapy session summaries*
(Psychother Res 2026, doi:10.1080/10503307.2026.2729093) is the closest study to
this project's task that the searches found. Every open route was tried:
Unpaywall, OpenAlex, Europe PMC, Semantic Scholar, OpenAIRE, arXiv, the Crossref
text-mining links the publisher itself registered (Taylor & Francis answers all
three with HTTP 403), and CORE.ac.uk with an API key, which has no copy by DOI or
title. There is no preprint and no repository deposit. The remaining legitimate
routes are institutional access, an author request, or waiting for the QMUL
deposit that UK funding rules require.

Later on 2026-09-13 the investigator supplied the publisher PDF (770 608 bytes,
SHA-256 beginning 9fa66024); the failed attempt and the supplied copy are both
events on the report in `reports.json`, and its status is retrieved. The paper was
read by the coding assistant from that PDF; it is not human-verified.

Its structured abstract was obtained, and it is substantial: 1008 segment-level
summaries, 504 clinician-written and 504 LLM-generated, over **108 five-minute
segments from 36 sessions**, judged blind to source on **factual consistency,
salient meaning preservation and clinical value**, using the transtheoretical
MIND framework. Clinician summaries won overall; at component level the model was
better at preserving central themes, and there was no difference on the clinical
value of the therapeutic relationship or intrapersonal functioning.

Searching by author then found the same team's **open-access companion study**
(JMIR Form Res 2026, PMC13069367), which sets out the same three-dimension
framework in full and supplies its rating design and its operational definition
of personalisation. It was found first; the session-summary paper itself was
supplied by the investigator the same day and read from the PDF, so its template
and agreement figures are read (AI extraction, human verification pending), not
unverified.

### A construct the previous map had no room for at all

From that companion paper: **personalisation**. Models "struggle with
personalization, defaulting to generic phrasing", which the authors attribute to
a "regression to the mean" — a language model aims at the most probable text and
so returns to safe, generic wording. Their evaluators found a trade-off: model
summaries were *more* comprehensive, human summaries better at focusing on what
was clinically salient.

This is a failure mode that passes every other criterion. A note can be
faithful, complete, well-organised and economical, and still be a note that would
fit half the other sessions. Nothing in the previous 26-candidate map detects it,
because it is only visible by comparing a system's notes **with each other** —
candidate K28, method ME17, assessment level L9. It is added, with its own
warning: the diversity proxy varied with the embedding model in the source study,
and high diversity can also mean hallucination, so it may only be read on notes
that already passed a faithfulness check.

### The supervision purpose does not

This is a negative finding and is recorded as one. The closest support is a
structured field for therapist reflections in iCARE, which iCARE does not claim
serves supervision, and a coding system for supervision sessions rather than
notes. Of the four declared purposes, supervision is the least evidenced.

## Two more errors found by auditing, not by a failing test

Before anything was committed, the pool was audited. Two faults surfaced, both mine.

**The BibTeX parser corrupted 1886 of 10066 recorded DOIs.** `acl_search.py` appended
any line it did not recognise as a collected field to the preceding one, so
`pages = "1--11",` landed inside the `doi` it followed. Because the record identifier
is derived from the DOI, those records could not deduplicate. Fixing it merged seven
records: unique records 10066 to 10059, duplicates removed 1296 to 1303. Query hit
counts and the screened set are unchanged, because screening reads title and abstract.

**Screening decisions were recorded as positions in an ordering that then moved.** The
parser fix left the 487-record priority set identical but shifted 29 positions inside
it, which would have silently reassigned decisions to different papers. Decisions are
now keyed by record title in `include-candidates.json`, and `screen.py` refuses to run
if a decision names a record the priority stratum does not contain.

The same audit removed a Google Scholar session token that a PubMed record carried
inside its `doi` ArticleId, which would otherwise have been committed as part of a
record identifier. DOI fields are now normalised at both ingest sites.

## A retrieval error found by reading, not by trusting

The first attempt to fetch the Walker negative finding used a guessed PMID
(28197625). That identifier belongs to an unrelated oncology paper, and the
retrieval pipeline returned its text without complaint. The error surfaced only
because the downloaded file was read. The correct record (PMID 28956888) was then
resolved by title search. `fulltext-retrieval-log.json` records the correction.

## What a methods section may truthfully say

"We executed a scoping search of PubMed and the complete ACL Anthology corpus on
2026-09-13, retrieving 11 397 records and 10 223 after deduplication (corrected on
2026-09-15 from 10 059 when the pool builder was found to take cited references'
DOIs). Scopus and
APA PsycINFO were not accessible and remain unsearched. Query amendments were
recorded before use, following a sensitivity check against known relevant works.
One investigator with AI assistance screened 487 of the 507 records in the priority
stratum (20 entered it after the screen, through the correction) and audited a random
sample of the remainder, estimating that 291 [134-621] eligible
records were left unscreened. Nineteen catalog reports were sought and eighteen
retrieved and read by the assistant; six evidence papers reached full text through
screening and the rest through declared routes; one report was not retrieved. Screening and
construct proposals await independent human review; no dual independent screening
was performed."

It would be inaccurate to describe this as a completed scoping review, to claim
that the seven families are validated dimensions, or to present any candidate as
ready for publication-grade measurement.

## What happened after this round

This memo records the round of 2026-09-13 and is not rewritten when later work
changes something. What has changed since:

- **2026-09-16.** The investigator supplied full texts for six of the thirteen
  abstract-only reports: the scoping review on sharing notes with mental health
  patients, the Swedish survey of what those patients find in their records, the
  supervision coding study, the npj scoping review of language models in mental
  health care, the study of what clinicians edit in AI drafts, and the emergency
  department note-quality tool. `reports.json` records each as retrieved on that
  date, by an investigator-supplied route, with a checksum. **Nobody has read
  them.** Their reading basis is still the abstract and every claim resting on
  them is still an abstract-level claim, which `tests/test_review_ledger.py`
  holds them to. Reading them is a later round, with its own extractions.
- **2026-09-16.** The candidate list moved from 29 to 31 in the catalog revision
  that answered audit findings A07 and A08. Language naturalness returned as K30
  and redundance became K31, separate from economy. The catalog carries the
  revision and its reasons; this memo keeps the count the round itself produced.

## Outputs

| File | What it is |
|---|---|
| `amendments.json` | Query amendments with the sensitivity check that motivated them |
| `search-log-pubmed.json`, `search-log-acl.json` | Exact queries, dates, counts, export checksums |
| `pool-summary.json`, `screening-strata.json` | Deduplication and the ordering rule |
| `screening-decisions.json` | Per-record AI include/exclude proposals and the audit estimate |
| `fulltext-retrieval-log.json` | The retrieval attempts of 2026-09-13, by route, with the correction; the historical log, frozen |
| `report-map.json`, `reports.json` | The report-level evidence ledger: one record per report, its route, identifiers, pool position, retrieval events and derived status; `ledger.py` holds the rule, `build_reports.py` builds it |
| `flow-recorded.json`, `flow.json` | PRISMA-style counts end to end, generated by `build_flow.py` from the ledger and the records; the recorded file holds what cannot be derived; hand edits to `flow.json` fail the suite |
| `local/gen2-review-2026-09-13/outputs/gen2-mapa.html` | The clickable Czech map |
| `local/.../outputs/gen2-map.svg`, `.pdf` | Static export |
| `local/.../outputs/gen2-registry.json` | Everything as structured data |
| `local/.../outputs/*.csv` | Candidate, method and level/blind-spot tables |

Full texts are under `local/gen2-review-2026-09-13/fulltext/` and are not
published.

The registry, the map and the tables are written in Czech because Jan asked for
them in Czech. They therefore live under `local/`, which git ignores, exactly as
the previous round's map did. `tests/test_no_clinical_content.py` locks the Czech
allow-list to three authored resource files and that guard was left untouched.
The English audit trail above stays tracked under `research/gen2/review-2026-09-13/`.
