# Gen-2: scoping review and transparent instrument development

**Research protocol 2.20.0, amended 2026-10-22; 2.19.0 to 1.0.0 are retained in
`history/`. Status: prepared and amended before any pilot run; the search of
2026-09-13 is bounded as a scoping search with a prioritised evidence map, and the
human selection and clinical validation are not complete.** Earlier reading, prototype
experiments and proposals are formative development, not erased history.

The review has its own literature findings. The instrument may additionally use
expert proposals and empirical observations before, during or after searching.
Historical origin and strength of supporting evidence are separate. Finding a
relevant paper later does not turn an expert-origin idea into a literature-origin
idea. Igor's QA proposal is initially a candidate measurement method, not a new
quality construct. Author input is not expert consensus; another LLM is not an
independent human reviewer.

## Protocol and evidence

`protocol.json` defines the current sequence and workload. Previous versions are
retained in `history/`; each is superseded, not silently edited, and the live file
names the version it supersedes and carries a decision ledger with the origin and
date of every change.
`queries.json` holds the planned queries and says of each whether it ran; a query
that ran names the search log that carries its date, its record count and the
sha256 of its export, and three have not run. It said all fifteen were unexecuted
until 2026-10-21, twelve of them while a log recorded them as executed.
`retrieval-seeds.json` is a
known-source retrieval inventory, not an included-study table.
`prior-proposals.json` records prior exposure and proposals, not validated criteria.
`catalog/catalog.json` is the single versioned record of what the search of
2026-09-13 proposed: sources, candidate constructs, methods, measurement levels,
blind spots, a pilot proposal and the comparison with the earlier criteria map.
`catalog/README.md` explains its provenance; the page under `docs/` and the draft
registry beside it are generated from it, and hand edits to either fail the suite.
`catalog/source-properties.json` is the inductive half of the framework: what each
read source itself defines as a property of note quality, in its own words and with
its location, mapped to candidates only afterwards. A literature-origin candidate
must rest on at least one such property; a property no candidate covers is listed
as open in the catalog until the investigator decides.

Use JBI scoping-review guidance with explicitly recorded adaptations. Report with
PRISMA-ScR and PRISMA-S; neither checklist by itself establishes review quality.
Verify the methodological full texts before claiming adherence. One investigator
screens and reviews with disclosed AI assistance; a second human screener will be
recruited to cover the priority stratum and the audit sample on the exact sheets,
and a clinical panel is not planned (decision D2). Until the second screener records
decisions, screening is single-reviewer and is reported as such. Role-specific
external validation remains outstanding.

Search PubMed/MEDLINE, APA PsycINFO, Scopus and ACL Anthology; add backward and
forward citation searches and attributable professional guidance. Preserve exact
platform syntax, dates, exports and checksums. Pilot queries against known
relevant sources. Crossref and OpenAlex help link metadata but do not replace
an unsearched database. Unavailable databases remain named gaps.

Use three evidence layers: direct psychotherapy documentation evidence,
transferable evaluation methods, and requirements for the intended use. Separate
peer-reviewed studies, preprints, guidelines, software, expert proposals and local
observations. Link multiple reports of a study instead of counting them as
independent validations. Record reports not retrieved separately from full-text
eligibility exclusions. Disclose English/Czech full-text restrictions.

For each source, retain eligibility decisions and precise extraction locations.
For each measure, record population, language, purpose, raters, unit, response
format, validation design, limitations and what was actually checked. Adapt COSMIN
principles: a heterogeneous error checklist is not necessarily a reflective scale;
internal consistency, a fixed family count, model variance or prevalence gates do
not determine clinical importance. Semantic clustering is optional organization,
not psychometric validation.

## Development and actual human review

1. Record the protocol revision and prior exposure before the corresponding steps.
2. Execute and log searches; perform human screening and source-anchored extraction.
3. Record proposals and empirical inputs whenever they arise, with attribution,
   rationale and immutable origin references. Initial extraction does not force
   the prototype categories or any target number of constructs.
4. Review source classifications, interpretations, definitions, examples,
   applicability, four-purpose relevance and consequences of error. Keep rejected,
   unresolved and revised candidates as well as accepted ones.
5. Specify each selected measurement and method, including QA/claim-only designs:
   units, required information, outcome categories, severity rules and Czech wording.
6. Import the human's actual decisions on the exact material shown. The code binds
   response artifacts to content digests; typing a reviewer name is insufficient.
   It does not authenticate a person's identity or prove their interpretation true.
7. Freeze a reviewed instrument snapshot before pilot judgments. A new snapshot
   names its parent and amendment reason. Preserve historical origins. A separate
   literature-only snapshot can be taken when useful; it does not gate expert input.
8. Freeze exact reference and unit assignments before treating them as pilot
   reference data. Developmental findings may motivate revisions; subsequent
   confirmatory evaluation needs new independent evidence and preregistration.

