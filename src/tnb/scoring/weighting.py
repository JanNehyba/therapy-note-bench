"""What the completeness order would be under a different weighting.

The leaderboard's completeness is the equal-weighted mean of a note's four SOAP
section fractions (`tneval.aggregate`). That arithmetic is kept as it is,
because it reproduces TN-Eval's own per-section numbers and the comparison with
their published figures rests on it. This module never changes it.

What it does is compute, over the same notes, the two readings a reader might
reasonably have expected instead, and publish what each does to the order:

* **item-weighted** -- every one of the 23 criteria counts once, so an
  eight-item section is worth twice a four-item one rather than the same;
* **importance-weighted** -- the rubric's own grading. TN-Eval's appendix marks
  every criterion Mandatory, Mandatory in certain circumstances, Highly
  recommended, Good to have or Optional (agreed among five therapists, Fleiss'
  kappa 0.68). The released data carries none of these labels and neither did
  this repository until 2026-09-13; they are transcribed here from the paper,
  with the section they come from.

Both are conventions, exactly as the macro mean is, and the point of publishing
them is that the choice among the three is not a detail: recomputed
item-weighted, systems change place. The artefact this writes is what lets that
sentence be a checked number rather than a remark in a docstring.

**Which notes.** The same ones the table averages, reached the same way. The
leaderboard admits a note on `Scores.is_complete` -- all four sections of every
measure, conciseness and faithfulness included -- and that test needs the note
text, because which conciseness questions *should* have been asked cannot be
known from the answer cache alone. `saturation` reads only the cache and admits
a note on completeness alone, and says so; under the first judge that keeps a
note the table drops for eight of the twenty-one systems, and moves the mean
of seven of them. This module therefore goes through `run.from_cache`, the path
`tnb score --cache-only` publishes from, as `edges` does. The macro column here
is the table's column by construction, and `notes_used` is the table's
`n_complete`.

Two things this module refuses to do. It does not weight a note the table did
not, for the reason `SystemAggregate.complete` gives. And it does not invent a
label for `assessment-triggers`, the one criterion of the 27 whose appendix
entry carries no importance line: that criterion is excluded from the
importance-weighted figure and named, which is the only honest reading of a
source that says nothing.
"""

from __future__ import annotations

import datetime as dt
import json
import statistics
from collections import defaultdict
from pathlib import Path

from tnb import judge
from tnb.scoring import tneval

#: TN-Eval's five importance levels, in the order the paper lists them
#: (Appendix C: "Mandatory, Mandatory in certain circumstances, Highly
#: recommended, Good to have, and Optional").
LEVELS = (
    "mandatory",
    "mandatory_in_certain_circumstances",
    "highly_recommended",
    "good_to_have",
    "optional",
)

#: One entry per implemented criterion, transcribed from TN-Eval's Appendix A
#: (Shah et al., ACL Industry 2025, pp. 190-191). The value is the level the
#: appendix states, or ``None`` where it states none. Nothing here is inferred.
#:
#: Two facts about the mapping, both checked against the paper on 2026-09-13.
#: The appendix lists six objective items and this repository scores five:
#: "Interventions [A]" and "[B]" are both Highly recommended and are one
#: criterion here, so the merge is weight-neutral. And the appendix has three
#: General Items (safety concerns -- Mandatory; cultural competence and
#: professionalism -- Highly recommended) that this repository does not score at
#: all; they are listed in ``NOT_IMPLEMENTED`` so the artefact says so.
IMPORTANCE: dict[str, str | None] = {
    # A.1 Subjective
    "subjective-chief-complaint": "mandatory",
    "subjective-symptoms": "mandatory",
    "subjective-history": "mandatory",
    "subjective-goals": "highly_recommended",
    "subjective-homework": "highly_recommended",
    "subjective-quotes": "highly_recommended",
    # A.2 Objective
    "objective-behavior": "mandatory",
    "objective-mental-status": "mandatory",
    "objective-assessment-tools": "highly_recommended",
    "objective-therapy-activities": "highly_recommended",
    "objective-interventions": "highly_recommended",
    # A.3 Assessment
    "assessment-diagnosis": "mandatory",
    # "Identifying Triggers: Any triggers shown by the client." -- and no
    # importance line follows it. The only such entry in the appendix.
    "assessment-triggers": None,
    "assessment-progress": "highly_recommended",
    "assessment-analysis": "highly_recommended",
    "assessment-response": "highly_recommended",
    "assessment-overall-progress": "highly_recommended",
    "assessment-goals": "highly_recommended",
    "assessment-stages": "highly_recommended",
    # A.4 Plan
    "plan-interventions": "mandatory",
    "plan-follow-up": "mandatory",
    "plan-adjustment": "mandatory_in_certain_circumstances",
    "plan-homework": "highly_recommended",
}

