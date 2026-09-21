"""Translate AnnoMI conversations into Czech with a translator that is a recorded instrument.

The Czech half of a paired EN/CS benchmark is only a paired design if the
translation is part of the instrument rather than a step somebody once ran. Ten
Czech translations already exist in this project with no record of the model,
the prompt or the settings behind them, which is why decision D4 of protocol
2.1.0 supersedes them: a translation without provenance cannot carry a language
comparison, because a difference found between the languages could be a
difference between translators (audit A11).

So this tool refuses to translate until an instrument is recorded, and it
records one only from a measured check:

1. `select` translates a sample of turns with each candidate model, has a
   separate back-translator put them back into English, and measures the
   result: how close the round trip lands (chrF against the original), whether
   the turn structure survived one for one, and whether anything came back
   untranslated. It writes the measurements and decides nothing.
2. `record` writes the instrument -- provider, model, settings, prompt digest,
   the digest of the check it rests on -- for a model that check actually
   measured. It refuses a judge model of the pilot, and it refuses a
   back-translator that is the candidate itself: a model that mangles
   consistently would otherwise score its own damage as agreement.
3. `translate` runs the recorded instrument over whole conversations and
   verifies the structure it gets back. A conversation whose turns do not map
   one for one is recorded as a failure, never repaired into a pair.
4. `review-sheet` and `import-review` carry the human meaning review: a sample
   of turns with their translation and back-translation goes out, verdicts come
   back, and the verdicts are recorded per turn.

**A measurement is a screen, not a decision.** chrF over a round trip is an
indirect measure of meaning: a fluent mistranslation that back-translates
neatly scores well, and a good translation of an idiom scores badly. It is here
to rank candidates and to catch structural damage, and the human review is what
says whether the meaning survived.

**What is written where.** AnnoMI text and every translation of it stay under
the gitignored `local/`, because this repository never vendors a corpus. The
tracked records under `research/gen2/translation/` carry counts, digests and
model identity, and no transcript text at all.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RECORDS = REPO / "research" / "gen2" / "translation"
WORKSPACE = REPO / "local" / "gen2-translation"
INSTRUMENT_PATH = RECORDS / "instrument.json"

#: The line format both directions must come back in. Numbered, so a dropped or
#: merged turn is visible rather than silently changing what a turn says.
LINE = re.compile(r"^\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(.*\S)\s*$")
SPEAKERS = ("therapist", "client")

#: A Czech translation that still reads as its English source is not a
#: translation. Measured as chrF of the output against its own input: identical
#: text scores 1.0, and above this a turn is reported as untranslated.
UNTRANSLATED_ABOVE = 0.90
#: "Mm-hmm." and "Kia ora." come back unchanged from a faithful translator, and
#: the first live check failed two models for exactly that. A turn that came
#: back unchanged is a failure only when it had this many words, enough English
#: to be sure it should have changed; shorter ones are listed, not failed, and
#: the human meaning review sees them.
UNTRANSLATED_MIN_WORDS = 3
#: A whole conversation in Czech takes far longer than a note; the provider's
#: default timeout is for a note.
TIMEOUT_S = 600
CHECK_VERSION = "back-translation-check-v2"
#: A round trip lands near, not on, its original. Reported, never enforced:
#: what this number means for meaning is exactly what the human review asks.
ROUND_TRIP_FLOOR = 0.50


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


# --- what a round trip is worth ------------------------------------------------


def _grams(text: str, n: int) -> Counter:
    clean = re.sub(r"\s+", " ", text.strip().lower())
    return Counter(clean[i : i + n] for i in range(len(clean) - n + 1))


def chrf(candidate: str, reference: str, *, order: int = 6, beta: float = 2.0) -> float:
    """Character n-gram F-score (Popovic 2015), averaged over orders 1..order.

    Chosen over a word metric because Czech inflects: `terapeut` and
    `terapeutovi` share no word token and nearly all their characters. Chosen
    over an embedding metric because this has to be deterministic, offline and
    explainable -- the number is counted, not modelled.
    """
    if not candidate.strip() or not reference.strip():
        return 0.0
    precisions, recalls = [], []
    for n in range(1, order + 1):
        c, r = _grams(candidate, n), _grams(reference, n)
        overlap = sum((c & r).values())
        if sum(c.values()):
            precisions.append(overlap / sum(c.values()))
        if sum(r.values()):
            recalls.append(overlap / sum(r.values()))
    if not precisions or not recalls:
        return 0.0
    p = sum(precisions) / len(precisions)
    r = sum(recalls) / len(recalls)
    if p + r == 0:
        return 0.0
    return (1 + beta**2) * p * r / (beta**2 * p + r)


# --- the transcript, in and out ------------------------------------------------


@dataclass(frozen=True)
class Turn:
    index: int
    speaker: str
    text: str


def numbered(turns: list[Turn]) -> str:
    return "\n".join(f"{t.index} | {t.speaker} | {t.text}" for t in turns)


def parse_numbered(text: str) -> list[Turn]:
    """Every line that is a turn. Anything else a model wrote is dropped here
    and shows up as a structural failure, not as a turn with a preamble in it."""
    out = []
    for line in text.splitlines():
        match = LINE.match(line)
        if match:
            out.append(Turn(int(match.group(1)), match.group(2).strip().lower(), match.group(3)))
    return out


PROMPT_VERSION = "gen2-translate-v1"
PROMPT = {
    "en->cs": (
        "Translate this psychotherapy session transcript from English into Czech.\n\n"
        "Rules:\n"
        "- Output exactly one line per input line, in the same order, in the same\n"
        "  format: number | speaker | text. Keep the number and the speaker unchanged.\n"
        "- Never merge, split, add, drop or reorder a line, even when Czech would\n"
        "  read better that way.\n"
        "- Translate what was said, including hesitation, repetition and unfinished\n"
        "  sentences. Do not tidy the speech up, summarise it, or explain it.\n"
        "- Keep the register: a client speaks the way a client speaks.\n"
        "- Write nothing except those lines.\n\n"
        "Transcript:\n{body}"
    ),
    "cs->en": (
        "Translate this psychotherapy session transcript from Czech into English.\n\n"
        "Rules:\n"
        "- Output exactly one line per input line, in the same order, in the same\n"
        "  format: number | speaker | text. Keep the number and the speaker unchanged.\n"
        "- Translate literally enough that a reader can tell what the Czech says.\n"
        "  Do not improve, tidy or complete it.\n"
        "- Write nothing except those lines.\n\n"
        "Transcript:\n{body}"
    ),
}


def build_prompt(turns: list[Turn], direction: str) -> str:
    if direction not in PROMPT:
        raise SystemExit(f"Unknown direction {direction!r}")
    return PROMPT[direction].format(body=numbered(turns))


def prompt_digest(direction: str) -> str:
    return digest(
        {"version": PROMPT_VERSION, "direction": direction, "template": PROMPT[direction]}
    )


# --- what came back ------------------------------------------------------------


@dataclass
class Check:
    """What a translation of one conversation is and is not.

    `problems` is the list that decides: a conversation with any problem is not
    a translation of the original, and nothing downstream may pair it.
    """

    turns_in: int
    turns_out: int
    problems: list[str] = field(default_factory=list)
    untranslated: list[int] = field(default_factory=list)
    unchanged_short: list[int] = field(default_factory=list)
    length_ratio: float = 0.0

    @property
    def ok(self) -> bool:
        return not self.problems

    def record(self) -> dict:
        return {
            "turns_in": self.turns_in,
            "turns_out": self.turns_out,
            "problems": list(self.problems),
            "untranslated_turns": len(self.untranslated),
            "unchanged_short_turns": list(self.unchanged_short),
            "length_ratio": round(self.length_ratio, 4),
            "ok": self.ok,
        }


def check_structure(source: list[Turn], result: list[Turn]) -> Check:
    """One for one, or not a translation. Every failure is named, none repaired."""
    check = Check(turns_in=len(source), turns_out=len(result))
    if len(result) != len(source):
        check.problems.append(f"turn count {len(result)} does not match {len(source)}")
    by_index = {t.index: t for t in result}
    if len(by_index) != len(result):
        check.problems.append("a turn number came back more than once")
    for turn in source:
        got = by_index.get(turn.index)
        if got is None:
            check.problems.append(f"turn {turn.index} is missing")
            continue
        if got.speaker != turn.speaker:
            check.problems.append(f"turn {turn.index} changed speaker")
        if not got.text.strip():
            check.problems.append(f"turn {turn.index} came back empty")
        elif chrf(got.text, turn.text) >= UNTRANSLATED_ABOVE:
            if len(turn.text.split()) >= UNTRANSLATED_MIN_WORDS:
                check.untranslated.append(turn.index)
            else:
                check.unchanged_short.append(turn.index)
    if check.untranslated:
        check.problems.append(f"{len(check.untranslated)} turn(s) came back untranslated")
    source_chars = sum(len(t.text) for t in source)
    check.length_ratio = sum(len(t.text) for t in result) / source_chars if source_chars else 0.0
    return check


def round_trip(source: list[Turn], back: list[Turn]) -> dict:
    """How near the round trip landed, per turn and over the conversation.

    Reported with the count of turns that could be compared at all, because a
    round trip that lost half the turns must not average over the half it kept.
    """
    by_index = {t.index: t for t in back}
    scores = [chrf(by_index[t.index].text, t.text) for t in source if t.index in by_index]
    return {
        "compared_turns": len(scores),
        "of_turns": len(source),
        "mean_chrf": round(sum(scores) / len(scores), 4) if scores else None,
        "worst_chrf": round(min(scores), 4) if scores else None,
        "below_floor": sum(1 for s in scores if s < ROUND_TRIP_FLOOR),
        "floor": ROUND_TRIP_FLOOR,
    }


# --- the instrument ------------------------------------------------------------


def load_instrument(path: Path = INSTRUMENT_PATH) -> dict:
    if not path.exists():
        raise SystemExit(
            "No translation instrument is recorded. Run `select` to measure candidates "
            "and `record` to write the one chosen, before translating anything (D4)."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def instrument_record(
    *,
    provider: str,
    model: str,
    settings: dict,
    check: dict,
    check_digest: str,
    judges: list[str],
    reason: str,
) -> dict:
    """The record decision D4 asks for, refusing what it may not contain."""
    measured = {row["model"] for row in check["candidates"]}
    if model not in measured:
        raise SystemExit(
            f"{model} was not measured by this check. A translator is recorded from a "
            f"measurement, not chosen beside one. Measured: {', '.join(sorted(measured))}."
        )
    if model in judges:
        raise SystemExit(f"{model} judges this pilot; a judge may not also be its translator.")
    if model == check["back_translator"]["model"]:
        raise SystemExit(
            "The back-translator measured this candidate; a model cannot check its own "
            "translation, because consistent damage would come back as agreement."
        )
    row = next(row for row in check["candidates"] if row["model"] == model)
    if row.get("failed") or row["round_trip"] is None:
        why = (row.get("failed") or {}).get("error", "no round trip")
        raise SystemExit(
            f"{model}: its measurement failed ({why}); a translator is recorded from a "
            "measurement that completed."
        )
    if not row["structure"]["ok"]:
        raise SystemExit(
            f"{model} did not return the sample one turn for one turn "
            f"({'; '.join(row['structure']['problems'])}); it cannot be the instrument."
        )
    return {
        "version": "translation-instrument-v1",
        "recorded_at": now(),
        "direction": "en->cs",
        "provider": provider,
        "model": model,
        "settings": settings,
        "prompt_version": PROMPT_VERSION,
        "prompt_digest": prompt_digest("en->cs"),
        "back_translation_check": {
            "digest": check_digest,
            "recorded_at": check["recorded_at"],
            "back_translator": check["back_translator"],
            "sample_turns": check["sample"]["turns"],
            "measurement": next(row for row in check["candidates"] if row["model"] == model),
        },
        "not_a_judge_of": sorted(judges),
        "reason": reason,
        "status": "recorded_before_use",
        "supersedes": "the ten undocumented Czech translations of the earlier Gen-2 draft, "
        "which are retained as historical artifacts and are not used as pairs (D4)",
    }


# --- the calls -----------------------------------------------------------------


class ModelFailure(Exception):
    """A model returned nothing usable. The caller records it; nothing repairs it."""


def _provider(provider_name: str):
    from dataclasses import replace

    from dotenv import load_dotenv

    from tnb.config import load_policy

    load_dotenv(REPO / ".env")  # the credential lives where `tnb` reads it, never in a tracked file
    provider = load_policy().get(provider_name)
    return replace(provider, generation=replace(provider.generation, timeout_s=TIMEOUT_S))


def call_settings(provider_name: str) -> dict:
    """The settings every call of a check or a run is made with, recorded beside it.

    A whole conversation in Czech does not fit the budget a note does, and a
    reasoning model spends part of any budget thinking, so the translator gets
    the provider's escalation budget from the first call. The budget is part
    of the instrument: the same model under a smaller one truncates.
    """
    generation = _provider(provider_name).generation
    return {
        "temperature": generation.temperature,
        "max_tokens": max(generation.max_tokens, generation.escalate_max_tokens),
        "timeout_s": generation.timeout_s,
    }


def _complete(provider_name: str, model: str, prompt: str, max_tokens: int | None = None) -> str:
    """One call, through the same client every other model call here uses."""
    from tnb.providers import openai_compatible as client

    answer = client.complete(_provider(provider_name), model, prompt, max_tokens=max_tokens)
    if not answer.ok or not answer.text.strip():
        raise ModelFailure(f"{model} returned no usable answer: {answer.error or 'empty'}")
    return answer.text


def translate_turns(turns: list[Turn], direction: str, call) -> list[Turn]:
    return parse_numbered(call(build_prompt(turns, direction)))


# --- commands ------------------------------------------------------------------


def cmd_select(args, call=None, settings=None) -> dict:
    """Measure every candidate over the same sample, and decide nothing.

    A candidate that returns nothing usable, or whose back-translation does
    not, is a row that says so: the check is a measurement of every candidate,
    and a crash on the first would have measured none of the others.
    """
    sample = read_turns(args.sample)
    if call is None:
        settings = call_settings(args.provider)
        budget = settings["max_tokens"]
        call = lambda model, prompt: _complete(args.provider, model, prompt, budget)  # noqa: E731
    settings = settings or {}
    back = args.back_translator
    last: dict[str, str] = {}

    def remembering(model: str, prompt: str) -> str:
        last["text"] = call(model, prompt)
        return last["text"]

    rows = []
    for model in args.candidates:
        if model == back:
            raise SystemExit(f"{model} cannot be both a candidate and the back-translator")
        try:
            translated = translate_turns(sample, "en->cs", lambda p, m=model: remembering(m, p))
        except ModelFailure as failure:
            rows.append(
                {
                    "model": model,
                    "structure": None,
                    "round_trip": None,
                    "failed": {"stage": "forward", "error": str(failure)},
                }
            )
            continue
        forward = check_structure(sample, translated)
        if not forward.ok:
            write_raw(args.workspace / f"selection-{model}.failed.txt", last["text"])
        row = {"model": model, "structure": forward.record(), "round_trip": None}
        if forward.ok:
            try:
                english = translate_turns(translated, "cs->en", lambda p: remembering(back, p))
            except ModelFailure as failure:
                row["failed"] = {"stage": "back", "error": str(failure)}
                rows.append(row)
                continue
            row["round_trip"] = round_trip(sample, english)
            write_local(args.workspace / f"selection-{model}.json", translated, english)
        rows.append(row)
    check = {
        "version": CHECK_VERSION,
        "recorded_at": now(),
        "direction": "en->cs",
        "prompt_version": PROMPT_VERSION,
        "prompt_digests": {d: prompt_digest(d) for d in PROMPT},
        "provider": args.provider,
        "settings": settings,
        "back_translator": {"provider": args.provider, "model": back},
        "sample": {
            "source": args.sample.name,
            "turns": len(sample),
            "digest": digest([(t.index, t.speaker, t.text) for t in sample]),
        },
        "metric": {
            "name": "chrF",
            "order": 6,
            "beta": 2.0,
            "means": "character n-gram agreement of the round trip with the original; "
            "an indirect screen for meaning, not a measurement of it",
        },
        "structure_rule": {
            "untranslated_above": UNTRANSLATED_ABOVE,
            "untranslated_min_words": UNTRANSLATED_MIN_WORDS,
            "means": "a turn that came back unchanged fails only with at least this many "
            "words; shorter unchanged turns are listed for the human review",
        },
        "candidates": rows,
    }
    return check


def cmd_translate(args, call=None) -> dict:
    """Run the recorded instrument, and record what it produced and what failed."""
    instrument = load_instrument(args.instrument)
    if call is None:
        budget = (instrument.get("settings") or {}).get("max_tokens")
        call = lambda prompt: _complete(  # noqa: E731
            instrument["provider"], instrument["model"], prompt, budget
        )
    records = []
    for path in sorted(args.conversations):
        source = read_turns(path)
        try:
            translated = translate_turns(source, "en->cs", call)
        except ModelFailure as failure:
            check = Check(turns_in=len(source), turns_out=0, problems=[str(failure)])
        else:
            check = check_structure(source, translated)
        if check.ok:
            write_local(args.workspace / f"{path.stem}.cs.json", translated, None)
        records.append(
            {
                "conversation": path.stem,
                "source_digest": digest([(t.index, t.speaker, t.text) for t in source]),
                "translation_digest": digest([(t.index, t.speaker, t.text) for t in translated])
                if check.ok
                else None,
                "check": check.record(),
                "translated_at": now(),
            }
        )
    return {
        "version": "translations-v1",
        "instrument_digest": digest(instrument),
        "model": instrument["model"],
        "provider": instrument["provider"],
        "prompt_digest": instrument["prompt_digest"],
        "conversations": records,
        "usable": sorted(r["conversation"] for r in records if r["check"]["ok"]),
        "failed": sorted(r["conversation"] for r in records if not r["check"]["ok"]),
        "rule": "Only a conversation whose turns map one for one is a translation of its "
        "original; a failed one is recorded and never paired.",
    }


def translation_groups(translations: dict, reviews: list[dict]) -> dict:
    """The EN/CS pairs a language contrast may join on, and the ones it may not.

    A pair needs two things, and paired filenames are neither (audit A11): the
    turns mapped one for one, and a person who read a sample and said the
    meaning survived. A conversation missing either is listed with the reason
    and gets no group, so `Case.translation_group` cannot be filled from here
    for a pair nobody established.
    """
    by_conversation = {r["conversation"]: r for r in reviews}
    established, withheld = {}, []
    for record in translations["conversations"]:
        name = record["conversation"]
        review = by_conversation.get(name)
        if not record["check"]["ok"]:
            withheld.append({"conversation": name, "reason": "the turns did not map one for one"})
        elif review is None:
            withheld.append({"conversation": name, "reason": "no human meaning review is recorded"})
        elif not review["turns_marked"]:
            withheld.append(
                {"conversation": name, "reason": "the meaning review sheet came back unmarked"}
            )
        else:
            established[name] = {
                "translation_group": "translation:" + name,
                "source_digest": record["source_digest"],
                "translation_digest": record["translation_digest"],
                "review": {
                    "reviewer": review["reviewer"],
                    "turns_marked": review["turns_marked"],
                    "of_turns": review["turns_offered"],
                    "verdicts": review["verdicts"],
                },
            }
    return {
        "version": "translation-groups-v1",
        "recorded_at": now(),
        "instrument_digest": translations["instrument_digest"],
        "model": translations["model"],
        "established": established,
        "not_established": withheld,
        "rule": "A pair is established by a verified one-for-one structure and a recorded "
        "human meaning review. A shared filename is not a pair, and neither is a passing "
        "structure check on its own.",
        "note": "The review records what a reader found, including shifted or lost meaning; "
        "a pair with such verdicts is established and carries them, because a contrast that "
        "hid them would compare two languages and report one.",
    }


def review_rows(source: list[Turn], translated: list[Turn], back: list[Turn], every: int) -> list:
    """The sheet a person marks: the original, the Czech, and the way back."""
    cs = {t.index: t for t in translated}
    en = {t.index: t for t in back}
    return [
        {
            "turn": t.index,
            "speaker": t.speaker,
            "original": t.text,
            "translation": cs[t.index].text if t.index in cs else None,
            "back_translation": en[t.index].text if t.index in en else None,
            "verdict": "",
            "note": "",
        }
        for t in source[::every]
    ]


VERDICTS = ("same_meaning", "shifted", "lost", "added", "cannot_tell")


def import_review(sheet: list[dict], *, reviewer: str, conversation: str) -> dict:
    """Human verdicts, counted; the text they were given stays in the sheet."""
    marked = [row for row in sheet if row.get("verdict")]
    unknown = sorted({row["verdict"] for row in marked} - set(VERDICTS))
    if unknown:
        raise SystemExit(f"Unknown verdict(s): {', '.join(unknown)}. Use one of {VERDICTS}.")
    counts = Counter(row["verdict"] for row in marked)
    return {
        "version": "meaning-review-v1",
        "conversation": conversation,
        "reviewer": reviewer,
        "reviewed_at": now(),
        "sheet_digest": digest(
            [(row["turn"], row.get("original"), row.get("translation")) for row in sheet]
        ),
        "turns_offered": len(sheet),
        "turns_marked": len(marked),
        "verdicts": {name: counts.get(name, 0) for name in VERDICTS},
        "marked_turns": {
            str(row["turn"]): {"verdict": row["verdict"], "note": row.get("note", "")}
            for row in marked
        },
        "rule": "Unmarked turns are unmarked, never counted as agreement.",
    }


# --- files ---------------------------------------------------------------------


def read_turns(path: Path) -> list[Turn]:
    """A conversation as turns, from the JSON this project already writes."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    turns = raw["turns"] if isinstance(raw, dict) else raw
    out = []
    for i, turn in enumerate(turns, start=1):
        speaker = str(turn["speaker"]).strip().lower()
        if speaker not in SPEAKERS:
            raise SystemExit(f"{path.name} turn {i}: unknown speaker {speaker!r}")
        out.append(Turn(i, speaker, str(turn["text"]).strip()))
    if not out:
        raise SystemExit(f"{path.name} holds no turns")
    return out


