"""Do the rows, the tables page, both briefs and both PDFs say the same numbers?

Six passes, each comparing two representations of the same measurement:

1. rows -> tables payload   every drawn cell equals the row it came from
2. payload -> tables page   the page carries the payload it was built from
3. rows -> brief tables     every headline value in the brief exists in a row
4. brief counts             the notes-scored figures match the rows
5. English brief -> Czech   the two languages print the same figures
6. brief -> PDF             every number survives printing, both languages

Read-only. Nothing here writes to the repository.
"""

from __future__ import annotations

import html as htmllib
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

from tnb import results
from tnb.config import REPO_ROOT as REPO

LOCAL = REPO / "local"
problems: list[str] = []


def note(passing: bool, message: str) -> None:
    print(("  ok   " if passing else "  FAIL ") + message)
    if not passing:
        problems.append(message)


#: The spaces Czech groups thousands with. Removed from every side before
#: anything is compared, so a figure that is one token in English is not two
#: in Czech.
GROUPING_SPACE = re.compile(r"[\u00a0\u202f\u2009]")


def text_of(page: pathlib.Path) -> str:
    """The page as a reader sees it: no markup, no style, no chart, no thin spaces.

    The thin space matters. Czech groups thousands with U+202F, so a figure
    that is one token in English is two in Czech and a naive comparison reports
    a difference where the two pages agree.

    A chart's numbers are dropped along with its markup, for a reason that is
    about the printer rather than about the chart. `pdftotext` rebuilds text
    runs from where the glyphs landed on the page, so an axis tick that sits
    beside a data label comes back as one token -- "0.6" next to "0.62" prints
    as "0.6 0.62" on the page and can arrive as "0.60.62" from the PDF. Pass 6
    would then report a figure lost and a figure invented, and both would be
    artefacts of the layout. The numbers inside a figure are checked instead by
    `tests/test_czech_figures.py`, against the payload they were drawn from,
    which is the stronger check anyway: it compares them with the record rather
    than with themselves.
    """
    raw = page.read_text(encoding="utf-8")
    raw = re.sub(r"(?s)<style.*?</style>", " ", raw)
    raw = re.sub(r"(?s)<script.*?</script>", " ", raw)
    raw = re.sub(r"(?s)<svg.*?</svg>", " ", raw)
    flat = htmllib.unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"\s+", " ", GROUPING_SPACE.sub("", flat))


def chart_text(page: pathlib.Path) -> str:
    """Only what the charts print, which is what `text_of` throws away.

    Pass 6 reads the print and cannot tell a chart's text from the prose around
    it, so the two sides would disagree about every figure in every chart if
    only the page were stripped. This is the other half of the same cut: what
    it returns is subtracted from the print before the print is asked to
    account for itself.
    """
    raw = page.read_text(encoding="utf-8")
    inside = " ".join(re.findall(r"(?s)<svg.*?</svg>", raw))
    inside = re.sub(r"(?s)<style.*?</style>", " ", inside)
    flat = htmllib.unescape(re.sub(r"<[^>]+>", " ", inside))
    return re.sub(r"\s+", " ", GROUPING_SPACE.sub("", flat))


NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def runs_on(token: str, parts: Counter) -> bool:
    """Is this token two or more of `parts` printed hard against each other?

    The merge the charts are cut out for, arriving from the other side. A print
    can only be asked what it holds, not where a glyph came from, so a chart's
    "0.6" and "0.62" reach `pdftotext` as "0.60.62" and look like a figure the
    print invented. Forgiven only where the token comes apart exactly into
    figures a chart drew: a number that is genuinely new still fails, because
    it will not decompose.
    """
    if token in parts:
        return True
    return any(
        part
        and len(part) < len(token)
        and token.startswith(part)
        # `parts` holds a handful of short tokens and `token` is shorter still,
        # so the recursion is bounded by the length of the token.
        and runs_on(token[len(part) :], parts)
        for part in parts
    )


