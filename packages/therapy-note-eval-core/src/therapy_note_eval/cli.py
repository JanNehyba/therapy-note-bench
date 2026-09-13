"""Run gen-2 stages in a private workspace; API stages always require a named model."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from . import PROTOCOL_VERSION, annotations, controls, pipeline, profiles, report
from .metrics import plan_sample, validation_metrics
from .schema import (
    PROFILES,
    Bank,
    Case,
    Evaluation,
    Manifest,
    Model,
    Note,
    NoteSpec,
    Segmentation,
    ValidationError,
    decode,
    digest,
    plain,
    require,
    validate_cases,
)
from .storage import Budget, Runner, Store


def emit(value) -> None:
    print(json.dumps(plain(value), ensure_ascii=True, indent=2, allow_nan=False))


def load(store: Store, kind: str, cls) -> list:
    return [decode(cls, row) for row in store.all(kind)]


def only(values, message):
    require(len(values) == 1, message)
    return values[0]


def runner(args, store) -> Runner:
    from .legacy import HostBackend

    require(
        bool(args.provider and args.model and args.family),
        "API stages need --provider, --model and --family",
    )
    backend = HostBackend(args.provider, args.model, args.family, args.max_tokens, args.effort)
    return Runner(
        backend,
        store,
        Budget(args.max_calls, args.max_judge_usd, args.input_price, args.output_price),
        args.max_input_chars,
        args.replicate_id,
    )


def selected_notes(store, args) -> list[Note]:
    notes = load(store, "notes", Note)
    return [
        n
        for n in notes
        if (not getattr(args, "profile", None) or n.spec.profile == args.profile)
        and (not getattr(args, "language", None) or n.spec.language == args.language)
        and (not getattr(args, "generator", None) or n.generator.model == args.generator)
        and (not getattr(args, "note", None) or args.note in (n.id, n.revision))
    ]


def note_inputs(store, note):
    case = only(
        [c for c in load(store, "cases", Case) if c.revision == note.case_revision],
        "Case selection is ambiguous",
    )
    bank = only(
        [b for b in load(store, "banks", Bank) if b.case_revision == case.revision],
        "Bank selection is missing or ambiguous; use a separate workspace per bank recipe",
    )
    segmentation = only(
        [s for s in load(store, "segmentations", Segmentation) if s.note_revision == note.revision],
        "Segmentation is missing or ambiguous; freeze one extraction recipe per run",
    )
    return case, bank, segmentation


def prepare_manifest(store, case, bank, note, segmentation, judge, args):
    population = [
        c for c in load(store, "cases", Case) if c.cohort == case.cohort and c.split == case.split
    ]
    banks = load(store, "banks", Bank)
    revisions = {}
    for c in population:
        b = only(
            [b for b in banks if b.case_revision == c.revision and b.author == bank.author],
            "Prepare a bank for every planned case before scoring",
        )
        revisions[c.id] = b.revision
    return Manifest(
        {c.id: c.revision for c in population},
        revisions,
        case.corpus,
        case.origin,
        case.split,
        note.spec,
        bank.author,
        segmentation.extractor,
        judge,
        "retrieved" if args.retrieval_turns else "full_context",
        args.retrieval_turns or 32,
        measurements=args.instrument.measurements,
        research_revision=args.instrument.revision,
        methods=args.instrument.methods,
        assessment_scope=args.instrument.assessment_scope,
        required_methods=args.instrument.required_methods,
        method_specs=args.instrument.method_specs,
        replicate_id=args.replicate_id,
    )


def reviewed_instrument(args, store):
    from .registry import load_registry

    require(
        args.registry is not None,
        "Research stages require --registry; use demo for legacy defaults",
    )
    instrument = load_registry(json.loads(args.registry.read_text(encoding="utf-8")), pilot=True)
    research_store = Store(args.research_workspace or store.root)
    from .development import verify_snapshot

    active = verify_snapshot(research_store, instrument)
    args.research_protocol = active["protocol"]
    return instrument


def do_api(args, store):
    cases = load(store, "cases", Case)
    validate_cases(cases)
    args.instrument = reviewed_instrument(args, store)
    for case in cases:
        args.instrument.check_language(case.language)
    store.put("registries", args.instrument.revision, args.instrument)
    notes = selected_notes(store, args)
    if args.action == "prepare":
        estimate = len(cases) if "qa" in args.instrument.methods else 0
    elif args.action == "generate":
        estimate = len(cases) * len(args.profiles)
    else:
        require(bool(notes), "No notes match this stage")
        estimate = len(notes) * (5 if args.action == "score" else 1)
    emit(
        {
            "stage": args.action,
            "planned_calls_upper_bound": estimate,
            "call_ceiling": args.max_calls,
            "dollar_ceiling": args.max_judge_usd,
            "execution": "dry-run" if args.dry_run else "API",
            "cached_calls_cost": 0,
        }
    )
    if args.dry_run:
        return 0
    active = runner(args, store)
    # Validate the entire source policy before sending the first prompt.
    for case in cases:
        case.authorize(active.identity.provider)
    failures, completed = [], 0
    if args.action == "prepare":
        jobs = [(case, None) for case in cases]
    elif args.action == "generate":
        jobs = [
            (
                case,
                NoteSpec(
                    profile,
                    case.language,
                    args.format,
                    args.word_limit,
                    required_headings=tuple(args.required_heading),
                ),
            )
            for case in cases
            for profile in args.profiles
        ]
        cohorts = defaultdict(list)
        for case, spec in jobs:
            cohorts[(case.cohort, case.split, digest(spec))].append((case, spec))
        for cohort in cohorts.values():
            plan = {
                "cases": {c.id: c.revision for c, _ in cohort},
                "spec": plain(cohort[0][1]),
                "generator": plain(active.identity),
            }
            store.put("generation_plans", digest(plan), plan)
    else:
        by_id = {c.id: c for c in cases}
        jobs = [(by_id[n.case_id], n) for n in notes]
    for case, value in jobs:
        try:
            if args.action == "prepare":
                pipeline.prepare(case, active, args.instrument)
            elif args.action == "generate":
                pipeline.generate(case, value, active)
            elif args.action == "segment":
                pipeline.segment(case, value, active)
            else:
                _, bank, segmentation = note_inputs(store, value)
                manifest = prepare_manifest(
                    store, case, bank, value, segmentation, active.identity, args
                )
                result = pipeline.score(case, value, bank, segmentation, manifest, active)
                if result.failures:
                    failures.append({"case_digest": digest(case.id), "stages": result.failures})
                    continue
            completed += 1
        except ValidationError as exc:
            failures.append({"case_digest": digest(case.id), "error": str(exc)})
    outcome = {
        "completed": completed,
        "planned": len(jobs),
        "failures": failures,
        "api_calls": active.budget.calls,
        "reserved_usd_upper_bound": active.budget.reserved_usd,
    }
    store.put("runs", digest(outcome), outcome)
    emit(outcome)
    return 2 if failures else 0


def do_controls(args, store):
    variants = args.variants
    estimate = len(args.languages) * len(args.profiles) * len(variants) * 6
    emit(
        {
            "planned_calls_upper_bound": estimate,
            "max_calls": args.max_calls,
            "status": "Enriched synthetic controls, not natural error prevalence",
        }
    )
    if args.dry_run:
        return 0
    active = runner(args, store)
    records, failures = [], 0
    for language in args.languages:
        for profile in args.profiles:
            for variant in variants:
                case, bank, note, _, _, _ = controls.fixture(language, profile, variant)
                try:
                    for kind, key, value in (
                        ("cases", case.revision, case),
                        ("banks", bank.revision, bank),
                        ("notes", note.revision, note),
                    ):
                        store.put(kind, key, value)
                    segmentation = pipeline.segment(case, note, active)
                    manifest = Manifest(
                        {case.id: case.revision},
                        {case.id: bank.revision},
                        case.corpus,
                        case.origin,
                        case.split,
                        note.spec,
                        bank.author,
                        active.identity,
                        active.identity,
                        replicate_id=active.replicate_id,
                    )
                    result = pipeline.score(case, note, bank, segmentation, manifest, active)
                    from .metrics import measure

                    assessment = controls.assess(
                        variant, result, measure(case, note, bank, segmentation, result)
                    )
                    records.append(
                        {
                            "language": language,
                            "profile": profile,
                            "variant": variant,
                            **assessment,
                            "failed_stages": result.failures,
                        }
                    )
                    failures += bool(result.failures)
                except ValidationError:
                    failures += 1
                    records.append(
                        {
                            "language": language,
                            "profile": profile,
                            "variant": variant,
                            "expected_error": variant not in controls.POSITIVE,
                            "detected": None,
                            "target_detected": None,
                            "failed_stages": ["control_failed"],
                        }
                    )
    by_group = defaultdict(list)
    for r in records:
        if r["detected"] is not None:
            by_group[(r["language"], r["profile"])].append(
                (str(r["expected_error"]), str(r["detected"]))
            )
    result = {
        "judge": plain(active.identity),
        "protocol": PROTOCOL_VERSION,
        "controls_version": "controls-v1",
        "api_calls": active.budget.calls,
        "planned": len(records),
        "fully_evaluated": sum(r.get("complete", False) for r in records),
        "records": records,
        "by_language_profile": {
            "/".join(k): validation_metrics(v, "True") for k, v in by_group.items()
        },
        "status": "Experimental controls; not human calibration or clinical validation.",
    }
    store.put("controls", digest(result), result)
    emit(result)
    return 2 if failures else 0


def command(args):
    store = Store(args.workspace)
    if args.action == "research":
        from . import research

        emit(research.command(args, store))
    elif args.action == "export-public":
        from .privacy import public_report

        payload = public_report(report.build_report(store))
        destination = store.put("public_exports", digest(payload), payload)
        emit({"export": str(destination), "status": "aggregate-only; review before publication"})
    elif args.action == "profiles":
        emit(profiles.DEFINITIONS)
    elif args.action == "import":
        if args.input:
            raw = json.loads(args.input.read_text(encoding="utf-8"))
            cases = [decode(Case, c) for c in raw]
        else:
            from .legacy import import_cases

            groups = json.loads(args.groups.read_text(encoding="utf-8")) if args.groups else None
            cases = import_cases(args.corpus, args.limit, args.czech_root, groups)
        validate_cases(cases)
        existing = load(store, "cases", Case)
        validate_cases(list({c.revision: c for c in [*existing, *cases]}.values()))
        for case in cases:
            store.put("cases", case.revision, case)
        emit(
            {
                "imported": len(cases),
                "cohorts": sorted({c.cohort for c in cases}),
                "independent_groups": len({c.group_id for c in cases}),
                "text_published": False,
            }
        )
    elif args.action == "demo":
        emit(controls.demo(store))
        data, page = report.write_report(store)
        emit({"report": str(page), "aggregate_data": str(data)})
    elif args.action in ("prepare", "generate", "segment", "score"):
        return do_api(args, store)
    elif args.action == "controls":
        return do_controls(args, store)
    elif args.action == "report":
        data, page = report.write_report(store)
        emit({"report": str(page), "aggregate_data": str(data)})
    elif args.action == "link-findings":
        from .findings import summarize

        raw = store.get("evaluations", args.evaluation)
        require(raw is not None, "Unknown evaluation revision")
        evaluation = decode(Evaluation, raw)
        linkage = json.loads(args.input.read_text(encoding="utf-8"))
        summary = summarize(evaluation, linkage)
        store.put("finding_links", digest(linkage), linkage)
        emit(summary)
    elif args.action == "pilot-plan":
        from .pilot import plan

        instrument = reviewed_instrument(args, store)
        selection = json.loads(args.input.read_text(encoding="utf-8"))
        cases = [c for c in load(store, "cases", Case) if c.revision in selection["case_revisions"]]
        require(len(cases) == len(selection["case_revisions"]), "Unknown selected case revision")
        result = plan(
            cases,
            instrument,
            [decode(Model, m) for m in selection["generators"]],
            [decode(Model, m) for m in selection["judges"]],
            args.seed,
            selection.get("format", "sections"),
            selection.get("word_limit", 500),
            protocol=args.research_protocol,
        )
        path = store.put("pilot_plans", result["id"], result)
        emit(
            {
                "plan": str(path),
                "generation_jobs": len(result["jobs"]),
                "human_notes": len(result["human_note_sample"]),
                "status": result["status"],
            }
        )
    elif args.action == "annotate":
        if args.bank_only:
            cases = {c.revision: c for c in load(store, "cases", Case)}
            banks = [
                b
                for b in load(store, "banks", Bank)
                if not args.language or cases[b.case_revision].language == args.language
            ]
            require(bool(banks), "No source banks match the selection")
            for bank in banks[: args.limit]:
                review = annotations.bank_sheet(cases[bank.case_revision], bank)
                emit({"review": str(report.write_review(store, review)), "sheet_id": review["id"]})
            return 0
        notes = selected_notes(store, args)
        require(bool(notes), "No notes match the annotation selection")
        if args.tasks:
            for note in notes[: args.limit]:
                case, bank, _ = note_inputs(store, note)
                review, lookup = annotations.task_sheet(case, bank, note)
                store.put("task_keys", review["id"], lookup)
                emit({"review": str(report.write_review(store, review)), "sheet_id": review["id"]})
            return 0
        if args.pairs:
            review, lookup = annotations.pair_sheet(
                {c.id: c for c in load(store, "cases", Case)}, notes, args.limit
            )
            store.put("pair_keys", review["id"], lookup)
            emit({"review": str(report.write_review(store, review)), "sheet_id": review["id"]})
        else:
            for note in sorted(notes, key=lambda n: digest(n.revision))[: args.limit]:
                case, bank, segmentation = note_inputs(store, note)
                evaluations = [
                    e
                    for e in load(store, "evaluations", Evaluation)
                    if e.note_revision == note.revision
                    and (not args.judge_model or e.judge.model == args.judge_model)
                ]
                require(len(evaluations) <= 1, "Choose --judge-model for the note-answer display")
                instrument = reviewed_instrument(args, store) if args.registry else None
                settings = (
                    {
                        "measurements": instrument.measurements,
                        "research_revision": instrument.revision,
                        "methods": instrument.methods,
                    }
                    if instrument
                    else {}
                )
                if instrument and evaluations:
                    require(
                        evaluations[0].research_revision == instrument.revision,
                        "Annotation registry differs from the evaluated instrument",
                    )
                review = annotations.sheet(
                    case,
                    note,
                    bank,
                    segmentation,
                    evaluations[0] if evaluations else None,
                    **settings,
                )
                emit({"review": str(report.write_review(store, review)), "sheet_id": review["id"]})
    elif args.action in ("ratings", "adjudicate"):
        review = store.get("sheets", args.sheet)
        require(review is not None, "Unknown annotation sheet")
        responses = [json.loads(p.read_text(encoding="utf-8")) for p in args.responses]
        for response in responses:
            validated = annotations.import_response(review, response)
            store.put("ratings", digest(validated), validated)
        if args.action == "adjudicate":
            next_sheet = annotations.adjudication_sheet(review, responses)
            emit(
                {
                    "review": str(report.write_review(store, next_sheet)),
                    "sheet_id": next_sheet["id"],
                }
            )
        elif store.get("task_keys", review["id"]):
            emit(
                {
                    "imported": len(responses),
                    "status": "Task answers stored for blinded "
                    "human assessment against the separate reference key; "
                    "no automatic utility score.",
                }
            )
        elif store.get("pair_keys", review["id"]):
            emit(annotations.pair_results(review, store.get("pair_keys", review["id"]), responses))
        else:
            emit(annotations.agreement(review, responses))
            evaluations = [
                e
                for e in load(store, "evaluations", Evaluation)
                if e.note_revision == review.get("note_revision")
                and e.bank_revision == review.get("bank_revision")
                and e.segmentation_revision == review.get("segmentation_revision")
                and e.case_revision == review.get("case_revision")
                and digest(e.measurements) == review.get("measurement_revision")
                and e.research_revision == review.get("research_revision")
            ]
            for evaluation in evaluations:
                for response in responses:
                    calibration = annotations.compare_to_judge(review, response, evaluation)
                    store.put("calibration", digest(calibration), calibration)
                    emit(calibration)
    elif args.action == "sample-plan":
        emit(plan_sample(args.half_width, args.prevalence, args.sessions_per_client, args.icc))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="therapy-note-eval", description=__doc__)
    p.add_argument("--workspace", type=Path, default=Path("local/gen2"))
    sub = p.add_subparsers(dest="action", required=True)
    from . import research

    research.add_parser(sub)
    sub.add_parser("export-public", help="private staging of an allow-listed aggregate export")
    sub.add_parser("profiles", help="print the four public bilingual profiles")
    imp = sub.add_parser("import", help="import cases into the private workspace")
    choice = imp.add_mutually_exclusive_group(required=True)
    choice.add_argument("--input", type=Path, help="JSON array of Case records")
    choice.add_argument("--corpus", choices=("tneval", "ihope", "czech-real", "czech-translated"))
    imp.add_argument("--czech-root", type=Path)
    imp.add_argument("--groups", type=Path, help="private id-to-client/translation-group mapping")
    imp.add_argument("--limit", type=int)
    sub.add_parser("demo", help="offline synthetic demonstration; no LLM results")

    def selectors(cmd):
        cmd.add_argument("--profile", choices=PROFILES)
        cmd.add_argument("--language", choices=("en", "cs"))
        cmd.add_argument("--generator")
        cmd.add_argument("--note")

    def api(cmd):
        cmd.add_argument("--provider")
        cmd.add_argument("--model")
        cmd.add_argument("--family")
        cmd.add_argument("--effort")
        cmd.add_argument("--max-tokens", type=int, default=8192)
        cmd.add_argument("--replicate-id", default="primary")
        cmd.add_argument("--max-input-chars", type=int, default=200_000)
        cmd.add_argument("--max-calls", type=int, default=100)
        cmd.add_argument("--max-judge-usd", type=float)
        cmd.add_argument("--input-price", type=float, help="USD per million input tokens")
        cmd.add_argument("--output-price", type=float, help="USD per million output tokens")
        cmd.add_argument("--dry-run", action="store_true")

    for action in ("prepare", "generate", "segment", "score"):
        cmd = sub.add_parser(action)
        api(cmd)
        cmd.add_argument(
            "--registry",
            type=Path,
            help="human-reviewed instrument registry; no implicit research defaults",
        )
        cmd.add_argument(
            "--research-workspace",
            type=Path,
            help="private workspace containing the exact reviewed instrument snapshot",
        )
        if action == "generate":
            cmd.add_argument("--profiles", nargs="+", choices=PROFILES, default=list(PROFILES))
            cmd.add_argument(
                "--format", choices=("sections", "soap", "dap", "birp"), default="sections"
            )
            cmd.add_argument("--word-limit", type=int, default=500)
            cmd.add_argument(
                "--required-heading",
                action="append",
                default=[],
                help="exact heading required on a separate line; repeat for multiple headings",
            )
        if action in ("segment", "score"):
            selectors(cmd)
        if action == "score":
            cmd.add_argument(
                "--retrieval-turns", type=int, help="opt-in lexical retrieval diagnostic"
            )
    control = sub.add_parser(
        "controls", help="measure a real judge on planted errors and clean controls"
    )
    api(control)
    control.add_argument("--languages", nargs="+", choices=("en", "cs"), default=["en", "cs"])
    control.add_argument("--profiles", nargs="+", choices=PROFILES, default=list(PROFILES))
    control.add_argument(
        "--variants", nargs="+", choices=controls.VARIANTS, default=list(controls.VARIANTS)
    )
    sub.add_parser("report", help="local aggregate report, separate per instrument and cohort")
    annotate = sub.add_parser("annotate", help="create blinded local review pages")
    pilot = sub.add_parser("pilot-plan", help="freeze the six-case balanced feasibility design")
    pilot.add_argument("--registry", type=Path, required=True)
    pilot.add_argument("--research-workspace", type=Path)
    pilot.add_argument("--input", type=Path, required=True)
    pilot.add_argument("--seed", type=int, default=20260911)
    linking = sub.add_parser(
        "link-findings", help="import human-reviewed links between overlapping errors"
    )
    linking.add_argument("--evaluation", required=True)
    linking.add_argument("--input", type=Path, required=True)
    selectors(annotate)
    annotate.add_argument("--judge-model")
    annotate.add_argument("--registry", type=Path)
    annotate.add_argument("--research-workspace", type=Path)
    annotate.add_argument("--limit", type=int, default=1)
    annotation_mode = annotate.add_mutually_exclusive_group()
    annotation_mode.add_argument("--pairs", action="store_true")
    annotation_mode.add_argument(
        "--tasks", action="store_true", help="note-only information-finding tasks"
    )
    annotation_mode.add_argument(
        "--bank-only",
        action="store_true",
        help="source-bank review before any candidate notes are shown",
    )
    for action in ("ratings", "adjudicate"):
        rating = sub.add_parser(action)
        rating.add_argument("--sheet", required=True)
        rating.add_argument("--responses", nargs="+", type=Path, required=True)
    size = sub.add_parser(
        "sample-plan", help="freeze explicit precision and clustering assumptions"
    )
    size.add_argument("--half-width", type=float, default=0.05)
    size.add_argument("--prevalence", type=float, default=0.5)
    size.add_argument("--sessions-per-client", type=int, default=1)
    size.add_argument("--icc", type=float, default=0.0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return command(args)
    except (ValidationError, OSError, json.JSONDecodeError, RuntimeError, ImportError):
        # Artifacts can contain clinical text in paths or invalid JSON values.
        # Detailed model outputs stay private; never print traceback bodies.
        print(
            "Gen-2 stopped: invalid/incompatible artifact, unavailable file, or blocked operation. "
            "Check the private workspace and command arguments.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
