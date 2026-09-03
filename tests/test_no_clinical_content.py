"""No fragment of a clinical transcript may enter a tracked file.

The Czech track reads ten real psychotherapy sessions from one client. They live
in ``data/``, which is ignored — but "ignored" is a property of one checkout, and
this repository has already had a working document swept into a commit by a
`git add` that was wider than its author meant. Scores may be published; text
may not.

So it is a test rather than a promise, and it is deliberately a different test
from ``test_secrets.py``: that one looks for credentials, and would not notice a
paragraph of a session.

Three limits, stated rather than implied. It runs after ``git commit``, so it is
a backstop and not a gate. It reads the current worktree, so text committed and
later deleted stays in history where this cannot see it. And the diacritic scan
is a net, not a proof — a Czech sentence typed without diacritics passes it. The
corpus-fragment scan below is the one that is exact, and it is exact only while
``data/czech`` is present.

Nothing here prints what it finds. A failure names the tracked file and the
session's digest id; reproducing the offending sentence in a test report would
be the leak.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from tnb.config import REPO_ROOT

#: Letters that exist in Czech and not in English. A cheap, broad net for
#: transcript text that reached a file it should not have.
#:
#: Written as escapes rather than as the letters themselves, because this file
#: asserts that no tracked file outside the allow-list holds Czech -- and
#: spelling the class out put the scanner into its own report. Allow-listing it
#: instead would have been the wrong repair: the allow-list opens a door per
#: file with a reason, and "the file that guards the door" is the one entry
#: that must never be on it.
DIACRITIC = re.compile(
    "[" + "\u011b\u0161\u010d\u0159\u017e\u00fd\u00e1\u00ed\u00e9\u00fa\u016f\u0148\u0165\u010f"
    "\u011a\u0160\u010c\u0158\u017d\u00dd\u00c1\u00cd\u00c9\u00da\u016e\u0147\u0164\u010e]"
)

#: The only tracked files that may contain Czech, each with the reason it may.
#: A path is listed one per line so that adding one is a decision somebody made
#: rather than a wildcard that quietly grew.
ALLOWED_CZECH = {
    "src/tnb/scoring/czech.py": "the six language questions are put to the judge in Czech",
    "src/tnb/tasks/czech.py": "the note-generation prompt is Czech",
    "src/tnb/tasks/deepsy.py": "the macros the Deepsy application fills its prompts with",
    "tests/test_czech_scoring.py": "an invented note, used to exercise the rubric",
    "tests/test_czech_datasets.py": "asserts on the invented fixtures",
    "tests/test_czech_run.py": "an invented note, used to exercise the runner",
    "tests/test_deepsy.py": "an invented session, and the prompt fragments it checks for",
    "tests/test_czech_pdsqi.py": "an invented note, and an invented line of a session "
    "that must not reach the judge",
    "tests/test_czech_anchor.py": "an invented note, quoted two ways, to exercise the "
    "counted column",
    "tools/czech_control.py": "an invented clean note, and seven faults planted in it",
    "tools/czech_pdsqi_control.py": "the filler sentences that pad the invented "
    "note, to test whether the succinctness column responds",
    "tools/czech_pdsqi_form.py": "the three PDSQI questions and their anchors in "
    "Czech, so the rating page can be read without translating as you go",
    "tools/czech_length.py": "the Czech wording a length instruction would use, "
    "searched for in the prompts rather than assumed",
    "tools/czech_brief_cs.py": "the Czech text of the briefing that goes to the team",
    "tests/fixtures/czech/real/999001.txt": "invented transcript, marked as such",
    "tests/fixtures/czech/translated/ukazka-b.txt": "invented transcript, marked as such",
    "tests/test_counts_match_their_lists.py": "four published Czech sentences, "
    "quoted so their counts can be checked against the same list in code as their "
    "English twins, and the Czech numerals those sentences spell. Nothing from a "
    "session: every string is a page's own wording",
    "tools/czech_calques.py": "the prompt that asks a judge which expressions in a "
    "note are literal translations from English, plus the two examples it is given. "
    "Checked fragment by fragment against every transcript and both code files: "
    "twenty fragments, thirty-six files, no match",
    "tools/czech_category_control.py": "one invented sentence per category, planted "
    "in the invented clean note so gate 7 can ask whether a category fires on a note "
    "built to carry it. Checked fragment by fragment against every transcript and "
    "every coded span: none of them appears in real material",
    "tools/czech_code.py": "the two coder prompts, in the language of the notes "
    "they are asked about",
    "tools/czech_units.py": "the abbreviations a full stop does not end a sentence "
    "after, the openers that only qualify what came before, and the subordinators "
    "that open a second clause -- all of them Czech grammar, none of them a note",
    "tools/czech_structure.py": "the Czech a regular expression has to match to "
    "count a paralinguistic claim, a refusal to judge, or a stopword",
    "tests/test_czech_code.py": "an invented note, used to exercise the span check",
    "tests/test_czech_units.py": "invented sentences, used to exercise the cut",
    "tests/test_czech_structure.py": "an invented note, used to exercise the census",
}

#: What every file under ``tests/fixtures/czech`` must say about itself. The
#: allow-list above opens a door; this is what stops a real transcript walking
#: through it by being dropped into a directory whose path is permitted.
FIXTURE_MARKER = "SYNTHETIC-FIXTURE"

#: The published surface that may never carry Czech at all. `docs/index.html`
#: and `docs/methods.html` left this list when the pages became bilingual and
#: came back on 2026-09-03, when the Czech mirror was taken off them: the rule
#: they were the exception to is now the rule for everything published, which
#: is both simpler and stricter than the pair of tests that stood in for it.
PUBLISHED = (
    "docs/leaderboard.json",
    "README.md",
    "docs/index.html",
    "docs/methods.html",
    "docs/brief.html",
)

#: Where a page inlines the numbers. A leak lands in the payload -- it would
#: arrive as a measure, a caveat, a blurb or a failure reason.
PAGES = ("docs/index.html", "docs/methods.html")
PAYLOAD_MARKER = "const DATA = "

#: A corpus label reaches `Row.dataset_checksums` and therefore the page. The
#: real transcripts are named after clinical record numbers, so a key carrying a
#: run of digits is the shape of a leak even when it looks harmless.
PUBLISHABLE_LABEL = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")

#: Reasons written before the vocabulary existed, and left where they are.
#:
#: `results/` is append-only, so these three rows keep what they were written
#: with. They are e-INFRA rate-limit bodies; the key hash was already masked
#: when they were written and there is no clinical text in them, which is why
#: leaving them is safe rather than merely convenient.
#:
#: This body did reach the published page, and the history says exactly when.
#: `5a4d2e6` (2026-08-25 16:05) wrote it into `docs/leaderboard.json` and
#: `docs/index.html`; `33b9e8c` (18:54) took it out again, when a rate limit
#: stopped being counted as the model's failure and the row moved groups. Both
#: commits are on `origin/main`, which is public and serves the page, so for
#: those three hours it was live. It is out of the current render, and
#: `Row.__post_init__` now brings every row through `normalise_reason` on the
#: way in, so no renderer can put it back. Only the raw line still holds it, and
#: git history holds it permanently.
#:
#: Verified 2026-08-26 by `git log -S` over both files. Nothing may be added to
#: this tuple: a new entry means a run wrote an off-vocabulary reason, which is
#: the thing the test exists to catch.
GRANDFATHERED = (
    'HTTP429: {"error":{"message":"Rate limit exceeded for api_key: .... '
    "Limit type: max_parallel_requests. Current limit: 4,",
)
RECORD_NUMBER = re.compile(r"\d{4,}")


@pytest.fixture(scope="session")
def tracked_files() -> list[Path]:
    """Every file git would publish. Ignored files are not this test's business."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [REPO_ROOT / name for name in result.stdout.split("\0") if name]