IMPORTANCE_SOURCE = (
    "Shah et al., TN-Eval, ACL 2025 Industry Track, Appendix A (definitions of SOAP "
    "note sections, pp. 190-191) and Appendix C (five importance levels, p. 191)"
)

#: Rubric items the appendix carries and this repository does not ask about.
NOT_IMPLEMENTED = (
    {"item": "safety concerns assessed and addressed", "level": "mandatory", "section": "A.5"},
    {"item": "culturally competent treatment", "level": "highly_recommended", "section": "A.5"},
    {"item": "professionalism", "level": "highly_recommended", "section": "A.5"},
)

#: The weight each level gets in the importance-weighted figure. A convention,
#: declared as one: the paper grades, it does not weigh. The two mandatory
#: levels are read as full weight and Highly recommended as ``RATIO`` of it;
#: the two levels no implemented criterion carries are given values only so
#: the table is total. `build` recomputes the figure at every ratio in
#: ``RATIOS`` and publishes what each does to the order, which is the
#: sensitivity the repository prints beside every convention it adopts.
RATIO = 0.5
RATIOS = (0.25, 0.5, 0.75)


def weights(ratio: float = RATIO) -> dict[str, float]:
    return {
        "mandatory": 1.0,
        "mandatory_in_certain_circumstances": 1.0,
        "highly_recommended": ratio,
        "good_to_have": ratio / 2,
        "optional": ratio / 4,
    }


def weighted(scores: tneval.Scores, ratio: float = RATIO) -> dict:
    """One note's completeness under the three readings.

    Refuses a note whose completeness did not rest on all four sections: a
    two-section mean and a four-section mean print identically and are not the
    same measurement, and item-weighting a partial note would hide that the
    macro figure already refused it.
    """
    if not scores.rests_on_every_section("completeness"):
        raise ValueError("completeness did not rest on every section; nothing to weight")
    found = scores.by_criterion
    missing = [key for key in IMPORTANCE if key not in found]
    if missing:
        raise ValueError(f"note is complete but lacks criteria: {missing}")

    by_level: dict[str, float] = {}
    for level in LEVELS:
        keys = [key for key, own in IMPORTANCE.items() if own == level]
        if keys:
            by_level[level] = sum(found[key] for key in keys) / len(keys)

    table = weights(ratio)
    labelled = [key for key, own in IMPORTANCE.items() if own is not None]
    numerator = sum(found[key] * table[IMPORTANCE[key]] for key in labelled)
    denominator = sum(table[IMPORTANCE[key]] for key in labelled)

    return {
        "macro": scores.headline["completeness"],
        "item_weighted": sum(found[key] for key in IMPORTANCE) / len(IMPORTANCE),
        "by_level": by_level,
        "importance_weighted": numerator / denominator,
    }


def per_system(notes) -> dict[str, dict]:
    """Every system's three readings, over the notes the table's row averaged.

    ``notes`` are `run.NoteResult`s from `run.from_cache`. A note counts when
    `Scores.is_complete` accepts it -- the table's own rule, applied by
    `run.SystemAggregate.complete` -- and is otherwise counted in
    ``notes_dropped``, which is the row's ``n_partial``. No coverage rule is
    applied: the table draws `gpt-oss-120b` on its 42 notes with the count
    beside it, and this artefact does the same rather than ranking a different
    set of systems than the page.
    """
    per_note: dict[str, dict[str, dict]] = defaultdict(dict)
    dropped: dict[str, int] = defaultdict(int)
    for note in notes:
        system = note.candidate.system_id
        if not note.scores.is_complete:
            dropped[system] += 1
            continue
        per_note[system][note.candidate.session_id] = {
            ratio: weighted(note.scores, ratio) for ratio in RATIOS
        }

    out: dict[str, dict] = {}
    for system, sessions in per_note.items():
        first = {s: r[RATIO] for s, r in sessions.items()}
        levels = sorted({level for r in first.values() for level in r["by_level"]})
        out[system] = {
            "notes_used": len(sessions),
            "notes_dropped": dropped.get(system, 0),
            "macro": statistics.mean(r["macro"] for r in first.values()),
            "item_weighted": statistics.mean(r["item_weighted"] for r in first.values()),
            "by_level": {
                level: statistics.mean(r["by_level"][level] for r in first.values())
                for level in levels
            },
            "importance_weighted": {
                str(ratio): statistics.mean(
                    r[ratio]["importance_weighted"] for r in sessions.values()
                )
                for ratio in RATIOS
            },
        }
    return out


