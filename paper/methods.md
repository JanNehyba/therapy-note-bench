# Methods

**Draft of 2026-09-21. Not yet reviewed by the investigator. Every figure below
is read from a committed artefact of the repository on that date and names the
file it comes from; when an artefact changes, the sentence that quotes it is
wrong until it is re-read.**

## Design

We develop a bilingual instrument for the quality of psychotherapy session
notes and a benchmark that applies it to model-written notes in English and in
Czech. The work reported here is the first phase of instrument development,
item generation followed by content validity (Boateng et al., 2018; Terwee et
al., 2018). Items were generated deductively, from a bounded scoping search of
the literature and the instruments it found, and inductively, from a criteria
map this project recorded before the search, three named expert proposals and
one repeated observation of our own outputs; drawing on both is what the
procedure prescribes rather than a mixture to be explained away. The
investigator's clinical input during development is recorded entry by entry with
its date, its rationale and what changed because of it
(`research/gen2/expert-input.json`), each entry stating the proposition, the
argument behind it and what it rests on, and each marked as awaiting his
confirmation of the assistant's wording, so that the inductive half is readable
rather than absorbed: it contains, among others, the objection that the first
framework was not inductive at all, which produced the source-first extraction,
and the objection that language naturalness is not clinical terminology, which
produced a construct the review had buried inside a source property that named
several concepts at once. The framework
is nevertheless reported from the sources upwards, because that is the part a
reader can check: for every source read in full we list every property of note
quality the source itself defines, and 33 of the 34 candidates are anchored in
at least one such property. The prior map is reported as the comparison the
framework was tested against rather than as its derivation, and the one
candidate no source defines is named. What the procedure requires besides is
that the origin of every item is declared and never rewritten when support is
found later, and that every claim about a source carries the passage it rests
on. One rule makes the
mixture safe and is enforced by the repository's validator: a construct may be
proposed for measurement only when at least one of its evidence lines quotes a
source read in full. An idea may come from anywhere; what is measured must be
supported. An earlier draft described this as a best-fit framework synthesis;
that method begins from a published framework, ours began from our own
prototype, and the citation is withdrawn. The instrument is developed for two purposes of a note,
continuity of care and documentation audit; supervision and client
communication remain declared and out of scope for this round. A feasibility
pilot on a small balanced sample precedes any confirmatory study; the present
paper claims a framework and a design, not a validated instrument.

## The prior framework

Before the search, the project held a map of 26 criteria that had accumulated
from a prototype of the instrument, from proposals by colleagues and from the
investigator's design requirements. The map, and eight named prior proposals
behind it, were recorded on 2026-09-12 with their origins
(`research/gen2/prior-proposals.json`), so that no criterion could later be
relabelled as having come from the literature.

## Search

On 2026-09-13 we searched PubMed/MEDLINE through the NCBI E-utilities with six
queries and the complete ACL Anthology corpus (131 040 records, searched offline
against title and abstract) with three, in four layers: direct evidence on
psychotherapy notes and session summaries, transfer evidence from clinical
documentation and general summarisation, professional and legal requirements,
and, in the Anthology, summarisation evaluation. Exact strings, execution
dates, counts and export checksums are logged (`search-log-pubmed.json`,
`search-log-acl.json`) and reported in the appendix following PRISMA-S. Query
amendments were recorded before use after a sensitivity check against known
relevant works (`amendments.json`). APA PsycINFO and Scopus were planned and not
searched, for want of institutional access; they are reported as a limit.

The searches returned 11 397 records (8 820 and 2 577); 35 book-chapter records
were not parsed into the pool and are counted rather than dropped; 10 223 unique
records remained after deduplication by DOI, then PMID, then normalised title
(1 139 removed; `pool-summary.json`, `flow.json`).

## Screening

Records were ordered by a priority rule and a stratum of 507 was screened with
AI assistance by one investigator: 487 received a proposal (192 include,
295 exclude), 20 entered the stratum after a correction of the pool builder and
are listed as not screened, and the remaining 9 716 were not screened. No
screening proposal has yet received a human decision, and no second screener
has been recruited; screening is therefore single-reviewer and AI-assisted, and
is reported as such. A simple random sample of 200 records from the unscreened
remainder found 6 clearly eligible and 5 borderline records, which estimates
291 eligible records left unscreened (95% Wilson interval 134 to 621;
`screening-decisions.json`). We call the whole a scoping search with a
prioritised evidence map, not a scoping review.

