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
    "src/tnb/i18n.py": "the Czech translations of the two published pages",
    "src/tnb/templates/_helpers.html": "the language switch names its own languages",
    # The two generated pages carry Czech deliberately, and a blanket pass here
    # would be the wrong repair -- it is the surface a leak would actually be
    # read on. They are covered instead by the two stronger tests below, which
    # say more than "no Czech": that the payload has none, and that every Czech
    # string on the page is one somebody authored as a translation.
    "docs/index.html": "bilingual; held by the payload and translation tests",
    "docs/methods.html": "bilingual; held by the payload and translation tests",
}

#: What every file under ``tests/fixtures/czech`` must say about itself. The
#: allow-list above opens a door; this is what stops a real transcript walking
#: through it by being dropped into a directory whose path is permitted.
FIXTURE_MARKER = "SYNTHETIC-FIXTURE"

#: The published surface that may never carry Czech at all. `docs/index.html`
#: and `docs/methods.html` left this list when the pages became bilingual; what
#: replaced their guarantee is the pair of tests at the end of this file.
PUBLISHED = ("docs/leaderboard.json", "README.md")

#: The two generated pages, and where each one inlines the numbers as against
#: the words. A leak lands in the payload -- it would arrive as a measure, a
#: caveat, a blurb or a failure reason -- and never in the phrase book.
BILINGUAL_PAGES = ("docs/index.html", "docs/methods.html")
PAYLOAD_MARKER = "const DATA = "
DICTIONARY_MARKER = "const I18N = "

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
    """The half of a bilingual page that a leak would arrive in.

    Everything measured reaches the reader through `const DATA` -- measures,
    caveats, blurbs, track titles, failure reasons, every row. The phrase book
    beside it is authored prose and is Czech on purpose. Splitting them is what
    keeps a diacritic scan meaningful now that the page is bilingual; scanning
    the whole file stopped saying anything the day the Czech UI landed.
    """
    for name in BILINGUAL_PAGES:
        text = _readable_text(REPO_ROOT / name)
        if text is None:
            continue
        czech = [t for t in _strings(_inlined(text, PAYLOAD_MARKER)) if DIACRITIC.search(t)]
        assert not czech, f"{name}: {len(czech)} Czech strings in the data payload"


def test_every_czech_string_on_the_page_is_a_translation():
    """And the other half: the Czech that is there is Czech somebody wrote.

    Stronger than the rule it replaces. "No Czech on the page" only said a leak
    would look out of place; this says every Czech string is a value in
    `i18n.CS` or one of the two language names, so a sentence that is neither
    fails whatever it is.
    """
    from tnb import i18n

    vouched = {i18n.norm(value) for value in i18n.CS.values()}
    # Escaped for the same reason `DIACRITIC` is: this file asserts what may
    # carry Czech, so it may not carry any itself.
    vouched |= {"English", "\u010ce\u0161tina"}

    for name in BILINGUAL_PAGES:
        text = _readable_text(REPO_ROOT / name)
        if text is None:
            continue
        strays = [
            fragment
            for fragment in _strings(_inlined(text, DICTIONARY_MARKER))
            if DIACRITIC.search(fragment) and i18n.norm(fragment) not in vouched
        ]
        assert not strays, f"{name}: {len(strays)} Czech strings that are not translations"

        # And nothing Czech outside the phrase book either -- a translation that
        # reached the page any other way would not be in `i18n.CS` to check.
        start = text.index(DICTIONARY_MARKER)
        outside = text[:start] + text[text.index("\n", start) :]
        remaining = [
            line
            for line in outside.splitlines()
            if DIACRITIC.search(line) and "LANGUAGE_NAMES" not in line
        ]
        assert not remaining, f"{name}: Czech outside the phrase book ({len(remaining)} lines)"


# --- the fixtures ----------------------------------------------------------


def test_every_czech_fixture_says_it_is_invented(tracked_files):
    """Closes the hole the allow-list opens: a real transcript dropped into an
    allow-listed directory still fails, because it would not carry the marker."""
    fixtures = [p for p in tracked_files if "tests/fixtures/czech/" in _relative(p)]
    assert fixtures, "the Czech fixtures are missing"
    for path in fixtures:
        text = _readable_text(path) or ""
        assert FIXTURE_MARKER in text, f"{_relative(path)} carries no {FIXTURE_MARKER} marker"


# --- the corpus itself -----------------------------------------------------


def test_no_tracked_path_is_under_data(tracked_files):
    """`data/` is ignored, and this is what proves the rule still holds."""
    inside = [_relative(p) for p in tracked_files if _relative(p).startswith("data/")]
    assert not inside, f"corpus files are tracked: {inside}"


def test_no_fragment_of_the_real_corpus_appears_in_a_tracked_file(tracked_files):
    """The exact check, where the diacritic scan is only a net.

    Skipped where the corpus is absent -- on CI, and on any checkout that is not
    Jan's. That is a real limit and it is why the net above exists as well.
    """
    from tnb.datasets import czech

    if not czech.CORPUS_DIR.is_dir():
        pytest.skip("the Czech corpus is not present in this checkout")

    sessions = czech.load_real()
    haystacks = {
        _relative(path): text
        for path in tracked_files
        if (text := _readable_text(path)) is not None
    }

    for session in sessions:
        for turn in session.turns:
            words = turn.text.split()
            for start in range(0, max(1, len(words) - 5), 5):
                fragment = " ".join(words[start : start + 6])
                if len(fragment) < 30:
                    continue
                for name, text in haystacks.items():
                    # The message names the file and the digest id, never the
                    # fragment: a test report is written to a terminal and to CI.
                    assert fragment not in text, (
                        f"{name} contains a passage from session {session.id}"
                    )


def test_no_transcript_filename_reaches_a_tracked_file(tracked_files):
    """The files are named after clinical record numbers. The loader derives
    session ids from content precisely so a number cannot travel, and this is
    what holds that to being true."""
    from tnb.datasets import czech

    if not czech.IDS_PATH.exists():
        pytest.skip("the Czech corpus has not been loaded in this checkout")

    names = json.loads(czech.IDS_PATH.read_text(encoding="utf-8"))
    filenames = {name for mapping in names.values() for name in mapping.values()}

    # The whole filename, not its stem. A six-digit stem occurs by chance inside
    # the hex digests in uv.lock, and a check that cries wolf there is a check
    # somebody switches off.
    for path in tracked_files:
        text = _readable_text(path)
        if text is None:
            continue
        for filename in filenames:
            assert filename not in text, f"{_relative(path)} carries a transcript filename"


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
