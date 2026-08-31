"""A string split across two lines must not lose the space between them.

Python joins adjacent string literals silently, so

    "Released to benefit research community, with a citation "
    "requested. Fetched"
    "at run time."

publishes `Fetchedat run time.` and nothing complains. Two of these were live
on the public licence table for weeks -- `neverredistributed` and `Fetchedat` --
and they were found by a reader, not by the suite. The failure is invisible in
the source, because the two halves look correct one above the other, and
invisible to `ruff`, which has no opinion about what a concatenation means.

The rule, and why it has the shape it has:

    Flag a join where the left part ends with a letter, the right part begins
    with a letter, and the left part contains a space.

The last clause is what keeps it quiet. Prose wrapped mid-word is always a
mistake; an identifier, a URL or a long token split across lines is not, and
those have no spaces in the part before the break. Checked against every
Python file in the repository: with the two known faults repaired it fires
nowhere, and re-introducing either one is caught.

`tokenize`, not `ast`: the parser folds implicit concatenation into one
constant, so by the time there is a tree the join is gone.

**F-strings are read too, and they were not.** From Python 3.12 an f-string is
no longer one `STRING` token -- it comes apart into `FSTRING_START`,
`FSTRING_MIDDLE` and `FSTRING_END` -- so the first version of this test reset
its state across every one of them and never examined a seam with an f-string
on either side. That was 439 of the 3 670 implicit concatenations in `src`,
`tests` and `tools`, concentrated in exactly the files that build published
text. A run of f-string tokens is now collapsed into one atom carrying the
first and last character of its *literal* text, with the edge treated as
unknown when a `{...}` sits there, so an interpolation at the seam simply does
not fire rather than firing wrongly.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
import warnings
from dataclasses import dataclass
from pathlib import Path

import pytest

from tnb.config import REPO_ROOT

#: Where a joined word is a published sentence rather than a variable name.
SEARCHED = ("src", "tests", "tools")

#: Fields whose contents are quoted from somewhere else, where a wrap inside a
#: word is correct and adding the space would corrupt the quotation.
#:
#: Keyed by `(constant, field)`, not by file and not by constant. Allow-listing
#: `report.py` would blind the licence table, which is where both of the faults
#: this test exists for actually shipped. Allow-listing `SIMILARITY_EXAMPLE`
#: blinded its `note` field, which is not a quotation at all: it is the ordinary
#: English caption rendered under the example on the methods page, so a
#: `Fetchedat`-shaped fault in it would have been published unseen.
QUOTED_VERBATIM = {
    ("SIMILARITY_EXAMPLE", "expert"): "an iHOPE note section, reproduced exactly",
    ("SIMILARITY_EXAMPLE", "generated"): (
        "one model's answer to it, reproduced exactly; the line breaks are ours "
        "and the words are theirs"
    ),
}


@dataclass(frozen=True)
class Atom:
    """One string-ish token, reduced to what the seam rule needs.

    `first` and `last` are None where an interpolation sits at that edge of an
    f-string: nothing literal is there, so no seam can be judged.
    """

    line: int
    first: str | None
    last: str | None
    has_space: bool
    text: str


def _owners(source: str) -> dict[int, tuple[str, str | None]]:
    """Which module-level constant -- and which of its fields -- owns each line.

    Module level only: `ast.walk` reached into every function body, so a *local*
    variable named `SIMILARITY_EXAMPLE` anywhere in `src`, `tests` or `tools`
    claimed the exemption. `AnnAssign` as well as `Assign`: writing the same
    constant as `SIMILARITY_EXAMPLE: dict[str, str] = {...}`, which is how a
    typed constant is normally written, silently dropped the exemption and
    produced failures telling the reader to insert spaces into a quotation.
    """
    lines: dict[int, tuple[str, str | None]] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
        else:
            continue
        if not names or node.value is None:
            continue

        for line in range(node.lineno, (node.end_lineno or node.lineno) + 1):
            lines[line] = (names[0], None)
        if isinstance(node.value, ast.Dict):
            for key, value in zip(node.value.keys, node.value.values, strict=True):
                field = key.value if isinstance(key, ast.Constant) else None
                if not isinstance(field, str):
                    continue
                for line in range(value.lineno, (value.end_lineno or value.lineno) + 1):
                    lines[line] = (names[0], field)
    return lines


#: The escape sequences that can appear inside an `FSTRING_MIDDLE` token, which
#: `tokenize` hands over raw. Without decoding them the last character of
#: `f"... judge questions.\n"` is the letter `n`, and eleven ordinary lines in
#: this repository were reported as glued words.
_ESCAPE = re.compile(
    r"\\(?:N\{[^}]*\}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{2}|[0-7]{1,3}|.)", re.S
)


def _unescape(text: str) -> str:
    r"""An `FSTRING_MIDDLE` as the characters it stands for.

    Decoded by `ast.literal_eval` on the escape itself, so what `\n` means is
    Python's answer rather than a copy of it kept here. Anything it cannot read
    falls back to the escape's own body, which is never a letter at a seam.
    """

    def one(match: re.Match) -> str:
        # A regex written inside an f-string carries `\s`, `\.`, `\|` and the
        # rest, which Python keeps verbatim and warns about. The value is right
        # either way; only the noise is silenced.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            try:
                return ast.literal_eval('"' + match.group(0) + '"')
            except (ValueError, SyntaxError):
                return match.group(0)[1:]

    return _ESCAPE.sub(one, text.replace("{{", "{").replace("}}", "}"))


def _plain(token: tokenize.TokenInfo) -> Atom | None:
    """A `STRING` token as an atom, or None if it is not a plain literal."""
    try:
        value = ast.literal_eval(token.string)
    except (ValueError, SyntaxError):
        return None
    if not isinstance(value, str) or not value:
        return None
    return Atom(token.start[0], value[0], value[-1], " " in value, value)


def _atoms_of(source: str) -> list[Atom | None]:
    """Every string-ish token in order, one atom each, anything else a None.

    A None breaks the run, which is what makes two atoms either side of it not
    a seam. An f-string arrives as a run of tokens and leaves as one atom: its
    tail is literal only if the token before `FSTRING_END` was a
    `FSTRING_MIDDLE`, which is not known until that token has been seen, so
    this is a list rather than a generator.
    """
    out: list[Atom | None] = []
    depth, parts, start_line = 0, [], 0
    opened_literal = ended_literal = False
    previous_type = None
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.FSTRING_START:
            if depth == 0:
                parts, start_line = [], token.start[0]
                opened_literal = ended_literal = False
            depth += 1
            previous_type = token.type
            continue
        if depth:
            if token.type == tokenize.FSTRING_MIDDLE:
                if not parts:
                    opened_literal = True
                parts.append(_unescape(token.string))
            elif token.type == tokenize.FSTRING_END:
                depth -= 1
                if depth == 0:
                    ended_literal = previous_type == tokenize.FSTRING_MIDDLE
                    text = "".join(parts)
                    out.append(
                        Atom(
                            start_line,
                            text[0] if (opened_literal and text) else None,
                            text[-1] if (ended_literal and text) else None,
                            " " in text,
                            text,
                        )
                    )
            previous_type = token.type
            continue
        previous_type = token.type
        if token.type in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT):
            continue
        out.append(_plain(token) if token.type == tokenize.STRING else None)
    return out


def joins_without_a_space(source: str) -> list[tuple[int, str, str]]:
    """Every implicit concatenation that glues two words together."""
    try:
        owner = _owners(source)
    except SyntaxError:
        owner = {}

    found = []
    previous: Atom | None = None
    for atom in _atoms_of(source):
        if atom is None:
            previous = None
            continue
        if (
            previous is not None
            and previous.last
            and atom.first
            and previous.last.isalpha()
            and atom.first.isalpha()
            and previous.has_space
            and owner.get(atom.line) not in QUOTED_VERBATIM
        ):
            found.append((atom.line, previous.text[-24:], atom.text[:24]))
        previous = atom
    return found


def _files() -> list[Path]:
    return [
        path
        for directory in SEARCHED
        for path in sorted((REPO_ROOT / directory).rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def test_no_published_string_glues_two_words_together():
    """The two that shipped were `never` + `redistributed` and `Fetched` + `at`."""
    faults = []
    for path in _files():
        try:
            source = path.read_text(encoding="utf-8")
            found = joins_without_a_space(source)
        except SyntaxError:
            continue  # a file caught half-written; ruff and the imports say so
        for line, left, right in found:
            faults.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{line} ...{left}|{right}...")
    assert not faults, "a string was joined without its space:\n  " + "\n  ".join(faults)


def test_the_check_would_catch_the_two_that_shipped():
    """Pinned with the real text, so a rule relaxed into uselessness is caught.

    Without this, a future edit could narrow the rule until it fires on nothing
    and the test above would still be green.
    """
    shipped = (
        'x = ("The Apache licence is on the code repository, not this one. Fetched at run "\n'
        '     "time, never"\n'
        '     "redistributed.")\n'
    )
    assert joins_without_a_space(shipped), "the `neverredistributed` fault is no longer caught"

    also = "\n".join(
        (
            'y = ("Released to benefit research community, with a citation "',
            '     "requested. Fetched"',
            '     "at run time.")',
            "",
        )
    )
    assert joins_without_a_space(also), "the `Fetchedat` fault is no longer caught"


@pytest.mark.parametrize(
    "source",
    (
        # An f-string on the left of the seam.
        'x = (f"scored {n} sessions and Fetched"\n"at run time")\n',
        # An f-string on the right.
        'x = ("scored the sessions and Fetched"\nf"at run time in {n} steps")\n',
        # Both sides.
        'x = (f"scored {n} sessions and Fetched"\nf"at {when} run time")\n',
    ),
)
def test_a_seam_with_an_fstring_is_read(source):
    """439 of the repository's concatenations have one, and none was examined."""
    assert joins_without_a_space(source), "an f-string at the seam is invisible again"