def _readable_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


# --- the broad net ---------------------------------------------------------


def test_only_named_files_contain_czech(tracked_files):
    offenders = []
    for path in tracked_files:
        text = _readable_text(path)
        if text and DIACRITIC.search(text) and _relative(path) not in ALLOWED_CZECH:
            offenders.append(_relative(path))
    assert not offenders, f"Czech text in tracked files that may not carry it: {offenders}"


def test_the_scanner_is_never_allow_listed():
    """The one file that may not buy itself an exemption.

    Spelling the diacritic class out as letters makes this file match its own
    scan, and the cheapest way to green is to add it to the allow-list. That
    repair costs the guarantee: "no tracked file holds Czech except these six"
    would then be enforced by a scanner standing outside its own rule, and a
    real transcript pasted into this file as a test case would pass. The class
    is escaped instead, so the scanner stays under the scan.
    """
    assert _relative(REPO_ROOT / "tests/test_no_clinical_content.py") not in ALLOWED_CZECH
    assert not DIACRITIC.search(path_text := Path(__file__).read_text(encoding="utf-8"))
    assert "ALLOWED_CZECH" in path_text  # the file really is the one being read


def test_the_allow_list_has_no_stale_entries(tracked_files):
    """An entry for a file that no longer holds Czech is a door left open."""
    present = {_relative(path) for path in tracked_files}
    for name in ALLOWED_CZECH:
        if name not in present:
            continue  # not written yet; the entry is a decision made in advance
        text = _readable_text(REPO_ROOT / name)
        assert text is not None and DIACRITIC.search(text), (
            f"{name} is allow-listed for Czech but contains none -- remove the entry"
        )