## Sources and evidence

Nineteen reports were sought as catalog sources: 18 were retrieved and read,
one (the 2008 preliminary PDQI paper) was not. Thirteen further reports were
used from their abstracts; six of them were obtained on 2026-09-16 and read on
2026-09-20, and seven remain abstract-only, marked as such wherever they are
cited. Every report has a ledger entry with its route into the review, its
identifiers, every retrieval attempt with date and checksum, and a reading basis
that is kept separate from retrieval (`reports.json`). Sources are classed by
evidence layer: direct, transfer, requirements, or methodological guidance that
defines no property of a note. Each construct rests on evidence lines that
quote a located passage and state separately what the passage supports and what
our adaptation adds; there are 61 such lines (`catalog.json`).

## The derivation, from the sources upwards

The evidence above was collected for candidates already on the table, so it
cannot say whether the sources contain anything the table missed. The
derivation we report runs the other way. For every source read in full we
listed every property of note quality the source itself defines or measures, in
the source's own words and with its location, without reference to the catalog,
and mapped each to a candidate afterwards (`source-properties.json`). The table
holds 140 properties from 26 sources. 132 map to a candidate; the eight that do
not are rating formats, findings about raters, or limitations of a source
rather than properties of a note. Thirty-three of the 34 candidates rest on at
least one source property. The one that does not is K06, a note that says what
it could not record rather than leaving the gap silent; no source defines it
and it stands on the observation this project declares as its origin, which is
that models write a denial of information nobody asked for and score full
marks for it. This convergence is not a blind replication: the extraction was
written by the assistant that had already written the catalog, source by
source and with the mapping done afterwards, and it is reported as what it is. Two properties that no candidate had
covered, culturally competent care evidenced in the note and internal
consistency within one note, were recorded as open with a proposed disposition
and adopted as candidates by the investigator on 2026-09-21, one against the
proposal; the record keeps both the proposal and the decision.

## The construct framework

The catalog holds 34 candidates. By origin, 19 came from the literature, 11
existed in the project before the search, 3 are named expert proposals and 1
arose from observation; origin never changes when support is found later, which
is recorded as evidence instead. Origin and support are reported separately,
because they answer different questions: all 17 constructs proposed for
measurement in this round rest on at least one source read in full, and the one
candidate with no such support is not measured. One candidate was found late:
a property of a source can enumerate several concepts, and until 2026-10-05
nothing checked that each of them had a candidate of its own, so professional
terminology sat inside a bundled property for three weeks. It is K34 now, the
validator refuses such a gap when a mapping note admits it, and two further
concepts the notes had set aside in prose are recorded as open. Against the prior map, 8 criteria were kept, 12
revised on what the sources say, 6 merged where they had counted one finding
twice, and 11 added. Every candidate carries one of seven states that say why
it is or is not measured in this round: 16 are proposed for measurement, 7 lack
an operational rule, 4 cannot be measured on the present data, 5 are out of
scope by decision, 1 awaits a rater the pilot does not have, and 1 lacks
evidence. Each also records what would make an answer to it correct, because
that is what decides whether its number can rank a system at all: of the 16
measured, 10 are decided by the transcript, 1 by a written template, 3 by a
professional's verdict whose only evidence of validity is agreement between
raters, and 2 describe rather than grade and carry no target value. Candidates also carry a record kind, because a content topic, a
specification criterion and a practical outcome are not interchangeable
constructs; families organise the catalog and are not claimed as independent
latent dimensions. The catalog is a single versioned file from which the public
page and the executable registry draft are generated, and the test suite fails
when either drifts.

## Human review

The framework is reviewed subject by subject: each source, each evidence line,
each construct and the instrument's scope is a separate decision (accept,
revise, exclude, unresolved, merge) with a mandatory reason, bound to a digest
of the exact text it was made about, so that a later change of wording voids
the decision rather than inheriting it. The investigator is recorded as the
instrument's author on every decision; an author's review is not independent
validation. The investigator decided every construct: 31 on 2026-09-16 and
2026-09-21, and the two adopted from the source-first extraction. The source and
evidence subjects were not verified item by item: on 2026-09-21 the investigator
accepted them on the assistant's reading by a recorded delegation (decision D9),
which the registry stores as a distinct decision mode that can only accept and
lists on every frozen snapshot. A second reviewer has not been recruited.