Every pilot entry must follow the chain **origin/support -> construct -> observable
criterion -> operational measurement -> actual validation evidence or named gap**.
Source, evidence, construct, method, measurement, language and assessment scope
have separate review subjects. Changing their content invalidates their prior
acceptance. Independent conflicting decisions block acceptance until explicitly
resolved; original responses remain available. AI proposals cannot self-promote
into human-reviewed evidence.

The investigator's own clinical input is a declared part of the method, not an
unrecorded influence. Item generation draws deductively on the literature and
inductively on expert input, which is the prescribed procedure and is honest
only if the expert half is visible; `expert-input.json` records what he
contributed, when, why and what changed because of it, from the narrowing of the
round's purposes to the criterion the review had buried inside a bundled source
property. It is not an expert panel and says so: he is the instrument's author.

A review may be delegated, and the record then says so. On 2026-09-21 the
investigator, having decided every construct, declined to verify the sources and
evidence lines item by item and accepted them on the assistant's reading (decision
D9). Such a response is imported with `delegated: true`, must name the ledger
decision, can only accept, and is stored in the review mode `delegated`; every
frozen instrument snapshot lists the subjects that rest on it, so nothing built on
them is reported as human-verified evidence. The same day the investigator delegated
the operational rules and the translator choice as well (decision D10): the scope,
the three method specifications, the three rubric items and their Czech wording are
the assistant's proposal accepted without item-by-item review, and the feasibility
pilot is their first test.

## Commands

Install the optional extras with `uv sync --all-groups --all-extras`. The standalone
`therapy-note-eval` CLI accepts the same arguments after `tnb gen2`.
Use a new private workspace for each protocol revision; a study started on 2.0.0
keeps its snapshots and is refused by `pilot-plan`:

```sh
tnb gen2 --workspace local/gen2-research-v3 research init --protocol research/gen2/protocol.json --queries research/gen2/queries.json --proposals research/gen2/prior-proposals.json
tnb gen2 --workspace local/gen2-research-v3 research status
tnb gen2 --workspace local/gen2-research-v3 research export-protocol
tnb gen2 --workspace local/gen2-research-v3 research import-records --input local/export.nbib --format nbib --search-log local/executed-search.json
tnb gen2 --workspace local/gen2-research-v3 research screening-sheet --stage title_abstract
tnb gen2 --workspace local/gen2-research-v3 research import-screening --sheet SHEET_ID --input local/actual-human-response.json
tnb gen2 --workspace local/gen2-research-v3 research screening-sheet --stage full_text
tnb gen2 --workspace local/gen2-research-v3 research extraction-prompt --record-id RECORD_ID --input local/full-text.txt
tnb gen2 --workspace local/gen2-research-v3 research import-extraction --request-id REQUEST_ID --input local/candidate-extraction.json
tnb gen2 --workspace local/gen2-research-v3 research build-pool
```

Development commands do not require a prior literature freeze:

```sh
tnb gen2 --workspace local/gen2-research-v3 research record-input --input local/proposal.json
tnb gen2 --workspace local/gen2-research-v3 research compare-proposals --registry local/candidates.json
tnb gen2 --workspace local/gen2-research-v3 research import-proposal-decisions --comparison-id COMPARISON_ID --input local/actual-proposal-decisions.json
tnb gen2 --workspace local/gen2-research-v3 research registry-sheet --registry local/instrument-draft.json
tnb gen2 --workspace local/gen2-research-v3 research import-registry-review --sheet SHEET_ID --input local/actual-registry-review.json
tnb gen2 --workspace local/gen2-research-v3 research freeze-instrument --registry local/reviewed-draft.json
tnb gen2 --workspace local/gen2-research-v3 research validate --registry local/frozen-instrument.json --pilot
```

The Czech side of the paired design is produced by a recorded translator, not by
whatever model was at hand: `tools/translate_annomi_cs.py` measures candidates by
back-translation, records the chosen one with its provider, settings and prompt
digest, verifies that every conversation maps one turn for one turn, and writes an
EN/CS pair only for a conversation a person has read a sample of (decision D4,
audit A11). The ten earlier translations have no such record and are superseded.
Which two conversations the pilot translates is drawn by a seeded rule in
`research/gen2/translation/draw_pilot_cases.py` and recorded in `pilot-cases.json`
with the sample the translator check scores candidates on, taken from other
conversations; the test suite re-derives the record wherever the corpus is.

