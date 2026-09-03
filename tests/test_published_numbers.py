"""Every number in the hand-written pages is accounted for, or the count is.

Seven files are the evidence the site links to and nothing regenerates them:
the five `docs/*.md`, `README.md` and `NOTICE`. The audit of 2026-08-30 and 31
found 51 false claims and most of them were here -- a figure that was true when
it was typed and went quietly wrong when the thing it described moved.

`test_docs_figures.py` already recomputes eight of them and it works; it was
written after seven were wrong at once. The gap is coverage: the scanner below
finds roughly 900 numbers in these files and eight tests is not a net.

**Classifying all 900 in one sitting would be rubber-stamping, not checking**,
so this file does two things instead:

* a **registry** of claims that have been checked, each carrying the class of
  check it passed and the reason it is in that class; and
* a **ratchet**: the number of unaccounted figures per document may not go up.
  A new number in a published page fails the suite until somebody says what
  kind of number it is.

The five classes, and what each one obliges:

    computed    a figure this repository produces. Carries an expression that
                recomputes it from the published payload, compared **position
                by position** against the figures the sentence states -- so a
                sentence that swaps two right numbers between two judges fails.
    corpus      a figure measured over the fetched corpus or the generated
                notes. Recomputed here when `data/` and `generations/` are on
                disk, and **skipped, loudly, when they are not**: they are
                gitignored, so this one class cannot hold on a fresh checkout.
                It is still worth having -- it holds on the machine where the
                numbers are actually produced, which is where they change.
    external    a figure from somebody else's paper. Must name its source
                *beside* the figure, so it cannot be mistaken for one of ours,
                which is exactly what "alpha 0.08" did until it was attributed.
    historical  a measurement whose inputs no longer exist. Must say so beside
                the figure, so a reader is not invited to re-derive it.
    elsewhere   already recomputed by another test, named here so the two files
                do not quietly both stop checking it.

Everything except `corpus` reads `docs/leaderboard.json` and its siblings,
which are committed. A check that skips on a fresh checkout is a check nobody
runs, so only the class that cannot avoid it is allowed to skip.

**What the scanner does not see, stated rather than glossed over.** A number
inside a code span, a link target or a URL is an id, a path or a version and is
not counted. A range written with a dash -- `5-10`, `2023-2024` -- counts as
nothing at all, because the alternative is counting `gpt-5.6-terra` as the
figure 5.6 wherever a model id appears outside backticks. So a range added to a
published page slips past the ratchet. That is a hole, it is the price of not
crying wolf on every model id, and it is written here rather than left for
somebody to discover.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from tnb.config import REPO_ROOT

DOCS = REPO_ROOT / "docs"

#: The hand-written published surface. `docs/index.html` and `methods.html` are
#: not here: they are generated, and `test_i18n.py` and `test_page_runs.py`
#: hold them.
DOCUMENTS = (
    "docs/datasets.md",
    "docs/landscape.md",
    "docs/limitations.md",
    "docs/methodology.md",
    "docs/models-snapshot.md",
    "README.md",
    "NOTICE",
)

# --- the scanner -------------------------------------------------------------

#: A number that is part of a claim.
#:
#: `\d+(?:[  ,]\d{3})*` reads a thousands group as one figure: the docs
#: write `51 000` and `10 879` and `65 902`, and splitting each of those into
#: two numbers both inflated the ratchet and made `as_value` return 0.0 for the
#: tail. A separator only joins when exactly three digits follow it, which is
#: what keeps `in 2026, 40 sessions` two figures rather than one.
#:
#: The lookarounds drop what is not a claim: a word character, a dot or a dash
#: before the digits means an id, a path or a version (`gpt-5.6-terra`), and a
#: dash between two numbers means a range. See the module docstring for what
#: that costs.
NUMBER = re.compile(r"(?<![\w.<>/–-])\d+(?:[  ,]\d{3})*(?:\.\d+)?\s*%?(?![\w.]|\s*[–-]\s*\d)")
_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b|\b\d{1,2}\.\s*\d{1,2}\.\s*20\d\d\b")
_VERSION = re.compile(r"\b\d+\.\d+\.\d+\b")
_GENERATED = re.compile(r"<!-- (\w+):BEGIN -->.*?<!-- \1:END -->", re.S)

#: Some sentences spell their figures. `Eight of the nineteen` is the published
#: wording and a check must not force it into digits.
WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    # Before "twenty": the alternation `_WORD` builds from this map takes the
    # first entry that matches, and "twenty" alone would match the front of it.
    "twenty-one": 21,
    "twenty": 20,
}

#: Anchored on both sides. Without the boundaries `nine` and `ten` both match
#: inside `nineteen`, and `Eight of the nineteen` would report four figures
#: where it states two.
_WORD = re.compile(r"\b(" + "|".join(WORDS) + r")\b", re.I)


def readable(path: str) -> str:
    """One document with the parts that are not prose taken out."""
    text = (REPO_ROOT / path).read_text(encoding="utf-8")
    text = _GENERATED.sub(" ", text)  # regenerates with the data; not hand-written
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"\]\([^)]*\)", "] ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return text


def numbers(text: str) -> list[str]:
    """Every figure in a piece of prose, written in digits, as it is written."""
    text = _VERSION.sub(" ", _DATE.sub(" ", text))
    return [match.group(0).strip() for match in NUMBER.finditer(text)]


def tokens_in(phrase: str) -> list[str]:
    """Every figure a phrase states, digits and words alike, as written."""
    return numbers(phrase) + [match.group(0) for match in _WORD.finditer(phrase)]


def as_value(token: str) -> float:
    """`5.6%`, `51 000`, `Eight` and `0.575` as something comparable."""
    word = WORDS.get(token.strip().lower())
    if word is not None:
        return float(word)
    bare = token.strip().rstrip("%").replace(",", "").replace(" ", "").replace(" ", "")
    return float(bare)


def flat(path: str) -> str:
    """Markdown wraps, so a published sentence spans lines in the file."""
    return re.sub(r"\s+", " ", (REPO_ROOT / path).read_text(encoding="utf-8"))


def payload() -> dict:
    return json.loads((DOCS / "leaderboard.json").read_text(encoding="utf-8"))


# --- the registry ------------------------------------------------------------


@dataclass(frozen=True)
class Claim:
    """One published figure, and the reason it may stand."""

    where: str
    phrase: str
    kind: str  # computed | corpus | external | historical | elsewhere
    because: str
    #: The figures the phrase states, in the order it states them. Not a
    #: comment: `unaccounted` credits the document exactly these, and a
    #: computed claim is compared against `expected()` position by position, so
    #: this is what stops two right numbers being printed the wrong way round.
    #: Kept honest by `test_a_claim_covers_the_figures_it_states`.
    covers: tuple[str, ...]
    expected: Callable[[], tuple[float, ...]] | None = None
    source: str | None = None  # external: the text that must sit beside the figure
    caveat: str | None = None  # historical: the text that must sit beside the figure


#: How far from the figure an attribution or a caveat may sit and still be read
#: as belonging to it. Measured on the three that exist: 32, 403 and 464
#: characters of flattened text -- the next paragraph, at worst. A guard that
#: accepted the whole file would pass on an attribution four screens away.
NEARBY = 900


def _gemini_soap_table() -> dict:
    """The SOAP table the leaderboard opens on: the default judge's."""
    from tnb import judge

    return next(
        table
        for table in payload()["tables"]
        if table["track"] == "tneval-soap"
        and table["versions"]["judge_model"] == judge.DEFAULT_MODEL
    )


