"""Freeze a balanced feasibility design; neither execute it nor invent human decisions."""

from collections import defaultdict

from .schema import PROFILES, Case, Model, NoteSpec, digest, plain, require, validate_cases


def plan(
    cases: list[Case],
    instrument,
    generators: list[Model],
    judges: list[Model],
    seed: int,
    note_format: str = "sections",
    word_limit: int = 500,
    *,
    protocol: dict,
) -> dict:
    validate_cases(cases)
    instrument.check(pilot=True)
    require(
        digest(protocol) == instrument.protocol_revision,
        "Pilot configuration differs from reviewed protocol",
    )
    cfg = protocol["pilot"]
    require("cohorts" in cfg, "Protocol lists no eligible pilot cohorts; amend it to name them")
    rule = protocol["selection"].get("first_round_measurements") or {}
    require(
        "pilot_measurements_target" not in protocol["selection"]
        and rule.get("rule") == "record_not_cap",
        "Protocol caps the measurement count; amend it to record the count instead",
    )
    # Recorded, never capped: what the review supported is carried, and what
    # the human budget cannot cover is reported as not measured.
    count = len(instrument.measurements) + sum(m != "items" for m in instrument.methods)
    require(count > 0, "Pilot has no executable measurement")
    for key in (
        "generator_families",
        "judge_families",
        "max_notes",
        "human_note_sample",
        "human_decisions_target",
        "unique_decisions",
        "blind_repeats",
    ):
        require(type(cfg[key]) is int and cfg[key] > 0, "Invalid pilot workload parameter")
    require(
        cfg["unique_decisions"] + cfg["blind_repeats"] == cfg["human_decisions_target"],
        "Pilot decision counts are inconsistent",
    )
    require(
        len(generators) == cfg["generator_families"] and len(judges) == cfg["judge_families"],
        "Model counts differ from the reviewed design",
    )
    require(
        len({m.family for m in generators}) == len(generators)
        and len({m.family for m in judges}) == len(judges),
        "Use distinct declared model families for each role",
    )
    cohorts = defaultdict(list)
    for case in cases:
        require(case.split == "pilot", "Feasibility cases must use the pilot split")
        cohorts[(case.origin, case.language)].append(case)
        for model in (*generators, *judges):
            case.authorize(model.provider)
    # The strata come from the protocol, not from this file: adding a cohort
    # is a protocol amendment, and a cohort the protocol excludes is refused
    # by name before the counts are compared.
    expected: dict[tuple[str, str], int] = {}
    for entry in cfg["cohorts"]:
        key = (entry["origin"], entry["language"])
        require(
            key not in expected
            and entry["origin"] in ("public_demo", "translated_demo", "native_real", "synthetic")
            and entry["language"] in ("en", "cs")
            and type(entry["cases"]) is int
            and entry["cases"] > 0,
            "Invalid pilot cohort in protocol",
        )
        expected[key] = entry["cases"]
    excluded = {(e["origin"], e["language"]) for e in cfg.get("excluded_cohorts", ())}
    require(not (excluded & set(expected)), "Protocol both lists and excludes a cohort")
    require(
        not (set(cohorts) & excluded),
        "Case cohort is excluded from this pilot by the protocol",
    )
    require(
        set(cohorts) == set(expected) and all(len(cohorts[k]) == v for k, v in expected.items()),
        "Cases differ from the protocol's eligible cohorts",
    )
    pairing = cfg.get("translation_pairing") or {}
    if pairing.get("required"):
        original = (pairing["original"]["origin"], pairing["original"]["language"])
        translation = (pairing["translation"]["origin"], pairing["translation"]["language"])
        require(
            original in expected and translation in expected,
            "Translation pairing names a cohort the protocol does not list",
        )
        originals = {c.translation_group for c in cohorts[original]}
        translations = {c.translation_group for c in cohorts[translation]}
        require(
            None not in originals
            and originals == translations
            and len(originals) == expected[original],
            "Verify the original/translation pairs before planning",
        )
    instrument.check_language("cs")
    # A purpose may be left out of a round, and it may not be left out quietly.
    # The rule was "keep all four", which stopped a silent drop and also stopped
    # a recorded one; an investigator who narrows the scope now has to say which
    # purposes are out and why, and the plan carries that with it.
    purposes = tuple(cfg["purposes"])
    require(bool(purposes) and set(purposes) <= set(PROFILES), "Pilot names an unknown purpose")
    out_of_scope = {e["purpose"]: e for e in cfg.get("purposes_out_of_scope", ())}
    require(
        not (set(purposes) & set(out_of_scope)),
        "A purpose cannot be both planned and out of scope",
    )
    require(
        set(purposes) | set(out_of_scope) == set(PROFILES),
        "Every purpose is either planned or recorded as out of scope",
    )
    require(
        all(e.get("reason") and e.get("decision") for e in out_of_scope.values()),
        "A purpose left out needs a reason and the decision that left it out",
    )
    jobs, human_notes = [], []
    for _cohort, pair in sorted(cohorts.items()):
        ordered = sorted(pair, key=lambda c: digest((seed, c.revision)))
        for profile_index, profile in enumerate(cfg["purposes"]):
            for generator_index, generator in enumerate(generators):
                for case_index, case in enumerate(ordered):
                    job = {
                        "case_revision": case.revision,
                        "profile": profile,
                        "language": case.language,
                        "origin": case.origin,
                        "generator": plain(generator),
                        "spec": plain(NoteSpec(profile, case.language, note_format, word_limit)),
                    }
                    job_id = digest(job)
                    jobs.append({"id": job_id, **job})
                    if case_index == (profile_index + generator_index) % len(pair):
                        human_notes.append(job_id)
    require(len(jobs) <= cfg["max_notes"], "Pilot exceeds its generation budget")
    require(
        len(human_notes) == cfg["human_note_sample"],
        "Balanced sample differs from protocol; amend the assignment design explicitly",
    )
    result = {
        "version": "feasibility-design-v3",
        "research_revision": instrument.revision,
        "protocol_revision": instrument.protocol_revision,
        "seed": seed,
        "cases": {c.id: c.revision for c in cases},
        "jobs": jobs,
        "judges": plain(judges),
        "human_note_sample": human_notes,
        "human_item_budget": {
            "unique_decisions": cfg["unique_decisions"],
            "blinded_repeats": cfg["blind_repeats"],
            "total": cfg["human_decisions_target"],
        },
        "measurement_rule": rule["rule"],
        "measurements_recorded": {
            "executable": count,
            "items": len(instrument.measurements),
            "non_item_methods": [m for m in instrument.methods if m != "items"],
            "recorded_at": "pilot_plan",
        },
        "cohorts": [
            {
                "origin": origin,
                "language": language,
                "cases": len(group),
                "client_groups": len({c.group_id for c in group}),
            }
            for (origin, language), group in sorted(cohorts.items())
        ],
        "purposes": list(purposes),
        # Named in the plan, not only in the protocol: a reader of the plan has
        # to see that two purposes exist and are not being served, and why.
        "purposes_out_of_scope": list(cfg.get("purposes_out_of_scope", ())),
        "excluded_cohorts": list(cfg.get("excluded_cohorts", ())),
        "human_anchor": cfg.get("human_anchor"),
        "human_hours": cfg["human_hours"],
        "configuration": cfg,
        "unit_selection": "Pending reviewed banks and segmentations; "
        "freeze unit assignments before ratings.",
        "translation_meaning_review": "Required; group identifiers alone "
        "do not validate clinical meaning.",
        "format_experiments": "Compare response formats on identical units; "
        "vary granularity separately.",
        "status": "Planned feasibility pilot; "
        "no notes, model measurements or human ratings executed.",
    }
    return {"id": digest(result), **result}