def _local_only(path: Path) -> None:
    resolved = path.resolve()
    inside = REPO in resolved.parents
    if inside and REPO / "local" not in resolved.parents:
        raise SystemExit("Translated transcripts may only be written under local/")


def write_raw(path: Path, text: str) -> None:
    """What a model actually returned when the parser could not make turns of it.

    A structural failure is recorded by name in the tracked check; this is the
    text behind the name, kept where corpus text is kept and nowhere else, so
    that "changed every speaker" can be read rather than guessed at.
    """
    _local_only(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_local(path: Path, translated: list[Turn], back: list[Turn] | None) -> None:
    """Corpus text, and therefore never anywhere this repository publishes.

    The rule is about what gets committed, so it is written as one: a path
    inside this checkout must be under the ignored `local/`. A path outside the
    checkout is somewhere this repository does not publish from and is left to
    whoever named it.
    """
    _local_only(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "turns": [{"index": t.index, "speaker": t.speaker, "text": t.text} for t in translated],
        "back_translation": [
            {"index": t.index, "speaker": t.speaker, "text": t.text} for t in (back or ())
        ],
        "written_at": now(),
    }
    path.write_bytes((json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def write_record(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    resolved = path.resolve()
    shown = resolved.relative_to(REPO).as_posix() if REPO in resolved.parents else str(resolved)
    print("wrote", shown)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    parser.add_argument("--records", type=Path, default=RECORDS)
    sub = parser.add_subparsers(dest="command", required=True)

    pick = sub.add_parser("select", help="measure candidate translators by back-translation")
    pick.add_argument("--sample", type=Path, required=True)
    pick.add_argument("--provider", default="einfra")
    pick.add_argument("--candidates", required=True)
    pick.add_argument("--back-translator", required=True)

    keep = sub.add_parser("record", help="record the chosen translator as the instrument")
    keep.add_argument("--model", required=True)
    keep.add_argument("--provider", default="einfra")
    keep.add_argument("--check", type=Path, required=True)
    keep.add_argument("--judges", default="", help="comma-separated judge models of this pilot")
    keep.add_argument("--reason", required=True)
    keep.add_argument("--settings", default=None, help="JSON; default: the check's settings")

    run = sub.add_parser("translate", help="translate conversations with the recorded instrument")
    run.add_argument("conversations", type=Path, nargs="+")
    run.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)

    sheet = sub.add_parser("review-sheet", help="write a meaning-review sheet for a human")
    sheet.add_argument("--conversation", required=True)
    sheet.add_argument("--source", type=Path, required=True)
    sheet.add_argument("--every", type=int, default=5)

    got = sub.add_parser("import-review", help="record a human's verdicts from a marked sheet")
    got.add_argument("--file", type=Path, required=True)
    got.add_argument("--conversation", required=True)
    got.add_argument("--reviewer", required=True)

    sub.add_parser("groups", help="write the EN/CS pairs a contrast may join on")

    args = parser.parse_args(argv)
    if args.command == "select":
        args.candidates = [name.strip() for name in args.candidates.split(",") if name.strip()]
        check = cmd_select(args)
        stamp = now()[:16].replace(":", "")
        write_record(args.records / f"back-translation-check-{stamp}.json", check)
    elif args.command == "record":
        check = json.loads(args.check.read_text(encoding="utf-8"))
        write_record(
            args.records / "instrument.json",
            instrument_record(
                provider=args.provider,
                model=args.model,
                settings=json.loads(args.settings) if args.settings else check.get("settings", {}),
                check=check,
                check_digest=digest(check),
                judges=[j.strip() for j in args.judges.split(",") if j.strip()],
                reason=args.reason,
            ),
        )
    elif args.command == "translate":
        write_record(args.records / "translations.json", cmd_translate(args))
    elif args.command == "groups":
        write_record(
            args.records / "groups.json",
            translation_groups(
                json.loads((args.records / "translations.json").read_text(encoding="utf-8")),
                [
                    json.loads(path.read_text(encoding="utf-8"))
                    for path in sorted(args.records.glob("meaning-review-*.json"))
                ],
            ),
        )
    elif args.command == "review-sheet":
        source = read_turns(args.source)
        local = json.loads(
            (args.workspace / f"{args.conversation}.cs.json").read_text(encoding="utf-8")
        )
        rows = review_rows(
            source,
            [Turn(t["index"], t["speaker"], t["text"]) for t in local["turns"]],
            [Turn(t["index"], t["speaker"], t["text"]) for t in local["back_translation"]],
            args.every,
        )
        path = args.workspace / f"{args.conversation}.review.json"
        path.write_bytes((json.dumps(rows, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print("wrote", path, f"({len(rows)} turns to mark)")
    else:
        sheet = json.loads(args.file.read_text(encoding="utf-8"))
        write_record(
            args.records / f"meaning-review-{args.conversation}.json",
            import_review(sheet, reviewer=args.reviewer, conversation=args.conversation),
        )


if __name__ == "__main__":
    main()