def _part_answered_notes() -> tuple[float, ...]:
    """Notes scored on fewer than all four sections, all notes, and the section count.

    The count that narrows the band analysis's shared set. It was 42 until the
    re-ask of 2026-09-02 and is computed from the payload rather than carried
    over, so the sentence moves when the notes do.
    """
    rows = _gemini_soap_table()["rows"]
    return (
        float(sum(row.get("n_partial") or 0 for row in rows)),
        float(sum(row.get("n_generated") or 0 for row in rows)),
        4.0,
    )


def _systems_on_the_gemini_table() -> tuple[float, ...]:
    return (float(len(_gemini_soap_table()["rows"])),)


def _saturation(judge_model: str) -> dict:
    import json as _json

    with open(f"docs/saturation-{judge_model}.json", encoding="utf-8") as handle:
        return _json.load(handle)


def _shared_sets_stated() -> tuple[float, ...]:
    """Gemini's shared set, the corpus, gpt's shared set -- the band analysis's
    denominators, in the order the sentence states them."""
    gemini = _saturation("gemini-3.1-pro-preview")
    gpt = _saturation("gpt-5.6-terra")
    return (float(gemini["sessions"]), float(gemini["corpus_sessions"]), float(gpt["sessions"]))


def _gpt_oss_missing_under_gpt() -> tuple[float, ...]:
    return (float(_saturation("gpt-5.6-terra")["narrowed_by"]["gpt-oss-120b"]),)


def _qwen_flash_next_missing_under_gpt() -> tuple[float, ...]:
    return (float(_saturation("gpt-5.6-terra")["narrowed_by"]["qwen3.8-flash-next"]),)