def figures(text: str, *, grouped: bool = True) -> Counter:
    """Only numbers a reader would read as a measurement.

    Bare one- and two-digit integers are excluded: they are counts, years,
    version fragments and list positions, and they differ legitimately between
    two languages ("in 5 short paragraphs" against "ve 5 odstavcich" agree,
    while "three" against "3" do not and neither is wrong). What is compared is
    every decimal figure -- which is every score, share and interval on the
    page.
    """
    # English groups thousands with a comma and Czech with a space that
    # `text_of` has already removed, so 5,266 and 5266 are the same figure
    # written by two conventions. Canonicalise before comparing, or every
    # four-digit number in the document reads as a difference between the
    # languages -- which is how this checker first reported one.
    # Commas only. A plain space between digits is a thousands separator in
    # Czech AND the gap between two table cells, and a PDF lays those out
    # differently from the page it was printed from -- joining on space made
    # "340 278 938" one number in the print and three on the page. `text_of`
    # has already removed the non-breaking space the document actually uses.
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    out = Counter()
    for match in NUMBER.finditer(text):
        token = match.group(0)
        # Decimals are measurements. Bare integers are counts, years and list
        # positions and differ legitimately between two languages -- except the
        # large ones, which are the corpus figures and must agree.
        if "." not in token and "," not in token and (len(token) < 4 or not grouped):
            continue
        # A version inside an identifier is not a figure: `gemini-3.1-pro` holds
        # "3.1", and a print that hyphenates the name differently from the page
        # reports a difference where none exists.
        before = text[match.start() - 1] if match.start() else " "
        after = text[match.end()] if match.end() < len(text) else " "
        if before.isalpha() or before == "-" or after.isalpha() or after == "-":
            continue
        out[token.replace(",", ".")] += 1
    return out


# --- 1. rows -> tables payload ---------------------------------------------
print("\n1. rows -> tables payload")
payload = json.loads((LOCAL / "czech.json").read_text(encoding="utf-8"))
rows, _refused = results.drawable(results.load(results.LOCAL_ROWS_PATH))
by_key = {
    (row.track, row.judge_model, row.judge_prompt_version, row.system_id): row
    for row in results.latest(rows)
}

checked = mismatched = unmatched = 0
for table in payload["tables"]:
    versions = table.get("versions") or {}
    for drawn in table["rows"]:
        row = by_key.get(
            (
                table["track"],
                versions.get("judge_model"),
                versions.get("judge_prompt_version"),
                drawn["system_id"],
            )
        )
        if row is None:
            unmatched += 1
            continue
        for key, value in (drawn.get("headline") or {}).items():
            if value is None:
                continue
            was = row.metrics.headline.get(key)
            checked += 1
            if was is None or abs(float(was) - float(value)) > 5e-4:
                mismatched += 1
                print(f"    {table['track']} {drawn['system_id']} {key}: row {was} page {value}")
        for name, field in (
            ("n_scored", "n_sessions_scored"),
            ("n_generated", "n_sessions_generated"),
        ):
            if drawn.get(name) is None:
                continue
            checked += 1
            if drawn[name] != getattr(row, field):
                mismatched += 1
                print(
                    f"    {table['track']} {drawn['system_id']} {name}: "
                    f"row {getattr(row, field)} page {drawn[name]}"
                )
note(unmatched == 0, f"every drawn row is traceable to a record row ({unmatched} are not)")
note(mismatched == 0, f"{checked} drawn values equal their rows ({mismatched} differ)")
note(checked > 500, f"the comparison actually ran ({checked} values)")


# --- 2. payload -> tables page ----------------------------------------------
print("\n2. payload -> tables page")
page = (LOCAL / "czech.html").read_text(encoding="utf-8")
match = re.search(r"const DATA\s*=\s*(\{.*?\});\n", page, re.S)
note(match is not None, "the page carries a DATA block")
if match:
    embedded = json.loads(match.group(1))
    same = json.dumps(embedded, sort_keys=True) == json.dumps(payload, sort_keys=True)
    note(same, "the embedded payload is identical to czech.json")


# --- 3. rows -> brief tables ------------------------------------------------
print("\n3. the brief's figures exist in the record")
known = {f"{value:.2f}" for row in results.latest(rows) for value in row.metrics.headline.values()}
known |= {f"{value:.1f}" for row in results.latest(rows) for value in row.metrics.headline.values()}
brief_cells = []
for body in re.findall(
    r"<tbody>(.*?)</tbody>", (LOCAL / "czech-brief.html").read_text(encoding="utf-8"), re.S
):
    for cell in re.findall(r"<td[^>]*>([^<]*)</td>", body):
        for part in re.findall(r"\d+\.\d+", cell):
            brief_cells.append(part)
