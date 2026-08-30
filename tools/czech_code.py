"""Putting the notes to a panel of coders, and checking what comes back.

Two modes, and the difference between them is the whole method.

**Open coding is inductive and the coder is shown nothing.** No codebook, no
candidate list, no census, no model name, no score. QualReAI enforces the same
thing by forcing an empty codebook into the prompt and guarding it with three
regression tests, and its comment says why: a coder told what to look for finds
it. What comes back is whatever the coder saw, with a verbatim span for each code.

**Deductive coding applies a frozen codebook** and is asked at temperature 0 so
that it is reproducible and cacheable. Its output is one verdict per unit per
category, from four values -- present, absent, unclear, not-applicable -- and
``unclear`` is never folded into ``absent``. A coder that returns fewer verdicts
than there were units leaves the note marked incomplete rather than having its
silence read as absence.

**Every span is checked against the bytes it claims to quote.** A code whose span
is not in its unit is discarded before anything is counted, and the discard rate
is reported per coder. This is the gate the tool this study borrows from does not
have: there the span is free text, re-located in the browser by a four-tier fuzzy
search that falls back to matching the first forty characters, and a code whose
span cannot be found simply renders without a highlight. On a corpus of models
writing about models, an unchecked quotation is the most likely way to produce a
confident wrong answer.

**The panel is three coders from three places, and one of them is missing.** The
design called for Claude, ``gemini-3.1-pro-preview`` and one e-INFRA model, so
that no coder shared a vendor with more than one system in the corpus. The
Anthropic key in ``.env`` returns HTTP 401, so Claude could not be run as a coder
here. It is recorded as absent rather than replaced quietly: the substitute is a
second e-INFRA model, which raises the number of systems sharing a vendor with a
coder from two to four, and that is a real cost to the independence of the panel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import dotenv
import httpx

from tnb.scoring import czech_run, deepsy_run
from tnb.tasks import czech as czech_task
from tnb.tasks import deepsy as deepsy_task

sys.path.insert(0, str(Path(__file__).resolve().parent))

import czech_units  # noqa: E402  -- sibling tool, reached via the path above

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "local" / "codes-cache"
DEFAULT_TARGET = REPO / "local" / "czech-codes.jsonl"

#: Bumped whenever anything reaching a coder changes. Two versions are two
#: instruments and their rows are never added together.
CODE_PROMPT_VERSION = "czech-open-v1"

#: e-INFRA rate-limits per API key, not per model, and it is a personal academic
#: quota. Six concurrent requests drew 429 on a third of calls.
EINFRA_CONCURRENCY = 2
_EINFRA_SLOTS = threading.Semaphore(EINFRA_CONCURRENCY)

#: How many notes are in flight at once, across all backends. Raising this cannot
#: raise the load on e-INFRA, which the semaphore above pins at two no matter what
#: this says.
WORKERS = 8

#: Room for the answer, after the thinking. Measured rather than chosen: at 8192
#: two of the first 41 notes came back `MAX_TOKENS` with the JSON cut mid-object,
#: and the two were long ones -- the same clustering the judge's thinking budget
#: showed, where what goes missing is the longest material and dropping it would
#: bias a denominator in a direction nobody picked. A truncated answer is recorded
#: as a failure on both sides and the note is re-asked, never half-read.
ANSWER_TOKENS = 16384


@dataclass(frozen=True)
class Coder:
    """One member of the panel, and what it shares a vendor with."""

    name: str
    backend: str
    model: str
    #: Systems in the corpus written by the same vendor. Named, not hidden: a
    #: coder is not neutral about its own family and the estimate of how far it
    #: is not neutral needs to know which rows to look at.
    in_family: tuple[str, ...] = ()
    temperature: float = 0.0


PANEL = (
    Coder("A", "vertex", "gemini-3.1-pro-preview", in_family=("gemma4",)),
    Coder(
        "B",
        "einfra",
        "deepseek-v4-flash",
        in_family=("deepseek-v4-flash", "deepseek-v4-flash-thinking"),
    ),
)

#: Why the panel is two and not three, measured rather than decided.
#:
#: Every candidate for a third coder was tried on one note and failed for its own
#: reason. None of this was foreseeable from the model list, which is why the
#: benchmark exists: QualReAI's own model benchmark is five weeks old, runs on
#: interview snippets rather than notes, and validates only that the answer is
#: JSON -- so "recommended for coder" there means "returns valid JSON", not
#: "codes well".
REJECTED_CODERS = {
    "claude": "ANTHROPIC_API_KEY in .env returns HTTP 401. The only candidate "
    "sharing a vendor with no system in this corpus, so its loss costs the panel "
    "its one fully neutral member.",
    "kimi-k3": "Over six minutes for one coding call, and zero of eleven notes "
    "finished in fifteen minutes at two concurrent slots. At corpus scale that is "
    "roughly twelve hours. It had the best capability index on e-INFRA and the "
    "smallest family in the corpus, so this is a real loss and not a preference.",
    "glm-5.3-flash": "HTTP 400 from the endpoint on every attempt.",
    "qwen3.8-flash-next": "Answered in 37 seconds and the answer did not parse as JSON.",
    "gpt-oss-120b": "Works and is fast in open coding (36 s), but it is a system "
    "in this corpus and Jan asked for no GPT-named model. Not used.",
    "gemma4": "Works (111 s) but is Google's, and coder A is Gemini. Two thirds of "
    "the panel from one vendor is worse for independence than a panel of two.",
    "mistral-medium-3.5": "Did not return a deductive answer within ten minutes.",
}

MISSING_CODER = {
    "planned": 3,
    "actual": len(PANEL),
    "cost": (
        "With two coders a disagreement cannot be broken: there is no majority, so "
        "`partial` and `unique` collapse into one category and the judge has nothing "
        "to weigh. Agreement is still measurable; adjudication is not. This is "
        "QualReAI's own shipped configuration -- coder_count is 2 there -- but its "
        "documentation and this study's plan both called for three."
    ),
    "rejected": REJECTED_CODERS,
}

OPEN_SYSTEM = """Jsi výzkumník provádějící otevřené kódování v kvalitativní obsahové analýze.