def _order(systems: dict[str, dict], pick) -> list[str]:
    """Systems by one reading, best first; ties broken by name so it is stable."""
    return sorted(systems, key=lambda s: (-pick(systems[s]), s))


def rank_changes(systems: dict[str, dict], pick) -> dict:
    """What one reading does to the macro order: who moves, and how far."""
    macro = _order(systems, lambda row: row["macro"])
    other = _order(systems, pick)
    place = {s: i + 1 for i, s in enumerate(macro)}
    moved = [
        {"system": s, "macro_place": place[s], "place": i + 1, "by": (i + 1) - place[s]}
        for i, s in enumerate(other)
        if place[s] != i + 1
    ]
    return {
        "moved": len(moved),
        "of": len(macro),
        "order": other,
        "changes": sorted(moved, key=lambda c: (-abs(c["by"]), c["system"])),
    }


def build(judge_model: str = judge.DEFAULT_MODEL, cache_root: Path | None = None) -> dict | None:
    """The artefact, from the answers on disk. Asks the judge nothing.

    The client exists for its fingerprint and name only, as in `edges`: it
    names the instrument directory the cache is read from, so this reads
    exactly the settings the table was scored at and no other.
    """
    from tnb.scoring import run

    client = judge.Judge(judge.config_from_env(model=judge_model))
    sessions = run.load_sessions()
    candidates = list(run.from_reference(sessions)) + list(run.from_generations(sessions))
    notes = run.from_cache(candidates, client, cache_root=cache_root)
    systems = per_system(notes)
    if len(systems) < 2:
        return None

    changes = {
        "item_weighted": rank_changes(systems, lambda row: row["item_weighted"]),
    }
    for ratio in RATIOS:
        changes[f"importance_weighted_{ratio}"] = rank_changes(
            systems, lambda row, r=str(ratio): row["importance_weighted"][r]
        )

    return {
        "judge_model": judge_model,
        "judge_prompt_version": tneval.JUDGE_PROMPT_VERSION,
        "judge_settings": client.config.fingerprint(),
        "built": dt.date.today().isoformat(),
        "note_rule": (
            "Scores.is_complete, the table's own: all four sections of every measure. "
            "notes_used is the row's n_complete; notes_dropped is its n_partial."
        ),
        "importance": {
            "source": IMPORTANCE_SOURCE,
            "levels": list(LEVELS),
            "by_criterion": IMPORTANCE,
        },
        "unlabelled": sorted(key for key, own in IMPORTANCE.items() if own is None),
        "not_implemented": list(NOT_IMPLEMENTED),
        "convention": {
            "ratio": RATIO,
            "weights": weights(RATIO),
            "alternatives": {str(r): weights(r) for r in RATIOS},
            "note": (
                "The paper grades criteria; it does not weigh them. The weights are this "
                "repository's convention and the figure is published at three ratios so "
                "a reader can see how much of the order the convention decides."
            ),
        },
        "macro_order": _order(systems, lambda row: row["macro"]),
        "systems": {s: systems[s] for s in sorted(systems)},
        "rank_changes": changes,
    }


def weighting_path(judge_model: str, docs_dir: Path | None = None) -> Path:
    """One file per judge, for the reason `report.saturation_path` gives."""
    from tnb.generation import _slug
    from tnb.report import DOCS_DIR

    return (docs_dir or DOCS_DIR) / f"weighting-{_slug(judge_model)}.json"


def load(judge_model: str, docs_dir: Path | None = None) -> dict | None:
    path = weighting_path(judge_model, docs_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write(found: dict, docs_dir: Path | None = None) -> Path:
    """Publish the artefact whole or not at all."""
    from tnb.config import write_published

    path = weighting_path(found["judge_model"], docs_dir)
    write_published(path, json.dumps(found, indent=2, sort_keys=True) + "\n")
    return path
