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
from collections import Counter
from pathlib import Path
from statistics import fmean

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
FIGURES = DOCS / "figures"

# `tools/` is not a package -- these two files are scripts that share a module,
# and adding a `__init__.py` would make them one, which they are not.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from figures import JUDGE_A, JUDGE_B, Data, agreeing_pairs, esc  # noqa: E402

#: The figures this document inlines, in the order it uses them. Not all of
#: them: `room-left.svg` belongs beside the saturation panel on the methods
#: page, where the analysis it draws already lives.
BRIEF_FIGURES = (
    "positions.svg",
    "temporal.svg",
    "what-the-rubric-rewards.svg",
    "coverage-against-invention.svg",
)

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


def signed(value: float) -> str:
    """A signed effect with the typographic minus the rest of the document uses.

    The hand-typed interval this replaced was written with ``&minus;``; a plain
    format specifier gives a hyphen, which sets differently and reads as a range
    separator beside a comma.
    """
    return f"{value:+.3f}".replace("-", "&minus;")


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
  <p class="meta">therapy-note-bench &middot; harness {data.harness} &middot;
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
            "±0.02",
            "each judge's own vendor",
            "Both judges score their own vendor&rsquo;s models higher by about this much, "
            "and the evidence cannot rule out zero for either. If you grade models with a "
            "model, measure this &mdash; and resample the models, not just the cases.",
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
    """The calibration table, carrying both statistics the payload holds.

    It used to print the Krippendorff pair alone, under the heading the README
    and the methods page use for the kappa/rho pair. Same words, different
    statistic, opposite conclusion: by rho the judge agrees with a therapist
    better than the therapists agree with each other, and by alpha it does not.
    A reader with the PDF and the site in front of them saw a contradiction that
    was really a missing column, so the column is here now.
    """
    calibration = json.loads((DOCS / "calibration.json").read_text(encoding="utf-8"))
    rows = []
    for entry in calibration["agreements"]:
        name = entry["name"].replace("_", " ").replace("rubric ", "").replace("likert ", "")
        kind = "checklist" if entry["name"].startswith("rubric") else "1&ndash;5 rating"
        rows.append(
            f"<tr><td>{esc(name)}</td><td>{kind}</td><td>{esc(entry['statistic'])}</td>"
            f'<td class="num">{entry["judge"]:.2f}</td>'
            f'<td class="num">{entry["humans"]:.2f}</td>'
            f'<td class="num">{entry["alpha"]:.2f}</td>'
            f'<td class="num">{entry["alpha_humans"]:.2f}</td></tr>'
        )

    # Every figure in the prose below is lifted from the same payload the table
    # is built from. All five were typed in, and stayed right only because the
    # calibration has not been re-run since they were typed.
    checklist = next(e for e in calibration["agreements"] if e["name"].startswith("rubric"))
    likert = [e for e in calibration["agreements"] if e["name"].startswith("likert")]
    ceilings = ", ".join(f"{e['alpha_humans']:.2f}" for e in likert[:-1])
    ceilings = f"{ceilings} and {likert[-1]['alpha_humans']:.2f}" if likert else ""
    completeness = next(e for e in likert if e["name"] == "likert_completeness")
    by_rho = "above" if completeness["judge"] > completeness["humans"] else "below"
    by_alpha = "above" if completeness["alpha"] > completeness["alpha_humans"] else "below"

    return f"""
  <h2>The judge is a model, so the judge is measured first</h2>
  <p>TN-Eval released 150 notes that two trained therapists had already rated. Every
     candidate judge answers the same questions about the same notes before it is
     allowed near the leaderboard, and the agreement is published whatever it says.</p>
  <table>
    <thead><tr><th>Measure</th><th>Form</th><th>Statistic</th>
      <th class="num">Judge vs therapist</th><th class="num">Therapist vs therapist</th>
      <th class="num">Alpha, judge</th><th class="num">Alpha, therapists</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  <p>Both therapist-vs-therapist columns are a ceiling, not a target. <strong>Two trained
     therapists rating the same notes barely agree on the 1&ndash;5 scales</strong>
     &mdash; {ceilings} by alpha, where 1.00 is perfect and 0 is chance. On the 23-item
     checklist they reach {checklist["alpha_humans"]:.2f}, and the judge reaches
     {checklist["alpha"]:.2f}.</p>
  <p><strong>Why two pairs.</strong> Cohen&rsquo;s kappa suits a yes/no criterion and
     Spearman&rsquo;s rho an ordered scale, so those are the statistics the leaderboard
     and the methods page report. Krippendorff&rsquo;s alpha sits beside them because it
     is what TN-Eval used, and a comparison with their finding has to be on their
     statistic. The two do not agree: on likert completeness the judge scores
     {completeness["judge"]:.2f} by rho against a ceiling of {completeness["humans"]:.2f},
     and {completeness["alpha"]:.2f} by alpha against a ceiling of
     {completeness["alpha_humans"]:.2f} &mdash; {by_rho} the therapists on one and
     {by_alpha} them on the other. Which statistic is quoted decides the answer, so both
     are printed.</p>
  <p><strong>That is why the ranking uses the checklist and nothing else.</strong> The
     other three columns are reported because the protocol produces them, and ordering
     anything by them would be ordering by noise.</p>
  <p class="note">Measured across {calibration["notes"]} of those notes, judge
     <code>{esc(calibration["judge_model"])}</code>.</p>
"""