Dostaneš klinickou poznámku ze sezení, rozřezanou na číslované významové celky. Jeden celek je jedno tvrzení.

U každého celku napiš, CO TO TVRZENÍ DĚLÁ — ne o čem je. Kód je krátký pojem, ne parafráze.

Pravidla:
- Kód má 2 až 5 slov, česky, podstatné jméno nebo dějové jméno. Nikdy víc než 5 slov.
- Ne každý celek potřebuje kód. Když celek nedělá nic, co by stálo za pojmenování, vrať pro něj prázdný seznam.
- Nesnaž se rozdat kódy rovnoměrně. Některé celky jsou bohaté, jiné prázdné.
- U každého kódu uveď `span`: doslovný úsek textu ZKOPÍROVANÝ z toho celku, znak po znaku. Nepřepisuj ho, nezkracuj, needituj. Když nemůžeš zkopírovat doslovný úsek, kód nedávej.
- U každého celku navíc uveď `splittable`: true, pokud ten celek obsahuje víc než jedno samostatné tvrzení.

Odpověz POUZE tímto JSON objektem, bez dalšího textu:
{"units": [{"unit_index": <číslo>, "splittable": <true|false>, "codes": [{"name": "<2-5 slov>", "description": "<jedna věta>", "span": "<doslovný úsek>", "confidence": <0.0-1.0>}]}]}"""

DEDUCTIVE_SYSTEM = """Jsi výzkumník aplikující hotový kódovací klíč v kvalitativní obsahové analýze.

Dostaneš klinickou poznámku ze sezení, rozřezanou na číslované významové celky, a seznam kategorií. Jeden celek je jedno tvrzení.

U KAŽDÉHO celku a KAŽDÉ kategorie odpověz JEDNÍM PÍSMENEM:
- "p" = present        — kategorie na ten celek sedí
- "a" = absent         — kategorie na ten celek nesedí
- "u" = unclear        — nedokážeš rozhodnout
- "n" = not-applicable — ten celek nedává příležitost na tu otázku vůbec odpovědět

"u" ani "n" nikdy neslévej do "a". Když nevíš, napiš "u".

Ke KAŽDÉ odpovědi "p" přidej do `s` doslovný úsek ZKOPÍROVANÝ z toho celku, znak po znaku. Bez doslovného úseku "p" nedávej.

Musíš vrátit záznam pro každý celek, který jsi dostal, i kdyby byly všechny odpovědi "a".