@pytest.mark.parametrize(
    "source",
    (
        # A space on either side of the break is the normal case.
        'x = ("a sentence that wraps "\n"onto the next line")\n',
        'x = ("a sentence that wraps"\n" onto the next line")\n',
        # A long token with no space before the break: a URL, an id, a digest.
        'x = ("https://example.invalid/some/very/long/"\n"path/that/continues")\n',
        # Punctuation at the seam is not two words.
        'x = ("ends with a full stop."\n"Starts a new one")\n',
        # An interpolation at the seam: nothing literal is there to judge.
        'x = ("a sentence that ends in {n} "\nf"{n}"\n"words")\n',
        'x = (f"a sentence ending in an expression {n}"\n"words")\n',
    ),
)
def test_legitimate_wraps_are_not_flagged(source):
    """A rule that fires on ordinary wrapping would be turned off within a week."""
    assert not joins_without_a_space(source)


def test_the_exemption_is_a_field_and_not_a_whole_constant():
    """`SIMILARITY_EXAMPLE`'s caption is ordinary prose and must stay under the rule.

    `report.py` puts `**SIMILARITY_EXAMPLE` into the payload and the methods
    page renders `example.note` as the sentence under the worked example, so a
    glued word there is published. Exempting the constant exempted the caption.
    """
    source = "\n".join(
        (
            "SIMILARITY_EXAMPLE = {",
            '    "expert": ("a quotation that wraps mid-wo"',
            '               "rd on purpose"),',
            '    "note": ("an ordinary caption that lost its spa"',
            '             "ce at the seam"),',
            "}",
            "",
        )
    )
    found = joins_without_a_space(source)
    lines = {line for line, _, _ in found}
    assert 5 in lines, "the caption is exempted; it is prose and must not be"
    assert 3 not in lines, "the quotation is not exempted; it must be"


def test_a_local_of_that_name_buys_no_exemption():
    """`_owners` walked every scope, so any function could claim the allow-list."""
    source = "\n".join(
        (
            "def render():",
            "    SIMILARITY_EXAMPLE = {",
            '        "generated": ("prose that lost its spa"',
            '                      "ce at the seam"),',
            "    }",
            "    return SIMILARITY_EXAMPLE",
            "",
        )
    )
    assert joins_without_a_space(source), "a local variable claimed the exemption"


def test_an_annotated_constant_keeps_its_exemption():
    """`X: dict = {...}` is an `AnnAssign`, which `_owners` did not look at."""
    source = "\n".join(
        (
            "SIMILARITY_EXAMPLE: dict[str, str] = {",
            '    "generated": ("a quotation that wraps mid-wo"',
            '                  "rd on purpose"),',
            "}",
            "",
        )
    )
    assert not joins_without_a_space(source), (
        "annotating the constant lost the exemption, which would demand a space "
        "be inserted into a verbatim quotation"
    )
