"""Command line entry point.

``tnb models`` answers the question every run starts with: what is actually
deployed on e-INFRA right now? ``tnb prompts`` shows what will be sent to those
models and can check the copied wording against its source repositories.
``run`` and ``report`` are declared so the surface is visible, and fail loudly
rather than pretending to work.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from tnb import generation, results, tasks
from tnb.config import REPO_ROOT, load_policy
from tnb.providers.einfra import (
    DiscoveredModel,
    discover,
    fingerprint,
    group_by_fingerprint,
)

SNAPSHOT_PATH = REPO_ROOT / "docs" / "models-snapshot.md"


def _render_snapshot(models: list[DiscoveredModel], today: str) -> str:
    included = [model for model in models if model.included]
    excluded = [model for model in models if not model.included]

    lines = [
        f"## {today} — live capture",
        "",
        f"`GET /v1/models` reported {len(models)} models; "
        f"{len(included)} are benchmarkable after `models.yaml` filtering.",
        "",
        "| Model id | Benchmarked | Note |",
        "|---|---|---|",
    ]
    for model in models:
        mark = "yes" if model.included else "no"
        note = "" if model.included else f"`{model.excluded_by}`"
        lines.append(f"| `{model.id}` | {mark} | {note} |")
    lines.append("")
    if excluded:
        lines.append(
            f"Excluded {len(excluded)}: embeddings, speech models and unversioned "
            "aliases. See `models.yaml` for the rules."
        )
        lines.append("")
    return "\n".join(lines)


def _probe(policy, models: list[DiscoveredModel]) -> int:
    """Ask every reported model a fixed question and group identical answers.

    The endpoint publishes almost no metadata, so identity has to be measured.
    This is what produced the verified `aliases:` map in models.yaml, and it is
    how to check that map still holds after e-INFRA redeploys.
    """
    digests: dict[str, str] = {}
    print(f"Probing {len(models)} models (temperature 0, one fixed prompt)...\n")
    for model in models:
        digest, excerpt = fingerprint(policy, model.id)
        digests[model.id] = digest
        print(f"  {model.id:34} {digest or '-':10} {excerpt}")

    groups = group_by_fingerprint(digests)
    if not groups:
        print("\nNo two models answered identically: every id is its own model.")
        return 0

    print("\nIdentical answers -- these ids are the same model:")
    for canonical, aliases in sorted(groups.items()):
        print(f"  {canonical}  <-  {', '.join(aliases)}")
    print("\nCopy into models.yaml under discovery.aliases if this differs.")
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    policy = load_policy()
    models = discover(policy)
    included = [model for model in models if model.included]

    if args.probe:
        return _probe(policy, models)

    if args.json:
        print(
            json.dumps(
                [
                    {"id": m.id, "included": m.included, "excluded_by": m.excluded_by}
                    for m in models
                ],
                indent=2,
            )
        )
    else:
        for model in models:
            marker = "  " if model.included else "x "
            suffix = "" if model.included else f"   ({model.excluded_by})"
            print(f"{marker}{model.id}{suffix}")
        print(f"\n{len(included)} benchmarkable of {len(models)} reported.")

    if len(included) > policy.discovery.max_models:
        print(
            f"\nWarning: {len(included)} models exceeds max_models="
            f"{policy.discovery.max_models} in models.yaml.",
            file=sys.stderr,
        )

    if args.write_snapshot:
        today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
        section = _render_snapshot(models, today)
        existing = SNAPSHOT_PATH.read_text(encoding="utf-8")
        marker = "---\n"
        head, _, tail = existing.partition(marker)
        SNAPSHOT_PATH.write_text(f"{head}{marker}\n{section}\n{tail}", encoding="utf-8")
        print(f"\nWrote snapshot to {SNAPSHOT_PATH.relative_to(REPO_ROOT)}")

    return 0


def cmd_prompts(args: argparse.Namespace) -> int:
    """Show what will be sent to the models, and optionally check it upstream."""
    for task in tasks.TASKS.values():
        print(f"{task.name:6} {task.prompt_version:20} {task.calls_per_session} call(s)/session")

    if not args.verify:
        print("\nAdd --verify to compare the copied wording with its source repository.")
        return 0

    from tnb.tasks import fidelity

    print("\nChecking the copied prompts against their sources...")
    failed = False
    for check in fidelity.check_all():
        print(f"  {'ok  ' if check.ok else 'FAIL'} {check.name:16} {check.detail}")
        failed |= not check.ok

    if failed:
        print(
            "\nA prompt drifted from its source. Results generated before and after "
            "are not comparable: update the copy and bump prompt_version.",
            file=sys.stderr,
        )
        return 1
    return 0


def _select_models(policy, args) -> list[str]:
    """Which models this run writes notes with.

    ``--models`` names them explicitly; otherwise the live endpoint decides,
    filtered by models.yaml. Nothing is hard-coded either way.
    """
    if args.models:
        return [name.strip() for name in args.models.split(",") if name.strip()]

    discovered = [model.id for model in discover(policy) if model.included]
    if args.max_models:
        # Alphabetical, so "the first two" means the same two tomorrow.
        discovered = discovered[: args.max_models]
    elif len(discovered) > policy.discovery.max_models and not args.allow_large:
        raise RuntimeError(
            f"{len(discovered)} models exceeds max_models={policy.discovery.max_models} "
            "in models.yaml. Re-run with --allow-large if that is intended."
        )
    return discovered


def cmd_generate(args: argparse.Namespace) -> int:
    policy = load_policy()
    model_ids = _select_models(policy, args)
    if not model_ids:
        raise RuntimeError("No models to generate with.")

    jobs: list[generation.Job] = []
    for task in tasks.resolve(args.tasks):
        sessions = task.load_sessions(args.limit)
        jobs.extend(generation.build_jobs(model_ids, task, sessions))
        print(f"{task.name:6} {len(sessions):3} sessions x {task.calls_per_session:2} call(s)")

    pending = [job for job in jobs if args.force or generation.load_cached(job, policy) is None]
    print(
        f"\n{len(model_ids)} model(s): {', '.join(model_ids)}\n"
        f"{len(jobs)} calls total, {len(jobs) - len(pending)} already cached, "
        f"{len(pending)} to generate at concurrency {policy.generation.concurrency}."
    )

    if args.dry_run:
        print("\nDry run: nothing was sent. Drop --dry-run to generate.")
        return 0
    if not pending:
        print("\nNothing to do; every note is cached.")
        return 0

    counts = {"cached": 0, "generated": 0, "failed": 0}
    failures: list[generation.Outcome] = []

    def report(outcome: generation.Outcome) -> None:
        counts[outcome.status] += 1
        if outcome.status == "failed":
            failures.append(outcome)
        done = sum(counts.values())
        print(
            f"  [{done}/{len(pending)}] {outcome.job.model_id} "
            f"{outcome.job.task}/{outcome.job.session_id}/{outcome.job.unit} "
            f"{outcome.status}"
            + ("" if outcome.status != "failed" else f" -- {outcome.record.get('error')}"),
            flush=True,
        )

    print()
    generation.run_jobs(pending, policy, force=args.force, on_done=report)

    print(f"\nGenerated {counts['generated']}, failed {counts['failed']}.")
    if failures:
        print("\nFailures (re-running the same command retries only these):")
        for outcome in failures[:20]:
            print(
                f"  {outcome.job.model_id:30} {outcome.job.task}/{outcome.job.session_id}"
                f"/{outcome.job.unit}: {outcome.record.get('error')}"
            )
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")
    print(f"\nNotes are under {generation.CACHE_DIR.relative_to(REPO_ROOT)}/.")
    return 0


def cmd_results(args: argparse.Namespace) -> int:
    """Turn the generation cache into coverage rows the leaderboard can render.

    These rows carry no scores. They exist so the table's shape -- and the fact
    that one model lost sessions to its output format rather than to bad notes
    -- is visible before a single judge call is paid for.
    """
    run_id = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H-%MZ")
    rows = results.index_generations(run_id=run_id)
    if not rows:
        print(
            f"Nothing in {generation.CACHE_DIR.name}/ to index yet. Run 'tnb generate' first.",
            file=sys.stderr,
        )
        return 1

    print(f"{'system':30} {'track':12} {'generated':>9} {'failed':>7}")
    for row in rows:
        print(
            f"{row.system_id:30} {row.track:12} "
            f"{row.n_sessions_generated:>4}/{row.n_sessions_attempted:<4} {row.n_failed:>7}"
        )
        for reason, count in row.failure_reasons.items():
            print(f"{'':30} {'':12} {count:>9}x {reason}")

    if args.dry_run:
        print("\nDry run: results/rows.jsonl not touched.")
        return 0

    path = results.append(rows)
    print(f"\nAppended {len(rows)} rows to {path.relative_to(REPO_ROOT)}.")
    return 0


def cmd_not_implemented(args: argparse.Namespace) -> int:
    print(
        f"'tnb {args.command}' is not implemented yet — see the roadmap in README.md.",
        file=sys.stderr,
    )
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tnb", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    models = subparsers.add_parser("models", help="list what e-INFRA has deployed right now")
    models.add_argument("--json", action="store_true", help="machine-readable output")
    models.add_argument(
        "--probe",
        action="store_true",
        help="ask each model a fixed question and group ids that answer identically",
    )
    models.add_argument(
        "--write-snapshot",
        action="store_true",
        help="prepend a dated section to docs/models-snapshot.md",
    )
    models.set_defaults(func=cmd_models)

    prompts = subparsers.add_parser(
        "prompts", help="show the generation prompts and check them against their sources"
    )
    prompts.add_argument(
        "--verify",
        action="store_true",
        help="fetch TN-Eval and iCARE and confirm the copied wording still matches",
    )
    prompts.set_defaults(func=cmd_prompts)

    generate = subparsers.add_parser(
        "generate", help="write notes with every discovered model (phase 2)"
    )
    generate.add_argument(
        "--models",
        help="comma-separated model ids; default is whatever the endpoint reports",
    )
    generate.add_argument(
        "--max-models",
        type=int,
        help="use only the first N discovered models, alphabetically (for a smoke run)",
    )
    generate.add_argument("--tasks", help="comma-separated: soap, icare; default is both")
    generate.add_argument("--limit", type=int, help="use only the first N sessions of each task")
    generate.add_argument(
        "--force", action="store_true", help="re-generate even where a cached note exists"
    )
    generate.add_argument(
        "--dry-run", action="store_true", help="print the plan and the call count, send nothing"
    )
    generate.add_argument(
        "--allow-large",
        action="store_true",
        help="proceed even when more models are discovered than models.yaml allows",
    )
    generate.set_defaults(func=cmd_generate)

    results_parser = subparsers.add_parser(
        "results", help="record what has been generated as leaderboard rows"
    )
    results_parser.add_argument(
        "action", choices=["index"], help="index: walk the generation cache and append rows"
    )
    results_parser.add_argument(
        "--dry-run", action="store_true", help="print the rows without appending them"
    )
    results_parser.set_defaults(func=cmd_results)

    for name, help_text in (
        ("run", "generate and score notes end to end (phases 2-4)"),
        ("report", "regenerate the leaderboard (phase 5)"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.set_defaults(func=cmd_not_implemented)

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv(Path.cwd() / ".env")
    parser = build_parser()
    args = parser.parse_known_args(argv)[0]
    try:
        return args.func(args)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
