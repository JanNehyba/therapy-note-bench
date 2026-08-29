"""The PDSQI sheet as a page you click through, not a document you fill in.

The markdown sheet asks for 120 answers and Jan said, reasonably, that it is too
much. This is the part of it that decides something.

**Ten notes, three attributes, thirty clicks.** The three are `useful`,
`organized` and `synthesized` -- the three where the judge gives every one of the
eleven models exactly 5.00. Tonight's planted-fault control showed the judge is
not blind to them: shuffle a note's sentences into the wrong sections and
`organized` comes back 1. So the flatness is the models genuinely not differing.
That is half the answer. The other half is whether a clinician agrees, and only a
clinician can supply it.

The other three attributes are left out on purpose. `comprehensible`, `succinct`
and `stigmatizing` already separate the models under at least one judge, so a
human answer there confirms rather than decides -- and thirty answers that decide
something are worth more than a hundred and twenty that mostly do not.

**Same ten notes as the markdown sheet**, drawn by the same hash of session and
model, so the two remain the same sample and neither was chosen after seeing a
score. The presentation order is the sheet's too.

**It stays on this machine.** The page carries whole notes, which are clinical
content: it is written to gitignored `local/`, opened from disk, and saves
nothing anywhere but the browser it is opened in. The Save button writes a file
to Downloads -- that works from `file://` where it would not from a hosted page.

Run: `uv run python tools/czech_pdsqi_form.py`. Costs nothing and calls nobody.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from pathlib import Path

from tnb.scoring import czech_run, pdsqi
from tnb.tasks import czech as czech_task

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO / "local" / "czech-pdsqi-form.html"

#: The three the judge cannot separate the models on. Answering these decides
#: something; the other three would confirm what is already visible.
ASKED = ("useful", "organized", "synthesized")

#: Czech for the three questions and their anchors. The English is PDSQI-9's own
#: and is shown beside the Czech rather than replaced by it: the judge was asked
#: in English, and a rater answering a paraphrase is not answering the same
#: question. The Czech is a reading aid, and it says so on the page.
CS = {
    "useful": (
        "Je zápis užitečný?",
        "Je v něm všechno, co potřebuje ten, kdo ho bude číst — a nic navíc.",
        [
            "Nic v zápisu není pro čtenáře podstatné.",
            "Něco v zápisu podstatné je.",
            "Podstatné to je, ale míra podrobnosti nesedí (moc, nebo málo).",
            "Nic nepodstatného navíc, ale něco je jen možná podstatné.",
            "Nic nepodstatného navíc a podrobnost přesně sedí.",
        ],
    ),
    "organized": (
        "Je zápis dobře uspořádaný?",
        "Je poskládaný tak, že čtenář pochopí průběh.",
        [
            "Všechno je přeházené a seskupení nedává smysl.",
            "Něco je přeházené NEBO seskupení nedává smysl.",
            "Pořadí ani seskupení se nijak neliší od přepisu sezení.",
            "Logické pořadí NEBO logické seskupení, ale ne obojí.",
            "Logické pořadí i seskupení, všechno.",
        ],
    ),
    "synthesized": (
        "Je v zápisu syntéza?",
        "Je z něj zřejmé, kde klient je a proč — ne jen výčet toho, co padlo.",
        [
            "Není tam žádný kontext ani zdůvodnění.",
            "Trochu kontextu, ale zdůvodnění chybí.",
            "Kontext i zdůvodnění, ale nespojené dohromady.",
            "Spojené, ale něco podstatného chybí.",
            "Celistvý obraz: kde klient je, proč, a co z toho plyne.",
        ],
    ),
}


def _rank(session_id: str, system_id: str) -> str:
    """The language sheet's draw, so every sheet rates the same notes."""
    return hashlib.sha256(f"{session_id}/{system_id}".encode()).hexdigest()


def _order(session_id: str, system_id: str) -> str:
    return hashlib.sha256(f"pdsqi/{session_id}/{system_id}".encode()).hexdigest()


