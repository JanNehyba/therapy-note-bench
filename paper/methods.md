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
quality the source itself defines, and all but one of the candidates are anchored in
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
relevant works (`amendments.json`). Scopus was planned, was not reachable
without an API key, and was searched on 2026-10-07 with three queries covering
the same three subjects, by the investigator in the institutional web interface
(amendment AM-7, `search-log-scopus.json`). Because those searches were run by
hand, the hit count each query reported was not captured: their record counts
are export row counts, that is lower bounds, and no export can be verified
complete. APA PsycINFO remains unsearched for want of institutional access and
is reported as a limit.

The searches identified at least 14 569 records (8 820, 2 577 and at least
3 172); 35 book-chapter records were not parsed into the pool and are counted
rather than dropped; 12 042 unique records remained after deduplication by DOI,
then PMID, then normalised title (2 492 removed; `pool-summary.json`,
`flow.json`). Scopus contributed 3 100 of those records and 1 819 of them were
reached by no other query. The deduplication rule tries DOI before title, so
the same work enters twice whenever one database supplies a DOI and the other
does not: 126 normalised titles sit on 253 records, 94 of those groups
involving Scopus. We report that as a measured defect of the pool rather than
correct it, because merging on title needs a guard against short and generic
titles and would move every stratum, every sample drawn from one and every
judgement made over a sample.

## Screening

Records were ordered by a priority rule at a threshold registered before the
first screen and unchanged since. The stratum now holds 687 records and 666
received a proposal across two dated rounds: 487 in the first (192 include,
295 exclude) and 180 in the second, the records the Scopus searches added
(55 include, 125 exclude, each with its reason recorded,
`include-candidates-2026-10-07.json`). Twenty-one records are listed as not
screened, never as excluded. No screening proposal has yet received a human
decision, and no second screener has been recruited; screening is therefore
single-reviewer and AI-assisted, and is reported as such.

The unscreened remainder of 11 355 records is audited as two strata, because
the records Scopus alone reached were not reachable when the first sample was
drawn and the first sample's rate is a property of the frame it came from. A
simple random sample of 200 from the 9 716 records reachable without Scopus
found 6 clearly eligible and 5 borderline, estimating 291 eligible records left
unscreened (95% Wilson interval 134 to 621). A separate sample of 200 from the
1 639 Scopus-only records found 28 clearly eligible and 11 borderline,
estimating 229 (162 to 319). The difference between the two rates is not a
measurement: the two samples were judged on different days from differently
formatted listings, and comparing them would mean judging the first frame again
under the second procedure. What the second estimate does establish is that the
ordering leaves more eligible material below the threshold in the Scopus
stratum than in the original one, which is consistent with Scopus matching a
query against indexed keywords as well as title and abstract
(`screening-decisions.json`). We call the whole a scoping search with a
prioritised evidence map, not a scoping review.

## Sources and evidence

Thirty-four reports were sought as catalog sources and all thirty-four have
been retrieved. The round of 2026-10-07 attempted thirty, retrieved nine, read
nine in full and seven became sources; the 2008 preliminary PDQI paper came in
that round. Which of the earlier reports was sought when is not derivable from
any artefact and is therefore not stated. The round joined that
day, when SESPI was read in full and the Scopus searches brought seven further
papers that the assistant read the same day. The thirty-fourth is the consensus
error taxonomy, which the language sweep of 2026-10-14 found outside the pool
and which three candidates rest on; it was brought into the report ledger on
2026-10-21, having been traced only by its DOI until then. Thirty-three of the
thirty-four have been read in full text and one from its abstract, which the
flow diagram now reports as three separate figures: retrieved, read in full
text, and verified by a person, the last of which is zero. The 2008 paper is
the one read from its abstract, so the entry resting on it still rests on
that. Twelve further reports are
used from their abstracts; six were obtained on 2026-09-16 and read on
2026-09-20, four more were obtained on 2026-10-07 and have not been read, and
two could not be obtained at all and carry a dated failed attempt, which is a
different fact from untried. Every source cited from an abstract is marked as
such wherever it appears. Every report has a ledger entry with its route into the review, its
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
holds 186 properties from 40 sources. 168 map to a candidate; the eighteen
that do not are rating formats, findings about measurement, reliability
figures, or properties of the encounter the note reports rather than of the
note. Thirty-eight of the thirty-nine candidates rest on at least one source property. The one that does not is K06, a note that says what
it could not record rather than leaving the gap silent; no source defines it
and it stands on the observation this project declares as its origin, which is
that models write a denial of information nobody asked for and score full
marks for it. This convergence is not a blind replication: the extraction was
written by the assistant that had already written the catalog, source by
source and with the mapping done afterwards, and it is reported as what it is. Four properties that no candidate had
covered were recorded as open with a proposed disposition. Culturally competent
care evidenced in the note and internal consistency within one note were
adopted as candidates by the investigator on 2026-09-21, one against the
proposal, and the record keeps both the proposal and the decision. Two more
were opened on 2026-10-07 and adopted the same day from a source read in full,
which the next section describes.

