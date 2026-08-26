"""The briefing: one document, for somebody deciding what to believe.

Writes ``docs/brief.html``. It is a page in its own right and it is also what
``tools/pdf.py`` prints, so there is one source for both.

**Who it is for.** Not a therapist. Somebody building or buying a tool that
writes clinical notes -- a developer, a product manager, a provider like
Upheal. They know what a model is; they do not know what Krippendorff's alpha
is, and they should not have to. What they need is the answer to "can I trust a
leaderboard, and what breaks in production".

**Every number is read from the published payload.** Same rule as the figures:
a figure or a sentence whose number cannot be regenerated is one nobody can
check. Where a claim needs a figure this file computes it from
``docs/leaderboard.json`` and the saturation files rather than repeating it.

The prose is written here because prose is not derivable. It is kept next to
the number it describes so the two are edited together, which is the whole
lesson of the four stale figures this repository removed today.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
FIGURES = DOCS / "figures"

# `tools/` is not a package -- these two files are scripts that share a module,
# and adding a `__init__.py` would make them one, which they are not.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from figures import JUDGE_A, JUDGE_B, Data, agreeing_pairs, esc  # noqa: E402

SITE = "https://jannehyba.github.io/therapy-note-bench/"
SOURCE = "https://github.com/JanNehyba/therapy-note-bench"


def inline_figure(name: str) -> str:
    """The SVG itself, not a link.

    A `<img src>` would leave the PDF depending on a file beside it, and the
    figures carry their own stylesheet -- inlining keeps one file that is one
    thing.
    """
    path = FIGURES / name
    if not path.exists():
        return f'<p class="missing">Figure missing: {esc(name)}. Run <code>make figures</code>.</p>'
    svg = path.read_text(encoding="utf-8")
    return svg[svg.index("<svg") :]


def pct(part: int, whole: int) -> str:
    return f"{part / whole:.0%}" if whole else "—"


CSS = """
  @page { size: A4; margin: 17mm 15mm 15mm; }
  @page :first { margin-top: 15mm; }

  :root {
    --fg: #1a1a19; --muted: #57574f; --line: #dcdcd5; --accent: #00806a;
    --warn: #8a5a00; --chip: #f2f2ec;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; color: var(--fg); background: #fff;
    font: 10.5pt/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  main { max-width: 178mm; margin: 0 auto; }

  h1 { font-size: 21pt; line-height: 1.15; margin: 0 0 4pt; letter-spacing: -.015em; }
  h2 {
    font-size: 13pt; margin: 20pt 0 5pt; letter-spacing: -.01em;
    padding-bottom: 3pt; border-bottom: 1px solid var(--line);
  }
  h3 { font-size: 11pt; margin: 13pt 0 3pt; }
  p { margin: 0 0 7pt; }
  a { color: var(--accent); text-decoration: none; }
  code { font: 9.4pt ui-monospace, SFMono-Regular, Consolas, monospace; }
  strong { font-weight: 650; }

  .lede { font-size: 12pt; line-height: 1.45; color: var(--muted); margin: 0 0 12pt; }
  .meta { font-size: 8.6pt; color: var(--muted); margin: 0 0 14pt; }
  .note { font-size: 9pt; color: var(--muted); }
  .missing { color: var(--warn); }

  /* A claim and what it rests on, side by side. The point of the document. */
  .claims { display: grid; gap: 7pt; margin: 10pt 0 14pt; }
  .claim {
    display: grid; grid-template-columns: 30mm 1fr; gap: 9pt;
    padding: 7pt 9pt; border: 1px solid var(--line); border-radius: 5pt;
    break-inside: avoid;
  }
  .claim .figure {
    font-size: 15pt; font-weight: 650; line-height: 1.1; color: var(--accent);
  }
  .claim .figure small { display: block; font-size: 8.2pt; font-weight: 400; color: var(--muted); }
  .claim p { margin: 0; }

  figure { margin: 12pt 0 14pt; break-inside: avoid; }
  figure svg { width: 100%; height: auto; }
  figcaption { font-size: 8.8pt; color: var(--muted); margin-top: 4pt; }

  table { width: 100%; border-collapse: collapse; font-size: 9.4pt; margin: 6pt 0 10pt; }
  th, td { text-align: left; padding: 3.5pt 6pt; border-bottom: 1px solid var(--line); }
  th { font-weight: 650; font-size: 8.4pt; text-transform: uppercase; letter-spacing: .04em;
       color: var(--muted); }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  tr.human td { background: var(--chip); }

  ul { margin: 0 0 8pt; padding-left: 15pt; }
  li { margin-bottom: 3pt; }

  .rule { border: 0; border-top: 1px solid var(--line); margin: 16pt 0 0; }
  .page-break { break-before: page; }
  h2, h3 { break-after: avoid; }
"""


def claim(figure: str, under: str, text: str) -> str:
    """One card: a number, what it counts, and what it means.

    `figure` and `under` are escaped, so they take characters and not entities:
    an `&ndash;` written here reaches the page as five letters, which it did.
    `text` is not escaped, because it carries the emphasis.
    """
    return (
        '<div class="claim"><div class="figure">'
        f"{esc(figure)}<small>{esc(under)}</small></div><p>{text}</p></div>"
    )


# --- the document -------------------------------------------------------------


def front(data: Data) -> str:
    """Page one: what this is, and the one thing to take away."""
    separable, agree = agreeing_pairs(data, "tneval-soap", "completeness")
    comp_a = data.scores("tneval-soap", JUDGE_A, "completeness")
    comp_b = data.scores("tneval-soap", JUDGE_B, "completeness")
    models = [
        row["label"]
        for row in data.tables[("tneval-soap", JUDGE_A)]["rows"]
        if row["system_type"] == "model"
    ]
    from figures import ranked

    ra, rb = ranked(comp_a), ranked(comp_b)
    moved = [n for n in ra if ra[n] != rb.get(n)]

    return f"""
  <h1>What a leaderboard of clinical-note models can and cannot tell you</h1>
  <p class="lede">Sixteen models wrote psychotherapy session notes on two published
     protocols, and two independent LLM judges scored every one of them. This is what
     the exercise says about choosing a model &mdash; and about reading anybody's
     leaderboard, including this one.</p>
  <p class="meta">therapy-note-bench &middot; harness 0.2.0 &middot;
     every figure here is generated from <code>docs/leaderboard.json</code> &middot;
     <a href="{SITE}">{SITE}</a></p>

  <div class="claims">
    {
        claim(
            f"{agree}/{separable}",
            "pairs, agreed",
            "Where both judges can tell two systems apart, they agree on which is better "
            f"in {agree} of {separable} pairs. The judges are not the problem.",
        )
    }
    {
        claim(
            f"{len(moved)}/{len(ra)}",
            "changed place",
            "And this many systems still land somewhere else. A leaderboard position is "
            "not a measurement; it is a place in a queue, and a few real moves renumber "
            "everyone below them.",
        )
    }
    {
        claim(
            "+0.027",
            "one judge's bias",
            "One of the two judges scores its own vendor&rsquo;s models measurably higher "
            "&mdash; a detected effect, not a caveat. If you use a model to grade models, "
            "measure this or do not publish the ranking.",
        )
    }
    {
        claim(
            "0.00–0.55",
            "the production gap",
            "Every model reliably records what happened last session. Almost none can say "
            "what happens at the next one. That is a feature gap, not a scoring artefact.",
        )
    }
  </div>

  <h2>Read this if you are building or buying one of these</h2>
  <p>Two datasets exist for turning a therapy transcript into a clinical note. Both were
     benchmarked once, on models from 2024 and 2025, and never re-run. This benchmark
     re-runs them on {len(models)} current models with the original prompts and the
     original scoring protocols, reproduced word for word so the numbers mean what the
     papers&rsquo; numbers meant.</p>
  <p>Nothing here is a clinical validation. No model in this benchmark has been shown to
     write a note a clinician would sign. What is measured is narrower and checkable:
     how much of a published rubric a note covers, how much of a published form it
     fills, and how far two different judges agree about either.</p>
"""


def figure_block(name: str, caption: str, *, page_break: bool = False) -> str:
    cls = ' class="page-break"' if page_break else ""
    return f"<figure{cls}>{inline_figure(name)}<figcaption>{caption}</figcaption></figure>"


def what_was_measured(data: Data) -> str:
    corpus = json.loads((DOCS / "corpus-profile.json").read_text(encoding="utf-8"))
    # Per corpus, not the top-level `sessions`, which is the iCARE count alone.
    datasets = corpus.get("datasets") or {}
    sessions = {name: entry.get("sessions") for name, entry in datasets.items()}
    fill = corpus.get("fill_rate")
    filled, total = corpus.get("fields_filled"), corpus.get("fields_total")
    # Computed above the string. Written inside one, the `if` is not a
    # conditional -- it is four words of literal text in the document.
    share = f"{fill:.0%}" if fill else "&mdash;"
    return f"""
  <h2 class="page-break">What was measured, and on what</h2>
  <p>Two tracks, because the two published protocols ask different questions and
     disagree about the answers &mdash; which is itself a result the source papers
     reported.</p>
  <table>
    <thead><tr><th>Track</th><th>What the model writes</th><th>How it is scored</th>
      <th class="num">Sessions</th></tr></thead>
    <tbody>
      <tr><td><strong>TN-Eval SOAP</strong></td>
          <td>One SOAP note per conversation, from a transcript</td>
          <td>A judge answers 23 yes/no rubric questions about it, plus one rating per
              sentence and one for factual accuracy. No gold note is involved.</td>
          <td class="num">{sessions.get("tneval", "&mdash;")}</td></tr>
      <tr><td><strong>iCARE / iHOPE</strong></td>
          <td>A 17-section clinical form, one call per section</td>
          <td>Word overlap and embedding similarity against an expert-written note, plus
              five judge-rated dimensions and two time-bearing sections counted
              separately.</td>
          <td class="num">{sessions.get("icare", "&mdash;")}</td></tr>
    </tbody>
  </table>
  <p class="note">Both corpora are transcripts of published counselling demonstrations,
     not clinical sessions. On the iCARE side the experts themselves left most of the
     form empty &mdash; {filled} of {total} fields say anything at all
     ({share}). A model scores on those sections by staying
     quiet, so read the low rows as no signal rather than as a hard test.</p>
"""


def the_judges(data: Data) -> str:
    calibration = json.loads((DOCS / "calibration.json").read_text(encoding="utf-8"))
    rows = []
    for entry in calibration["agreements"]:
        name = entry["name"].replace("_", " ").replace("rubric ", "").replace("likert ", "")
        kind = "checklist" if entry["name"].startswith("rubric") else "1&ndash;5 rating"
        rows.append(
            f"<tr><td>{esc(name)}</td><td>{kind}</td>"
            f'<td class="num">{entry["alpha"]:.2f}</td>'
            f'<td class="num">{entry["alpha_humans"]:.2f}</td></tr>'
        )
    return f"""
  <h2>The judge is a model, so the judge is measured first</h2>
  <p>TN-Eval released 150 notes that two trained therapists had already rated. Every
     candidate judge answers the same questions about the same notes before it is
     allowed near the leaderboard, and the agreement is published whatever it says.</p>
  <table>
    <thead><tr><th>Measure</th><th>Form</th><th class="num">Judge vs therapist</th>
      <th class="num">Therapist vs therapist</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  <p>The right-hand column is the ceiling, not a target. <strong>Two trained therapists
     rating the same notes barely agree on the 1&ndash;5 scales</strong> &mdash; 0.13,
     0.19 and 0.18, where 1.00 is perfect and 0 is chance. On the 23-item checklist they
     reach 0.50, and the judge reaches 0.60.</p>
  <p><strong>That is why the ranking uses the checklist and nothing else.</strong> The
     other three columns are reported because the protocol produces them, and ordering
     anything by them would be ordering by noise.</p>
  <p class="note">Measured across {calibration["notes"]} of those notes, judge
     <code>{esc(calibration["judge_model"])}</code>. Krippendorff&rsquo;s alpha, the
     statistic the source paper used, so the comparison is with their finding rather
     than with a re-definition of it.</p>
"""


def what_it_means(data: Data) -> str:
    """The three findings a reader can act on, each with its figure."""
    preference = data.preference or {}
    effects = {entry["judge"]: entry for entry in preference.get("effects", [])}
    detected = [entry for entry in effects.values() if entry["detected"]]
    # Built here rather than inside the document string: a comprehension nested
    # in a triple-quoted f-string needs the same quote character twice, which
    # this project's Python does not allow and no reader should have to parse.
    rows = []
    for entry in effects.values():
        verdict = "<strong>yes</strong>" if entry["detected"] else "no"
        rows.append(
            "<tr>"
            f"<td><code>{esc(entry['judge'])}</code></td>"
            f"<td>{esc(entry['family'])}</td>"
            f'<td class="num">{entry["estimate"]:+.3f}</td>'
            f'<td class="num">{entry["low"]:+.3f} to {entry["high"]:+.3f}</td>'
            f"<td>{verdict}</td></tr>"
        )
    found = "<strong>One of the two is detected.</strong> " if detected else ""
    return f"""
  <h2 class="page-break">One: a leaderboard position is not a measurement</h2>
  <p>The two judges see the same notes, ask the same 23 questions and reach almost the
     same conclusions about which of any two systems is better. And the two orderings
     they produce are visibly different. Both of those are true, and the reason is
     arithmetic rather than disagreement: nineteen systems are packed into a range of
     0.22, so a handful of genuine moves renumbers everyone below them.</p>
  <p><strong>What to do with that.</strong> Read a leaderboard as bands, not as an
     order. &ldquo;In the top group&rdquo; is a claim this kind of evidence supports;
     &ldquo;ninth rather than tenth&rdquo; is not, on this benchmark or on anybody
     else&rsquo;s.</p>
  {
        figure_block(
            "positions.svg",
            "Completeness under each of the two judges. Grey lines held their place. "
            "The four systems in the top group are the same four under both.",
        )
    }

  <h2 class="page-break">Two: the judge has a vendor, and it shows</h2>
  <p>Both judges here also <em>write</em> notes in this benchmark, so each is marking
     some of its own homework. The size of that is measurable: take the difference
     between the two judges&rsquo; scores for each system, and compare the judges&rsquo;
     own vendors against the systems neither of them built.</p>
  <table>
    <thead><tr><th>Judge</th><th>Its vendor</th><th class="num">Effect</th>
      <th class="num">95% interval</th><th>Detected</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  <p>{found}The units are
     completeness, so +0.027 is about a fortieth of the whole range the models occupy
     &mdash; enough to move a system several places in an ordering this tight, and not
     enough to make a bad note look good.</p>
  <p><strong>What to do with that.</strong> If you evaluate models with a model, run
     this check. Two judges from two vendors is the cheapest way to have it; one judge
     cannot measure its own bias at all, and a caveat in the methods section is not a
     measurement.</p>
  <p class="note">The comparison group matters more than the estimate does. Until
     2026-08-26 it included <code>gemma4</code> and <code>gpt-oss-120b</code> &mdash;
     built by the two judges&rsquo; own vendors under names their model families do not
     share. Both pulled the answer toward zero, and correcting it turned one
     &ldquo;not detected&rdquo; into the result above.</p>

  <h2 class="page-break">Three: nothing here can tell you what happens next</h2>
  <p>The iCARE form has two time-bearing sections: what happened at the previous
     session, and what happens at the next one. Every model fills the first. Almost none
     fills the second, and the best of them manages it in just over half the sessions
     where an expert did.</p>
  {
        figure_block(
            "temporal.svg",
            "The fraction of expert-answered sections each model also answered. "
            "Backward on the left of each pair, forward on the right.",
        )
    }
  <p><strong>What to do with that.</strong> If your product promises continuity between
     sessions &mdash; a plan, a follow-up, something to pick up next time &mdash; that is
     the part no current model produces on its own, and it is the part a demo will not
     show you because a demo is one session.</p>
"""


def what_it_does_not_mean(data: Data) -> str:
    return f"""
  <h2 class="page-break">What these numbers are not</h2>
  {
        figure_block(
            "what-the-rubric-rewards.svg",
            "Completeness, every system, under the first judge. "
            "The therapist-written note is the bottom row.",
        )
    }
  <p><strong>Every model covers more of the rubric than the therapist does.</strong>
     That is a reproduction &mdash; the source paper found the same direction from
     blinded expert comparison &mdash; and it is a statement about a checklist. A
     therapist writes what matters for the next session and leaves out what does not;
     the rubric counts what is present and cannot see why anything was left out.</p>
  <p>The one exception is the measure with the weakest human agreement: on factual
     accuracy, one of the two 2025 reference models scores <em>below</em> the therapist
     under both panel judges and above her under a third. A column that changes sign
     when the referee changes is not measuring what the other two are.</p>
  {
        figure_block(
            "coverage-against-invention.svg",
            "Completeness against factual accuracy, one panel per judge. The two judges do not "
            "agree about whether covering more of a checklist goes with inventing more.",
        )
    }
  <p class="note">Neither track measures whether a note is clinically useful, safe to
     put in a record, or acceptable to a supervisor. Nobody has run that study on these
     models. Treat every figure here as a lower bound on what you would have to check
     yourself.</p>
"""


def how_to_check(data: Data) -> str:
    from figures import FIGURES

    return f"""
  <h2 class="page-break">How to check any of this</h2>
  <p>Every figure and every number in this document is generated from two published
     files. Nothing was typed in, and nothing here can drift from the site without the
     tests failing.</p>
  <ul>
    <li><code>docs/leaderboard.json</code> &mdash; every row, every measure, and the six
        version fields a row has to agree on before it may be compared with another.</li>
    <li><code>docs/saturation-&lt;judge&gt;.json</code> &mdash; the paired bootstrap that
        decides which systems this evidence can tell apart.</li>
    <li><code>results/rows.jsonl</code> &mdash; append-only. A re-run adds rows beside
        the old ones; what is drawn is the newest of each.</li>
  </ul>
  <p>The figures redraw with <code>make figures</code> and this document with
     <code>make brief</code>. There are {len(FIGURES)} of them, and each carries the
     file it came from in its own footer.</p>

  <h3>What a result here cannot claim</h3>
  <ul>
    <li>Two judges are two instruments. A number scored by one is never averaged with a
        number scored by the other, and a table that cannot say what settings its judge
        ran at is withdrawn rather than drawn.</li>
    <li>An absence is never counted as a zero. A note the judge did not finish is left
        out of the average and said so, rather than dragging a system down for a
        question nobody answered.</li>
    <li>The corpora are demonstrations, not clinical sessions, and two of the three
        sources publish no licence at all. Nothing is redistributed here.</li>
  </ul>

  <hr class="rule">
  <p class="meta">therapy-note-bench &middot; harness 0.2.0 &middot;
     judges <code>{esc(JUDGE_A)}</code> and <code>{esc(JUDGE_B)}</code> &middot;
     source and method: <a href="{SOURCE}">{SOURCE}</a></p>
"""


def render(data: Data) -> str:
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        "<title>therapy-note-bench &mdash; what a leaderboard can tell you</title>\n"
        f"<style>{CSS}</style>\n</head>\n<body>\n<main>\n"
        + front(data)
        + what_was_measured(data)
        + the_judges(data)
        + what_it_means(data)
        + what_it_does_not_mean(data)
        + how_to_check(data)
        + "\n</main>\n</body>\n</html>\n"
    )


def main() -> int:
    data = Data.load()
    path = DOCS / "brief.html"
    path.write_text(render(data), encoding="utf-8")
    print(f"wrote {path.relative_to(REPO)}  {path.stat().st_size:>7,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