def _transcript(session) -> str:
    """The session behind a note, folded away until it is wanted.

    **Why the form did not have this and now does.** `useful`, `organized` and
    `synthesized` were chosen precisely because they can be judged from the note
    alone -- which is what lets the JUDGE rate them without a transcript leaving
    the university. That reasoning does not transfer to the person: Jan is
    reading his own sessions on his own machine, and a note saying the client
    rested after lunch on the 25th cannot be called useful or synthesised by
    somebody who does not know what the session contained.

    So the transcript is here for the human and still never for the judge. It is
    the anonymised text -- `czech.REAL_DIR` is `data/czech/anonymised` and the
    loader reads nothing else -- and this file stays under `local/`, which is
    gitignored, for the same reason it always did: it carries whole notes, and
    now whole sessions too.
    """
    turns = "".join(
        '<p class="turn {who}"><span class="lbl">{tag}</span>'
        '<span class="said">{text}</span></p>'.format(
            who=turn.speaker,
            tag="T" if turn.speaker == "therapist" else "K",
            text=html.escape(turn.text),
        )
        for turn in session.turns
    )
    return (
        f'<details class="tr"><summary>p\u0159epis sezen\xed &mdash; {len(session.turns)} replik, '
        f"{session.word_count} slov</summary>"
        f'<div class="turns">{turns}</div></details>'
    )


def build(notes: int, corpus: str) -> str:
    loader = czech_task.load_real if corpus == "real" else czech_task.load_translated
    task_name = czech_task.NAME_REAL if corpus == "real" else czech_task.NAME_TRANSLATED
    sessions = loader()
    # Kept, not discarded. The transcript is what makes two of the three
    # attributes answerable by a person at all.
    behind = {session.id: session for session in sessions}
    candidates = list(czech_run.from_generations(sessions, task_name=task_name))
    if not candidates:
        raise SystemExit(f"Nothing generated for {corpus} yet.")

    drawn = sorted(candidates, key=lambda c: _rank(c.session_id, c.system_id))[:notes]
    shown = sorted(drawn, key=lambda c: _order(c.session_id, c.system_id))
    attributes = {a.key: a for a in pdsqi.ATTRIBUTES if a.key in ASKED}

    cards = []
    for index, candidate in enumerate(shown, start=1):
        rendered = html.escape(czech_task.render_note(candidate.note))
        questions = []
        for key in ASKED:
            attribute = attributes[key]
            question, gloss, anchors = CS[key]
            buttons = "".join(
                f'<label class="opt"><input type="radio" name="{index}-{key}" value="{n}">'
                f'<span class="n">{n}</span>'
                f'<span class="a">{html.escape(anchor)}</span></label>'
                for n, anchor in enumerate(anchors, start=1)
            )
            questions.append(
                f'<div class="q" data-key="{key}">'
                f'<p class="qt">{html.escape(question)}</p>'
                f'<p class="qg">{html.escape(gloss)}</p>'
                f"<details><summary>anglické znění, které dostal soudce</summary>"
                f"<p>{html.escape(attribute.question)} {html.escape(attribute.definition)}</p>"
                f"</details>"
                f'<div class="opts">{buttons}</div></div>'
            )
        session = behind.get(candidate.session_id)
        cards.append(
            f'<article class="note" id="n{index}" data-i="{index}">'
            f'<header><span class="num">{index} / {len(shown)}</span>'
            f'<span class="done" aria-hidden="true"></span></header>'
            f"<pre>{rendered}</pre>"
            + (_transcript(session) if session else "")
            + f'<div class="qs">{"".join(questions)}</div></article>'
        )

    key_rows = "".join(
        f"<tr><td>{i}</td><td>{html.escape(c.system_id)}</td>"
        f"<td>{html.escape(c.session_id)}</td></tr>"
        for i, c in enumerate(shown, start=1)
    )
    meta = json.dumps(
        [
            {"i": i, "system": c.system_id, "session": c.session_id}
            for i, c in enumerate(shown, start=1)
        ],
        ensure_ascii=False,
    )
    return TEMPLATE.format(
        cards="\n".join(cards),
        total=len(shown) * len(ASKED),
        notes=len(shown),
        key_rows=key_rows,
        meta=meta,
        asked=json.dumps(list(ASKED)),
    )


