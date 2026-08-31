"""Which calques, not how many. A diagnostic, never a score.

`calque` is the worst column in every Czech measurement this project has made
and the one nobody can act on, because the criterion answers yes or no. Out of
2 476 stored judgements, 2 455 are the bare word. Twenty-one leaked the judge's
reasoning past its instruction and those name actual expressions -- an accident,
not a measurement, and the only examples that exist.

So this asks the other question: of the notes a judge already marked, which
expressions are they, and what should stand there in Czech instead.

**It is not comparable with anything and produces no score.** Different prompt,
different question, its own file. Nothing it writes reaches `results/`, the
leaderboard, or any table in the briefing. A number from here may not be put
beside a number from the criteria.

**The list is one model's opinion and the frequency is the trustworthy part.**
A judge flagged `ambivalence`, which is ordinary Czech clinical vocabulary; a
single item can be wrong the same way. An expression named across many notes and
many models is evidence about the models, and an expression named once is
evidence about the judge.

**Only notes already marked are asked about.** Asking about a note the judge
said was clean would be asking it to disagree with itself, and this is a
diagnostic of what it found rather than a second opinion on whether it found it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import dotenv

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import czech_code  # noqa: E402

from tnb.scoring import czech_run, deepsy_run  # noqa: E402
from tnb.tasks import czech as czech_task  # noqa: E402

DEFAULT_TARGET = REPO / "local" / "czech-calques.json"
CACHE = REPO / "local" / "calque-cache"
SCORES = REPO / "scores"

#: Vertex, not e-INFRA. The e-INFRA key is one person's academic allocation and
#: this run has no reason to spend it: the same model already read every one of
#: these notes when it scored them.
CODER = czech_code.PANEL[0]

#: Which tracks to look at, and how a note is assembled for each.
TRACKS = {
    czech_task.NAME_REAL: (czech_task.load_real, czech_run.from_generations),
    czech_task.NAME_TRANSLATED: (czech_task.load_translated, czech_run.from_generations),
    "deepsy-real": (czech_task.load_real, deepsy_run.from_generations),
    "deepsy-translated": (czech_task.load_translated, deepsy_run.from_generations),
}

PROMPT_VERSION = "czech-calque-list-v1"

PROMPT = """Níže je klinický zápis psaný česky jazykovým modelem.

Jiný model už u něj označil, že obsahuje kalk — výraz utvořený doslovným
překladem z angličtiny. Tvůj úkol je vypsat, o které výrazy jde.

Kalk je například „pres“ tam, kde se česky řekne „tlak“, nebo „historie
kouření“ tam, kde se česky řekne „kuřácká anamnéza“. NEPATŘÍ sem anglické
slovo ponechané v původní podobě — to je jiná vada. A NEPATŘÍ sem odborný
termín, který se v české klinické praxi běžně používá (ambivalence,
reaktance, afekt, remise); ty jsou správně.

Odpověz POUZE tímto JSON, bez čehokoli dalšího:
{{"kalky": [{{"vyraz": "...", "cesky": "...", "proc": "..."}}]}}

- vyraz: doslovně, přesně jak stojí v zápisu
- cesky: co by tam mělo stát místo toho
- proc: nejvýš deset slov

Když žádný kalk nenajdeš, vrať {{"kalky": []}}.

