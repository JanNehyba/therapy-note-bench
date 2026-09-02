"""Does the Czech dictionary still answer the pages, or only look as though it does?

A translation that falls behind does not throw. `tr` and the tagged template
both hand back their English when a key is missing, which is the right failure
-- a reader gets a sentence rather than a blank -- and it is exactly why nothing
would notice a whole panel reverting to English after somebody rewrote it.

So the keys are extracted from the templates and from a rendered payload, and
every one of them has to be in `i18n.CS`. Three shapes of key, three ways in,
one dictionary:

- ``data-t="page.sub"`` in the HTML, keyed by the id;
- ``T`...` `` in the script, keyed by the English with numbered holes;
- a string out of the payload, keyed by the English itself.

The tagged sentences are scanned rather than matched with a regex. They nest --
one of them picks its own singular and plural with a second tag inside a hole --
and a regex stopping at the first backtick reads the shape wrong and would pass
while asserting on nothing.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tnb import i18n, report, results
from tnb.results import Metrics, Row

RUNNER = Path(__file__).parent / "support" / "run_page.js"

#: Fields of the payload a page passes through `tr`. Kept as a list here rather
#: than discovered, because that is the point: a new column, blurb or caveat is
#: a new sentence for a reader, and this test is where it is noticed.
#:
#: What is *not* here is as deliberate. TN-Eval's prompt and rubric and iCARE's
#: field names are quoted, not written, and the pages draw them without asking
#: the dictionary: a Czech paraphrase of an instruction would show a reader
#: something no model was ever given.
PAYLOAD_FIELDS = (
    "tables[].title",
    "tables[].blurb",
    "tables[].design.scored_against",
    "tables[].design.human_role",
    "tables[].design.calibration",
    # The two lines above every table saying what the corpus is and what a note
    # is. Added to the payload without being added here, so they drew in English
    # on the Czech page and nothing said so -- which is the whole job of this
    # list, and the reason it is a list rather than a walk of every string.
    "tables[].terms[].term",
    "tables[].terms[].gloss",
    "tables[].columns[].label",
    "tables[].columns[].definition",
    "tables[].columns[].caveat",
    # Which instrument asked for a column. It rides on the column header, on the
    # Beats-outright header and in that column's legend -- six places on the
    # Czech page, all of which printed "TN-Eval rubric" in English while the
    # blurb directly above the table called the same instrument "rubrika
    # TN-Eval".
    "tables[].columns[].instrument",
    # The same label again, reached from the concordance rather than from a
    # column, which is where the Beats-outright header gets it.
    "concordance.*.instrument",
    "tables[].groups.measure",
    "tables[].rows[].metrics_note",
    "tables[].rows[].settings",
    "tables[].rows[].source",
    "tables[].rows[].section_order[]",
    "selection.tracks[].label",
    "selection.tracks[].judges[].settings_label",
    "licences[].used_for",
    "licences[].note",
    "licences[].licence",
    "similarity_example.note",
    "concordance.*.track_label",
    "concordance.*.measures[].measure",
    "concordance.*.tensions[].first",
    "concordance.*.tensions[].second",
    # The repeatability panel's per-instrument headings, drawn the same way.
    "repeatability.judges[].tracks[].label",
    "preference.measure",
)


def _walk(value, path: list[str]):
    """Every string a dotted field path names, however deep it is nested."""
    if not path:
        if isinstance(value, str) and value:
            yield value
        return
    step, rest = path[0], path[1:]
    if step == "[]":
        for item in value or []:
            yield from _walk(item, rest)
    elif step == "*":
        for item in (value or {}).values():
            yield from _walk(item, rest)
    elif isinstance(value, dict):
        yield from _walk(value.get(step), rest)


def _steps(field: str) -> list[str]:
    return [part for part in re.split(r"\.|(\[\])", field) if part]


def payload_strings(data: dict) -> list[str]:
    return [text for field in PAYLOAD_FIELDS for text in _walk(data, _steps(field)) if text.strip()]


def tagged_keys(source: str) -> list[str]:
    """The key of every tagged sentence in a script, holes numbered.

    Hand-scanned, for the reason in this module's docstring. `\\uXXXX` is
    decoded because the tag reads the cooked strings: a sentence written with
    `\\u2014` has an em dash in it as far as the dictionary is concerned.
    """
    keys: list[str] = []
    opening = re.compile(r"(?<![\w$.])T`")
    index = 0
    while (found := opening.search(source, index)) is not None:
        start = found.end()
        out: list[str] = []
        holes = 0
        i = start
        while i < len(source):
            char = source[i]
            if char == "\\":
                out.append(source[i : i + 2])
                i += 2
                continue
            if char == "`":
                break
            if char == "$" and source[i + 1 : i + 2] == "{":
                depth, i = 1, i + 2
                while i < len(source) and depth:
                    if source[i] == "`":  # a template literal inside the hole
                        i = _skip_literal(source, i + 1)
                        continue
                    depth += source[i] == "{"
                    depth -= source[i] == "}"
                    i += 1
                out.append(f"{{{holes}}}")
                holes += 1
                continue
            out.append(char)
            i += 1
        keys.append(
            re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), "".join(out))
        )
        # From just inside this one, so a tag nested in a hole is found too.
        index = start
    return keys


def holes_that_pick_a_word(source: str) -> dict[str, set[str]]:
    """Per tagged sentence, the holes whose filler is another tagged sentence.

    `${row.n_partial === 1 ? T`note` : T`notes`}` is the English choosing a word
    for its own number. A Czech sentence that says the same thing with one form
    has nothing to put there, and dropping the hole is right. A hole carrying a
    figure or a clause is not this, and dropping one silently removes what it
    carried.
    """
    keys = tagged_keys(source)
    opening = re.compile(r"(?<![\w$.])T`")
    found_holes: dict[str, set[str]] = {}
    index, order = 0, 0
    while (found := opening.search(source, index)) is not None:
        start = found.end()
        holes, picks, i = 0, set(), start
        while i < len(source):
            char = source[i]
            if char == "\\":
                i += 2
                continue
            if char == "`":
                break
            if char == "$" and source[i + 1 : i + 2] == "{":
                depth, opened, i = 1, i + 2, i + 2
                while i < len(source) and depth:
                    if source[i] == "`":
                        i = _skip_literal(source, i + 1)
                        continue
                    depth += source[i] == "{"
                    depth -= source[i] == "}"
                    i += 1
                if _only_inflects(source[opened : i - 1]):
                    picks.add(str(holes))
                holes += 1
                continue
            i += 1
        if order < len(keys):
            found_holes.setdefault(i18n.norm(keys[order]), set()).update(picks)
        order += 1
        index = start
    return found_holes


#: A branch of a ternary that can only ever produce English morphology: another
#: tagged word, or a suffix of at most two characters. ``note` or
#: `notes`` and ``s` or nothing` are the two shapes in the
#: templates, and neither has anything for a Czech sentence to put anywhere.
_INFLECTION = re.compile(r"^(?:T`[^`]*`|'[^']{0,2}'|\"[^\"]{0,2}\")$")


def _only_inflects(filler: str) -> bool:
    """Can this hole produce nothing but a word form?"""
    if "?" not in filler:
        return False
    branches, depth, current = [], 0, []
    for char in filler.split("?", 1)[1]:
        depth += char in "([{"
        depth -= char in ")]}"
        if char == ":" and depth == 0:
            branches.append("".join(current))
            current = []
            continue
        current.append(char)
    branches.append("".join(current))
    return all(_INFLECTION.match(branch.strip()) for branch in branches)


def _skip_literal(source: str, i: int) -> int:
    """Past the end of a nested template literal, holes and all."""
    depth = 0
    while i < len(source):
        if source[i] == "\\":
            i += 2
            continue
        if source[i] == "`" and not depth:
            return i + 1
        if source[i] == "$" and source[i + 1 : i + 2] == "{":
            depth += 1
            i += 1
        elif source[i] == "}" and depth:
            depth -= 1
        i += 1
    return i


@pytest.fixture(scope="module")
def templates() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(report.TEMPLATE_DIR.glob("*.html"))
    )


def _row(system: str, judge_model: str, value: float) -> Row:
    return Row(
        track=results.TRACK_TNEVAL,
        system_id=system,
        system_type="model",
        provider="einfra",
        prompt_version="tneval-soap-v1",
        judge_model=judge_model,
        judge_prompt_version="tneval-rubric-v1",
        judge_settings={"model": judge_model, "thinking_budget": 256},
        n_sessions_attempted=50,
        n_sessions_generated=50,
        n_sessions_scored=50,
        metrics=Metrics(
            headline={"completeness": value, "conciseness": value, "faithfulness": value * 5},
            by_section={"subjective": {"completeness": value}},
            detail={"subjective-symptoms": value},
        ),
    )


def test_every_marked_paragraph_has_a_czech_entry(templates):
    """`data-t` names an id and nothing checks that the id exists."""
    missing = sorted(
        key for key in set(re.findall(r'data-t="([^"]+)"', templates)) if key not in i18n.CS
    )
    assert not missing, f"marked for translation and not translated: {missing}"


def test_every_tagged_sentence_has_a_czech_entry(templates):
    keys = {i18n.norm(key) for key in tagged_keys(templates) if key.strip()}
    assert len(keys) > 100, "the scanner found almost nothing, so it is the scanner that broke"
    dictionary = {i18n.norm(key) for key in i18n.CS}
    missing = sorted(keys - dictionary)
    assert not missing, f"sentences on the page with no Czech: {missing}"


def test_every_payload_string_the_page_draws_has_a_czech_entry():
    """The other half of the page, and the half that grows on its own.

    A track, a column or a caveat is authored in Python and reaches the reader
    through the payload. Adding one is exactly the change that leaves a Czech
    page with an English sentence in the middle of it, and nothing else would
    say so.
    """
    rows = [_row("x", "a-judge", 0.5)]
    data = report.build(rows)
    data["licences"] = report.LICENCES
    data["similarity_example"] = report.similarity_example()
    data["concordance"] = report.concordance_payload(rows)

    dictionary = {i18n.norm(key) for key in i18n.CS}
    missing = sorted({s for s in payload_strings(data) if i18n.norm(s) not in dictionary})
    assert not missing, f"drawn from the payload with no Czech: {missing}"


def test_the_published_pages_have_a_czech_entry_for_everything_they_draw():
    """The same question asked of the run that is actually published.

    The fixture above is three rows and cannot produce a failure reason, a
    withdrawn group or a settings label. `docs/leaderboard.json` is the real
    one, and it is in the repository, so the test can be exact about the page
    a reader will open.
    """
    import json

    from tnb.config import REPO_ROOT

    path = REPO_ROOT / "docs" / "leaderboard.json"
    if not path.exists():
        pytest.skip("no published payload in this checkout")
    data = json.loads(path.read_text(encoding="utf-8"))

    dictionary = {i18n.norm(key) for key in i18n.CS}
    missing = sorted({s for s in payload_strings(data) if i18n.norm(s) not in dictionary})
    assert not missing, f"published and untranslated: {missing}"


def test_a_missing_key_leaves_english_rather_than_a_hole():
    """The rule the whole design rests on, asserted rather than assumed."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the page cannot be executed here")

    script = """
      const I18N = {cs: {'Only this one': 'Jenom tahle'}};
      const DEFAULT_LANG = 'en';
      const NORM = v => String(v).replace(/\\s+/g, ' ').trim();
      let LANG = 'cs';
      const dict = () => (LANG === DEFAULT_LANG ? null : I18N[LANG]) || null;
      function tr(text) {
        if (text === null || text === undefined) return text;
        const table = dict();
        if (!table) return text;
        const found = table[NORM(text)];
        return found === undefined ? text : found;
      }
      function T(strings, ...values) {
        const english = strings.reduce(
          (out, part, i) => out + part + (i < values.length ? `{${i}}` : ''), '');
        const table = dict();
        const shape = (table && table[NORM(english)]) || english;
        return shape.replace(/\\{(\\d+)\\}/g, (whole, index) =>
          values[index] === undefined ? '' : values[index]);
      }
      console.log(tr('Only this one'));
      console.log(tr('Nobody translated this'));
      console.log(T`A sentence with ${7} in it`);
    """
    finished = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, encoding="utf-8", timeout=30
    )
    assert finished.returncode == 0, finished.stderr
    said = finished.stdout.splitlines()
    assert said[0] == "Jenom tahle", "a key that is there is used"
    assert said[1] == "Nobody translated this", "a key that is not there keeps its English"
    assert said[2] == "A sentence with 7 in it", "and so does a sentence with a hole in it"


