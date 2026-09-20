# Gen-2 candidate catalog

`catalog.json` is the one versioned record of what the scoping search of
2026-09-13 proposed for the Gen-2 instrument: the sources it read, the candidate
constructs, the methods, the levels at which a note can be measured, the blind
spots of the earlier criteria map, a pilot proposal and the comparison with the
earlier criteria. Everything in it is an AI-authored proposal. No entry has been
accepted by a person, and the record says so in its own status line.

Two files are generated from it and the suite fails when either drifts:

- `docs/gen2-catalog.html`, drawn by `render_catalog.py`, is the readable page.
- `draft-registry.json`, written by `convert_to_registry.py`, is the same record
  in the shape the Gen-2 core runs. `conversion-diagnostics.json` beside it lists
  every entry that did not become an operational item, a selected method or a
  review, with the reason, and records the core's own refusal to treat the draft
  as a pilot instrument.

`catalog.py` holds the validation rule and is what the tests and the two
generators run first.

`source-properties.json` is the inductive half. For every source read in full it
lists every property of note quality the source itself defines or measures, in the
source's own words with its location, extracted source by source without reference
to the catalog; the mapping to candidates is a second column, done afterwards. A
candidate the catalog calls literature-origin has to rest on at least one such
property, and a property no candidate covers is listed in the catalog as open, with
a proposed disposition, until the investigator decides. Together with the prior map
this is a best-fit framework synthesis: an a priori framework, evidence coded
against it, and new themes for what does not fit. The paper will cite the method
(Carroll et al., BMC Medical Research Methodology, 2013); that reference is not yet
in the review ledger and has to be added there before submission.

## Provenance

The six reports the investigator supplied on 2026-09-16 were read on 2026-09-20 for
the property extraction and are full sources since then; their evidence lines were
re-verified against the full texts on that day.

The original of this round is the investigator's Czech working catalog, which
stays in the private workspace under the repository's language rule. This English
record was assembled from it entry by entry on 2026-09-16 by the coding assistant;
nobody has checked the translation. Quotations from a Czech legal text are given
in translation and marked as such. Every source names the report it is in the
review's ledger, `../review-2026-09-13/reports.json`, so what was sought, retrieved
and read is looked up there and not restated here.

## What the record separates

- **Origin from later support.** `origin` is where an idea came from and never
  changes when a source is found later; the sources found later are evidence.
- **Kinds of record.** A candidate is a construct, a refinement of one, a
  refinement for one purpose, a content topic, an expert proposal, a specification
  criterion or a practical outcome. A pilot entry is an executable measure, a
  requirements check, a human-use outcome, a study condition, a corpus-level proxy
  or a derived ratio. The fourteen pilot entries are therefore not fourteen
  comparable measurements, and the protocol records the executable count instead
  of capping it.
- **Families from importance.** Families organise the catalog; they are not
  evidence that a candidate matters.

## Regenerating

```sh
uv run python research/gen2/catalog/catalog.py             # validate
uv run python research/gen2/catalog/render_catalog.py      # docs/gen2-catalog.html
uv run python research/gen2/catalog/convert_to_registry.py # draft-registry.json, diagnostics
```

Edit `catalog.json` and regenerate; never edit the page or the draft by hand.

## What comes next

The draft is the input to the human review, not a shortcut past it. Producing
the sheet a person answers takes one command against a study started on the
current protocol:

```sh
tnb gen2 --workspace local/gen2-research-v3 research registry-sheet --registry research/gen2/catalog/draft-registry.json
```

Every source, evidence line and construct arrives as its own subject with its
own reason, so the sheet is long by design: a single decision covering many
subjects is exactly what the registry refuses to accept later. Nothing is
frozen until those answers exist, and the origin references the diagnostics
mark as placeholders have to become real records first.
