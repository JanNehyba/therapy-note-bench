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
    target = protocol["selection"]["pilot_measurements_target"]
    require(
        len(target) == 2
        and all(type(v) is int and v > 0 for v in target)
        and target[0] <= target[1],
        "Invalid measurement target",
    )
    count = len(instrument.measurements) + sum(m != "items" for m in instrument.methods)
    require(0 < count <= target[1], "Pilot exceeds its reviewed operational measurement limit")
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
    expected = {
        ("public_demo", "en"): cfg["cases"]["english_demo"],
        ("translated_demo", "cs"): cfg["cases"]["paired_czech_translation"],
        ("native_real", "cs"): cfg["cases"]["native_czech"],
    }
    require(
        set(cohorts) == set(expected) and all(len(cohorts[k]) == v for k, v in expected.items()),
        "Cases differ from reviewed pilot strata",
    )
    english = {c.translation_group for c in cohorts[("public_demo", "en")]}
    translated = {c.translation_group for c in cohorts[("translated_demo", "cs")]}
    require(
        None not in english
        and english == translated
        and len(english) == cfg["cases"]["english_demo"],
        "Verify the two English/Czech translation pairs before planning",
    )
    instrument.check_language("cs")
    require(set(cfg["purposes"]) == set(PROFILES), "Pilot must retain the four purposes")
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
        "version": "feasibility-design-v2",
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
        "operational_measurements": count,
        "measurement_target": target,
        "below_target": count < target[0],
        "human_hours": cfg["human_hours"],
        "configuration": cfg,
        "unit_selection": "Pending reviewed banks and segmentations; "
        "freeze unit assignments before ratings.",
        "translation_meaning_review": "Required; group identifiers alone "
        "do not validate clinical meaning.",
        "format_experiments": "Compare response formats on identical units; "
        "vary granularity separately.",
        "independent_native_client_groups": len(
            {c.group_id for c in cohorts[("native_real", "cs")]}
        ),
        "status": "Planned feasibility pilot; "
        "no notes, model measurements or human ratings executed.",
    }
    return {"id": digest(result), **result}
