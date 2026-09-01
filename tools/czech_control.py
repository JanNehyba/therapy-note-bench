"""Plant one error per criterion and check the judge finds that one.

The scores say the criteria separate models: on the real half `calque` runs from
0.00 to 0.70 and `agreement` from 0.00 to 1.00. That is evidence the judge sees
*something*. It is not evidence it sees what the column claims.

This asks the narrower question. One clean note, seven variants, each carrying
exactly one deliberate fault of one kind. Two things have to be true for a
criterion to mean what its heading says:

* the judge answers "fault present" on the variant that carries it, and
* it does not answer "fault present" on the six that do not.

Reading the result, in the order it matters:

* **flags its own and nothing else** -- the criterion measures what it says.
* **misses its own** -- the judge cannot see that fault. The column is not a
  result and should be published as unmeasured, the way TRACE is published
  without a human anchor.
* **flags everything** -- the judge is rating an impression rather than
  answering the question, and seven columns are one column wearing seven hats.

The base note is invented rather than taken from a generated one, so this file
and its output carry no clinical text at all. It is written to be *clean*: the
point is that every fault the judge reports is one this script put there.

Run: `uv run python tools/czech_control.py --judge-model gemini-3.1-pro-preview`
Writes `local/czech-control.md`. Costs 7 x 7 = 49 judge calls, minus the ones a
variant does not earn.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from tnb import judge
from tnb.scoring import czech
from tnb.tasks import czech as czech_task
from tnb.tasks import deepsy as deepsy_task

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO / "local" / "czech-control.md"

#: A clean note. Invented, and deliberately ordinary: correct diacritics, whole
#: sentences, clinical register, Czech quotation marks, no English left in.
CLEAN = {
    "subjective": (
        "Klientka popisuje zvýšené napětí v posledních dvou týdnech, které "
        "spojuje s blížící se zkouškou. Uvádí: „nejhorší je to večer, když si "
        "lehnu.“ Spánek je přerušovaný, chuť k jídlu beze změny. Sestra jí "
        "podle jejích slov nabídla pomoc s přípravou."
    ),
    "objective": (
        "V kontaktu spolupracující, orientovaná všemi směry. Řeč plynulá, "
        "tempo přiměřené. Afekt přiléhavý, v úvodu sezení mírně úzkostné "
        "ladění, které v průběhu odeznívá. Bez známek psychotického prožívání."
    ),
    "assessment": (
        "Pokračuje práce na zvládání úzkosti vázané na výkonovou situaci. "
        "Klientka lépe rozpoznává tělesné signály napětí než na začátku "
        "terapie. Vyhýbavé chování se zmírnilo, přetrvává v oblasti přípravy "
        "na zkoušku."
    ),
    "plan": (
        "Nácvik bráničního dýchání, krátce každý den. Sledování "
        "spánkového režimu formou záznamu. Kontrola za dva týdny, dříve "
        "v případě zhoršení."
    ),
}

#: One fault per criterion, each a substitution into the clean note.
#:
#: The faults are the ones this track was built around -- `pres` for `tlak`,
#: `sebepece` for `sebepece` with the length marks gone, `Segra` for `sestra`,
#: an untranslated `behavioral avoidance coping`, straight quotation marks. They
#: came to this project through `HANDOFF-CZECH.md` as things noticed in some
#: earlier Czech notes; how they were noticed is not recorded and should not be
#: guessed at here. What matters for this control is only that each is a real
#: fault of the kind its criterion names, which is checkable by reading it.
PLANTED: dict[str, tuple[str, str, str]] = {
    # criterion: (section, from, to)
    "diacritics": ("assessment", "Vyhýbavé chování", "Vyhybave chovani"),
    "calque": ("subjective", "zvýšené napětí", "zvýšený pres"),
    "untranslated": (
        "assessment",
        "Vyhýbavé chování se zmírnilo",
        "Behavioral avoidance coping se zmírnilo",
    ),
    "agreement": ("objective", "V kontaktu spolupracující", "V kontaktu spolupracujícím byl"),
    "register": ("subjective", "Sestra jí", "Ségra jí"),
    # Only the marks change. An earlier version also dropped the diacritics,
    # so `diacritics` fired on this variant too and it was testing two faults.
    "quotes": (
        "subjective",
        "„nejhorší je to večer, když si lehnu.“",
        '"nejhorší je to večer, když si lehnu."',
    ),
    "nonword": ("plan", "bráničního dýchání", "bráničního dýchánkování"),
}


#: The same control, in the format the Deepsy application writes. Eleven short
#: labelled fields rather than four paragraphs, which is the point: the judge
#: sees each fault with far less text around it, and a criterion that finds a
#: missing length mark inside a paragraph need not find one inside a one-clause
#: field. Invented like the SOAP note above, so no clinical text is here.
#:
#: Every field is filled. A control note with empty fields would be measuring
#: what the judge does with an empty field, which is a different question and
#: one the Deepsy tables already raise on their own.
CLEAN_DEEPSY: dict[str, str] = {
    "main_themes": (
        "Zvýšené napětí před zkouškou a jeho dopad na spánek. Klientka téma "
        "otevřela sama v úvodu sezení."
    ),
    "problems_symptoms": (
        "Přerušovaný spánek v posledních dvou týdnech, večerní neklid. Chuť "
        "k jídlu beze změny. Klientka uvádí: „nejhorší je to večer, když si "
        "lehnu.“"
    ),
    "therapy_goals": (
        "Zmírnit večerní napětí natolik, aby klientka usínala do půl hodiny. "
        "Cíl formulovala klientka, terapeut jej přeformuloval do měřitelné "
        "podoby."
    ),
    "client_resources": (
        "Pravidelný denní režim, dokončené dva roky studia, ochota zkoušet "
        "nová řešení. Sestra jí podle jejích slov nabídla pomoc s přípravou."
    ),
    "important_persons": (
        "Sestra, se kterou je klientka v častém kontaktu. Spolubydlící, kterou zmiňuje neutrálně."
    ),
    "hypotheses": (
        "Napětí se váže na očekávané hodnocení a udržuje se vyhýbáním se "
        "přípravě. Vyhýbavé chování se zmírnilo po prvním nácviku, což "
        "podporuje výklad přes udržovací kruh."
    ),
    "treatment_plan": (
        "Pokračovat v nácviku bráničního dýchání před spaním a rozvrhnout "
        "přípravu do kratších úseků."
    ),
    "unresolved_problems": (
        "Vztah ke spolubydlící zůstává nezmapovaný. Klientka jej zatím neoznačila za téma."
    ),
    "between_session_tasks": (
        "Denní záznam večerního napětí na škále od jedné do deseti, vždy před ulehnutím."
    ),
    "referrals": "Nezajištěna, klientka o odborné vyšetření nežádá.",
    "crisis_planning": (
        "V sezení nebyly zmíněny sebevražedné myšlenky ani jiné akutní riziko, "
        "krizový plán proto nebyl sestavován."
    ),
}

#: The same six faults, in fields chosen so each sits in ordinary prose rather
#: than in a one-clause stub -- a fault planted in `referrals: nezajištěna` would
#: be testing whether the judge reads stubs, not whether the criterion works.
PLANTED_DEEPSY: dict[str, tuple[str, str, str]] = {
    # criterion: (field, from, to)
    "diacritics": ("hypotheses", "Vyhýbavé chování", "Vyhybave chovani"),
    "calque": ("main_themes", "Zvýšené napětí", "Zvýšený pres"),
    "untranslated": (
        "hypotheses",
        "Vyhýbavé chování se zmírnilo",
        "Behavioral avoidance coping se zmírnilo",
    ),
    "agreement": (
        "client_resources",
        "Pravidelný denní režim",
        "Pravidelným denním režimem byl",
    ),
    "register": ("client_resources", "Sestra jí", "Ségra jí"),
    "quotes": (
        "problems_symptoms",
        "„nejhorší je to večer, když si lehnu.“",
        '"nejhorší je to večer, když si lehnu."',
    ),
    "nonword": ("treatment_plan", "bráničního dýchání", "bráničního dýchánkování"),
}


#: **The prediction for the Deepsy run, written before it was made.**
#:
#: 1. Every criterion flags its own fault in the Deepsy format, as it does in
#:    SOAP. The planted text is identical and each criterion asks whether the
#:    fault appears ANYWHERE in the note, so the surrounding format should not
#:    matter. A miss here would say the criterion depends on the prose around
#:    the fault, which would be a finding about the instrument.
#:
#: 2. Cross-fire is LOWER in Deepsy than in SOAP. The SOAP control flags a fault
#:    that is not there in 4 of 30 off-diagonal cells under
#:    `gemini-3.1-pro-preview` and 5 of 30 under `gpt-5.6-terra`. A Deepsy note
#:    is eleven short labelled fields rather than four paragraphs, so there is
#:    less continuous prose from which to form a general impression of bad
#:    Czech -- and cross-fire is what an impression looks like. If it comes back
#:    HIGHER, this prediction is wrong and the shorter fields make the judge
#:    more suspicious rather than less.
#:
#: 3. The clean Deepsy note flags nothing. If it does, the format itself reads
#:    as faulty to the judge and every Deepsy criterion score carries that.
#:
#: Predictions 2 and 3 are the ones worth being wrong about; 1 is the floor.

#: Which clean note and which faults each format uses. A table rather than a
#: branch, for the reason the scorer's own corpus lookup is one: a format name
#: that matches neither arm of an `if` silently gets the other format's note.
FORMATS = {
    "soap": (CLEAN, PLANTED),
    "deepsy": (CLEAN_DEEPSY, PLANTED_DEEPSY),
}


def _variant(criterion: str, fmt: str = "soap") -> dict[str, str]:
    clean, planted = FORMATS[fmt]
    section, old, new = planted[criterion]
    note = dict(clean)
    if old not in note[section]:
        raise SystemExit(f"{criterion}: {old!r} is not in the {section} field any more.")
    note[section] = note[section].replace(old, new)
    return note


def _ask(note: str, client: judge.Judge, spend: judge.Spend) -> dict[str, bool | None]:
    answers = {}
    for task in czech.build_tasks(note):
        answer = client.ask(task.prompt)
        spend.record(client.config.model, answer)
        answers[task.criterion] = czech.parse_answer(answer.text) if answer.ok else None
    return answers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--judge-model", default=judge.DEFAULT_MODEL)
    parser.add_argument("--thinking-budget", type=int, default=2048)
    parser.add_argument("--target", type=Path, default=None)
    parser.add_argument(
        "--format",
        choices=sorted(FORMATS),
        default="soap",
        help=(
            "which note format to plant the faults in. `deepsy` is eleven short "
            "labelled fields rather than four paragraphs, so the judge sees each "
            "fault with far less text around it -- and the four Deepsy tracks had "
            "no control at all until this existed"
        ),
    )
    args = parser.parse_args(argv)
    # A separate file per format, never the same one: the two are different
    # measurements, and overwriting one with the other would publish an answer
    # about SOAP notes under the Deepsy tables.
    if args.target is None:
        args.target = (
            DEFAULT_TARGET
            if args.format == "soap"
            else DEFAULT_TARGET.with_name("czech-control-deepsy.md")
        )

    # `tnb.cli` does this at startup; a script run directly does not inherit it,
    # and the judge credentials live in `.env`.
    load_dotenv(REPO / ".env")

    config = judge.config_from_env(model=args.judge_model, thinking_budget=args.thinking_budget)
    client = judge.Judge(config)
    spend = judge.Spend(limit_usd=25.0)

    print(f"judge {config.model}, thinking budget {config.thinking_budget}")
    print("clean note first, then one variant per criterion\n")

    # The renderer follows the note, not the module it sits beside: the SOAP
    # renderer over a Deepsy note joins four headings that are not there and
    # emits nothing, which asks the judge no questions and reports a clean
    # sheet. `tests/test_pdsqi_cache_collision.py` records that failure.
    render = czech_task.render_note if args.format == "soap" else deepsy_task.render_note
    clean_note, _planted_here = FORMATS[args.format]
    print(f"format {args.format}")

    clean = _ask(render(clean_note), client, spend)
    print(
        f"  {'clean':14} "
        + " ".join(f"{k[:4]}={_cell(clean.get(k))}" for k in czech.CRITERION_KEYS)
    )

    variants: dict[str, dict[str, bool | None]] = {}
    for criterion in czech.CRITERION_KEYS:
        answers = _ask(render(_variant(criterion, args.format)), client, spend)
        variants[criterion] = answers
        print(
            f"  {criterion:14} "
            + " ".join(f"{k[:4]}={_cell(answers.get(k))}" for k in czech.CRITERION_KEYS)
        )

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(_report(config.model, clean, variants, spend), encoding="utf-8")

    # Beside the prose, so `tools/czech_brief.py` can put this next to the
    # numbers rather than in a file somebody has to be told about. What a column
    # is worth belongs in the same document as the column.
    payload = args.target.with_suffix(".json")
    payload.write_text(
        json.dumps(
            {
                "judge_model": config.model,
                "thinking_budget": config.thinking_budget,
                "format": args.format,
                "clean": clean,
                "variants": variants,
                "calls": spend.calls,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {args.target} and {payload.name}  ({spend.calls} calls)")
    return 0


def _cell(value: bool | None) -> str:
    return {True: "Y", False: ".", None: "?"}[value] if value in (True, False) else "?"


def _report(model, clean, variants, spend) -> str:
    lines = [
        "# Does the judge find a fault that was put there on purpose?",
        "",
        f"Judge `{model}`. One clean note, then one variant per criterion, each",
        "carrying exactly one deliberate fault. `Y` means the judge reported the",
        "fault present, `.` means absent, `?` means it did not answer.",
        "",
        "A criterion is doing its job when its own variant is `Y` on its own",
        "column and the clean note is `.` everywhere.",
        "",
        "| variant | " + " | ".join(czech.CRITERION_KEYS) + " |",
        "|---|" + "---|" * len(czech.CRITERION_KEYS),
        "| **clean** | " + " | ".join(_cell(clean.get(k)) for k in czech.CRITERION_KEYS) + " |",
    ]
    for criterion, answers in variants.items():
        cells = " | ".join(
            ("**" + _cell(answers.get(k)) + "**" if k == criterion else _cell(answers.get(k)))
            for k in czech.CRITERION_KEYS
        )
        lines.append(f"| {criterion} | {cells} |")

    caught = [c for c, a in variants.items() if a.get(c) is True]
    missed = [c for c, a in variants.items() if a.get(c) is False]
    unanswered = [c for c, a in variants.items() if a.get(c) is None]
    noisy = [c for c, a in variants.items() if sum(1 for v in a.values() if v is True) > 3]
    false_alarms = [k for k, v in clean.items() if v is True]

    lines += [
        "",
        "## What that says",
        "",
        f"- **Found its own fault:** {', '.join(caught) or 'none'}",
        f"- **Missed its own fault:** {', '.join(missed) or 'none'} "
        "-- these columns are not a result and should be published as unmeasured.",
        f"- **Did not answer:** {', '.join(unanswered) or 'none'}",
        f"- **Reported a fault in the clean note:** {', '.join(false_alarms) or 'none'} "
        "-- either the note is not as clean as intended, or the criterion fires on nothing.",
        f"- **Flagged more than three criteria at once:** {', '.join(noisy) or 'none'} "
        "-- a sign the judge is rating an impression rather than answering the question.",
        "",
        f"{spend.calls} judge calls.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