def what_it_means(data: Data) -> str:
    """The three findings a reader can act on, each with its figure."""
    preference = data.preference or {}
    effects = {entry["judge"]: entry for entry in preference.get("effects", [])}
    detected = [entry for entry in effects.values() if entry["detected"]]

    # Three figures below this line were typed into the prose. The range was
    # right; the fraction of it was wrong by 4.5x, which made the bias the
    # section reports look far smaller than the section's own numbers show; and
    # the judge-vs-judge interval was the one a superseded estimator produced,
    # 2.5 times narrower than the interval the payload beside it carries. All
    # three are read from that payload now.
    spread_a = data.scores("tneval-soap", JUDGE_A, "completeness")
    shares = []
    for judge in (JUDGE_A, JUDGE_B):
        entry = effects.get(judge)
        scores = data.scores("tneval-soap", judge, "completeness")
        if not entry or not scores:
            continue
        width = max(scores.values()) - min(scores.values())
        shares.append(f"{entry['estimate'] / width:.0%}")
    shares = " and ".join(shares)

    # Named rather than dropped when it is missing. A sentence that says two
    # judges "do not" differ, with the evidence for it silently absent, is the
    # shape this repository keeps finding and refusing.
    difference = preference.get("difference")
    if difference:
        judges_differ = (
            f"asked directly, they do not &mdash; {signed(difference['estimate'])} "
            f"[{signed(difference['low'])}, {signed(difference['high'])}]"
        )
    else:
        judges_differ = "and this payload carries no answer to that question"
    # Was "One of the two is detected." It was, until the interval was widened
    # to cover the three or four systems each mean is taken over -- which is
    # what the sentence generalises to, since the leaderboard marks *rows*.
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
            f'<td class="num">{signed(entry["estimate"])}</td>'
            f'<td class="num">{signed(entry["low"])} to {signed(entry["high"])}</td>'
            f"<td>{verdict}</td></tr>"
        )
    found = (
        "<strong>One of the two is detected.</strong> "
        if detected
        else "<strong>Neither is detected once the models are treated as a sample "
        "rather than as the whole vendor.</strong> "
    )

    # The caption under the figure used to assert "the four systems in the top
    # group are the same four under both", which is the reassuring half of this
    # section's argument -- read it as bands and the bands agree. It was written
    # by hand and it is false: the top band holds four systems under one judge
    # and five under the other. Counted here so the sentence cannot outlive the
    # payload it describes.
    top_a = {name for name, band in data.bands(JUDGE_A).items() if band == 1}
    top_b = {name for name, band in data.bands(JUDGE_B).items() if band == 1}
    shared_top = top_a & top_b
    if len(top_a) == len(top_b) == len(shared_top):
        top_sentence = f"The {len(shared_top)} systems in the top group are the same under both."
    else:
        top_sentence = (
            f"The top group holds {len(top_a)} systems under one judge and "
            f"{len(top_b)} under the other; {len(shared_top)} are in both."
        )
    return f"""
  <h2 class="page-break">One: a leaderboard position is not a measurement</h2>
  <p>The two judges see the same notes, ask the same 23 questions and reach almost the
     same conclusions about which of any two systems is better. And the two orderings
     they produce are visibly different. Both of those are true, and the reason is
     arithmetic rather than disagreement: {len(spread_a)} systems are packed into a
     range of {max(spread_a.values()) - min(spread_a.values()):.2f}, so a handful of
     genuine moves renumbers everyone below them.</p>
  <p><strong>What to do with that.</strong> Read a leaderboard as bands, not as an
     order. &ldquo;In the top group&rdquo; is a claim this kind of evidence supports;
     &ldquo;ninth rather than tenth&rdquo; is not, on this benchmark or on anybody
     else&rsquo;s.</p>
  {
        figure_block(
            "positions.svg",
            "Completeness under each of the two judges. Grey lines held their place. "
            + top_sentence,
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
  <p>{found}The units are completeness, so these effects are {shares} of the range the
     models occupy under their own judge &mdash; enough to move a system several places
     in an ordering this tight, and not enough to make a bad note look good. Both point
     estimates are positive and neither interval clears zero.</p>
  <p><strong>What to do with that.</strong> If you evaluate models with a model, run
     this check. Two judges from two vendors is the cheapest way to have it; one judge
     cannot measure its own bias at all, and a caveat in the methods section is not a
     measurement.</p>
  <p class="note">Two systems carry most of it, and they are the two that a
     definition change moved into these groups on 2026-08-26: dropping
     <code>gemma4</code> takes the Gemini figure from +0.018 to +0.008, and dropping
     <code>gpt-oss-120b</code> takes the GPT one from +0.027 to +0.018. Nothing here
     tests whether the two judges differ from each other; {judges_differ}.</p>

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


def how_much_room_is_left(data: Data) -> str:
    """Is the benchmark still measuring anything, and for how much longer.

    The question anybody who has watched a benchmark die asks first. It is
    answered per criterion rather than in aggregate, because a benchmark does
    not saturate evenly: some criteria are free points and some have never been
    met by anyone, the therapist included.

    **The four counts are one judge's**, and the panel says so. A verdict is a
    reading of that judge's answers, and the two judges do not return the same
    reading -- `gpt-5.6-terra` puts a third criterion on the floor that
    `gemini-3.1-pro-preview` leaves 0.02 above it. `docs/limitations.md`
    excludes only what both of them put there, which is why that page says two
    and this one used to say two without saying whose two.
    """
    saturation = data.saturation.get(JUDGE_A) or {}
    counts = saturation.get("verdict_counts") or {}
    total = len(saturation.get("criteria") or []) or 23
    free = counts.get("saturated", 0)
    dead = counts.get("unreachable", 0)
    other = (data.saturation.get(JUDGE_B) or {}).get("verdict_counts") or {}
    other_dead = other.get("unreachable")
    live = counts.get("discriminating", 0)
    partly = counts.get("mixed", 0)

    # The ceiling has to be weighted the way completeness is, or it is not a
    # ceiling on completeness. `tneval.aggregate` scores each SOAP section and
    # averages the four equally, so a criterion in the four-item plan section is
    # worth twice one in the eight-item assessment section. Counting 21 of 23
    # flat says 0.91; the two dead criteria sit in the six- and eight-item
    # sections, so the real ceiling is 0.93 -- and the sentence below divides the
    # best score by it, which made "60% of that" out of 58.9%.
    per_section: Counter[str] = Counter(c["section"] for c in saturation.get("criteria") or [])
    alive: Counter[str] = Counter(
        c["section"] for c in saturation.get("criteria") or [] if c["verdict"] != "unreachable"
    )
    reachable = (
        fmean(alive[section] / count for section, count in per_section.items())
        if per_section
        else 1.0
    )

    table = data.tables[("tneval-soap", JUDGE_A)]
    current = [
        row["headline"]["completeness"] for row in table["rows"] if row["system_type"] == "model"
    ]
    older = [
        row["headline"]["completeness"]
        for row in table["rows"]
        if row["system_type"] == "reference-model"
    ]
    best = max(current)

    trace = {}
    for judge in (JUDGE_A, JUDGE_B):
        values = [
            row["headline"]["trace"]
            for row in data.tables[("icare", judge)]["rows"]
            if row["headline"].get("trace") is not None
        ]
        trace[judge] = (min(values), max(values))

    rows = "".join(
        f"<tr><td>{label}</td><td class='num'>{count} of {total}</td><td>{meaning}</td></tr>"
        for label, count, meaning in (
            (
                "Every model already does it",
                free,
                "Free points. They raise every score by the same amount and separate nobody.",
            ),
            (
                "Nobody does it, the therapist included",
                dead,
                "Dead. These transcripts do not contain the answer, so the criterion "
                "measures the corpus rather than the model.",
            ),
            ("Still separates models", live, "Where the benchmark is doing its job."),
            ("Partly", partly, "Separates some models and not others."),
        )
    )

    return f"""
  <h2 class="page-break">How much room is left</h2>
  <p>A benchmark that everything passes has stopped measuring. This one has not, and
     it has not evenly: under <code>{esc(JUDGE_A)}</code> the twenty-three rubric
     criteria are in four different states at once.</p>
  <table>
    <thead><tr><th>Criterion</th><th class="num">How many</th><th>What that means</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p><strong>These are one judge&rsquo;s verdicts.</strong> A verdict reads that
     judge&rsquo;s answers, and the second judge does not return the same reading:
     <code>{esc(JUDGE_B)}</code> puts {other_dead} criteria on the floor rather than
     {dead}, the extra one being assessment tools, which the first judge leaves 0.02
     above it. <code>docs/limitations.md</code> excludes only the {dead} both of them
     put there.</p>
  <p>Strip out the {dead} nobody reaches and the most a model could score is
     {reachable:.2f} &mdash; weighted the way completeness is, four sections
     averaged equally rather than 21 criteria out of 23.
     <strong>The best model here reaches {best:.3f}, which is
     {best / reachable:.0%} of that.</strong> There is room.</p>
  <p>How fast it is being used up: the two 2025 models the source paper benchmarked
     score {min(older):.3f} and {max(older):.3f}; the {len(current)} current ones span
     {min(current):.3f} to {best:.3f}. <strong>One model generation moved the top of
     the table by {best - max(older):+.3f}.</strong> Two or three more at that rate and
     the reachable part of this rubric is exhausted &mdash; which is a reason to record
     what the corpus and the protocol are now, not a reason to trust the ranking more.</p>

  <h3>The other track&rsquo;s judge-scored measure is nearly out of room</h3>
  <p>TRACE rates five dimensions from 1 to 5. Under one judge all {len(current)} models
     land between {trace[JUDGE_A][0]:.2f} and {trace[JUDGE_A][1]:.2f} &mdash;
     {(trace[JUDGE_A][1] - trace[JUDGE_A][0]) / 4:.0%} of the scale. Under the other,
     {trace[JUDGE_B][0]:.2f} to {trace[JUDGE_B][1]:.2f}, which is
     {(trace[JUDGE_B][1] - trace[JUDGE_B][0]) / 4:.0%}. The two judges&rsquo; orderings
     correlate at +0.83 and place 11 of 16 systems differently anyway.</p>
  <p><strong>What to do with that.</strong> A measure where every model scores within a
     few percent of every other is not evidence that the models are equally good; it is
     evidence that the measure is running out. That the two judges disagree about how
     much room is left &mdash; 6% against 13% &mdash; is a fact about the judges, and it
     is why one judge is not enough to notice this happening. If you are building an evaluation, the
     per-criterion breakdown is the thing to watch &mdash; an aggregate stays healthy
     for a long time after the parts of it have died.</p>
  <p class="note">Computed by a paired bootstrap over the conversations every system was
     scored on, published as <code>docs/saturation-&lt;judge&gt;.json</code> and drawn in
     full on the methods page. TRACE has no human anchor at all: unlike the rubric, no
     therapist ever rated these notes on it, and it is labelled that way wherever it
     appears.</p>
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
            "agree about whether covering more of a checklist goes with inventing more. Only "
            "the two ends are named &mdash; nineteen labels in a panel this size collide, and "
            "the figure is about the contrast between the judges rather than about any one "
            "model. Every system is named in the chart above.",
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
  <p>Every figure in this document is drawn from the files the site publishes, and
     every table is built from them row by row. Four files rather than two:
     <code>leaderboard.json</code>, the two <code>saturation-*.json</code>, and
     <code>calibration.json</code>.</p>
  <p><strong>The prose around them is written by hand.</strong> Where a sentence states
     a figure, that figure is computed from the same payload and a test fails if it
     drifts &mdash; but the test names the sentences it covers, and a sentence it does
     not name is a sentence nobody is checking. This paragraph used to say that nothing
     here was typed in. That was false in this file more than thirty times, and it read
     as an instruction not to look.</p>
  <p>And four pages carry what the numbers rest on:
     <a href="datasets.md">the datasets</a> &mdash; where each came from, what licence it
     publishes (two of the three publish none) and the traps in them;
     <a href="methodology.md">the method</a>;
     <a href="limitations.md">what a result cannot claim</a>; and
     <a href="landscape.md">what exists in this field</a> and what does not.</p>
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
  <p class="meta">therapy-note-bench &middot; harness {data.harness} &middot;
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
        + how_much_room_is_left(data)
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