def test_the_published_surface_carries_no_czech_at_all():
    """No allow-list here, for the files that are still monolingual."""
    for name in PUBLISHED:
        text = _readable_text(REPO_ROOT / name)
        if text is None:
            continue
        assert not DIACRITIC.search(text), f"{name} contains Czech text"


def _inlined(page: str, marker: str):
    """One of the two JSON blobs a rendered page inlines, parsed.

    Parsed rather than scanned as text. `report` escapes `<` as `\\u003c` so a
    string carrying markup cannot end the `<script>` block early, and a regex
    over the raw line would compare that escaped form against the dictionary's
    real one and call every translation a stray.
    """
    start = page.index(marker) + len(marker)
    line = page[start : page.index("\n", start)].rstrip().rstrip(";")
    return json.loads(line)


def _strings(value) -> list:
    """Every string anywhere inside a parsed payload, keys included."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [t for k, v in value.items() for t in _strings(k) + _strings(v)]
    if isinstance(value, list):
        return [t for item in value for t in _strings(item)]
    return []


def test_the_published_data_payload_carries_no_czech():
    """The half of a page a leak would arrive in, named on its own.

    Everything measured reaches the reader through `const DATA` -- measures,
    caveats, blurbs, track titles, failure reasons, every row. The whole file is
    scanned by `test_the_published_surface_carries_no_czech_at_all` now that the
    Czech mirror is gone; this stays beside it because the two fail differently.
    A file-wide scan reports "the page contains Czech text" without saying that
    it arrived as data, which is the only way a corpus leak could get there.
    """
    for name in PAGES:
        text = _readable_text(REPO_ROOT / name)
        if text is None:
            continue
        czech = [t for t in _strings(_inlined(text, PAYLOAD_MARKER)) if DIACRITIC.search(t)]
        assert not czech, f"{name}: {len(czech)} Czech strings in the data payload"


def test_the_pages_carry_no_translation_machinery():
    """The Czech mirror is gone, and the plumbing went with it.

    Removed on 2026-09-03: a dictionary inlined beside the payload, a switch in
    the corner, and three call shapes that looked a sentence up. The call shapes
    stay as pass-throughs -- several hundred sites across two templates, and
    rewriting them would be a large edit to working pages for nothing a reader
    would see -- so what says the mirror is really gone is that nothing looks
    anything up and no second wording is shipped.

    The Czech *scoring* track is untouched and is a different thing entirely:
    notes written and judged in Czech, in `src/tnb/scoring/czech.py` and the
    tools beside it. That is a measurement, not a translation of this page.
    """
    for name in PAGES:
        text = _readable_text(REPO_ROOT / name)
        if text is None:
            continue
        for gone in ("const I18N", "installLanguageSwitch", "LANGUAGE_NAMES", 'id="lang"'):
            assert gone not in text, f"{name} still carries {gone!r}"


# --- the fixtures ----------------------------------------------------------


# --- the corpus itself -----------------------------------------------------


def test_no_tracked_path_is_under_data(tracked_files):
    """`data/` is ignored, and this is what proves the rule still holds."""
    inside = [_relative(p) for p in tracked_files if _relative(p).startswith("data/")]
    assert not inside, f"corpus files are tracked: {inside}"


# --- what a run records about a failure ------------------------------------


def test_the_grandfathered_reasons_are_still_the_only_ones(tracked_files):
    """A named exception that no longer applies is an exception nobody rechecks.

    If a redaction of `results/rows.jsonl` is ever authorised, this fails and
    the tuple goes with it.
    """
    from tnb import results

    found = set()
    for line in (REPO_ROOT / "results" / "rows.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        for field in ("failure_reasons", "unreached_reasons"):
            for reason in payload.get(field) or {}:
                if results.normalise_reason(reason) != reason:
                    found.add(reason)

    assert found == set(GRANDFATHERED), (
        "the set of pre-vocabulary reasons on disk changed -- update GRANDFATHERED "
        "only if a run did not write the new one"
    )


def test_every_recorded_reason_is_one_the_harness_wrote(tracked_files):
    """`failure_reasons` keys are rendered into the page. They used to be
    provider bodies passed through a filter; they are now values from a closed
    set, and this is what holds them to it.

    The check is that `normalise_reason` leaves the key alone: anything it would
    rewrite is something no run should have written.
    """
    from tnb import results

    for path in tracked_files:
        if path.suffix not in (".json", ".jsonl"):
            continue
        text = _readable_text(path)
        if text is None or "reasons" not in text:
            continue

        payloads = (
            [json.loads(line) for line in text.splitlines() if line.strip()]
            if path.suffix == ".jsonl"
            else [json.loads(text)]
        )
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            for field in ("failure_reasons", "unreached_reasons"):
                for reason in payload.get(field) or {}:
                    if reason in GRANDFATHERED:
                        continue
                    assert results.normalise_reason(reason) == reason, (
                        f"{_relative(path)}: {field} carries a reason no run would write today"
                    )


# --- what a run records about a corpus -------------------------------------


def test_every_recorded_corpus_label_is_publishable(tracked_files):
    """`Row.dataset_checksums` is copied into every row and rendered on the
    page. Its keys are corpus labels, so a key that looks like a record number
    is the shape of a leak."""
    for path in tracked_files:
        if path.suffix not in (".json", ".jsonl"):
            continue
        text = _readable_text(path)
        if text is None or "dataset_checksums" not in text:
            continue

        payloads = (
            [json.loads(line) for line in text.splitlines() if line.strip()]
            if path.suffix == ".jsonl"
            else [json.loads(text)]
        )
        for payload in payloads:
            for key in (
                (payload.get("dataset_checksums") or {}) if isinstance(payload, dict) else {}
            ):
                assert PUBLISHABLE_LABEL.match(key), f"{_relative(path)}: unpublishable key"
                assert not RECORD_NUMBER.search(key), (
                    f"{_relative(path)}: a corpus label carries a run of digits"
                )