strangers = sorted({c for c in brief_cells if c not in known})
# Informational, not a pass or a fail. The brief draws derived tables too --
# correlations, slopes, band widths, judge agreement -- and none of those is a
# value any row holds. Pass 1 is the one that proves the score tables.
print(
    f"  note {len(set(brief_cells)) - len(strangers)} of {len(set(brief_cells))} distinct "
    f"table figures are raw row values; the rest are derived"
)
note(len(brief_cells) > 200, f"the brief prints {len(brief_cells)} decimal table cells")


# --- 4. the counts under the tables -----------------------------------------
print("\n4. the notes-scored figures")
scored_by_track = {}
for row in results.latest(rows):
    if row.is_scored:
        scored_by_track.setdefault(row.track, set()).add(row.n_sessions_scored)
corpus = {"czech-real": 10, "czech-translated": 10, "deepsy-real": 10, "deepsy-translated": 10}
over = {
    track: sorted(v)
    for track, v in scored_by_track.items()
    if track in corpus and max(v) > corpus[track]
}
note(not over, f"no model is scored on more notes than the corpus holds ({over or '-'})")


# --- 5. the two languages print the same figures ----------------------------
print("\n5. English brief -> Czech brief")
en = figures(text_of(LOCAL / "czech-brief.html"))
cs = figures(text_of(LOCAL / "czech-brief-cs.html"))
only_en = dict((en - cs).most_common(12))
only_cs = dict((cs - en).most_common(12))
note(
    not only_en and not only_cs,
    f"the same figures in both languages (EN-only {only_en or '-'}, CS-only {only_cs or '-'})",
)
note(sum(en.values()) > 400, f"the comparison actually ran ({sum(en.values())} figures)")


# --- 6. brief -> PDF ---------------------------------------------------------
print("\n6. brief -> PDF")
for source, pdf in (
    ("czech-brief.html", "czech-report.pdf"),
    ("czech-brief-cs.html", "czech-report-cs.pdf"),
    # The short version is the copy more likely to be forwarded, so it is the
    # copy that most needs checking. It is built by `tools/czech_short.py` from
    # `czech_brief`'s own functions, which is why no figure in it can differ
    # from the long one -- and why a difference showing up here would mean that
    # stopped being true.
    ("czech-short.html", "czech-short.pdf"),
    ("czech-short-cs.html", "czech-short-cs.pdf"),
):
    if not (LOCAL / source).is_file() or not (LOCAL / pdf).is_file():
        note(True, f"{pdf}: not built, nothing to compare")
        continue
    out = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", str(LOCAL / pdf), "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if out.returncode != 0:
        note(False, f"{pdf}: pdftotext failed")
        continue
    # Decimals only. A grouped integer reaches the print as "5 266" whatever
    # the page wrote, and the space it arrives with cannot be told from the gap
    # between two table cells -- so those are checked below, by name.
    in_pdf = figures(re.sub(r"[\u00a0\u202f\u2009]", " ", out.stdout), grouped=False)
    in_html = figures(text_of(LOCAL / source), grouped=False)
    printed = re.sub(r"[\u00a0\u202f\u2009]", " ", out.stdout)
    missing_big = [
        big
        for big in figures(text_of(LOCAL / source))
        if "." not in big
        and len(big) > 3
        and big not in re.sub(r"(?<=\d)[ ,](?=\d{3}(?!\d))", "", printed)
    ]
    note(not missing_big, f"{pdf}: every grouped figure survives the print ({missing_big or '-'})")
    # What the charts drew, taken off the print's side of the ledger. `text_of`
    # has already taken it off the page's side; leaving it here would turn one
    # false alarm into the opposite one, with every value in every chart
    # reported as invented by the printer.
    charted = figures(chart_text(LOCAL / source), grouped=False)
    invented = Counter(
        {
            token: count
            for token, count in (in_pdf - in_html - charted).items()
            if not runs_on(token, charted)
        }
    )
    lost = dict((in_html - in_pdf).most_common(12))
    gained = dict(invented.most_common(12))
    note(not lost, f"{pdf}: nothing on the page is missing from the print ({lost or '-'})")
    note(not gained, f"{pdf}: the print invents nothing ({gained or '-'})")
    note(sum(in_pdf.values()) > 400, f"{pdf}: {sum(in_pdf.values())} figures compared")


print()
if problems:
    print(f"{len(problems)} problem(s):")
    for line in problems:
        print("  - " + line)
    sys.exit(1)
print("every representation agrees.")