TEMPLATE = """<!doctype html>
<html lang="cs"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PDSQI &mdash; 30 otázek</title>
<style>
  :root {{
    --paper:#f7f8f9; --card:#fff; --ink:#14181d; --muted:#5b646f;
    --rule:#dde2e8; --soft:#eef1f4; --accent:#134a7c; --accent-soft:#e6eef6;
    --done:#2f6b4f;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --paper:#101418; --card:#171c22; --ink:#e6eaef; --muted:#98a3af;
      --rule:#2a323b; --soft:#1c232b; --accent:#7db3e8; --accent-soft:#152634;
      --done:#7fc9a3;
    }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
    font:400 16px/1.6 "Segoe UI", system-ui, sans-serif; }}
  .wrap {{ max-width:52rem; margin:0 auto; padding:2.5rem 1.1rem 8rem; }}
  h1 {{ font-size:1.9rem; line-height:1.15; margin:0 0 .4rem; }}
  .lede {{ color:var(--muted); margin:0 0 2rem; max-width:44ch; }}
  .note {{ background:var(--card); border:1px solid var(--rule); border-radius:4px;
    padding:1.2rem 1.3rem; margin:0 0 1.4rem; }}
  .note header {{ display:flex; justify-content:space-between; align-items:center;
    margin-bottom:.7rem; }}
  .num {{ font:500 .78rem/1 ui-monospace,monospace; letter-spacing:.1em;
    text-transform:uppercase; color:var(--muted); }}
  .done {{ width:.6rem; height:.6rem; border-radius:50%; background:var(--rule); }}
  .note.complete .done {{ background:var(--done); }}
  .note.complete {{ border-color:var(--done); }}
  pre {{ background:var(--soft); border-radius:3px; padding:.9rem 1rem; margin:0 0 1.2rem;
    white-space:pre-wrap; font:400 .88rem/1.55 ui-monospace,monospace;
    max-height:22rem; overflow:auto; }}
  .tr {{ margin:0 0 1.2rem; border:1px solid var(--rule); border-radius:3px;
    background:var(--soft); }}
  .tr > summary {{ cursor:pointer; padding:.55rem .9rem; font-size:.85rem;
    color:var(--accent); font-weight:600; }}
  .tr[open] > summary {{ border-bottom:1px solid var(--rule); }}
  .turns {{ max-height:30rem; overflow:auto; padding:.7rem .9rem 1rem; }}
  .turn {{ margin:0 0 .55rem; display:flex; gap:.6rem; align-items:baseline;
    font-size:.9rem; line-height:1.55; }}
  .turn .lbl {{ flex:0 0 1.15rem; height:1.15rem; border-radius:50%; text-align:center;
    font:600 .68rem/1.15rem ui-monospace,monospace; background:var(--rule);
    color:var(--muted); }}
  .turn.therapist .lbl {{ background:var(--accent-soft); color:var(--accent); }}
  .turn.client .said {{ font-weight:500; }}
  .q {{ border-top:1px solid var(--rule); padding-top:.9rem; margin-top:.9rem; }}
  .q:first-child {{ border-top:none; padding-top:0; margin-top:0; }}
  .qt {{ font-weight:600; margin:0 0 .1rem; }}
  .qg {{ color:var(--muted); font-size:.9rem; margin:0 0 .5rem; }}
  details {{ margin:0 0 .7rem; }}
  summary {{ cursor:pointer; color:var(--muted); font-size:.82rem; }}
  details p {{ font-size:.86rem; color:var(--muted); margin:.4rem 0 0;
    padding-left:.8rem; border-left:2px solid var(--rule); }}
  .opts {{ display:flex; flex-direction:column; gap:.3rem; }}
  .opt {{ display:flex; gap:.6rem; align-items:flex-start; cursor:pointer;
    padding:.4rem .55rem; border-radius:3px; border:1px solid transparent; }}
  .opt:hover {{ background:var(--soft); }}
  .opt input {{ margin:.35rem 0 0; flex:none; }}
  .opt .n {{ font:600 .85rem/1.5 ui-monospace,monospace; color:var(--muted); flex:none;
    width:1ch; }}
  .opt .a {{ font-size:.9rem; }}
  .opt:has(input:checked) {{ background:var(--accent-soft); border-color:var(--accent); }}
  .opt:has(input:checked) .n {{ color:var(--accent); }}
  .bar {{ position:fixed; left:0; right:0; bottom:0; background:var(--card);
    border-top:1px solid var(--rule); padding:.8rem 1.1rem; }}
  .bar .in {{ max-width:52rem; margin:0 auto; display:flex; gap:1rem;
    align-items:center; justify-content:space-between; flex-wrap:wrap; }}
  .prog {{ font:500 .9rem/1 ui-monospace,monospace; }}
  .track {{ flex:1; height:5px; background:var(--soft); border-radius:3px;
    min-width:8rem; overflow:hidden; }}
  .fill {{ height:100%; width:0; background:var(--accent); transition:width .2s; }}
  button {{ font:500 .9rem/1 inherit; padding:.65rem 1.1rem; border-radius:3px;
    border:1px solid var(--accent); background:var(--accent); color:#fff;
    cursor:pointer; }}
  button.ghost {{ background:transparent; color:var(--accent); }}
  button:disabled {{ opacity:.45; cursor:default; }}
  table {{ border-collapse:collapse; width:100%; font-size:.85rem; margin-top:.8rem; }}
  th,td {{ text-align:left; padding:.35rem .5rem; border-bottom:1px solid var(--rule); }}
  h2 {{ font-size:1.15rem; margin:3rem 0 .3rem; }}
  :focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
</style></head><body>
<div class="wrap">
  <h1>Je ten zápis k něčemu?</h1>
  <p class="lede">{notes} poznámek, u každé tři otázky. Klikni jedno číslo u každé.
    Odpovědi se ukládají samy — můžeš kdykoli zavřít a vrátit se.</p>

  <p style="color:var(--muted);font-size:.92rem;max-width:52ch">
    Jsou to ty tři otázky, u kterých soudce dává <strong>všem jedenácti modelům
    pětku</strong>. Kontrola ukázala, že nástroj slepý není. Zbývá zjistit, jestli
    bys pětku dal i ty.
  </p>

{cards}

  <h2>Které poznámky to byly</h2>
  <p style="color:var(--muted);font-size:.9rem">Nedívej se sem, dokud nemáš
    hotovo — vědět, který model to psal, mění, jak se čte.</p>
  <details><summary>ukázat</summary>
    <table><thead><tr><th>#</th><th>model</th><th>sezení</th></tr></thead>
    <tbody>{key_rows}</tbody></table>
  </details>
</div>

<div class="bar"><div class="in">
  <span class="prog"><span id="n">0</span> / {total}</span>
  <span class="track"><span class="fill" id="fill"></span></span>
  <button class="ghost" id="reset" type="button">Vymazat</button>
  <button id="save" type="button" disabled>Uložit odpovědi</button>
</div></div>

<script>
const TOTAL = {total};
const META = {meta};
const ASKED = {asked};
const KEY = "tnb-pdsqi-form-v1";

function load() {{
  try {{ return JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{ return {{}}; }}
}}
function store(answers) {{
  try {{ localStorage.setItem(KEY, JSON.stringify(answers)); }} catch (e) {{ /* private window */ }}
}}

const answers = load();

for (const [name, value] of Object.entries(answers)) {{
  const input = document.querySelector(
    'input[name="' + CSS.escape(name) + '"][value="' + CSS.escape(String(value)) + '"]');
  if (input) input.checked = true;
}}

function paint() {{
  const n = Object.keys(answers).length;
  document.getElementById("n").textContent = n;
  document.getElementById("fill").style.width = (100 * n / TOTAL) + "%";
  document.getElementById("save").disabled = n === 0;
  for (const card of document.querySelectorAll(".note")) {{
    const i = card.dataset.i;
    const full = ASKED.every(k => answers[i + "-" + k] !== undefined);
    card.classList.toggle("complete", full);
  }}
}}

document.addEventListener("change", (event) => {{
  const input = event.target;
  if (input.type !== "radio") return;
  answers[input.name] = Number(input.value);
  store(answers);
  paint();
}});

document.getElementById("reset").addEventListener("click", () => {{
  if (!confirm("Opravdu vymazat všechny odpovědi?")) return;
  for (const k of Object.keys(answers)) delete answers[k];
  store(answers);
  for (const i of document.querySelectorAll("input[type=radio]")) i.checked = false;
  paint();
}});

document.getElementById("save").addEventListener("click", () => {{
  const rows = [];
  for (const note of META) {{
    for (const key of ASKED) {{
      const value = answers[note.i + "-" + key];
      if (value !== undefined) {{
        rows.push({{system: note.system, session: note.session, attribute: key, rating: value}});
      }}
    }}
  }}
  const blob = new Blob(
    [JSON.stringify({{answers: rows, of: TOTAL}}, null, 2)],
    {{type: "application/json"}});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "czech-pdsqi-answers.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}});

paint();
</script>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--notes", type=int, default=10)
    parser.add_argument("--corpus", choices=["real", "translated"], default="real")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    page = build(args.notes, args.corpus)
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(page, encoding="utf-8")
    print(f"wrote {args.target}  ({args.notes} notes x {len(ASKED)} = {args.notes * len(ASKED)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