## Operationalisation, freeze and pilot

Constructs proposed for measurement become operational measurements with a
question, a response format, anchors and examples in both languages; the core
implements four measurement methods (source-derived question answering,
atomic-claim verification, item scoring and citation checking), and each
operational item names the one it uses. The rules of the three methods this
round uses, the three rubric items and their Czech wording were drafted by the
assistant and accepted by the investigator by delegation on 2026-09-21
(decision D10), not reviewed item by item; the feasibility pilot is their
first test, and the translator was chosen the same way from the recorded
back-translation check. The current pilot proposal holds 14
entries that are deliberately not 14 comparable measures: 8 executable
measures, 2 human-use outcomes, 1 requirements check, 1 study condition on
rater training, 1 corpus-level proxy and 1 derived ratio. The protocol records
the executable count at freeze rather than capping it. The registry refuses to
freeze while any used subject lacks an accepted decision.

The feasibility pilot (protocol 2.7.0) freezes 16 generation jobs over two
cohorts, two English AnnoMI conversations and their Czech translations, two
purposes and two generator families, and balances an 8-note human sample across
them. Two Czech psychologists, neither the instrument author, rate under a
crossover over languages, an overlap block rated by both in the same language as
the only source of between-rater agreement, and blinded repeats for within-rater
agreement; agreement is reported per item as Gwet's AC1 or AC2. The human budget
is 150 annotation units, 120 unique and 30 repeats, within 8 to 12 hours. The
pilot asks of each measurement whether it can be performed, whether raters
agree, whether it discriminates or sits at a ceiling, and what it costs; the
protocol forbids dropping a measurement because systems do not differ on it.
Sample sizes for a confirmatory study are derived from the pilot's measured
agreement and time, not assumed.

## The bilingual design

The Czech half of the benchmark uses translations of the same public
conversations as the English half, so that a difference between languages is
not a difference between materials. The translator is a recorded instrument:
candidate models are measured by a back-translation check with a separate
back-translator, the chosen model is recorded with its settings and prompt
digest before use, every conversation is verified turn for turn and a mismatch
is a failure rather than a repaired pair, and a pair is established only where a
person has read a sample and recorded a meaning review. Ten earlier
translations without such a record are superseded and retained as history. The
project's real Czech sessions are a permanently private track and are in
neither the paper nor the pilot.

## Reporting

No composite quality score is computed. Each system is reported as a profile
over the operational measurements, separately by language, corpus, purpose,
protocol and judge, with intervals, and with every absence reported as a named
gap rather than as a zero. The only claim about one system beating another that
needs no weighting convention is dominance under both judges that survives
resampling; any order printed beside it is a declared rank-based convention
with its sensitivity reported. PRISMA-ScR and PRISMA-S checklists are in the
appendix; every artefact named here is committed and regenerated by the
repository's test suite.

## What this study does not claim

It does not present a completed scoping review: two databases were not
searched, most of the pool was not screened, and the estimate of what was
missed is reported. It does not present established content validity. The method it follows asks
for expert judges who "should be independent of those who developed the item
pool" (Boateng et al., 2018) and calls five to seven of them typical. The pool
was developed by the investigator with the assistant, and on 2026-10-07, before
any rating existed, a retention threshold was registered and the whole pool was
put to three therapists who are neither: three of three retains an item, two of
three retains it as contested with the dissent published, fewer removes it from
the measured set. Three raters is below the typical range, so what the panel
supplies is a screening of the pool and not established content validity, and
the measured set the pilot uses is the panel's rather than the authors'. The two Czech
psychologists of the pilot are raters, not independent judges of the pool, and
a feasibility pilot does not stand in for that judgement. COSMIN's criteria
name relevance, comprehensiveness and comprehensibility as what such a
judgement covers, and this round reports that nobody has assessed them. The
instruments we build on used therapist co-design and Delphi panels.
The passages quoted as evidence were read by the assistant and accepted by
delegation; no person verified each of them against its source. The operational
rules and the Czech wording the raters follow were drafted by the assistant and
accepted by delegation as well; they are tested by the pilot, not by review.
It does not present a validated instrument: no agreement statistic exists
before the pilot. The Czech legal criterion is a documentation-conformance check
for records kept by a provider of health services, not a statement about legal
compliance, and no lawyer has reviewed it. The English working record was
translated from the investigator's Czech working catalog by the assistant and
has not been checked by a person.