def test_the_helpers_read_the_dictionary_the_module_writes():
    """One inlined blob, one shape. `dictionary()` normalises keys and not values."""
    table = i18n.dictionary()
    assert set(table) == {"cs"}, "English is the source, not an entry"
    assert all(key == i18n.norm(key) for key in table["cs"]), "keys are normalised on the way in"
    assert table["cs"][i18n.norm("and")] == " a ", (
        "a joiner keeps the spaces a trimmed key cannot carry"
    )


def test_both_pages_run_in_czech(tmp_path):
    """A render function that only throws in Czech is a render function that throws.

    The page is one inline script, so a `null` where a string was expected
    blanks it with no error anywhere a reader would look -- and the Czech path
    goes through code the English path does not.
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the page cannot be executed here")

    rows = [
        _row(system, judge, value)
        for judge, scores in (("a-judge", {"x": 0.9, "y": 0.4}), ("b-judge", {"x": 0.5, "y": 0.8}))
        for system, value in scores.items()
    ]
    data = report.build(rows)
    data["concordance"] = report.concordance_payload(rows)
    data["licences"] = report.LICENCES
    data["similarity_example"] = report.similarity_example()
    data["protocol"] = report.protocol()

    for name, render in (("index", report.render_page), ("methods", report.render_methods)):
        script = tmp_path / f"{name}.js"
        script.write_text(
            "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", render(data), re.S)),
            encoding="utf-8",
        )
        finished = subprocess.run(
            [node, str(RUNNER), str(script)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            env={**__import__("os").environ, "PAGE_SEARCH": "?lang=cs"},
        )
        assert finished.returncode == 0, finished.stdout + finished.stderr
        assert "RAN." in finished.stdout, f"{name} did not finish in Czech"
        assert "lang: " in finished.stdout, f"{name} drew no language switch"


# --- the other direction ----------------------------------------------------
#
# Every test above asks "does this sentence on the page have a Czech entry?".
# Reversed, the question is "does this Czech entry still answer a sentence on
# the page?" -- and it is the one that catches a source somebody edited.
#
# Two of the three key shapes invalidate themselves: a tagged sentence and a
# payload string *are* their own key, so editing the English breaks the lookup
# and the coverage tests above fail. What they do not do is say that the old
# translation is now an orphan, which is the fact a maintainer needs. The third
# shape does not even do that: `data-t` is keyed by an id, so editing the prose
# under it changes nothing, the Czech keeps saying what it always said, and the
# two languages quietly disagree. Four of those paragraphs carry a hand-typed
# number.


#: Keys answered before their string can appear in a run. Each is a decision
#: made in advance rather than an oversight, and the reason is what makes it
#: one -- the same shape as the allow-list in `test_no_clinical_content.py`.
ANSWERED_IN_ADVANCE = {
    "therapist": "a system-type chip, drawn from TYPE_LABEL rather than from the payload",
    "reference model": "the same, for a source paper's own system",
    "as published": "the same, for a row from an older harness",
    "{ordinal-suffix}": "a sentinel, not a sentence: Czech writes every ordinal `4.`",
    "answer did not contain a SOAP dictionary": "a failure reason, only there when one failed",
    "truncated at max_tokens=16384": "an unreached reason, only there when a call was cut off",
    "tneval-soap": "a track id, printed only where a withdrawn group is named",
    "pdsqi-soap": "the same",
    "icare": "the same",
    "still separates models": "a verdict gloss, a JS constant rather than a marked sentence",
    "every model already does this": "the same",
    "partly, weakly": "the same",
    "nobody can, the therapist included": "the same",
}


def filter_labels(templates: str) -> set[str]:
    """The tick-box labels the leaderboard holds, whether or not a row needs one.

    `FILTERS` is a JS constant, so `T` never touches it and the tagged-sentence
    scanner cannot find it. Matched on the array's own shape so a filter added
    later is covered by the same rule.
    """
    inside = re.search(r"const FILTERS = \[(.*?)\n\];", templates, re.S)
    if not inside:
        return set()
    return {
        found.group(1).encode().decode("unicode_escape")
        for found in re.finditer(r"label:\s*'((?:[^'\\]|\\.)*)'", inside.group(1))
    }


def test_every_filter_the_table_offers_has_a_czech_label(templates):
    """A control the page draws in one language is a control half the readers cannot read.

    Not covered by the tagged-sentence test: these are constants, not `T`
    templates. Not covered by the drawn-page tests either, because a filter is
    only drawn when some row carries the type it filters, and `published` has
    no rows yet.
    """
    labels = filter_labels(templates)
    assert labels, "the scanner found no filter labels, so it is the scanner that broke"
    dictionary = {i18n.norm(key) for key in i18n.CS}
    missing = sorted(label for label in labels if i18n.norm(label) not in dictionary)
    assert not missing, f"tick boxes with no Czech: {missing}"


def live_strings(templates: str) -> set[str]:
    """Every English string the pages can ask the dictionary about.

    Read from where each one is authored -- a measure table, a track title, a
    licence row -- rather than from a run. A run shows only what today's data
    happens to contain, and the sentence this test exists for is the one nobody
    looked at.
    """
    import json

    live = set(re.findall(r'data-t="([^"]+)"', templates))
    live |= {i18n.norm(key) for key in tagged_keys(templates) if key.strip()}
    live |= {i18n.norm(title) for title in report.TRACK_TITLES.values()}
    live |= {i18n.norm(blurb) for blurb in report.TRACK_BLURBS.values()}
    live |= {i18n.norm(label) for label in report.TRACK_SWITCH_LABELS.values()}
    for design in report.TRACK_DESIGN.values():
        live |= {i18n.norm(value) for value in design.values() if isinstance(value, str)}
    # Every measure table the registry names, not a list of three. A track
    # added to `report.MEASURE_TABLES` brings its columns with it, and a test
    # that had to be edited to notice would not have noticed.
    for table in report.MEASURE_TABLES.values():
        for key, meta in table.items():
            live.add(i18n.norm(key))
            live |= {i18n.norm(meta[f]) for f in ("label", "definition", "caveat") if meta.get(f)}
    # Sentences the payload carries rather than the template. They are chosen
    # per track in Python -- which reason a table has for not being ranked,
    # what its expandable block holds -- so `tagged_keys` cannot see them and
    # every one of them would read as an orphan.
    live |= {i18n.norm(label) for label in report.DETAIL_LABELS.values()}
    for licence in report.LICENCES:
        live |= {i18n.norm(licence[f]) for f in ("used_for", "note", "licence") if licence.get(f)}
    live.add(i18n.norm(report.SIMILARITY_EXAMPLE["note"]))
    live |= {i18n.norm(name) for name in report.SECTION_ORDER}
    # The merged table's title and blurb, which no single track owns.
    published = report.DOCS_DIR / "leaderboard.json"
    if published.exists():
        payload = json.loads(published.read_text(encoding="utf-8"))
        live |= {i18n.norm(text) for text in payload_strings(payload)}

    # The methods page's other panels come from their own tracked files, and
    # every one of those files is in the repository -- so the measure names, the
    # statistics and the saturation verdicts are checkable rather than taken on
    # trust. Each is read where the page reads it.
    calibration = _json(report.DOCS_DIR / "calibration.json")
    for agreement in (calibration or {}).get("agreements", []):
        live.add(i18n.norm(agreement["name"].replace("_", " ")))
        live.add(i18n.norm(agreement["name"]))
        live.add(i18n.norm(agreement["statistic"]))
    for judge in (_json(report.DOCS_DIR / "judges.json") or {}).get("judges", []):
        live |= {i18n.norm(a["name"]) for a in judge.get("agreements", [])}
    for path in report.DOCS_DIR.glob("saturation-*.json"):
        for criterion in (_json(path) or {}).get("criteria", []):
            live.add(i18n.norm(criterion["section"]))
            live.add(i18n.norm(criterion["verdict"]))
    live.add(i18n.norm((_json(report.DOCS_DIR / "preference.json") or {}).get("measure", "")))
    return live


def _json(path):
    import json

    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def test_no_czech_entry_answers_a_sentence_that_no_longer_exists(templates):
    """A key that matches nothing is a source somebody edited.

    The failure this exists for: a number is corrected in a template or in a
    scorer, the English key stops matching, and the Czech page silently reverts
    that one sentence to English. Nothing else says so -- falling back to the
    English is the design, and a stale key is indistinguishable from a sentence
    nobody has translated yet.
    """
    from tnb import results

    # A failure reason is translated before it has ever happened, on purpose:
    # discovering the gap the first time a model fails means discovering it on
    # the page. They are exempt by rule rather than by list, so a reason added
    # later does not need remembering here as well.
    # A tick box for a declared system type that has no rows yet is drawn by no
    # page, and its translation is not stale -- it is early, for the same reason
    # a failure reason is translated before it has ever happened.
    in_advance = set(ANSWERED_IN_ADVANCE) | set(results.HARNESS_REASONS) | filter_labels(templates)

    live = live_strings(templates)
    orphans = sorted(
        key
        for key in i18n.CS
        if key not in in_advance and key not in live and i18n.norm(key) not in live
    )
    assert not orphans, (
        "Czech entries that answer nothing on either page -- the English was edited and the "
        f"translation was not, so these sentences now draw in English: {orphans}"
    )


def test_the_advance_answers_are_all_still_needed(templates):
    """And the allow-list does not outlive what it was written for."""
    live = live_strings(templates)
    stale = sorted(key for key in ANSWERED_IN_ADVANCE if key in live or i18n.norm(key) in live)
    assert not stale, f"listed as answered in advance and now drawn from a live source: {stale}"

    gone = sorted(key for key in ANSWERED_IN_ADVANCE if key not in i18n.CS)
    assert not gone, f"answered in advance and no longer in the dictionary: {gone}"


#: A number, however it is written: `0.18`, `2026`, `1.00`, `0.6.0`.
NUMBER = re.compile(r"\d+(?:\.\d+)*")
#: A numbered hole, stripped first -- otherwise `{0}` counts as the number zero.
HOLE = re.compile(r"\{\d+\}")


def numbers_in(text: str) -> list:
    """The numbers in a sentence, compared by value rather than by spelling.

    `08` and `8` are one number written two ways, and the Czech date format
    writes the second where the English writes the first.
    """
    found = NUMBER.findall(HOLE.sub(" ", text))
    return sorted(float(n) if n.count(".") < 2 else n for n in found)


def english_of(key: str, templates: str) -> str | None:
    """What a `data-t` id actually marks, read out of the template.

    The other two key shapes are their own English. This one is an id, so the
    English has to be fetched -- and fetching it is the point: it is the half
    that can change without the key changing with it.
    """
    found = re.search(rf'<(\w+)[^>]*\bdata-t="{re.escape(key)}"[^>]*>', templates)
    if not found:
        return None
    tag, start = found.group(1), found.end()
    end = templates.find(f"</{tag}>", start)
    return templates[start:end] if end != -1 else None


def test_a_translation_carries_the_same_numbers_as_its_english(templates):
    """The hole the two directions above still leave open.

    `data-t` is keyed by an id, so a number corrected in the marked paragraph
    leaves the key intact and the Czech untouched: no fallback, no orphan, two
    languages stating different figures. Four of these paragraphs carry a
    hand-typed number -- Krippendorff's alpha twice, a date and a section count
    -- and every one of them is written down somewhere else in this repository
    as well.

    Applied to all three shapes and not only to `data-t`, because a mistyped
    digit in a translation is the same defect arriving from the other side.
    """
    marked = set(re.findall(r'data-t="([^"]+)"', templates))
    wrong = []
    for key, czech in i18n.CS.items():
        english = english_of(key, templates) if key in marked else key
        assert english is not None, f"{key} is marked in a template and could not be read back"
        if numbers_in(english) != numbers_in(czech):
            wrong.append(f"{key}: English {numbers_in(english)} against Czech {numbers_in(czech)}")
    assert not wrong, "a translation states different numbers from its English: " + "; ".join(wrong)


def test_every_string_a_track_registry_holds_has_a_czech_entry():
    """The claim the payload test cannot make, and the one that matters.

    `test_every_payload_string_the_page_draws_has_a_czech_entry` builds a
    payload and checks what came out. That only ever sees a track with rows in
    `results/rows.jsonl` -- so a track registered in `report.COLUMNS` whose rows
    live somewhere else is invisible to it, and its title, its blurb and its
    seven columns can reach a page with no Czech behind them while every test
    passes. The Czech track is exactly that shape: it is registered so a local
    report can draw it, and its rows never reach the published file.

    So this asks the registries instead. Registering a track is the moment the
    strings exist; it should also be the moment they are answered.
    """
    missing = {}
    for track in report.COLUMNS:
        authored = {
            "title": report.TRACK_TITLES.get(track),
            "switch label": report.TRACK_SWITCH_LABELS.get(track),
            "blurb": report.TRACK_BLURBS.get(track),
        }
        for field, value in (report.TRACK_DESIGN.get(track) or {}).items():
            # `human_role_short` is a discriminator, not a sentence: `designBlock`
            # tests it against 'competitor' to pick which of two chips to draw,
            # and the chip's own words are a tagged sentence like any other.
            if isinstance(value, str) and field != "human_role_short":
                authored[f"design.{field}"] = value
        for key, _digits in report.COLUMNS[track]:
            # Through `column_meta`, not out of the raw table: a definition or a
            # caveat may hold a placeholder the report fills before the string
            # reaches a reader -- the rubric's criterion count is counted rather
            # than typed -- and the dictionary is keyed by what is drawn. Asking
            # the raw table would demand a Czech entry for a sentence with a
            # `{hole}` still in it and accept one whose filled form is missing.
            meta = report.column_meta(track, key)
            for field in ("label", "definition", "caveat"):
                authored[f"{key}.{field}"] = meta.get(field)
        for field, value in authored.items():
            if value and i18n.norm(value) not in {i18n.norm(k) for k in i18n.CS}:
                missing[f"{track}.{field}"] = value[:70]
    assert not missing, (
        "registered on a track and drawable on a page with no Czech behind it: "
        + "; ".join(f"{where} ({text}...)" for where, text in sorted(missing.items()))
    )


def test_every_failure_reason_the_harness_writes_has_a_czech_entry():
    """A failure reason reaches the page, so an untranslated one is an English
    sentence in the middle of a Czech table -- and `HARNESS_REASONS` is a
    closed list somebody adds to when they add a way to fail.

    The same shape as the parser table that let two tasks fall through: a list
    nothing checks is a list something falls out of. That one was caught by a
    person reading a commit; this one is caught here.
    """
    from tnb import results

    have = {i18n.norm(key) for key in i18n.CS}
    missing = [
        reason
        for reason in results.HARNESS_REASONS
        # The truncation reason carries the budget, so the phrase on the page is
        # a prefix with a number after it and is translated as its own string.
        if not reason.startswith("truncated at max_tokens") and i18n.norm(reason) not in have
    ]
    assert not missing, f"failure reasons with no Czech: {missing}"


def test_a_czech_sentence_holds_every_hole_its_english_does(templates):
    """A translation that drops a hole drops whatever the hole was carrying.

    Nothing else notices. `tr` fills the holes it finds and returns the string;
    a value one hole short renders cleanly, reads well, and is missing a clause.
    It happened to the sentence that gives the leaderboard's ordering column its
    reason: the English gained a clause saying whether the judge's lead over the
    two therapists clears zero, the Czech value was left as it was, and the
    Czech page drew the sentence with the finding silently cut off the end --
    the one fact that separates the two published judges.

    An extra hole is as bad and louder: it renders as a literal `{7}`.
    """
    holes = re.compile(r"\{(\d+)\}")
    inflections = holes_that_pick_a_word(templates)
    wrong = {}
    for key, value in i18n.CS.items():
        if not isinstance(value, str):
            continue
        in_key, in_value = set(holes.findall(key)), set(holes.findall(value))
        # A hole whose English filler is itself a tagged word -- the singular or
        # the plural of a noun -- may go: Czech says the same thing with one
        # form. Read out of the template, so a hole carrying a figure or a
        # clause is never covered by it.
        may_go = inflections.get(i18n.norm(key), set())
        if in_value - in_key or (in_key - in_value) - may_go:
            wrong[key[:60]] = f"key {sorted(in_key)} vs Czech {sorted(in_value)}"
    assert not wrong, (
        "Czech entries whose holes do not match their English -- whatever the missing hole "
        f"carried is dropped from the page without a trace: {wrong}"
    )