### What the seven further readings changed, and what they did not

The Scopus screening of 2026-10-07 proposed fifty-five candidates for
retrieval. Thirty sit in the three layers that could change the list of
criteria, nine of those were retrieved and nine were read; seven became sources.
None of the seven adds a candidate, and the pool did not grow for that reason
rather than by assumption. What they add is support for four claims that had rested on
argument.

Relevance to the recipient was an argument and is now a measurement. One study
had the same psychiatric admission notes rated independently by a specialist
registrar and a registered mental nurse, before and after a structured
assessment form was introduced. The form raised the clarity of the treatment
plan and of the risk record for the medical rater and for the nursing rater it
raised neither, which the authors read as the two professions looking for
different things. A single human anchor drawn from one profession is therefore
not a general anchor, and our own two-rater design has to say which professions
it speaks for.

Coverage and synthesis come apart under the same intervention. An audit of
risk-of-violence documentation found significant improvement in 45% of the
individual items of history and mental state, and no improvement at all in the
formulation of a risk assessment statement. Our catalog keeps coverage and
justified synthesis as separate candidates, and this is the measured case for
that separation.

Fidelity and coverage can trade against each other. A study of five diagnoses
with invariable physical findings classified each note as accurate, inaccurate
or omitted, which separates a wrong statement from a missing one without a
transcript. Moving from paper to an electronic record cut omissions from 41.2%
to 17.6% and raised inaccuracy from 4.4% to 24%. A system that covers more is
not thereby more faithful, and a benchmark that reports one number for both
would have called that transition an improvement.

The same study is the literature anchor for a rule this project had adopted on
its own: errors were fewer for findings obvious at first look and more frequent
for those needing a subtle examination. What goes missing clusters on the hard
cases, which is why dropping a missing measurement from the denominator is
biased rather than merely incomplete.

Finally, the rule that a token entry is not presence turns out to be thirty
years old. A 1996 audit of a community mental health team scored a heading as
recorded only if the notes held more than a minimal entry, and gave a date of
birth under personal history as its example of an entry that does not count.
This project had to write that rule for itself after a model was published with
a perfect temporal score for writing Nil four ways.

### Two constructs found by reading a source instead of its abstract

The same failure happened twice and the second time is the one that shows the
shape of it. On 2026-10-05 professional terminology was found inside a source
property that named three categories at once; nothing had checked that each
concept in such a row had a candidate, and the row counted as covered because
one part of it did. On 2026-10-07 the same thing was found in an abstract row.
The catalog had held the Scale for the Evaluation of Staff-Patient Interactions
in Progress Notes as an abstract-only source with a single row, "How
staff-patient interactions are captured in progress notes", mapped to the
candidate for supervision support and the candidate for attribution. Reading
the instrument showed four gated coding steps, two of which are properties of a
note and neither of which is either candidate: whether the note describes the
client's experience at all, scored as a yes-or-no gate, and whether it
describes both the therapist's approach and the client's response to it, scored
in four ordered levels. Both entered the pool as K36 and K35 with the source's
own wording, its manual's levels and its per-step reliability. The other two
steps rate the client's state and the therapist's attunement as the note
reports them; those are properties of the encounter and not of the note, and
they are recorded as non-adoptions with the reason rather than folded into note
quality.

An abstract row is a bundle by default, which is the general lesson. Six
sources are still cited from their abstracts and each is marked, and what that
mark now means is that the properties behind it have not been enumerated.

