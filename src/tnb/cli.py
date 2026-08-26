"""Command line entry point.

``tnb models`` answers the question every run starts with: what does each
configured provider have deployed right now? ``tnb prompts`` shows what will be
sent to those models and can check the copied wording against its source
repositories. ``tnb generate`` writes the notes, ``tnb results index`` records
what exists, and ``tnb report`` renders it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from tnb import generation, judge, report, results, tasks
from tnb.config import REPO_ROOT, load_policy
from tnb.providers.openai_compatible import (
    DiscoveredModel,
    discover,
    fingerprint,
    group_by_fingerprint,
)

SNAPSHOT_PATH = REPO_ROOT / "docs" / "models-snapshot.md"


def _render_snapshot(provider_name: str, models: list[DiscoveredModel], today: str) -> str:
    included = [model for model in models if model.included]
    excluded = [model for model in models if not model.included]

    lines = [
        f"## {today} — live capture, provider `{provider_name}`",
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


def _probe(provider, models: list[DiscoveredModel]) -> int:
    """Ask every reported model a fixed question and group identical answers.

    Endpoints publish almost no metadata, so identity has to be measured. This
    is what produced the verified `aliases:` map in models.yaml, and it is how
    to check that map still holds after a provider redeploys. Run it against
    two providers and it also answers the harder question: is their identically
    named model the same build, or two?
    """
    digests: dict[str, str] = {}
    print(f"Probing {len(models)} models on {provider.name} (temperature 0, one prompt)...\n")
    for model in models:
        digest, excerpt = fingerprint(provider, model.id)
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
    """What every configured provider has deployed, right now.

    Reported per provider rather than merged: the same model id on two
    endpoints is two rows in this benchmark, because it can be two different
    builds. `--probe` is what tells them apart.
    """
    policy = load_policy()
    everything: dict[str, list[DiscoveredModel]] = {}

    for provider in policy.resolve(args.providers):
        models = discover(provider)
        everything[provider.name] = models
        included = [model for model in models if model.included]

        if args.probe:
            _probe(provider, models)
            continue
        if args.json:
            continue

        print(f"\n{provider.name}  ({provider.base_url})")
        for model in models:
            marker = "  " if model.included else "x "
            suffix = "" if model.included else f"   ({model.excluded_by})"
            print(f"{marker}{model.id}{suffix}")
        print(f"\n{len(included)} benchmarkable of {len(models)} reported.")

        if len(included) > provider.discovery.max_models:
            print(
                f"\nWarning: {len(included)} models exceeds max_models="
                f"{provider.discovery.max_models} for {provider.name} in models.yaml.",
                file=sys.stderr,
            )

    if args.json:
        print(
            json.dumps(
                {
                    name: [
                        {"id": m.id, "included": m.included, "excluded_by": m.excluded_by}
                        for m in models
                    ]
                    for name, models in everything.items()
                },
                indent=2,
            )
        )

    if args.write_snapshot:
        today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
        section = "\n".join(
            _render_snapshot(name, models, today) for name, models in everything.items()
        )
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


def _select_models(provider, args) -> list[str]:
    """Which models this run writes notes with, on one provider.

    ``--models`` names them explicitly; otherwise the live endpoint decides,
    filtered by models.yaml. Nothing is hard-coded either way.
    """
    if args.models:
        return [name.strip() for name in args.models.split(",") if name.strip()]

    discovered = [model.id for model in discover(provider) if model.included]
    if args.max_models:
        # Alphabetical, so "the first two" means the same two tomorrow.
        discovered = discovered[: args.max_models]
    elif len(discovered) > provider.discovery.max_models and not args.allow_large:
        raise RuntimeError(
            f"{provider.name} reports {len(discovered)} models, over max_models="
            f"{provider.discovery.max_models} in models.yaml. "
            "Re-run with --allow-large if that is intended."
        )
    return discovered


def cmd_generate(args: argparse.Namespace) -> int:
    """Write notes with every model of every configured provider.

    Providers run one after another rather than together: rate limits are per
    API key, and a second endpoint does not make the first one faster.
    """
    generation.check_cache_layout()
    policy = load_policy()
    plans = []

    for provider in policy.resolve(args.providers):
        model_ids = _select_models(provider, args)
        if not model_ids:
            print(f"{provider.name}: no models to generate with.", file=sys.stderr)
            continue

        jobs: list[generation.Job] = []
        for task in tasks.resolve(args.tasks):
            sessions = task.load_sessions(args.limit)
            jobs.extend(generation.build_jobs(provider.name, model_ids, task, sessions))
            print(
                f"{provider.name:10} {task.name:6} {len(sessions):3} sessions"
                f" x {task.calls_per_session:2} call(s)"
            )
        plans.append((provider, jobs, model_ids))

    if not plans:
        raise RuntimeError("No models to generate with.")

    pending_by_provider = [
        (
            provider,
            [job for job in jobs if args.force or generation.load_cached(job, provider) is None],
        )
        for provider, jobs, _ in plans
    ]
    total = sum(len(jobs) for _, jobs, _ in plans)
    pending_total = sum(len(jobs) for _, jobs in pending_by_provider)

    print()
    for provider, _, model_ids in plans:
        print(f"{provider.name}: {len(model_ids)} model(s) -- {', '.join(model_ids)}")
    print(
        f"\n{total} calls total, {total - pending_total} already cached, "
        f"{pending_total} to generate."
    )

    if args.dry_run:
        print("\nDry run: nothing was sent. Drop --dry-run to generate.")
        return 0
    if not pending_total:
        print("\nNothing to do; every note is cached.")
        return 0

    counts = {"cached": 0, "generated": 0, "failed": 0}
    failures: list[generation.Outcome] = []

    def on_done(outcome: generation.Outcome) -> None:
        counts[outcome.status] += 1
        if outcome.status == "failed":
            failures.append(outcome)
        done = sum(counts.values())
        print(
            f"  [{done}/{pending_total}] {outcome.job.provider}/{outcome.job.model_id} "
            f"{outcome.job.task}/{outcome.job.session_id}/{outcome.job.unit} "
            f"{outcome.status}"
            + ("" if outcome.status != "failed" else f" -- {outcome.record.get('error')}"),
            flush=True,
        )

    print()
    for provider, jobs in pending_by_provider:
        if jobs:
            generation.run_jobs(jobs, provider, force=args.force, on_done=on_done)

    print(f"\nGenerated {counts['generated']}, failed {counts['failed']}.")
    if failures:
        print("\nFailures (re-running the same command retries only these):")
        for outcome in failures[:20]:
            print(
                f"  {outcome.job.provider}/{outcome.job.model_id:24} "
                f"{outcome.job.task}/{outcome.job.session_id}"
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
    generation.check_cache_layout()
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


def _today_run_id() -> str:
    """A default label for rows this command appends, so they can be traced."""
    return "report-" + dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")


def cmd_report(args: argparse.Namespace) -> int:
    """Render results/rows.jsonl into the JSON, the page and the README block.

    Coverage is re-read from ``generations/`` on the way, unless ``--no-index``
    says otherwise. It used to be somebody's job to remember `tnb results index`
    after generating, and it went exactly as that always goes: the page reported
    iCARE as "3/3" for two days after 7 480 sections had been written, because
    the last index predated them.

    Reading the cache is cheap and it cannot be stale by construction, so the
    page now describes what is on disk rather than what was on disk the last
    time anyone ran a second command.
    """
    if not args.no_index:
        coverage = results.index_generations(run_id=args.run_id or _today_run_id())
        if coverage:
            fresh = results.append(coverage)
            print(f"indexed {len(coverage)} coverage row(s) into {fresh.relative_to(REPO_ROOT)}")

    rows = results.load()
    if not rows:
        print("No rows in results/. Generate some notes first.", file=sys.stderr)
        return 1

    data = report.write(rows)
    for table in data["tables"]:
        state = "scored" if table["scored"] else "coverage only"
        print(f"{table['track']:12} {len(table['rows']):3} rows  ({state})")

    for path in (report.DATA_PATH, report.PAGE_PATH, report.README_PATH):
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    return 0


def _generated_per_system(candidates) -> dict[tuple[str, str], int]:
    """How many usable notes each system wrote.

    Every candidate is a note that exists and that the protocol could read, so
    counting them is the generation coverage -- separate from how many the judge
    has finished reading.
    """
    counts: dict[tuple[str, str], int] = {}
    for candidate in candidates:
        key = (candidate.provider, candidate.system_id)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _money(value: float | None) -> str:
    """A dollar figure, or the word for not knowing one."""
    return "unknown" if value is None else f"${value:.2f}"


def _measure_cell(value: float | None) -> str:
    """One headline figure for the progress line, or a dash when there is none."""
    return "  -  " if value is None else f"{value:.2f}"


def cmd_score(args: argparse.Namespace) -> int:
    """Run the judge over generated notes and append the scored rows.

    Scoring is where money is spent, so nothing here happens without a ceiling:
    `--max-judge-usd` is checked before every call and the run stops rather than
    crossing it. `--dry-run` prints the size of the job and asks nothing.
    """
    from tnb.scoring import run as scoring
    from tnb.scoring import tneval as rubric

    overrides = {"model": args.judge_model}
    if getattr(args, "concurrency", None):
        overrides["concurrency"] = args.concurrency
    if getattr(args, "thinking_budget", None) is not None:
        overrides["thinking_budget"] = args.thinking_budget
    config = judge.config_from_env(**overrides)
    sessions = scoring.load_sessions(args.limit)

    candidates: list[scoring.Candidate] = []
    if args.systems in ("all", "reference"):
        candidates += list(scoring.from_reference(sessions))
    if args.systems in ("all", "models"):
        candidates += list(scoring.from_generations(sessions))
    if args.models:
        wanted = {name.strip() for name in args.models.split(",") if name.strip()}
        candidates = [c for c in candidates if c.system_id in wanted]

    # Coverage is a fact about generation and is counted here, before `--notes`
    # takes a slice for this run. Counting afterwards published the slice as the
    # model's output: `tnb score --notes 20` over a 50-session corpus reported
    # "20/50 (30 unusable)" for a model that had written all fifty. That is the
    # gemma4 libel arriving through a flag instead of through the aggregator.
    coverage = _generated_per_system(candidates)
    # How each model was actually asked, from the generation records. The
    # reference systems have no records -- their notes came from TN-Eval, not
    # from us -- so they get an empty block, which is the truth.
    settings = results.settings_by_system()
    # And a reference model was only ever asked for the sessions TN-Eval
    # published a note for, so the corpus size is not its denominator either.
    attempted = {
        key: len(sessions) if key[0] != "tneval" else count for key, count in coverage.items()
    }
    # What e-INFRA refused, so the row does not charge it to the model.
    unreached = results.unreached_by_system(results.TRACK_TNEVAL)

    if args.notes:
        candidates = candidates[: args.notes]

    if not candidates:
        raise RuntimeError(
            "Nothing to score. Generate notes first, or use --systems reference "
            "to score the notes TN-Eval released."
        )

    questions = sum(len(rubric.build_tasks(c.note, c.conversation)) for c in candidates)
    systems = sorted({(c.provider, c.system_id) for c in candidates})
    print(
        f"{len(candidates)} note(s) from {len(systems)} system(s), "
        f"{questions} judge questions.\n"
        f"judge {config.model}, thinking budget {config.thinking_budget}, "
        f"ceiling ${args.max_judge_usd:.2f}"
    )

    if args.dry_run:
        print("\nDry run: the judge was not called.")
        return 0

    client = judge.Judge(config)

    if args.cache_only:
        scored = scoring.from_cache(candidates, client)
        print(f"\n{len(scored)} note(s) already answered in full; nothing asked.")
        if not scored:
            print("Nothing complete yet.", file=sys.stderr)
            return 1
        rows = scoring.to_rows(
            scored,
            judge_model=config.model,
            judge_settings=config.fingerprint(),
            n_generated=coverage,
            n_attempted=attempted,
            n_unreached=unreached,
            settings=settings,
            run_id=args.run_id or "",
        )
        path = results.append(rows)
        print(f"Appended {len(rows)} row(s) to {path.relative_to(REPO_ROOT)}.")
        print("Run 'tnb report' to rebuild the page.")
        return 0
    spend = judge.Spend(limit_usd=args.max_judge_usd)
    done = 0

    def on_note(result: scoring.NoteResult) -> None:
        nonlocal done
        done += 1
        head = result.scores.headline
        print(
            f"  [{done}/{len(candidates)}] {result.candidate.system_id[:28]:28} "
            f"session {result.candidate.session_id:>4}  "
            # A dash, not a zero. The aggregator omits a measure it could not
            # compute; putting 0.00 back for the human watching reports a model
            # that scored nothing when nobody measured anything.
            f"completeness {_measure_cell(head.get('completeness'))}  "
            f"asked {result.asked:3} cached {result.cached:3}"
            + (f" failed {result.failed}" if result.failed else "")
            + f"  {_money(spend.usd(config.model))}",
            flush=True,
        )

    print()
    scored = scoring.score_many(candidates, client, spend, force=args.force, on_note=on_note)

    # None when the judge model has no recorded price. No total is printed
    # at all then, rather than a $0.00 that reads as a measurement.
    total = spend.usd(config.model)
    print(
        f"\nScored {len(scored)} note(s). "
        f"{spend.calls} judge calls, {spend.input_tokens} in / {spend.output_tokens} out, "
        f"{_money(total)} at list price."
    )
    if scored and total is not None:
        per_note = total / max(1, sum(1 for r in scored if r.asked))
        print(f"Cost per freshly scored note: ${per_note:.4f}")

    if args.dry_run or not scored:
        return 0

    rows = scoring.to_rows(
        scored,
        judge_model=config.model,
        judge_settings=config.fingerprint(),
        n_generated=coverage,
        n_attempted=attempted,
        n_unreached=unreached,
        settings=settings,
        run_id=args.run_id or "",
    )
    if args.no_write:
        print("\n--no-write: rows were not appended.")
        return 0

    path = results.append(rows)
    print(f"\nAppended {len(rows)} row(s) to {path.relative_to(REPO_ROOT)}.")
    print("Run 'tnb report' to rebuild the page.")
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    """Check the judge against the two therapists who rated the same notes.

    Costs nothing: it reads answers the judge has already given. If the judge
    disagrees with the therapists, that number is published too — a leaderboard
    whose referee has never been checked against a person is a table of numbers,
    not a measurement.
    """
    import json as _json

    from tnb.scoring import calibration
    from tnb.scoring import run as scoring

    sessions = scoring.load_sessions(args.limit)
    report_data = calibration.calibrate(sessions, args.judge_model)

    if not report_data.agreements:
        print(
            "No judge answers found for the notes TN-Eval released. "
            "Run 'tnb score --systems reference' first.",
            file=sys.stderr,
        )
        return 1

    print(f"Judge {report_data.judge_model} vs 2 therapists, over {report_data.notes} notes\n")
    print(
        f"{'measure':24} {'statistic':16} {'judge':>7} {'humans':>7} "
        f"{'a-judge':>8} {'a-human':>8} {'n':>6}"
    )

    def _cell(value: float | None, width: int) -> str:
        return f"{'—':>{width}}" if value is None else f"{value:{width}.2f}"

    for agreement in report_data.agreements:
        print(
            f"{agreement.name:24} {agreement.statistic:16} "
            f"{_cell(agreement.judge_mean, 7)} {_cell(agreement.human_vs_human, 7)} "
            f"{_cell(agreement.alpha_judge_mean, 8)} "
            f"{_cell(agreement.alpha_human_vs_human, 8)} "
            f"{agreement.n:6}"
        )

    verdict = report_data.rubric_beats_likert
    if verdict is not None:
        print(
            "\nTN-Eval's finding (checklists beat 1-5 scales) is "
            + ("reproduced." if verdict else "NOT reproduced.")
        )

    if args.dry_run:
        print("\nDry run: nothing written.")
        return 0

    payload = {
        "judge_model": report_data.judge_model,
        "judge_prompt_version": report_data.judge_prompt_version,
        "notes": report_data.notes,
        "rubric_beats_likert": report_data.rubric_beats_likert,
        "agreements": [
            {
                "name": a.name,
                "statistic": a.statistic,
                "alpha": a.alpha_judge_mean,
                "alpha_humans": a.alpha_human_vs_human,
                "alpha_level": a.alpha_level,
                "judge": a.judge_mean,
                "humans": a.human_vs_human,
                "n": a.n,
            }
            for a in report_data.agreements
        ],
        "per_criterion": [
            {"criterion": key, "judge": judge_value, "humans": humans}
            for key, judge_value, humans in report_data.per_criterion
        ],
    }
    report.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report.CALIBRATION_PATH.write_text(
        _json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report.update_readme(
        calibration.render_markdown(report_data), markers=report.CALIBRATION_MARKERS
    )
    print(f"\nWrote {report.CALIBRATION_PATH.relative_to(REPO_ROOT)} and the README block.")
    print("Run 'tnb report' to rebuild the page.")
    return 0


def _say_which_instrument(judge_model: str, answers) -> None:
    """Name the judge settings an analysis read, and what it left out.

    The answer cache is scoped by judge model and prompt version but not by the
    judge's settings, so during a re-scoring run it holds two. Picking the
    larger set is the right call and reporting it is the rest of the call: a
    number over 128-token answers and a number over 256-token answers are two
    instruments, and the reader has to know which one this is.
    """
    if answers.chosen_fingerprint:
        settings = ", ".join(f"{k}={v}" for k, v in sorted(answers.chosen_fingerprint.items()))
        print(f"{judge_model}: reading answers at {settings}")
    for other, count in answers.other_fingerprints.items():
        print(f"  ignoring {count} answer(s) at different settings: {other}", file=sys.stderr)


def cmd_preference(args: argparse.Namespace) -> int:
    """Does either judge score its own family higher than a neutral rater would?

    Costs nothing: it reads answers both judges have already given.
    `docs/limitations.md` has told readers to check this panel before reading
    either table since the second judge was added, and until now there was no
    panel -- the module was written, tested, and never called.
    """
    import json as _json

    from tnb.scoring import preference, saturation

    by_judge = {}
    for judge_model in (args.judge_a, args.judge_b):
        answers = saturation.load_answers(judge_model=judge_model)
        _say_which_instrument(judge_model, answers)
        if not answers:
            print(
                f"No cached answers for {judge_model!r}. Both judges must have scored "
                f"before their difference means anything.",
                file=sys.stderr,
            )
            return 1
        by_judge[judge_model] = saturation.per_session_scores(answers, args.measure)

    effects = preference.compare(by_judge, judge_a=args.judge_a, judge_b=args.judge_b)
    if not effects:
        print(
            "Nothing to report: neither judge has a family among the scored systems, "
            "or there is no system that neither of them wrote to compare against.",
            file=sys.stderr,
        )
        return 1

    for effect in effects:
        print()
        print(preference.describe(effect, args.measure))

    if args.dry_run:
        print("\nDry run: nothing written.")
        return 0

    data = {
        "measure": args.measure,
        "judge_a": args.judge_a,
        "judge_b": args.judge_b,
        "effects": [
            {
                "judge": effect.judge,
                "family": effect.family,
                "estimate": round(effect.estimate, 4),
                "low": round(effect.low, 4),
                "high": round(effect.high, 4),
                "detected": effect.detected,
                "n_own": effect.n_own,
                "n_neutral": effect.n_neutral,
                # By name, not only counted. The comparison group is what the
                # whole estimate is measured against, and a reader who cannot
                # see who is in it cannot see that a judge's own vendor is.
                "neutral": list(effect.neutral),
                "n_sessions": effect.n_sessions,
                "summary": preference.describe(effect, args.measure),
            }
            for effect in effects
        ],
    }
    report.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report.PREFERENCE_PATH.write_text(
        _json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"\nWrote {report.PREFERENCE_PATH.relative_to(REPO_ROOT)}.")
    return 0


def cmd_saturation(args: argparse.Namespace) -> int:
    """Ask whether the benchmark can still tell these models apart.

    Costs nothing: it reads answers the judge has already given. Three findings
    a ranking cannot produce on its own -- which rubric items are used up, which
    are unanswerable from a transcript, and which models the evidence genuinely
    separates.
    """
    import json as _json

    from tnb.scoring import saturation

    _say_which_instrument(args.judge_model, saturation.load_answers(judge_model=args.judge_model))
    data = saturation.build(judge_model=args.judge_model)
    if data is None:
        print(
            "No judge answers to analyse. Run 'tnb score' first.",
            file=sys.stderr,
        )
        return 1

    counts = data["verdict_counts"]
    print(f"{len(data['criteria'])} rubric criteria over {data['sessions']} shared sessions:")
    for verdict in ("saturated", "discriminating", "mixed", "unreachable"):
        if counts.get(verdict):
            print(f"  {verdict:16} {counts[verdict]:2}")

    print("\nScore with the range the evidence supports (paired bootstrap):")
    for row in data["intervals"]:
        print(f"  {row['system']:30} {row['mean']:.3f}  [{row['low']:.3f}, {row['high']:.3f}]")

    groups = data["indistinguishable"]
    print("\nGroups this evidence cannot separate, best first:")
    for index, group in enumerate(groups, start=1):
        print(f"  {index}. {', '.join(group)}")
    if all(len(group) == 1 for group in groups):
        print("  (every system is distinguishable from every other)")

    if args.dry_run:
        print("\nDry run: nothing written.")
        return 0

    report.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    # One file per judge: two judges' analyses are two analyses, and writing
    # both to one path meant the second silently replaced the first.
    path = report.saturation_path(args.judge_model)
    path.write_text(_json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nWrote {path.relative_to(REPO_ROOT)}.")
    print("Run 'tnb report' to rebuild the page.")
    return 0


def cmd_judges(args: argparse.Namespace) -> int:
    """Score the calibration set with several judges and compare them to humans.

    A judge is chosen here by measured agreement with the two therapists who
    rated the same 150 notes, not by which model is newest. Every candidate
    answers the identical questions about the identical notes, so the comparison
    is of judges and nothing else.

    Scoring a candidate is resumable and cached: a judge already run costs
    nothing to include again.
    """
    import json as _json

    from tnb.scoring import calibration
    from tnb.scoring import run as scoring

    models = (
        [name.strip() for name in args.models.split(",") if name.strip()]
        if args.models
        else list(judge.JUDGE_CANDIDATES)
    )
    sessions = scoring.load_sessions(args.limit)
    candidates = list(scoring.from_reference(sessions))
    print(
        f"{len(models)} candidate judge(s) over {len(candidates)} released notes "
        f"({len(sessions)} conversations x therapist, Llama 3.1 70B, Mistral Large V2)\n"
    )

    reports = []
    for model in models:
        config = judge.config_from_env(model=model)
        client = judge.Judge(config)
        spend = judge.Spend(limit_usd=args.max_judge_usd)

        if not args.dry_run:
            done = 0

            def on_note(result, model=model) -> None:
                nonlocal done
                done += 1
                if done % 25 == 0 or done == len(candidates):
                    print(f"  {model:24} {done}/{len(candidates)} notes", flush=True)

            scoring.score_many(candidates, client, spend, on_note=on_note)

        report_data = calibration.calibrate(sessions, model)
        if report_data.agreements:
            reports.append(report_data)

    if not reports:
        print("No judge has answers to compare yet.", file=sys.stderr)
        return 1

    measures = [
        "rubric_completeness",
        "likert_completeness",
        "likert_conciseness",
        "likert_faithfulness",
    ]
    print(f"\n{'judge':26}" + "".join(f"{m.replace('likert_', 'L-')[:16]:>17}" for m in measures))
    ceilings = {}
    for report_data in reports:
        cells = ""
        for measure in measures:
            found = next((a for a in report_data.agreements if a.name == measure), None)
            value = found.judge_mean if found else None
            if found and found.human_vs_human is not None:
                ceilings[measure] = found.human_vs_human
            cells += f"{'—' if value is None else f'{value:.2f}':>17}"
        print(f"{report_data.judge_model:26}{cells}")
    print(
        f"{'therapist vs therapist':26}"
        + "".join(f"{ceilings.get(m, float('nan')):17.2f}" for m in measures)
    )
    print("\nThe last row is the ceiling. Agreeing with a therapist as often as the")
    print("other therapist does is as well as this task allows.")

    if args.dry_run or args.no_write:
        return 0

    report.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report.JUDGES_PATH.write_text(
        _json.dumps(
            {
                "notes": reports[0].notes,
                "judges": [
                    {
                        "judge_model": r.judge_model,
                        # What this candidate was measured at. Two candidates at
                        # two thinking budgets are two instruments, and the
                        # panel that picks a judge was comparing them without
                        # saying so.
                        "judge_settings": r.judge_settings,
                        "other_settings": r.other_settings,
                        "agreements": [
                            {
                                "name": a.name,
                                "statistic": a.statistic,
                                "alpha": a.alpha_judge_mean,
                                "alpha_humans": a.alpha_human_vs_human,
                                "alpha_level": a.alpha_level,
                                "judge": a.judge_mean,
                                "humans": a.human_vs_human,
                                "n": a.n,
                            }
                            for a in r.agreements
                        ],
                        "rubric_beats_likert": r.rubric_beats_likert,
                    }
                    for r in reports
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {report.JUDGES_PATH.relative_to(REPO_ROOT)}.")
    return 0


def cmd_score_icare(args: argparse.Namespace) -> int:
    """Score the iCARE notes: two local metrics, one judge, one flag.

    Separate from `cmd_score` because the two tracks share nothing but the
    judge. This one assembles 17 section files into one note, compares it with
    an expert note, and asks five questions rather than fifty-four.
    """
    from tnb.scoring import icare as icare_scorer
    from tnb.scoring import icare_run

    overrides = {"model": args.judge_model}
    if getattr(args, "concurrency", None):
        overrides["concurrency"] = args.concurrency
    config = judge.config_from_env(**overrides)
    client = judge.Judge(config)

    sessions = icare_run.load_sessions(args.limit)
    candidates = list(icare_run.from_generations(sessions))
    if args.models:
        wanted = {name.strip() for name in args.models.split(",") if name.strip()}
        candidates = [c for c in candidates if c.system_id in wanted]

    # Counted before `--notes` takes a slice: coverage is a fact about
    # generation, not about what this invocation chose to read.
    coverage: dict[tuple[str, str], int] = {}
    for candidate in candidates:
        key = (candidate.provider, candidate.system_id)
        coverage[key] = coverage.get(key, 0) + 1
    attempted = dict.fromkeys(coverage, len(sessions))
    unreached = results.unreached_by_system(results.TRACK_ICARE)
    settings = results.settings_by_system()

    if args.notes:
        candidates = candidates[: args.notes]
    if not candidates:
        raise RuntimeError("Nothing to score. Generate the iCARE notes first.")

    questions = len(candidates) * len(icare_scorer.TRACE_DIMENSIONS)
    print(f"{len(candidates)} note(s) from {len(coverage)} system(s), {questions} TRACE questions.")
    print(f"judge {config.model}, ceiling ${args.max_judge_usd:.2f}\n")
    if args.dry_run:
        print("Dry run: the judge was not called.")
        return 0

    # BERTScore over every note at once: the model loads once instead of 640
    # times. None when the optional extra is absent, and then the column is
    # simply not reported -- never zeroed.
    # The same content-only pair ROUGE-L compares. Given the rendered notes,
    # BERTScore would score the similarity of our own 17 field titles to
    # themselves -- the identical defect, and worse, because an embedding model
    # finds "Nil" and "Nil" similar rather than merely equal.
    pairs = [icare_scorer.comparable_pair(c.note, c.reference) for c in candidates]
    bert_values = icare_scorer.bertscore(
        [note for note, _gold in pairs], [gold for _note, gold in pairs]
    )
    if bert_values is None:
        print("BERTScore: the 'scoring' extra is not installed, so that column is skipped.\n")

    spend = judge.Spend(limit_usd=args.max_judge_usd)
    done = 0

    def on_note(result: icare_run.NoteResult) -> None:
        nonlocal done
        done += 1
        if done % 20 == 0 or done == len(candidates):
            print(f"  [{done}/{len(candidates)}] {result.candidate.system_id[:30]:30}", flush=True)

    try:
        scored = icare_run.score_many(
            candidates,
            client,
            spend,
            force=args.force,
            bert=bert_values,
            on_note=on_note,
        )
    except icare_run.BudgetExceeded as stop:
        # Nothing is appended. A truncated run's averages depend on how far the
        # pool got, and results/ is append-only, so a row written now cannot be
        # withdrawn. Every answer already paid for is cached, so raising the
        # ceiling and re-running costs only what was not asked yet.
        print(f"\n{stop}", file=sys.stderr)
        print("No rows were written. Raise --max-judge-usd and run again.", file=sys.stderr)
        return 1

    if not scored:
        print("Nothing scored.", file=sys.stderr)
        return 1

    total = spend.usd(config.model)
    # None rather than 0.00 when the model has no recorded price: a run whose
    # cost is unknown must not print a number that looks measured.
    cost = "unknown" if total is None else f"${total:.2f}"
    print(f"\nAsked {spend.calls} question(s); cost {cost}.")

    rows = icare_run.to_rows(
        scored,
        judge_model=config.model,
        judge_settings=config.fingerprint(),
        n_generated=coverage,
        n_attempted=attempted,
        n_unreached=unreached,
        settings=settings,
        run_id=args.run_id or "",
    )
    path = results.append(rows)
    print(f"Appended {len(rows)} row(s) to {path.relative_to(REPO_ROOT)}.")
    print("Run 'tnb report' to rebuild the page.")
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

    models = subparsers.add_parser(
        "models", help="list what each configured provider has deployed right now"
    )
    models.add_argument(
        "--providers", help="comma-separated provider names; default is every one with a token"
    )
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
        "--providers", help="comma-separated provider names; default is every one with a token"
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

    score_icare = subparsers.add_parser(
        "score-icare", help="score the iCARE notes: ROUGE-L, BERTScore, TRACE, temporal"
    )
    score_icare.add_argument("--models", help="comma-separated system ids to score")
    score_icare.add_argument("--limit", type=int, help="use only the first N sessions")
    score_icare.add_argument("--notes", type=int, help="stop after N notes (for a pilot)")
    score_icare.add_argument(
        "--judge-model", default=judge.DEFAULT_MODEL, help="which judge runs TRACE"
    )
    score_icare.add_argument(
        "--max-judge-usd",
        type=float,
        default=250.0,
        help="runaway guard; the run stops rather than exceeding it. 0 disables it",
    )
    score_icare.add_argument(
        "--concurrency",
        type=int,
        help=(
            "parallel judge calls; default 4. This ran one note at a time until "
            "2026-08-25 and managed 0.3 answers a second against a "
            "transcript-sized prompt -- five hours for two judges over 640 notes."
        ),
    )
    score_icare.add_argument("--force", action="store_true", help="re-ask cached questions")
    score_icare.add_argument(
        "--dry-run", action="store_true", help="print the size of the job, ask nothing"
    )
    score_icare.add_argument("--run-id", default="", help="label these rows in results/")
    score_icare.set_defaults(func=cmd_score_icare)

    score = subparsers.add_parser("score", help="run the judge over generated notes (phase 3)")
    score.add_argument(
        "--systems",
        choices=["all", "models", "reference"],
        default="all",
        help="reference = the therapist-written and TN-Eval model notes only",
    )
    score.add_argument("--models", help="comma-separated system ids to score")
    score.add_argument("--limit", type=int, help="use only the first N sessions")
    score.add_argument("--notes", type=int, help="stop after N notes (for a pilot)")
    score.add_argument("--judge-model", default=judge.DEFAULT_MODEL, help="which judge to run")
    score.add_argument(
        "--max-judge-usd",
        type=float,
        default=250.0,
        # A runaway guard, not a budget. A full pass over both tracks is on the
        # order of $40; this stops a loop that has gone wrong, and is set well
        # above any run anyone means to start so that it never interrupts one.
        help="runaway guard; the run stops rather than exceeding it",
    )
    score.add_argument(
        "--concurrency",
        type=int,
        help=(
            "parallel judge calls; default 4. A full pass is ~51 000 questions, "
            "which is hours at 4. Vertex and OpenAI both rate-limit per project "
            "and both retry 429 with backoff, so this is a throughput knob, not a "
            "risk one -- unlike e-INFRA's, which is one person's academic quota."
        ),
    )
    score.add_argument(
        "--thinking-budget",
        type=int,
        help=(
            "how much room the judge gets to think; default 256. It is part of the "
            "cache key, so a run at a budget the cache does not hold asks the judge "
            "again -- and --cache-only at that budget publishes only what was "
            "answered at it, which is how a table built from two budgets is split "
            "back into the two tables it always was."
        ),
    )
    score.add_argument("--force", action="store_true", help="re-ask cached questions")
    score.add_argument(
        "--cache-only",
        action="store_true",
        help="publish the notes already answered, without asking the judge anything",
    )
    score.add_argument("--dry-run", action="store_true", help="print the job, ask nothing")
    score.add_argument(
        "--no-write", action="store_true", help="score but do not append result rows"
    )
    score.add_argument("--run-id", help="label these rows with a run id")
    score.set_defaults(func=cmd_score)

    calibrate = subparsers.add_parser(
        "calibrate", help="check the judge against TN-Eval's two human annotators (phase 4)"
    )
    calibrate.add_argument(
        "--judge-model", default=judge.DEFAULT_MODEL, help="which judge's answers to check"
    )
    calibrate.add_argument("--limit", type=int, help="use only the first N sessions")
    calibrate.add_argument("--dry-run", action="store_true", help="print, write nothing")
    calibrate.set_defaults(func=cmd_calibrate)

    saturation = subparsers.add_parser(
        "saturation", help="is there anything left to measure? (reads the answer cache)"
    )
    saturation.add_argument(
        "--judge-model", default=judge.DEFAULT_MODEL, help="whose answers to analyse"
    )
    saturation.add_argument("--dry-run", action="store_true", help="print, write nothing")
    saturation.set_defaults(func=cmd_saturation)

    pref = subparsers.add_parser(
        "preference", help="does either judge favour its own family? (reads the answer cache)"
    )
    pref.add_argument("--judge-a", default=judge.DEFAULT_MODEL)
    pref.add_argument("--judge-b", default=judge.SECOND_JUDGE)
    pref.add_argument(
        "--measure",
        default="completeness",
        help="which headline measure to estimate the effect in; default completeness",
    )
    pref.add_argument("--dry-run", action="store_true", help="print, write nothing")
    pref.set_defaults(func=cmd_preference)

    judges = subparsers.add_parser(
        "judges", help="compare candidate judges against the two human annotators (phase 4)"
    )
    judges.add_argument(
        "--models",
        help=f"comma-separated judges; default {', '.join(judge.JUDGE_CANDIDATES)}",
    )
    judges.add_argument("--limit", type=int, help="use only the first N conversations")
    judges.add_argument(
        "--max-judge-usd", type=float, default=250.0, help="runaway guard per candidate"
    )
    judges.add_argument(
        "--dry-run", action="store_true", help="compare what is cached, ask nothing"
    )
    judges.add_argument("--no-write", action="store_true", help="print without writing the JSON")
    judges.set_defaults(func=cmd_judges)

    report_parser = subparsers.add_parser(
        "report", help="regenerate the leaderboard page, its JSON and the README table"
    )
    report_parser.add_argument(
        "--no-index",
        action="store_true",
        help="do not re-read generations/ first; render exactly what results/ already holds",
    )
    report_parser.add_argument("--run-id", default="", help="label the coverage rows this appends")
    report_parser.set_defaults(func=cmd_report)

    run = subparsers.add_parser(
        "run",
        help=(
            "generate and score end to end in one command — not built yet (phase 6); "
            "until then run generate, score, score-icare and report in turn"
        ),
    )
    run.set_defaults(func=cmd_not_implemented)

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
