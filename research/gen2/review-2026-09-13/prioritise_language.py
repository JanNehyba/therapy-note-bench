"""Rank the language-quality layer for AI-assisted title/abstract screening.

Like `prioritise.py`: a documented deterministic ordering, not a screening
decision, with the records below the cut moved to a stratum that is audited by
random sampling so the miss rate can be estimated instead of assumed to be zero.

Its signals cannot be reused. They encode the question of the 2026-09-13 round,
which was about psychotherapy notes and their quality instruments, and a paper
on the typology of translation errors matches almost none of them: it would
score the fidelity and language signals and nothing else, which is 5, and sit
below the cut by construction. Running the old signals over this layer and
reporting that nothing cleared the threshold would be a measurement of the
signals, not of the literature.

So this layer has its own signals, tied to its own question -- does the work
offer a property of a text, a rule for recognising it, or a way of measuring it
-- at the same registered threshold of 9 and with the same stratified audit.

The signals are committed before the script is run, as the queries were, so
"recorded before use" is checkable from the history.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPORTS = Path("C:/Users/Nehyba/therapy-note-bench/local/gen2-review-2026-09-13/exports")
LOG = ROOT / "search-log-acl-language.json"

#: Weighted signals. Weights are a stated convention for ordering only and
#: carry no claim about the importance of a study.
#:
#: The two heaviest are the two things that would end this layer's question. A
#: named typology is a list of text properties somebody already agreed on; one
#: of the six Czech criteria named outright is support for that criterion or a
#: reason it is wrong.
SIGNALS: list[tuple[str, str, int]] = [
    # A named, reusable list of error types for text quality.
    (
        r"\b(mqm|multidimensional quality metrics|dqf|error taxonom\w*|error typolog\w*"
        r"|annotation scheme|error categor\w*|error annotation)\b",
        "typology",
        5,
    ),
    # One of the six properties the Czech scorer measures, named.
    (
        r"\b(diacritics?|calque\w*|anglicism\w*|loan ?word\w*|untranslated"
        r"|agreement error\w*|grammatical error correction|register|formality"
        r"|non[- ]?words?|neologism\w*)\b",
        "six",
        5,
    ),
    # A text property a human is asked to rate, with the scheme for rating it.
    (
        r"\b(fluenc\w*|adequac\w*|grammaticalit\w*|acceptabilit\w*|naturalness)\b",
        "rated-property",
        4,
    ),
    # A way of recognising the property automatically.
    (
        r"\b(detect\w*|classif\w*|identif\w*|automatic metric|reference[- ]free"
        r"|quality estimation)\b",
        "method",
        4,
    ),
    # The layer exists for small languages, so the language itself is a signal.
    (
        r"\b(low[- ]resource\w*|under[- ]resourced|morphologically rich|slavic|czech"
        r"|highly inflected)\b",
        "small-language",
        3,
    ),
    # What a human had to fix is the closest existing thing to what is wrong
    # with a generated Czech note.
    (r"\b(post[- ]?editing|translationese|interference)\b", "post-editing", 3),
    # The inclusion criterion wants a rule that two people can apply the same
    # way, so evidence that anyone checked that is worth ordering on.
    (
        r"\b(inter[- ]?annotator|inter[- ]?rater|agreement|kappa|reliabilit\w*"
        r"|annotation guidelines)\b",
        "reliability",
        3,
    ),
    # Clinical or medical text outside English: the intersection this project
    # sits in and the one least likely to exist.
    (
        r"\b(clinical|medical|patient|health)\b.{0,60}\b(non[- ]english|multilingual"
        r"|cross[- ]lingual|translat\w*)\b",
        "clinical-non-english",
        2,
    ),
    (r"\b(human evaluation|human judg\w*|rater\w*|annotator\w*)\b", "human-eval", 2),
]

#: Signals that a record is probably off-topic even when it scores. They
#: subtract; they never exclude on their own.
#:
#: "register" and "detection" are common words in the field and pull in work
#: with no text property in it at all: a register in a machine architecture, a
#: detector of hate speech. The negatives are aimed at those, not at a topic
#: this review dislikes.
NEGATIVE: list[tuple[str, int]] = [
    (r"\b(speech recognition|acoustic model\w*|speaker diari[sz]ation|text[- ]to[- ]speech)\b", -3),
    (r"\b(hate speech|offensive language|sentiment analysis|spam|fake news)\b", -3),
    (r"\b(word embedding\w*|representation learning|pre[- ]?training objective)\b", -2),
    (r"\b(parsing|part[- ]of[- ]speech tagging|named entity recognition)\b", -2),
]

THRESHOLD = 9
AUDIT_SEED = 20261014
AUDIT_SIZE = 200


def score(record: dict) -> tuple[int, list[str]]:
    hay = f"{record.get('title', '')} {record.get('abstract', '')}"
    total, tags = 0, []
    for pattern, tag, weight in SIGNALS:
        if re.search(pattern, hay, re.I):
            total += weight
            tags.append(tag)
    for pattern, weight in NEGATIVE:
        if re.search(pattern, hay, re.I):
            total += weight
            tags.append("neg")
    return total, tags


def pool() -> list[dict]:
    """The distinct records of the layer, each carrying the queries that found it."""
    log = json.loads(LOG.read_text(encoding="utf-8"))
    merged: dict[str, dict] = {}
    for search in log["searches"]:
        hits = json.loads((EXPORTS / search["export_file"]).read_text(encoding="utf-8"))
        for record in hits:
            key = record["_key"]
            if key in merged:
                merged[key]["queries"].append(search["query_id"])
            else:
                merged[key] = {**record, "queries": [search["query_id"]]}
    return list(merged.values())


def main() -> int:
    records = pool()
    for record in records:
        record["priority_score"], record["signals"] = score(record)
    records.sort(key=lambda r: (-r["priority_score"], r.get("year") or ""))

    priority = [r for r in records if r["priority_score"] >= THRESHOLD]
    remainder = [r for r in records if r["priority_score"] < THRESHOLD]
    audit = random.Random(AUDIT_SEED).sample(remainder, min(AUDIT_SIZE, len(remainder)))

    for name, rows in (
        ("screen-priority-language.json", priority),
        ("screen-audit-sample-language.json", audit),
    ):
        (EXPORTS / name).write_bytes(
            (json.dumps(rows, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
        )

    distribution: dict[int, int] = {}
    for record in records:
        distribution[record["priority_score"]] = distribution.get(record["priority_score"], 0) + 1
    by_signal: dict[str, int] = {}
    for record in priority:
        for tag in set(record["signals"]):
            by_signal[tag] = by_signal.get(tag, 0) + 1

    summary = {
        "layer": "language",
        "amendment": "AM-8",
        "pool_size": len(records),
        "ordering_rule": "weighted keyword signals over title+abstract; a stated convention "
        "for ordering only",
        "why_its_own_signals": (
            "The signals of prioritise.py encode the question of the 2026-09-13 round. A paper "
            "on the typology of translation errors matches two of them, scores 5 and sits below "
            "the cut by construction, so running them here would measure the signals and not "
            "the literature."
        ),
        "signals": [{"tag": t, "weight": w, "pattern": p} for p, t, w in SIGNALS],
        "negative_signals": [{"weight": w, "pattern": p} for p, w in NEGATIVE],
        "priority_threshold": THRESHOLD,
        "priority_threshold_basis": (
            "the same cut as the 2026-09-13 round, which is registered. The signals are new "
            "because the question is, but moving the cut as well would make the two rounds "
            "incomparable in two ways at once."
        ),
        "priority_stratum": len(priority),
        "remainder_stratum": len(remainder),
        "priority_by_signal": dict(sorted(by_signal.items(), key=lambda kv: -kv[1])),
        "score_distribution": dict(sorted(distribution.items(), reverse=True)),
        "audit_sample_size": len(audit),
        "audit_sample_seed": AUDIT_SEED,
        "audit_sample_frame": "the remainder of this layer only",
        "audit_sample_note": (
            "Drawn from this layer's remainder and audited on its own. The eligibility rate of "
            "the 2026-09-13 remainder is a property of that remainder and says nothing about "
            "this one."
        ),
        "not_a_screening_decision": (
            "Nothing here is included or excluded. Records below the cut are audited by "
            "sampling, which is what lets the miss rate be reported rather than assumed."
        ),
        "export_digests": {
            name: hashlib.sha256((EXPORTS / name).read_bytes()).hexdigest()
            for name in ("screen-priority-language.json", "screen-audit-sample-language.json")
        },
    }
    out = ROOT / "priority-language.json"
    out.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"pool {len(records)} | priority {len(priority)} | remainder {len(remainder)}")
    print(f"audit sample {len(audit)} at seed {AUDIT_SEED}")
    print("priority records by signal:")
    for tag, count in summary["priority_by_signal"].items():
        print(f"  {tag:22} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