ZÁPIS:
{note}
"""


def marked_notes() -> dict[tuple[str, str, str], set[str]]:
    """Every (track, system, session) at least one judge marked as containing one.

    Read from the score cache rather than from the rows: a row carries the
    share, and what is wanted here is which individual notes the answer was yes
    for.
    """
    found: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for path in SCORES.rglob("czech.calque.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not (record.get("answer") or "").strip().lower().startswith("ano"):
            continue
        session = record.get("session_id") or ""
        if not session.startswith(("cz-r-", "cz-t-")):
            continue
        deepsy = "deepsy" in str(path)
        real = session.startswith("cz-r-")
        track = (
            ("deepsy-real" if real else "deepsy-translated")
            if deepsy
            else (czech_task.NAME_REAL if real else czech_task.NAME_TRANSLATED)
        )
        found[(track, record["system_id"], session)].add(record["judge_model"])
    return found


def notes_for(track: str) -> dict[tuple[str, str], str]:
    """The text of every note on a track, keyed by (system, session)."""
    loader, assemble = TRACKS[track]
    out = {}
    for candidate in assemble(loader(), task_name=track):
        note = candidate.note
        text = "\n\n".join(f"## {section}\n{body}" for section, body in note.items() if body)
        out[(candidate.system_id, candidate.session_id)] = text
    return out


def ask(track: str, system: str, session: str, text: str) -> dict:
    """One note to the judge, cached on the prompt that was actually sent."""
    prompt = PROMPT.format(note=text)
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    path = CACHE / track / re.sub(r"[^A-Za-z0-9._-]+", "-", system) / f"{session}.json"

    record = czech_code.load_cached(path, digest)
    if record is None:
        answer, elapsed, error = czech_code.call(CODER, prompt)
        record = {
            "track": track,
            "system_id": system,
            "session_id": session,
            "judge_model": CODER.model,
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": digest,
            "answer": answer,
            "error": error,
            "latency_s": round(elapsed, 3),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def parse(record: dict) -> list[dict] | None:
    """The list out of the answer, or None if the answer was not one.

    None and an empty list are different: the first is a note this run failed
    on and the second is a note the judge looked at and named nothing in. They
    are counted separately, because folding a failure into "found nothing"
    is the shape this repository forbids.
    """
    if record.get("error"):
        return None
    payload = czech_code.parse_json(record.get("answer") or "")
    if payload is None or not isinstance(payload.get("kalky"), list):
        return None
    out = []
    for item in payload["kalky"]:
        if isinstance(item, dict) and str(item.get("vyraz", "")).strip():
            out.append(
                {
                    "vyraz": str(item["vyraz"]).strip(),
                    "cesky": str(item.get("cesky", "")).strip(),
                    "proc": str(item.get("proc", "")).strip()[:120],
                }
            )
    return out


def main() -> int:
    dotenv.load_dotenv(REPO / ".env")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--track", action="append", choices=sorted(TRACKS))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    wanted = set(args.track or TRACKS)
    marked = {key: judges for key, judges in marked_notes().items() if key[0] in wanted}
    print(f"{len(marked)} zápisů, které aspoň jeden soudce označil")

    texts: dict[str, dict[tuple[str, str], str]] = {}
    jobs = []
    for track, system, session in sorted(marked):
        if track not in texts:
            texts[track] = notes_for(track)
        text = texts[track].get((system, session))
        if text:
            jobs.append((track, system, session, text))
    print(f"{len(jobs)} z nich se podařilo sestavit\n")

    done = 0
    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for record in pool.map(lambda j: ask(*j), jobs):
            records.append(record)
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(jobs)}")

    counts: Counter[str] = Counter()
    by_model: dict[str, Counter[str]] = defaultdict(Counter)
    suggestions: dict[str, Counter[str]] = defaultdict(Counter)
    failed = empty = 0
    for record in records:
        items = parse(record)
        if items is None:
            failed += 1
            continue
        if not items:
            empty += 1
        for item in items:
            key = item["vyraz"].lower()
            counts[key] += 1
            by_model[key][record["system_id"]] += 1
            if item["cesky"]:
                suggestions[key][item["cesky"]] += 1

    payload = {
        "what_this_is": __doc__.strip().split("\n\n")[0],
        "not_a_score": (
            "A different prompt asking a different question. Comparable with nothing, "
            "reaches no table, and a figure from here may not be put beside a criterion."
        ),
        "judge": CODER.model,
        "prompt_version": PROMPT_VERSION,
        "notes_asked": len(jobs),
        "notes_unparsed": failed,
        "notes_naming_nothing": empty,
        "distinct_expressions": len(counts),
        "expressions": [
            {
                "vyraz": word,
                "notes": count,
                "models": len(by_model[word]),
                "cesky": [c for c, _n in suggestions[word].most_common(3)],
                "by_model": dict(by_model[word].most_common()),
            }
            for word, count in counts.most_common()
        ],
    }
    args.target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nwrote {args.target}")
    print(
        f"  {len(counts)} různých výrazů; {failed} odpovědí se nepodařilo přečíst, "
        f"{empty} zápisů, kde soudce nejmenoval nic"
    )
    print(f"\n{'výraz':34s} {'zápisů':>7s} {'modelů':>7s}  česky")
    for entry in payload["expressions"][:30]:
        czech = "; ".join(entry["cesky"][:2])
        print(f"  {entry['vyraz'][:32]:32s} {entry['notes']:7d} {entry['models']:7d}  {czech[:50]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