```sh
python tools/translate_annomi_cs.py select --sample local/sample.json --candidates a,b --back-translator c
python tools/translate_annomi_cs.py record --model a --check research/gen2/translation/back-translation-check-DATE.json --judges JUDGE_A,JUDGE_B --reason "actual reason"
python tools/translate_annomi_cs.py translate local/conversations/*.json
python tools/translate_annomi_cs.py review-sheet --conversation CONVERSATION --source local/conversations/CONVERSATION.json
python tools/translate_annomi_cs.py import-review --file local/gen2-translation/CONVERSATION.review.json --conversation CONVERSATION --reviewer NAME
python tools/translate_annomi_cs.py groups
```

Transcripts and their translations stay under the ignored `local/`; the records under
`research/gen2/translation/` carry digests, counts and model identity and no text.

Use the paths returned by each command, not the example filenames. Imports retain
actual responses; none of these commands performs a human review. To revise a
previous decision, create `registry-sheet --amend`; the sheet displays original
decisions and exports their explicit replacement links. New instrument and
literature snapshots use `--parent SNAPSHOT_ID --reason "actual reason"`.
`freeze-literature` remains available for reviewed source-derived subsets.

A proposal input has `id`, `kind` (`proposal` or `observation`), `content`,
`attribution` and `rationale`. Its recorded time describes entry into this workflow,
not the time the idea first occurred. Proposal decisions name the exact comparison,
actual reviewer, role, decision time, mode, reference, decision and reason; merge
decisions also name exact target constructs. Amended responses retain their parent.

## First feasibility pilot

The first round carries **every measurement the review supported** (decision D3):
the executable count is recorded at freeze, never capped, and what the human budget
cannot cover is reported as not measured. The catalog entries are not
comparable measures of one kind: a training condition, two
human-use outcomes, a corpus-level proxy and a derived ratio sit among them, and the
protocol keeps catalog entries, executable measures and study conditions as distinct
records. Retain the larger candidate registry and clinically important unresolved
measurements. Executable pilot parameters come from the exact reviewed protocol
revision.

The eligible cohorts are two English AnnoMI conversations and their two Czech
translations, produced by a recorded translation instrument that is never a judge
(decision D4; the earlier Claude translations are superseded and redone). The native
Czech sessions are excluded (decision D1): the planner refuses a native case as not
eligible, and adding a cohort is a protocol amendment, not a planner option.

With the two purposes this round serves (decision D8; with four it would be and two generator families the design freezes at most 32
generated notes. The investigator's development budget is at most 16 balanced notes
and 120 unique annotation-unit decisions plus 30 blinded repeats within 8-12 hours
including reference checks; that is a budget of annotation units bounded by time,
not a count of notes. This is not the time budget for the whole review. If
preparation exceeds it, amend and reduce the sample; report the actual coverage
rather than marking unreviewed units complete.

The human anchor is two Czech psychologists (decision D2). Each rates one language
of each conversation in a crossover, so every conversation is rated in both
languages and no rater sees a conversation twice; an overlap block rated by both in
the same language is the only source of between-rater agreement, and blinded
repeats give within-rater agreement. Calibration uses notes outside the rated
sample; agreement is reported with Gwet's AC1/AC2 per item, with disagreements
retained. Counts for the confirmatory study are fixed in a later amendment from the
pilot's timing and agreement. This anchors the feasibility of the rating task; it is
not confirmatory validation, model ranking or clinical validation.

Check translation meaning, important-information banks, unanswered information
needs and atomic segmentation before using them as references. Prepare banks
before candidate-note exposure. Balance assignments across purposes, languages,
corpus origins and model families, retaining related sessions and translations in
one split. Never expose future sessions. The native Czech data are one client and a
permanently private track outside this pilot; TN-Eval's 43 videos are known grouping
units, not established client IDs.

Use two judge families and explicit replicate IDs for real repeated calls. Compare
response formats on the same units; test granularity separately. Include verified
correct controls and targeted errors. Enriched controls do not estimate natural
error prevalence. Report confusion, false alarms, sensitivity, missingness, time
and costs; agreement alone does not choose the method.

Freeze exact unit assignments after reviewed references exist. `pilot-plan` freezes
the workload and balanced note sample; it does not manufacture reference approvals,
unit assignments or human judgments. The next human round must supply those.

## Release and claims

Raw full texts, source passages, clinical derivatives and human responses remain
private. `export-protocol` stages a protocol bundle, excluding raw proposals,
clinical data and reviews; it does not publish or register it. Review the staged
bundle before release. A local timestamp or Git commit is not independent public
preregistration. Record an external registration only when it actually occurs;
preregister the later confirmatory study before its judgments.

Methodological sources for full-text verification include JBI guidance;
PRISMA-ScR (10.7326/M18-0850); PRISMA-S (10.1186/s13643-020-01542-z);
COSMIN content validity (10.1007/s11136-018-1829-0); and Boateng et al.
(10.3389/fpubh.2018.00149). These are a retrieval inventory, not completed review
findings. The latest attempted PRISMA-S retrieval was rejected before execution
by the approval service's API 404. It is not a completed literature search.