Odpověz POUZE tímto JSON objektem, bez dalšího textu a bez mezer navíc:
{"units":[{"i":<index celku>,"v":{"<klíč kategorie>":"<p|a|u|n>"},"s":{"<klíč kategorie>":"<doslovný úsek>"}}]}"""

#: The one-letter verdicts the compact format uses, and what they mean. The
#: format is compact because the long one was measured and did not work: 28 units
#: times 6 categories with a span field each ran a slow model past ten minutes on
#: a single note, which at corpus scale is days rather than hours.
LETTERS = {"p": "present", "a": "absent", "u": "unclear", "n": "not-applicable"}


def _section_label(section: str) -> str:
    """What a section is called in the note the coder is shown.

    SOAP's four have Czech headings the model itself wrote under; Deepsy's eleven
    are the application's own keys and have no Czech form here, so they are shown
    as they are rather than invented.
    """
    return czech_task.SECTION_LABELS.get(section, section.replace("_", " "))


def render_units(units: list[dict]) -> str:
    """The note as the coder sees it: numbered assertions, nothing else.

    No model name, no session id, no score, no other coder's output. Section
    labels stay, because a section is the context unit and a coder that cannot
    see whether it is reading the plan or the history is being asked a harder
    question than the one this study is about.
    """
    lines = []
    section = None
    for unit in units:
        if unit["section"] != section:
            section = unit["section"]
            label = _section_label(section)
            lines.append(f"\n## {label}")
        lines.append(f"[{unit['unit_index']}] {unit['text']}")
    return "\n".join(lines).strip()


def render_codebook(codebook: dict) -> str:
    out = []
    for key, entry in sorted(codebook.items()):
        out.append(f"- `{key}` — {entry['question']}")
        if entry.get("guidance"):
            out.append(f"    {entry['guidance']}")
    return "\n".join(out)


def build_prompt(units: list[dict], codebook: dict | None) -> str:
    if codebook:
        return (
            f"{DEDUCTIVE_SYSTEM}\n\nKATEGORIE:\n{render_codebook(codebook)}\n\n"
            f"POZNÁMKA:\n{render_units(units)}\n"
        )
    return f"{OPEN_SYSTEM}\n\nPOZNÁMKA:\n{render_units(units)}\n"


_JSON = re.compile(r"\{.*\}", re.S)


def parse_json(text: str) -> dict | None:
    """The object out of whatever the model wrapped it in.

    Models put JSON in prose, in code fences and after an apology. Returning None
    rather than an empty dict keeps a refusal distinguishable from a note the
    coder read and found nothing in -- which are different facts.
    """
    match = _JSON.search(text or "")
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0), strict=False)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


# --------------------------------------------------------------------------
# Backends


def _einfra_call(model: str, prompt: str, temperature: float) -> tuple[str, float, str]:
    base = os.environ["EINFRA_BASE_URL"].rstrip("/")
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": ANSWER_TOKENS,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {os.environ['EINFRA_API_TOKEN']}",
        "Content-Type": "application/json",
    }
    last = "no attempt made"
    for attempt in range(4):
        if attempt:
            time.sleep(6 * attempt)
        with _EINFRA_SLOTS:
            started = time.monotonic()
            try:
                response = httpx.post(
                    f"{base}/chat/completions", json=body, headers=headers, timeout=300
                )
            except httpx.TransportError as error:
                last = f"{type(error).__name__}: {error}"
                continue
            elapsed = time.monotonic() - started
        if response.status_code == 429 or response.status_code >= 500:
            last = f"HTTP{response.status_code}"
            continue
        if response.status_code != 200:
            return "", elapsed, f"HTTP{response.status_code}: {response.text[:200]}"
        payload = response.json()
        choice = payload["choices"][0]
        return choice["message"].get("content") or "", elapsed, ""
    return "", 0.0, last


_VERTEX_LOCK = threading.Lock()
_VERTEX: dict = {}


def _vertex_call(model: str, prompt: str, temperature: float) -> tuple[str, float, str]:
    from tnb import judge

    with _VERTEX_LOCK:
        if model not in _VERTEX:
            _VERTEX[model] = judge.Judge(
                judge.config_from_env(
                    model=model, thinking_budget=2048, answer_tokens=ANSWER_TOKENS
                )
            )
    answer = _VERTEX[model].ask(prompt)
    return answer.text, answer.latency_s, "" if answer.ok else (answer.error or "not ok")


def call(coder: Coder, prompt: str) -> tuple[str, float, str]:
    if coder.backend == "einfra":
        return _einfra_call(coder.model, prompt, coder.temperature)
    return _vertex_call(coder.model, prompt, coder.temperature)


# --------------------------------------------------------------------------
# Cache


def cache_path(coder: Coder, mode: str, system: str, session: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", coder.model)
    return CACHE / mode / slug / system / f"{session}.json"


def load_cached(path: Path, digest: str) -> dict | None:
    """A cached answer, but only if it answers the question being asked now.

    The prompt digest is part of the record, as the judge cache has recorded it
    since re-scoring a regenerated note reused the judgement of the text it
    replaced.
    """
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return record if record.get("prompt_sha256") == digest else None


# --------------------------------------------------------------------------
# Validation


@dataclass
class Tally:
    spans_checked: int = 0
    spans_discarded: int = 0
    units_expected: int = 0
    units_answered: int = 0
    notes: int = 0
    notes_incomplete: int = 0
    notes_failed: int = 0
    failures: list = field(default_factory=list)


def check_span(span: str, unit_text: str) -> bool:
    """Is this span actually in the text it claims to quote?

    Exact substring, after collapsing runs of whitespace on both sides. Nothing
    fuzzier: the entire point is to catch a coder that wrote a quotation instead
    of copying one, and a fuzzy match is exactly what would let that through.
    """
    if not span:
        return False
    tight = " ".join(span.split())
    return tight in " ".join(unit_text.split())


def rows_from_open(parsed: dict, units: list[dict], tally: Tally) -> list[dict]:
    by_index = {unit["unit_index"]: unit for unit in units}
    out = []
    for entry in parsed.get("units") or []:
        index = entry.get("unit_index")
        unit = by_index.get(index)
        if unit is None:
            continue
        tally.units_answered += 1
        for code in entry.get("codes") or []:
            span = str(code.get("span") or "")
            tally.spans_checked += 1
            valid = check_span(span, unit["text"])
            if not valid:
                tally.spans_discarded += 1
            out.append(
                {
                    "unit_index": index,
                    "section": unit["section"],
                    "code": str(code.get("name") or "").strip(),
                    "description": str(code.get("description") or "").strip(),
                    "span": span,
                    "span_valid": valid,
                    "confidence": code.get("confidence"),
                    "splittable": bool(entry.get("splittable")),
                }
            )
    return out


VALUES = ("present", "absent", "unclear", "not-applicable")


def rows_from_deductive(
    parsed: dict, units: list[dict], codebook: dict, tally: Tally
) -> list[dict]:
    by_index = {unit["unit_index"]: unit for unit in units}
    out = []
    for entry in parsed.get("units") or []:
        index = entry.get("i", entry.get("unit_index"))
        unit = by_index.get(index)
        if unit is None:
            continue
        tally.units_answered += 1
        verdicts = entry.get("v") or entry.get("verdicts") or {}
        spans = entry.get("s") or {}
        for key in codebook:
            raw = verdicts.get(key)
            value = LETTERS.get(str(raw).strip().lower()) if raw is not None else None
            if value is None and isinstance(raw, str) and raw.lower() in VALUES:
                value = raw.lower()
            span = str(spans.get(key) or "")
            valid = False
            if value == "present":
                tally.spans_checked += 1
                valid = check_span(span, unit["text"])
                if not valid:
                    tally.spans_discarded += 1
            out.append(
                {
                    "unit_index": index,
                    "section": unit["section"],
                    "category": key,
                    "value": value,
                    "span": span,
                    "span_valid": valid,
                }
            )
    return out


# --------------------------------------------------------------------------
# The run


def code_note(
    coder: Coder, candidate, units: list[dict], codebook: dict | None, mode: str, tally: Tally
) -> list[dict]:
    prompt = build_prompt(units, codebook)
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    path = cache_path(coder, mode, candidate.system_id, candidate.session_id)

    record = load_cached(path, digest)
    if record is None:
        text, elapsed, error = call(coder, prompt)
        record = {
            "coder": coder.name,
            "model": coder.model,
            "backend": coder.backend,
            "temperature": coder.temperature,
            "mode": mode,
            "prompt_version": CODE_PROMPT_VERSION,
            "prompt_sha256": digest,
            "system_id": candidate.system_id,
            "session_id": candidate.session_id,
            "latency_s": round(elapsed, 3),
            "error": error,
            "answer": text,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")

    tally.notes += 1
    tally.units_expected += len(units)
    if record.get("error"):
        tally.notes_failed += 1
        tally.failures.append(
            {
                "coder": coder.name,
                "system_id": candidate.system_id,
                "session_id": candidate.session_id,
                "error": record["error"][:200],
            }
        )
        return []

    parsed = parse_json(record["answer"])
    if parsed is None:
        tally.notes_failed += 1
        tally.failures.append(
            {
                "coder": coder.name,
                "system_id": candidate.system_id,
                "session_id": candidate.session_id,
                "error": "answer did not parse as JSON",
            }
        )
        return []

    before = tally.units_answered
    if codebook:
        rows = rows_from_deductive(parsed, units, codebook, tally)
    else:
        rows = rows_from_open(parsed, units, tally)
    if tally.units_answered - before < len(units):
        tally.notes_incomplete += 1

    stamp = {
        "coder": coder.name,
        "coder_model": coder.model,
        "mode": mode,
        "prompt_version": CODE_PROMPT_VERSION,
        "prompt_sha256": digest,
        "temperature": coder.temperature,
        "system_id": candidate.system_id,
        "session_id": candidate.session_id,
    }
    return [{**stamp, **row} for row in rows]


#: One verdict is one (coder, model, session, unit, category). Two rows with that
#: key are the same answer written twice, never two answers.
ROW_KEY = ("coder", "system_id", "session_id", "unit_index", "category")


def _write_rows(target: Path, rows: list[dict]) -> tuple[int, int]:
    """Merge this run's rows into the file, and refuse to count anything twice.

    **This is a repair, and the bug it repairs reached a published number.** The
    file used to be opened in append mode, on the reasoning that ``results/`` is
    append-only and this should match it. It should not: ``results/`` appends one
    row per scoring run and every row there is a distinct measurement, whereas
    two runs over the same notes here produce the same verdicts again. A partial
    rebuild followed by a full run left 13,716 of 53,796 rows duplicated -- a
    quarter of the file -- and the sentence counts printed in the briefing were
    inflated by exactly that. The rates survived, because a duplicate doubles a
    numerator and its denominator together; the counts did not, and neither did
    the weight each model carried in a figure averaged over all of them.

    Existing rows are read back and keyed, this run's rows overwrite their own
    keys, and how many were replaced is returned so the caller can print it. An
    older answer to the same question is not a second measurement: it is the same
    measurement, and keeping both weights one note twice.
    """
    merged: dict[tuple, dict] = {}
    if target.is_file():
        with target.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                merged[tuple(row.get(name) for name in ROW_KEY)] = row
    before = len(merged)
    for row in rows:
        merged[tuple(row.get(name) for name in ROW_KEY)] = row
    with target.open("w", encoding="utf-8") as handle:
        for row in merged.values():
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(merged), before + len(rows) - len(merged)


#: Every track this can code, with the loader that reaches its sessions and the
#: assembler that turns a generation directory into a note. The same shape as
#: ``czech_variance.CRITERIA_TRACKS``, and for the reason its docstring gives: a
#: track that loads the wrong sessions pairs a note with a transcript that is not
#: its own, and nothing downstream notices.
TRACKS = {
    czech_task.NAME_REAL: (czech_task.load_real, czech_run.from_generations),
    czech_task.NAME_TRANSLATED: (czech_task.load_translated, czech_run.from_generations),
    deepsy_task.NAME_REAL: (czech_task.load_real, deepsy_run.from_generations),
    deepsy_task.NAME_TRANSLATED: (czech_task.load_translated, deepsy_run.from_generations),
}


def _candidates(track: str):
    """The notes of one track, however that track stores them.

    A SOAP note is one file; a Deepsy note is three, and is assembled or refused
    as a whole. Raising on an unknown track rather than defaulting: a silent
    default here would code one corpus and label it another, which is the one
    mistake nothing further down could catch.
    """
    if track not in TRACKS:
        raise ValueError(f"{track} is not a track this codes. Known: {', '.join(TRACKS)}")
    loader, assemble = TRACKS[track]
    return list(assemble(loader(), task_name=track))


def run(
    track: str,
    sessions: list[str] | None,
    codebook: dict | None,
    mode: str,
    target: Path,
) -> dict:
    candidates = [
        candidate
        for candidate in _candidates(track)
        if sessions is None or candidate.session_id in sessions
    ]
    units_by_note = {
        (candidate.system_id, candidate.session_id): czech_units.split_note(candidate.note)
        for candidate in candidates
    }

    tallies = {coder.name: Tally() for coder in PANEL}
    rows: list[dict] = []
    lock = threading.Lock()

    def work(item):
        coder, candidate = item
        units = units_by_note[(candidate.system_id, candidate.session_id)]
        produced = code_note(coder, candidate, units, codebook, mode, tallies[coder.name])
        with lock:
            rows.extend(produced)

    # One pool per backend, run at the same time.
    #
    # A single pool starves the fast backend. e-INFRA is pinned at two concurrent
    # requests by the semaphore, so with the jobs interleaved most workers sit
    # blocked on that semaphore holding an e-INFRA job, and the Vertex coder --
    # which has no such limit -- waits behind them for a worker. Measured: the
    # Vertex coder produced nothing at all for several minutes while two e-INFRA
    # calls were in flight. Splitting the queues lets each backend run at its own
    # ceiling and makes the wall clock the slower of the two rather than the sum.
    def drain(items, workers):
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(work, items))

    by_backend: dict[str, list] = {}
    for coder in PANEL:
        by_backend.setdefault(coder.backend, []).extend(
            (coder, candidate) for candidate in candidates
        )

    with ThreadPoolExecutor(max_workers=max(1, len(by_backend))) as outer:
        list(
            outer.map(
                lambda item: drain(item[1], WORKERS if item[0] != "einfra" else EINFRA_CONCURRENCY),
                by_backend.items(),
            )
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    written, duplicates = _write_rows(target, rows)

    return {
        "track": track,
        "mode": mode,
        "prompt_version": CODE_PROMPT_VERSION,
        "notes": len(candidates),
        "rows_in_file": written,
        "rows_replaced": duplicates,
        "missing_coder": MISSING_CODER,
        "panel": [
            {
                "coder": coder.name,
                "model": coder.model,
                "backend": coder.backend,
                "temperature": coder.temperature,
                "in_family": list(coder.in_family),
            }
            for coder in PANEL
        ],
        "coders": {
            name: {
                "notes": tally.notes,
                "notes_failed": tally.notes_failed,
                "notes_incomplete": tally.notes_incomplete,
                "units_expected": tally.units_expected,
                "units_answered": tally.units_answered,
                "spans_checked": tally.spans_checked,
                "spans_discarded": tally.spans_discarded,
                "span_discard_rate": (
                    round(tally.spans_discarded / tally.spans_checked, 4)
                    if tally.spans_checked
                    else None
                ),
                "failures": tally.failures[:20],
            }
            for name, tally in tallies.items()
        },
    }


def main() -> None:
    dotenv.load_dotenv(REPO / ".env")
    parser = argparse.ArgumentParser(description="Put the Czech notes to the coder panel.")
    parser.add_argument("--track", default=czech_task.NAME_REAL)
    parser.add_argument("--sessions", nargs="*", default=None)
    parser.add_argument("--codebook", type=Path, default=None)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--report", type=Path, default=REPO / "local" / "czech-coding-run.json")
    args = parser.parse_args()

    codebook = None
    mode = "open"
    if args.codebook:
        codebook = json.loads(args.codebook.read_text(encoding="utf-8"))["categories"]
        mode = "deductive"

    summary = run(args.track, args.sessions, codebook, mode, args.target)
    args.report.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.target} and {args.report}")
    for name, stats in summary["coders"].items():
        print(
            f"  coder {name}: {stats['notes']} notes, {stats['notes_failed']} failed, "
            f"{stats['notes_incomplete']} incomplete, units "
            f"{stats['units_answered']}/{stats['units_expected']}, spans discarded "
            f"{stats['spans_discarded']}/{stats['spans_checked']}"
        )


if __name__ == "__main__":
    main()