def _completeness_moved() -> tuple[float, ...]:
    """Systems whose completeness moved between the gemini SOAP rows at 0.6.0 and
    0.7.0, all systems compared, and the largest move down and up -- from
    results/rows.jsonl, which is committed, so the sentence is re-derivable."""
    rows = [
        json.loads(line)
        for line in (REPO_ROOT / "results" / "rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    def latest(harness: str) -> dict[str, float | None]:
        out: dict[str, float | None] = {}
        for row in rows:
            if (
                row.get("track") == "tneval-soap"
                and row.get("judge_model") == "gemini-3.1-pro-preview"
                and row.get("harness_version") == harness
                and (row.get("metrics") or {}).get("headline")
            ):
                out[row["system_id"]] = row["metrics"]["headline"].get("completeness")
        return out

    before, after = latest("0.6.0"), latest("0.7.0")
    deltas = [
        after[system] - before[system]
        for system in after
        if system in before and after[system] is not None and before[system] is not None
    ]
    moved = sum(1 for delta in deltas if abs(delta) >= 0.0005)
    return (float(moved), float(len(deltas)), round(abs(min(deltas)), 3), round(max(deltas), 3))


def _short_of_the_corpus() -> tuple[float, ...]:
    """The one model short of 50 for a reason that is not the rubric parser.

    The sentence used to end "and the other eighteen on 50", which was an
    era count and wrong twice over once two systems joined: there are nineteen
    others, and one of them is not on 50 either.
    """
    from tnb import judge

    rows = next(
        table
        for table in payload()["tables"]
        if table["track"] == "tneval-soap"
        and table["versions"]["judge_model"] == judge.DEFAULT_MODEL
    )["rows"]
    row = next(r for r in rows if r["system_id"] == "qwen3.8-flash-next")
    return (float(row["n_scored"]), float(row["n_attempted"] - row["n_scored"]))


def _repeat_counts() -> tuple[float, ...]:
    """Each judge's repeated answers and questions re-asked, in the order named."""
    from tnb import judge

    found = json.loads((REPO_ROOT / "docs" / "repeatability.json").read_text(encoding="utf-8"))
    by_judge = {entry["judge_model"]: entry for entry in found["judges"]}
    out = []
    for name in (judge.DEFAULT_MODEL, judge.SECOND_JUDGE):
        entry = by_judge[name]
        out.extend((float(entry["same"]), float(entry["questions"])))
    return tuple(out)


def _leans_on() -> tuple[float, ...]:
    """What is left of each judge's lean without the model it rests on.

    Published under `leans_on` in `docs/preference.json` since 2026-09-03. The
    two figures were hand-computed in a terminal before that, and the briefing's
    copy of the same sentence was a payload out of date for a week while this
    document was right -- which is the argument for registering them here.
    """
    from tnb import judge

    effects = {entry["judge"]: entry for entry in payload()["preference"]["effects"]}
    return tuple(
        round(effects[name]["leans_on"]["estimate"], 3)
        for name in (judge.DEFAULT_MODEL, judge.SECOND_JUDGE)
    )


def _tneval_undominated() -> tuple[float, ...]:
    """Undominated systems, systems, and the measures dominance was read over.

    The third figure is the point. "Eight of the nineteen are beaten outright by
    nobody" was published with no instrument named, on a page whose SOAP table
    draws eleven columns from two instruments -- and the payload carried three
    concordances that answered the same sentence 8 of 19, 11 of 19 and 8 of 16.
    """
    found = payload()["concordance"]["tneval-soap"]
    return (
        float(len(found["undominated"])),
        float(found["n_systems"]),
        float(len(found["measures"])),
    )


def _edges(track: str) -> dict:
    import json as _json

    with open(f"docs/edges-{track}.json", encoding="utf-8") as handle:
        return _json.load(handle)


def _tested_claims() -> tuple[float, ...]:
    """Kept at the threshold; rubric stored and held, PDSQI stored and held,
    iCARE stored and held -- in the order the sentence states them."""
    out: list[float] = []
    for track in ("tneval-soap", "pdsqi-soap", "icare"):
        found = _edges(track)
        out += [float(found["counts"]["stored"]), float(found["counts"]["holds"]["0.95"])]
    return (0.95, *out)


def _tested_groups() -> tuple[float, ...]:
    """Top-group size, systems, systems below the top group (rubric), then the
    same top-group and systems figures for PDSQI-9 and iCARE."""
    rubric, pdsqi, icare = (_edges(t) for t in ("tneval-soap", "pdsqi-soap", "icare"))
    return (
        float(len(rubric["layers"][0])),
        float(len(rubric["systems"])),
        float(len(rubric["layers"][1])),
        float(len(pdsqi["layers"][0])),
        float(len(pdsqi["systems"])),
        float(len(icare["layers"][0])),
        float(len(icare["systems"])),
    )


def _readme_top_group() -> tuple[float, ...]:
    found = _edges("tneval-soap")
    return (float(len(found["layers"][0])), float(len(found["systems"])))


def _pdsqi_undominated() -> tuple[float, ...]:
    """The same three figures for the other instrument on the same table."""
    found = payload()["concordance"]["pdsqi-soap"]
    return (
        float(len(found["measures"])),
        float(len(found["undominated"])),
        float(found["n_systems"]),
    )


def _trace_spread() -> tuple[float, ...]:
    """The models counted, then TRACE's spread under each judge **by name**.

    In the sentence's own order, not sorted. Sorting compared the two
    percentages as a set, so swapping which judge each belonged to -- the
    difference between "gemini separates them least" and the opposite -- would
    have passed. TRACE is rated 1 to 5, so its scale is 4 wide.
    """
    spread: dict[str, float] = {}
    counted: set[int] = set()
    for table in payload()["tables"]:
        # Scored tables only: the queue of models awaiting the judge is an
        # iCARE table too, with nothing to spread.
        if table["track"] != "icare" or not table["scored"]:
            continue
        values = [
            row["headline"]["trace"] for row in table["rows"] if "trace" in (row["headline"] or {})
        ]
        spread[table["versions"]["judge_model"]] = round((max(values) - min(values)) / 4 * 100, 1)
        counted.add(len(values))
    assert len(counted) == 1, f"the two iCARE tables draw different model counts: {counted}"
    return (float(counted.pop()), spread["gemini-3.1-pro-preview"], spread["gpt-5.6-terra"])


# --- what the corpus says, on a machine that has the corpus -------------------

_GOLD = REPO_ROOT / "data" / "ihope_test.json"
_GENERATIONS = REPO_ROOT / "generations"


def _ihope_labels() -> tuple[float, ...]:
    """Notes labelling fewer than all the fields, notes in all, fields in all.

    Read straight off the file rather than through `datasets.ihope.load`, which
    fetches. A test does not go to the network.
    """
    from tnb.datasets.ihope import SECTION_COUNT
    from tnb.scoring.icare import split_sections

    raw = json.loads(_GOLD.read_text(encoding="utf-8"))
    entries = raw if isinstance(raw, list) else list(raw.values())
    notes = [note for entry in entries if (note := (entry.get("summary") or "").strip())]
    incomplete = sum(1 for note in notes if len(split_sections(note)) < SECTION_COUNT)
    return (float(incomplete), float(len(notes)), float(SECTION_COUNT))


def _dressed_up_empties() -> tuple[float, ...]:
    """Distinct strings that say nothing while looking like content, and records.

    The definition is `corpus.is_filled` said twice: nothing is filled, and yet
    the whole string is not the bare marker, so a reader checking only "is this
    literally Nil?" reads it as content. `tools/count_dressed_up_empties.py`
    writes the same definition out at length and prints both populations.
    """
    from tnb import corpus

    values = []
    for path in _GENERATIONS.rglob("section-*.json"):
        try:
            section = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if section.get("ok") and isinstance(text := section.get("text"), str) and text:
            values.append(text)

    hits = [
        value
        for value in values
        if not corpus.is_filled(value)
        and value.strip().lower().rstrip(".;,! ") not in corpus.EMPTY_MARKERS
    ]
    return (float(len({value.strip() for value in hits})), float(len(hits)))


CLAIMS = (
    Claim(
        where="docs/limitations.md",
        phrase=(
            "Nine of the twenty-one are beaten outright by nobody on TN-Eval's three rubric columns"
        ),
        kind="computed",
        because="the dominance count is the reason no winner is named, and it moved once already",
        covers=("Nine", "twenty-one", "three"),
        expected=_tneval_undominated,
    ),
    Claim(
        where="docs/limitations.md",
        phrase="On PDSQI-9's eight columns, on its own table, it is twelve of the twenty-one",
        kind="computed",
        because=(
            "the same sentence answered over the other instrument; printing one without "
            "the other is what made the count read as the page's"
        ),
        covers=("eight", "twelve", "twenty-one"),
        expected=_pdsqi_undominated,
    ),
    # The tested dominance graph, read from the committed edges artefacts.
    Claim(
        where="docs/limitations.md",
        phrase=(
            "kept only where it held in 0.95 of the draws. Of the 38 rubric claims 14 hold; of "
            "PDSQI-9's 12 claims 1 holds; of iCARE's 40 claims 9 hold"
        ),
        kind="computed",
        because="the threshold and the counts in docs/edges-<track>.json, per track",
        covers=("0.95", "38", "14", "12", "1", "40", "9"),
        expected=_tested_claims,
    ),
    Claim(
        where="docs/limitations.md",
        phrase=(
            "on the rubric 16 of 21 systems share the top group, with 4 below them and the "
            "therapist alone at the bottom; on PDSQI-9 20 of 21 share it; on iCARE 15 of 18"
        ),
        kind="computed",
        because="the layers in docs/edges-<track>.json, per track",
        covers=("16", "21", "4", "20", "21", "15", "18"),
        expected=_tested_groups,
    ),
    Claim(
        where="README.md",
        phrase=(
            "Adhikary, P. K., Mukherjee, A., Deb, K. S., Singh, S., Singh, S. M., & Chakraborty, "
            "T. (2026). Discourse-guided summarisation of psychotherapy dialogues via graph-fused "
            "language models. *IEEE Journal of Biomedical and Health Informatics*. Advance online "
            "publication."
        ),
        kind="external",
        because=(
            "bibliographic data -- year, volume, issue, pages, version -- read from "
            "Crossref and medRxiv on 2026-09-02, not from memory"
        ),
        covers=("2026",),
        source="Adhikary",
    ),
    Claim(
        where="README.md",
        phrase=(
            "Adhikary, P. K., Singh, S., Singh, S., Sharma, P., Soni, P., Choudhary, R., Saxena, "
            "C., Chauhan, P., Gupta, S. K., Deb, K. S., Singh, S. M., & Chakraborty, T. (2026). "
            "*Clinically grounded AI-scribing in psychotherapy: Benchmarking LLMs against expert "
            "documentation in the iCARE framework* (Version 2) [Preprint]. medRxiv."
        ),
        kind="external",
        because=(
            "bibliographic data -- year, volume, issue, pages, version -- read from "
            "Crossref and medRxiv on 2026-09-02, not from memory"
        ),
        covers=("2026", "2"),
        source="Adhikary",
    ),
    Claim(
        where="README.md",
        phrase=(
            "Croxford, E., Gao, Y., Pellegrino, N., Wong, K., Wills, G., First, E., Schnier, M., "
            "Burton, K., Ebby, C., Gorski, J., Kalscheur, M., Khalil, S., Pisani, M., Rubeor, T., "
            "Stetson, P., Liao, F., Goswami, C., Patterson, B., & Afshar, M. (2025). Development "
            "and validation of the provider documentation summarization quality instrument for "
            "large language models. *Journal of the American Medical Informatics Association, "
            "32*(6), 1050–1060."
        ),
        kind="external",
        because=(
            "bibliographic data -- year, volume, issue, pages, version -- read from "
            "Crossref and medRxiv on 2026-09-02, not from memory"
        ),
        covers=("2025", "32", "6"),
        source="Croxford",
    ),
    Claim(
        where="README.md",
        phrase=(
            "Shah, R. S., Xu, L., Liu, Q., Burnsky, J., Bertagnolli, A., & Shivade, C. (2025). "
            "TN-Eval: Rubric and evaluation protocols for measuring the quality of behavioral "
            "therapy notes. In *Proceedings of the 63rd Annual Meeting of the Association for "
            "Computational Linguistics (Volume 6: Industry Track)* (pp. 179–199). Association for "
            "Computational Linguistics."
        ),
        kind="external",
        because=(
            "bibliographic data -- year, volume, issue, pages, version -- read from "
            "Crossref and medRxiv on 2026-09-02, not from memory"
        ),
        covers=("2025", "6"),
        source="Shah",
    ),
    Claim(
        where="README.md",
        phrase=(
            "Wu, Z., Balloccu, S., Kumar, V., Helaoui, R., Reiter, E., Reforgiato Recupero, D., & "
            "Riboni, D. (2022). Anno-MI: A dataset of expert-annotated counselling dialogues. In "
            "*ICASSP 2022 – 2022 IEEE International Conference on Acoustics, Speech and Signal "
            "Processing (ICASSP)* (pp. 6177–6181). IEEE."
        ),
        kind="external",
        because=(
            "bibliographic data -- year, volume, issue, pages, version -- read from "
            "Crossref and medRxiv on 2026-09-02, not from memory"
        ),
        covers=("2022", "2022"),
        source="Wu",
    ),
    Claim(
        where="README.md",
        phrase="16 of 21 systems share the top group",
        kind="computed",
        because="the rubric's top layer in docs/edges-tneval-soap.json",
        covers=("16", "21"),
        expected=_readme_top_group,
    ),
    # The judge's non-answers: what they were and what the re-ask changed.
    # Historical where the figure lives in the gitignored answer cache or a
    # run's console output, said so beside each; computed where the payload,
    # the saturation analyses or results/rows.jsonl hold it.
    Claim(
        where="docs/limitations.md",
        phrase="78 of 51 000 rubric answers were of this kind",
        kind="historical",
        because="counted in scores/, which is gitignored; a reader cannot re-derive it here",
        covers=("78", "51 000"),
        caveat="not in this repository",
    ),
    Claim(
        where="docs/limitations.md",
        phrase="The 43 fragments",
        kind="historical",
        because="the replies the aggregator refused all along, counted in the gitignored cache",
        covers=("43",),
        caveat="not in this repository",
    ),
    Claim(
        where="docs/limitations.md",
        phrase="left 42 notes scored on fewer than all four sections",
        kind="historical",
        because="the part-answered count before the re-ask; the rows behind it are superseded",
        covers=("42", "four"),
        caveat="not in this repository",
    ),
    Claim(
        where="docs/limitations.md",
        phrase="the 35 echoes",
        kind="historical",
        because="prompt echoes that passed the old answer test, counted in the gitignored cache",
        covers=("35",),
        caveat="not in this repository",
    ),
    Claim(
        where="docs/limitations.md",
        phrase="and 29 were scored as criteria the note met",
        kind="historical",
        because="the echoes `parse_yes_no` read as Yes, counted in the gitignored cache",
        covers=("29",),
        caveat="not in this repository",
    ),
    Claim(
        where="docs/limitations.md",
        phrase="62 of the 78 came back as answers and 16 did not",
        kind="historical",
        because="two passes of one run on 2026-09-02, counted from their console output",
        covers=("62", "78", "16"),
        caveat="not in this repository",
    ),
    Claim(
        where="docs/limitations.md",
        phrase="19 of the 1040 SOAP notes are still scored on fewer than all four sections",
        kind="computed",
        because="the part-answered count after the re-ask; if it moves, this sentence must",
        covers=("19", "1040", "four"),
        expected=_part_answered_notes,
    ),
    Claim(
        where="docs/limitations.md",
        phrase="all 21 systems share",
        kind="computed",
        because="the systems whose intersection the band analysis runs on",
        covers=("21",),
        expected=_systems_on_the_gemini_table,
    ),
    Claim(
        where="docs/limitations.md",
        phrase="is 36 of 50 under gemini and 40 under gpt",
        kind="computed",
        because="the band analysis's denominators, read from the two committed saturation analyses",
        covers=("36", "50", "40"),
        expected=_shared_sets_stated,
    ),
    Claim(
        where="docs/limitations.md",
        phrase="8 unrecoverable notes and",
        kind="computed",
        because="gpt-oss-120b's unrecoverable notes, as the gpt analysis records them",
        covers=("8",),
        expected=_gpt_oss_missing_under_gpt,
    ),
    Claim(
        where="docs/limitations.md",
        phrase="`qwen3.8-flash-next`'s two notes with truncated judge answers are missing",
        kind="computed",
        because="qwen3.8-flash-next's notes the gpt judge truncated, as its analysis records them",
        covers=("two",),
        expected=_qwen_flash_next_missing_under_gpt,
    ),
    Claim(
        where="docs/limitations.md",
        phrase="under gemini it had been 25",
        kind="historical",
        because="the shared set before the re-ask; the analysis that held it was overwritten",
        covers=("25",),
        caveat="not in this repository",
    ),
    Claim(
        where="docs/limitations.md",
        phrase="Completeness moved on 16 of the 19 systems, by between −0.003 and +0.009",
        kind="computed",
        because="the 0.6.0 and 0.7.0 gemini rows both sit in results/rows.jsonl",
        covers=("16", "19", "0.003", "0.009"),
        expected=_completeness_moved,
    ),
    # The self-preference intervals are recomputed against docs/preference.json
    # by tests/test_docs_figures.py::test_the_self_preference_intervals_are_the_published_ones,
    # so they are named here and checked there.
    Claim(
        where="docs/methodology.md",
        phrase=(
            "`gemini-3.1-pro-preview` +0.018 [−0.009, +0.046] and `gpt-5.6-terra` +0.017 "
            "[−0.007, +0.043]"
        ),
        kind="elsewhere",
        because="test_docs_figures.py recomputes both intervals from docs/preference.json",
        covers=("0.018", "0.009", "0.046", "0.017", "0.007", "0.043"),
    ),
    Claim(
        where="docs/methodology.md",
        phrase="they do not: −0.000 [−0.041, +0.042]",
        kind="elsewhere",
        because="test_docs_figures.py recomputes the judges' difference from docs/preference.json",
        covers=("0.000", "0.041", "0.042"),
    ),
    Claim(
        where="docs/methodology.md",
        phrase=(
            "without `gemma4` the Gemini figure is about +0.006, without `gpt-oss-120b` "
            "the GPT figure about +0.011"
        ),
        kind="computed",
        because=(
            "the leave-one-out is an artefact now, and the same sentence in the briefing "
            "was two payloads stale while this one was right"
        ),
        covers=("0.006", "0.011"),
        expected=_leans_on,
    ),
    Claim(
        where="docs/methodology.md",
        phrase=(
            "`gemini-3.1-pro-preview` repeated 326 of 333 answers and `gpt-5.6-terra` 293 of 334"
        ),
        kind="computed",
        because=(
            "the wider re-ask, published on 2026-09-02, which the drift section did not "
            "have when it quoted one judge at 98.3% and stopped"
        ),
        covers=("326", "333", "293", "334"),
        expected=_repeat_counts,
    ),
    Claim(
        where="docs/methodology.md",
        phrase="0.15% (78 of 51 000)",
        kind="historical",
        because="the non-answer rate at budget 256, counted in the gitignored cache",
        covers=("0.15%", "78", "51 000"),
        caveat="not in this repository",
    ),
    Claim(
        where="docs/methodology.md",
        phrase="those 78 were re-asked",
        kind="historical",
        because="the same count, restated where the paragraph turns to the repair",
        covers=("78",),
        caveat="not in this repository",
    ),
    Claim(
        where="docs/limitations.md",
        phrase="`qwen3.8-flash-next`, at 48, on two notes its own generator truncated",
        kind="computed",
        because=(
            "the sentence used to say the other eighteen were on 50; there are nineteen "
            "others and one of them is not"
        ),
        covers=("48", "two"),
        expected=_short_of_the_corpus,
    ),
    Claim(
        where="docs/limitations.md",
        phrase="alpha of **0.08** between trained therapists",
        kind="external",
        because=(
            "TN-Eval's published figure. Recomputed here it is 0.13, and printing it "
            "unattributed is what made the README read it as ours"
        ),
        covers=("0.08",),
        source="TN-Eval",
    ),
    Claim(
        where="docs/limitations.md",
        phrase="51 000 questions were asked again",
        kind="historical",
        because="the budget-128 answers were overwritten before the cache separated instruments",
        covers=("51 000",),
        caveat="not in this repository",
    ),
    Claim(
        where="docs/landscape.md",
        phrase="| Models benchmarked | 11 (2023–2024-era) | 8 (2024-era) |",
        kind="external",
        because="both counts are the source papers'; 8 was 7 until it was read out of Table 4",
        covers=("11", "8", "2024"),
        source="ACL 2025",
    ),
    Claim(
        where="docs/landscape.md",
        phrase=(
            "separates the eighteen models across 5.6% of its scale under "
            "`gemini-3.1-pro-preview` and 13.3% under `gpt-5.6-terra`"
        ),
        kind="computed",
        because=(
            "stated for one judge as though it held for both; the other spreads them 2.4x wider"
        ),
        covers=("eighteen", "5.6%", "13.3%"),
        expected=_trace_spread,
    ),
    Claim(
        where="docs/datasets.md",
        phrase="96 distinct such strings over 499 model-written sections",
        kind="corpus",
        because=(
            "replaced a figure with no definition behind it; the definition is beside it now. "
            "Moved 88/486 -> 96/499 on 2026-09-01 when two more models' iCARE notes landed in "
            "generations/, re-derived with tools/count_dressed_up_empties.py"
        ),
        covers=("96", "499"),
        expected=_dressed_up_empties,
    ),
    Claim(
        where="docs/datasets.md",
        phrase="18 of the 40 gold notes do not carry all 17 labels",
        kind="corpus",
        because="said 'most' when 22 of the 40 carry all seventeen",
        covers=("18", "40", "17"),
        expected=_ihope_labels,
    ),
)

#: Which gitignored input each corpus claim needs, so a skip can name it.
_CORPUS_INPUT = {
    "_dressed_up_empties": (_GENERATIONS, "generations/"),
    "_ihope_labels": (_GOLD, "data/ihope_test.json"),
}


def _for(path: str) -> tuple[Claim, ...]:
    return tuple(claim for claim in CLAIMS if claim.where == path)


def _of_kind(kind: str) -> list[Claim]:
    return [claim for claim in CLAIMS if claim.kind == kind]


def _gap(claim: Claim, needle: str) -> int | None:
    """Characters between the figure and the text that has to qualify it."""
    text = flat(claim.where)
    at = text.find(claim.phrase)
    if at < 0 or not needle:
        return None
    found = [match.start() for match in re.finditer(re.escape(needle), text)]
    return min((abs(where - at) for where in found), default=None)


# --- what a registered claim owes --------------------------------------------


@pytest.mark.parametrize("claim", CLAIMS, ids=lambda c: f"{c.where}:{c.phrase[:38]}")
def test_a_registered_claim_is_still_published(claim: Claim):
    """A rewrite has to come here and say what it changed.

    Silence is the failure mode this whole file exists for: a figure that moves
    and takes its explanation with it leaves nothing behind to notice.
    """
    assert claim.phrase in flat(claim.where), (
        f"{claim.where} no longer contains {claim.phrase!r}.\n"
        f"It was registered because {claim.because}.\n"
        "Update the phrase if it was reworded, or remove the entry and say why."
    )


@pytest.mark.parametrize("claim", CLAIMS, ids=lambda c: f"{c.where}:{c.phrase[:38]}")
def test_a_claim_covers_the_figures_it_states(claim: Claim):
    """`covers` is load-bearing twice over, so it may not drift from the phrase.

    It is what the ratchet credits and what a computed claim is compared
    against. A phrase that gained a figure while `covers` did not would hand
    its document a free unaccounted number and shift every later position by
    one.
    """
    assert sorted(claim.covers) == sorted(tokens_in(claim.phrase)), (
        f"{claim.where}: covers={claim.covers} but the phrase states "
        f"{tuple(tokens_in(claim.phrase))}.\n  phrase: {claim.phrase}"
    )


@pytest.mark.parametrize("claim", _of_kind("computed"), ids=lambda c: c.phrase[:38])
def test_a_computed_claim_still_equals_the_data(claim: Claim):
    said = tuple(as_value(token) for token in claim.covers)
    assert claim.expected and said == claim.expected(), (
        f"{claim.where} prints {said} where the data gives "
        f"{claim.expected() if claim.expected else None}, compared in the order "
        f"the sentence states them.\n"
        f"  phrase: {claim.phrase}\n  registered because {claim.because}"
    )


@pytest.mark.parametrize("claim", _of_kind("corpus"), ids=lambda c: c.phrase[:38])
def test_a_corpus_claim_still_equals_the_corpus(claim: Claim):
    """Only on a machine that has the corpus. Named, so a skip is not silence."""
    assert claim.expected, "a corpus claim with nothing to recompute is not checked at all"
    where, name = _CORPUS_INPUT[claim.expected.__name__]
    if not where.exists():
        pytest.skip(f"{name} is gitignored and absent here, so this figure cannot be recomputed")
    said = tuple(as_value(token) for token in claim.covers)
    assert said == claim.expected(), (
        f"{claim.where} prints {said} where {name} gives {claim.expected()}.\n"
        f"  phrase: {claim.phrase}\n  registered because {claim.because}"
    )


@pytest.mark.parametrize("claim", _of_kind("external"), ids=lambda c: c.phrase[:38])
def test_an_external_figure_names_whose_it_is_beside_it(claim: Claim):
    """A borrowed number printed bare reads as one of ours.

    That is not hypothetical: `alpha 0.08` sat unattributed in the README while
    this repository's own recomputation of the same quantity gives 0.13. And
    the attribution has to be *near* it: naming TN-Eval once at the top of a
    twelve-thousand-character file does not qualify a figure four screens down.
    """
    assert claim.source, "an external claim with no source is unfalsifiable"
    gap = _gap(claim, claim.source)
    assert gap is not None and gap <= NEARBY, (
        f"{claim.where} prints {claim.phrase!r} with {claim.source!r} "
        f"{'nowhere in the file' if gap is None else str(gap) + ' characters away'}, "
        f"further than {NEARBY}. A reader meets the figure first."
    )


@pytest.mark.parametrize("claim", _of_kind("historical"), ids=lambda c: c.phrase[:38])
def test_a_historical_figure_says_beside_itself_that_its_inputs_are_gone(claim: Claim):
    """Otherwise a reader is invited to re-derive something that cannot be."""
    gap = _gap(claim, claim.caveat or "")
    assert claim.caveat and gap is not None and gap <= NEARBY, (
        f"{claim.where} prints {claim.phrase!r} without saying, within {NEARBY} "
        f"characters, that its inputs are gone (looked for {claim.caveat!r}, "
        f"{'not found' if gap is None else str(gap) + ' characters away'}).\n"
        f"  registered because {claim.because}"
    )


def test_every_kind_is_one_the_docstring_explains():
    """A sixth class invented in passing would be a claim nothing checks."""
    known = {"computed", "corpus", "external", "historical", "elsewhere"}
    assert {claim.kind for claim in CLAIMS} <= known
    for claim in CLAIMS:
        if claim.kind in {"computed", "corpus"}:
            assert claim.expected, f"{claim.phrase!r} is {claim.kind} but recomputes nothing"


# --- the ratchet -------------------------------------------------------------

#: Figures in each document that nobody has classified yet, as of 2026-08-31.
#:
#: This is a debt, written down. It may go down and it may not go up: a new
#: number in a published page fails until it is registered above or the budget
#: is deliberately raised in a commit that says why.
UNACCOUNTED = {
    # Four budgets lowered on 2026-09-01, when the Czech branch left this
    # repository and took its sections of these documents with it. The debt
    # did not get paid; the documents got shorter.
    "docs/datasets.md": 53,
    "docs/landscape.md": 66,
    # Lowered from 146 on 2026-09-02: the saturation and floor-criteria
    # sections were rewritten for the two new systems and state fewer
    # figures (the old baseline/headline pair became one number, and the
    # old five-criterion-era rows went with them).
    # Lowered from 143 on 2026-09-03 with the count of the one model short of
    # the corpus for a non-parser reason, registered rather than left bare.
    "docs/limitations.md": 142,
    # Lowered from 74 on 2026-09-03: the leave-one-out pair is registered
    # rather than unclassified, and `+0.011` only began counting when it
    # stopped ending its sentence -- the number regex does not see a figure
    # with a full stop against it.
    "docs/methodology.md": 73,
    # Raised from 38 on 2026-09-01: a live capture was retaken and recorded
    # as its own dated section. Its counts -- how many ids the endpoint
    # returned that day and how many survived the filter -- are a log of one
    # capture, not a claim that can go stale, and registering each would say
    # otherwise.
    "docs/models-snapshot.md": 41,
    # Lowered from 40 on 2026-09-02: the Credits became APA references, every
    # figure in them registered as bibliographic, and the two bare venue years
    # the old list carried went with it.
    "README.md": 37,
    "NOTICE": 7,
}


def unaccounted(path: str) -> int:
    """Numbers in a document that no registered claim covers."""
    total = len(numbers(readable(path)))
    # Token by token, never joined into one string: `" ".join(("88", "486"))`
    # is `88 486`, which the thousands rule reads as a single figure, and the
    # document was silently credited one number for two.
    claimed = sum(len(numbers(token)) for claim in _for(path) for token in claim.covers)
    return total - claimed


@pytest.mark.parametrize("path", DOCUMENTS)
def test_a_document_gains_no_unaccounted_figure(path: str):
    now = unaccounted(path)
    assert now <= UNACCOUNTED[path], (
        f"{path} carries {now} unclassified figures, up from {UNACCOUNTED[path]}.\n"
        "A number added to a published page has to be registered in CLAIMS as "
        "computed, corpus, external, historical or elsewhere -- or the budget "
        "raised in a commit that says why it may be."
    )


@pytest.mark.parametrize("path", DOCUMENTS)
def test_the_debt_is_kept_honest(path: str):
    """A budget left far above the truth stops being a ratchet.

    Two of slack, so ordinary editing does not fail; more than that and the
    number is stale and has to be brought down.
    """
    now = unaccounted(path)
    assert UNACCOUNTED[path] - now <= 2, (
        f"{path} is down to {now} unclassified figures from a budget of "
        f"{UNACCOUNTED[path]}. Lower the budget to {now}."
    )


def test_no_published_document_escapes_the_ratchet():
    """A new page under `docs/` would otherwise be born uncovered.

    The list is written out rather than globbed, so that adding a document is a
    decision somebody makes here with a budget beside it -- but nothing may be
    published that this file has not been told about.
    """
    published = {f"docs/{path.name}" for path in DOCS.glob("*.md")} | {"README.md", "NOTICE"}
    assert published == set(DOCUMENTS), (
        "the published hand-written pages and the ratchet's list disagree.\n"
        f"  published but not listed: {sorted(published - set(DOCUMENTS))}\n"
        f"  listed but not published: {sorted(set(DOCUMENTS) - published)}"
    )


def test_the_scanner_reads_prose_and_not_machinery(tmp_path):
    """Through `readable`, the way it runs, not through a hand-made copy of it.

    An earlier version of this test stripped the code spans and the links
    itself and scanned the result, which exercised a re-implementation: it
    would have stayed green if `readable` had stopped stripping anything at all.
    """
    document = tmp_path / "sample.md"
    document.write_text(
        "The judge ran at harness 0.6.0 on 2026-08-27, scoring 40 sessions\n"
        "across 17 fields and 51 000 answers, with `thinking_budget 256` and a\n"
        "link [to it](https://example.invalid/1234) and a range of 5-10.\n"
        "<!-- LEADERBOARD:BEGIN -->\n999 generated\n<!-- LEADERBOARD:END -->\n",
        encoding="utf-8",
    )
    # `REPO_ROOT / absolute` is that absolute path, so `readable` reads the
    # sample itself and every rule it applies is the shipping one.
    found = numbers(readable(str(document)))
    assert found == ["40", "17", "51 000"], found