The arrival also gives the construct framework its first measured base rate in
psychotherapy. The 2025 application of the instrument scored 193 journal notes
of a Norwegian municipal mental health team: 49.3% were at the level where the
therapist's approach is missing or too thin to read, and 15.1% described both
sides, rising to 39.2% after an intervention that asked therapists to write
notes with their clients. A property that most notes fail and some pass can
separate notes, which is the question the investigator put to the catalog on
2026-10-05 and which almost no other candidate can answer with a number.

Neither candidate is measured in this round: the measured set was frozen at 16
before they arrived. Both are in the pool the content-validity panel rates, and
protocol amendment D14 records that a pool may grow until the first rating
sheet is sent and not afterwards.

## The construct framework

The catalog holds 39 candidates. By origin, 24 came from the literature, 11
existed in the project before the search, 3 are named expert proposals and 1
arose from observation; origin never changes when support is found later, which
is recorded as evidence instead. Origin and support are reported separately,
because they answer different questions: all 16 constructs proposed for
measurement in this round rest on at least one source read in full, and the one
candidate with no such support is not measured. One candidate was found late:
a property of a source can enumerate several concepts, and until 2026-10-05
nothing checked that each of them had a candidate of its own, so professional
terminology sat inside a bundled property for three weeks. It is K34 now, the
validator refuses such a gap when a mapping note admits it, and two further
concepts the notes had set aside in prose are recorded as open. Against the prior map, 8 criteria were kept, 12
revised on what the sources say, 6 merged where they had counted one finding
twice, and 11 added. Every candidate carries one of seven states that say why
it is or is not measured in this round: 16 are proposed for measurement, 10 lack
an operational rule, 6 cannot be measured on the present data, 5 are out of
scope by decision, 1 awaits a rater the pilot does not have, and 1 lacks
evidence. Each also records what would make an answer to it correct, because
that is what decides whether its number can rank a system at all: of the 16
proposed, 10 are decided by the transcript, 1 by a written template, 3 by a
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
2026-09-21, and the two adopted from the source-first extraction.

Those 33 decisions are read two ways by two tracked files, and both readings
hold. The rescued review record carries them in the mode the review form
captured, `human`; the instrument registry imports the same 33 as
`seen_no_objection`, because on 2026-10-08 the investigator said he does not
stand behind those lines as judgements. The registry's reading is the one any
claim of human verification would rest on, and it supports none. Each decision
also records what kind of act it was: 30 are a retention verdict, which decision
D13 returned to the content-validity panel on 2026-10-07, two are item
generation, and one is agreement to a rewording. Fifteen of the 33 reasons
carried, in free text, a checkable claim about the construct rather than about
whether it stays; those are lifted out and reported separately, each against the
catalog field it bears on. Nine are answered by a field of the catalog, one
partly, and five are not answered at all and are reported as gaps. One of the
five, the question of what a construct is measured over, was raised again as a
new finding on 2026-10-17, which is what a claim recorded in a field named for
something else costs.

The source and
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
back-translation check. The current pilot proposal holds 13
entries that are deliberately not comparable measures of one kind: 8 executable
measures, 2 human-use outcomes, 1 study condition on rater training, 1
corpus-level proxy and 1 derived ratio. A fourteenth, a requirements check, was
removed with K19 on 2026-10-05. The protocol records
the executable count at freeze rather than capping it. The registry refuses to
freeze while any used subject lacks an accepted decision.

The feasibility pilot (protocol 2.9.0) freezes 16 generation jobs over two
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
with its sensitivity reported. Every artefact named here is committed and
regenerated by the repository's test suite. The PRISMA-ScR and PRISMA-S
checklists are not written and this paper has no appendix; the claim that it had
one was withdrawn on 2026-10-22, when a review found nothing in paper/ but this
file.

## What this study does not claim

It does not present a completed scoping review: APA PsycINFO was not
searched, most of the pool was not screened, and the estimate of what was
missed is reported. It does not present established content validity. The method it follows asks
for expert judges who "should be independent of those who developed the item
pool" (Boateng et al., 2018) and calls five to seven of them typical. The pool
was developed by the investigator with the assistant, and on 2026-10-07, before
any rating existed, a retention threshold was registered and the whole pool is to
be put to three therapists who are neither. No sheet has been sent and no answer
has been collected, which the protocol's registration records; the rule is: three of three retains an item, two of
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
