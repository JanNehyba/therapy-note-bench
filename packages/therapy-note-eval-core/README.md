# therapy-note-eval-core

An experimental, source-grounded evaluator of psychotherapy documentation, with
English and Czech profiles for continuity of care, supervision, client
communication and documentation audit. It evaluates notes, not therapists.

The distribution and import namespace (`therapy_note_eval`) are independent of
both existing `tnb` applications. Runtime core dependencies: Python 3.11+ only.
The optional host adapter imports the active checkout's providers and datasets.

Install this directory with `uv pip install -e packages/therapy-note-eval-core`,
or use `uv sync --all-groups --all-extras` in the main repository. Run an entirely synthetic,
offline example:

```sh
therapy-note-eval --workspace local/gen2-v3-demo demo
therapy-note-eval --workspace local/gen2-v3-demo annotate --language cs --limit 1
```

The detailed protocol, command reference, artifact definitions, validation
requirements and limitations are in [docs/gen2.md](../../docs/gen2.md).
Research tooling and the prior-exposure declaration are in
[research/gen2](../../research/gen2/README.md). The literature pool begins empty;
the demonstration's four legacy criteria are not the research instrument.
Research protocol 2.0.0 admits literature, expert and empirical inputs throughout
development while preserving origins. Software 0.3.0 / gen2-v3 requires exact
human review records and explicit assessment scope for research runs.
The main repository runs the core regression tests in `tests/test_gen2.py`
and `tests/test_gen2_research.py`.
`review.js` is an included package resource; annotation pages work offline.

No clinical corpus, generated patient notes, reference QA or human annotations
are distributed with the package. The demo's judgments are authored fixtures,
not measurements of any language model. Actual model evaluation uses the
separate `prepare`, `generate`, `segment`, `score` and `controls` commands.
