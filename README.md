# therapy-note-bench

**A reproducible benchmark of LLM-written psychotherapy session notes, scored
on two published protocols and re-run as models change.**

Two datasets exist for turning a therapy transcript into a clinical note. Both
were benchmarked once, on models from 2024 and 2025, and never re-run. This
repository re-runs them from a button — so the table stays true as models
change.

Which models is a question of configuration, not of design. Providers are a
swappable backend: today the harness measures what is deployed on
[e-INFRA CZ](https://www.e-infra.cz/en), and adding another provider adds rows
rather than a second benchmark.

> **Status: both tracks are measured.** **16 models** have written notes on 50
> AnnoMI conversations and on 40 iHOPE sessions, scored by two independent
> judges. On the TN-Eval track each judge is first checked against the two
> therapists who annotated the source data; TRACE, on the iCARE track, has no
> human anchor and says so wherever it appears.
>
> Every model scores above both 2025 models TN-Eval released *and* above the
> therapist-written note — on a rubric that rewards coverage, which is not the
> same as writing a better note.
>
> **The two judges agree on the shape of the ranking and not on the order**, so
> "near the top" is a claim this benchmark supports and "ninth rather than
> tenth" is not. Most systems are beaten outright by nobody, which is why no
> single winner is named. The figures are on the methods page, where a run
> keeps them current. See [Roadmap](#roadmap).

---

## The leaderboard

Full version, with per-section detail, the reference systems and a switch
between the tracks and the judges:
**<https://jannehyba.github.io/therapy-note-bench/>**

How it was measured — which judge, how far it agrees with two therapists, how
much the two judges disagree with each other, what the corpora are, and which
rows are no longer drawn:
**<https://jannehyba.github.io/therapy-note-bench/methods.html>**

<!-- LEADERBOARD:BEGIN -->
**TN-Eval SOAP · AnnoMI conversations** — scored by gemini-3.1-pro-preview (max_output_tokens 288, temperature 0, thinking_budget 256)

| Model | Provider | Completeness (0-1) | Conciseness (0-1) | Faithfulness (1-5) | Notes | Scored |
|---|---|---|---|---|---|---|
| `kimi-k3` | einfra | 0.546 | 0.885 | 4.98 | 50/50 | 50 |
| `qwen3.5-int4` | einfra | 0.535 | 0.848 | 4.92 | 50/50 | 50 |
| `qwen3.5-122b` | einfra | 0.526 | 0.814 | 4.76 | 50/50 | 50 |
| `google_gemini-3.1-pro-preview` | vertex | 0.525 | 0.878 | 4.97 | 50/50 | 50 |
| `google_gemini-3.7-flash` | vertex | 0.524 | 0.872 | 4.98 | 50/50 | 50 |
| `glm-5` | einfra | 0.502 | 0.860 | 4.96 | 50/50 | 50 |
| `glm-5.2` | einfra | 0.499 | 0.875 | 4.97 | 50/50 | 50 |
| `gpt-5.6-sol` | openai | 0.497 | 0.882 | 4.95 | 50/50 | 50 |
| `gpt-5.6-terra` | openai | 0.493 | 0.888 | 5.00 | 50/50 | 50 |
| `gpt-oss-120b` | einfra | 0.482 | 0.827 | 4.29 | 42/50 (8 unusable) | 42 |
| `deepseek-v4-flash-thinking` | einfra | 0.477 | 0.895 | 4.84 | 50/50 | 50 |
| `gpt-5.6-luna` | openai | 0.476 | 0.888 | 4.93 | 50/50 | 50 |
| `gemma4` | einfra | 0.475 | 0.898 | 4.95 | 50/50 | 50 |
| `qwen3.8-27b` | einfra | 0.471 | 0.836 | 4.94 | 50/50 | 50 |
| `mistral-medium-3.5` | einfra | 0.456 | 0.901 | 4.89 | 50/50 | 50 |
| `deepseek-v4-flash` | einfra | 0.446 | 0.915 | 4.88 | 50/50 | 50 |

*Ordered by **Completeness**. Every other column is context.*
- **Completeness** (0-1) — Fraction of the section's rubric criteria the judge found present. 0.65 means about two thirds of the required items are in the note. Counts coverage of a checklist, not judgement. A therapist writes what matters for the next session and leaves out what does not; the rubric sees what is present and cannot see why anything was left out -- which is why every model here scores above the therapist on it. This is the column the table is ordered by, so the caveat travels with the ranking: quote the number with this sentence attached, or do not quote it.
- **Conciseness** (0-1) — Fraction of the note's sentences that fit at least one rubric item. 1.00 means nothing is off-topic; it does not mean the note is short. Not a length measure, despite the name: a note twice as long scores the same if every added sentence is on topic. It is also the measure most moved by the judge's own settings -- raising the thinking budget from 128 to 256 tokens shifted all nineteen systems and reordered sixteen of them.
- **Faithfulness** (1-5) — Whether the note contradicts the transcript, rated 1 to 5, where 5 is no inaccuracies. TN-Eval's protocol has no criterion-based version of this one, so it stays a Likert scale. A different scale from the two columns beside it, and a weak one: TN-Eval measured Krippendorff's alpha of 0.18 between trained therapists on this rating. Read it as a flag for gross invention, not as a ranking.

**TN-Eval SOAP · AnnoMI conversations** — scored by gpt-5.6-terra (backend openai, effort medium, max_output_tokens 672)

| Model | Provider | Completeness (0-1) | Conciseness (0-1) | Faithfulness (1-5) | Notes | Scored |
|---|---|---|---|---|---|---|
| `kimi-k3` | einfra | 0.514 | 0.897 | 4.33 | 50/50 | 50 |
| `qwen3.5-122b` | einfra | 0.508 | 0.835 | 3.90 | 50/50 | 50 |
| `google_gemini-3.1-pro-preview` | vertex | 0.503 | 0.882 | 4.49 | 50/50 | 50 |
| `gpt-oss-120b` | einfra | 0.494 | 0.837 | 3.39 | 42/50 (8 unusable) | 42 |
| `qwen3.5-int4` | einfra | 0.490 | 0.845 | 4.37 | 50/50 | 50 |
| `gpt-5.6-terra` | openai | 0.487 | 0.892 | 4.73 | 50/50 | 50 |
| `gpt-5.6-sol` | openai | 0.478 | 0.887 | 4.76 | 50/50 | 50 |
| `google_gemini-3.7-flash` | vertex | 0.475 | 0.889 | 4.53 | 50/50 | 50 |
| `deepseek-v4-flash-thinking` | einfra | 0.473 | 0.905 | 4.09 | 50/50 | 50 |
| `glm-5` | einfra | 0.459 | 0.872 | 4.47 | 50/50 | 50 |
| `glm-5.2` | einfra | 0.459 | 0.886 | 4.41 | 50/50 | 50 |
| `gpt-5.6-luna` | openai | 0.449 | 0.866 | 4.69 | 50/50 | 50 |
| `deepseek-v4-flash` | einfra | 0.438 | 0.928 | 4.25 | 50/50 | 50 |
| `qwen3.8-27b` | einfra | 0.438 | 0.845 | 4.45 | 50/50 | 50 |
| `mistral-medium-3.5` | einfra | 0.429 | 0.917 | 4.25 | 50/50 | 50 |
| `gemma4` | einfra | 0.409 | 0.899 | 4.46 | 50/50 | 50 |

*Ordered by **Completeness**. Every other column is context.*
- **Completeness** (0-1) — Fraction of the section's rubric criteria the judge found present. 0.65 means about two thirds of the required items are in the note. Counts coverage of a checklist, not judgement. A therapist writes what matters for the next session and leaves out what does not; the rubric sees what is present and cannot see why anything was left out -- which is why every model here scores above the therapist on it. This is the column the table is ordered by, so the caveat travels with the ranking: quote the number with this sentence attached, or do not quote it.
- **Conciseness** (0-1) — Fraction of the note's sentences that fit at least one rubric item. 1.00 means nothing is off-topic; it does not mean the note is short. Not a length measure, despite the name: a note twice as long scores the same if every added sentence is on topic. It is also the measure most moved by the judge's own settings -- raising the thinking budget from 128 to 256 tokens shifted all nineteen systems and reordered sixteen of them.
- **Faithfulness** (1-5) — Whether the note contradicts the transcript, rated 1 to 5, where 5 is no inaccuracies. TN-Eval's protocol has no criterion-based version of this one, so it stays a Likert scale. A different scale from the two columns beside it, and a weak one: TN-Eval measured Krippendorff's alpha of 0.18 between trained therapists on this rating. Read it as a flag for gross invention, not as a ranking.

**TN-Eval SOAP · AnnoMI conversations** — scored by gemini-2.5-pro (max_output_tokens 160, temperature 0, thinking_budget 128)

| Model | Completeness (0-1) | Conciseness (0-1) | Faithfulness (1-5) | Notes | Scored |
|---|---|---|---|---|---|
| `kimi-k3` | 0.654 | 0.961 | 4.98 | 50/50 | 50 |
| `qwen3.5-122b` | 0.644 | 0.871 | 4.75 | 50/50 | 50 |
| `qwen3.5-int4` | 0.643 | 0.925 | 4.88 | 50/50 | 50 |
| `glm-5` | 0.597 | 0.941 | 4.95 | 50/50 | 50 |
| `deepseek-v4-flash-thinking` | 0.578 | 0.965 | 4.81 | 50/50 | 50 |
| `qwen3.8-27b` | 0.578 | 0.946 | 4.92 | 50/50 | 50 |
| `gpt-oss-120b` | 0.575 | 0.898 | 4.39 | 42/50 (8 unusable) | 42 |
| `glm-5.2` | 0.574 | 0.939 | 4.99 | 50/50 | 50 |
| `mistral-medium-3.5` | 0.558 | 0.974 | 4.88 | 50/50 | 50 |
| `gemma4` | 0.556 | 0.944 | 4.99 | 50/50 | 50 |
| `deepseek-v4-flash` | 0.524 | 0.973 | 4.80 | 50/50 | 50 |

*Ordered by **Completeness**. Every other column is context.*
- **Completeness** (0-1) — Fraction of the section's rubric criteria the judge found present. 0.65 means about two thirds of the required items are in the note. Counts coverage of a checklist, not judgement. A therapist writes what matters for the next session and leaves out what does not; the rubric sees what is present and cannot see why anything was left out -- which is why every model here scores above the therapist on it. This is the column the table is ordered by, so the caveat travels with the ranking: quote the number with this sentence attached, or do not quote it.
- **Conciseness** (0-1) — Fraction of the note's sentences that fit at least one rubric item. 1.00 means nothing is off-topic; it does not mean the note is short. Not a length measure, despite the name: a note twice as long scores the same if every added sentence is on topic. It is also the measure most moved by the judge's own settings -- raising the thinking budget from 128 to 256 tokens shifted all nineteen systems and reordered sixteen of them.
- **Faithfulness** (1-5) — Whether the note contradicts the transcript, rated 1 to 5, where 5 is no inaccuracies. TN-Eval's protocol has no criterion-based version of this one, so it stays a Likert scale. A different scale from the two columns beside it, and a weak one: TN-Eval measured Krippendorff's alpha of 0.18 between trained therapists on this rating. Read it as a flag for gross invention, not as a ranking.

**iCARE / iHOPE · 17 sections per session** — scored by gemini-3.1-pro-preview (max_output_tokens 288, temperature 0, thinking_budget 256)

| Model | Provider | ROUGE-L (0-1) | BERTScore (0-1) | TRACE (1-5) | Looks back (0-1) | Looks forward (0-1) | Notes | Scored |
|---|---|---|---|---|---|---|---|---|
| `deepseek-v4-flash` | einfra | 0.168 | 0.816 | 4.78 | 1.000 | 0.091 | 40/40 | 40 |
| `deepseek-v4-flash-thinking` | einfra | 0.170 | 0.811 | 4.87 | 1.000 | 0.182 | 40/40 | 40 |
| `gemma4` | einfra | 0.202 | 0.820 | 4.83 | 1.000 | 0.364 | 40/40 | 40 |
| `glm-5` | einfra | 0.179 | 0.820 | 4.88 | 1.000 | 0.364 | 40/40 | 40 |
| `glm-5.2` | einfra | 0.173 | 0.820 | 4.92 | 1.000 | 0.364 | 40/40 | 40 |
| `google_gemini-3.1-pro-preview` | vertex | 0.182 | 0.817 | 4.96 | 1.000 | 0.455 | 40/40 | 40 |
| `google_gemini-3.7-flash` | vertex | 0.186 | 0.819 | 4.97 | 0.971 | 0.364 | 40/40 | 40 |
| `gpt-5.6-luna` | openai | 0.150 | 0.811 | 4.92 | 1.000 | 0.273 | 40/40 | 40 |
| `gpt-5.6-sol` | openai | 0.169 | 0.816 | 4.99 | 1.000 | 0.545 | 40/40 | 40 |
| `gpt-5.6-terra` | openai | 0.155 | 0.815 | 4.97 | 0.971 | 0.455 | 40/40 | 40 |
| `gpt-oss-120b` | einfra | 0.159 | 0.808 | 4.79 | 1.000 | 0.000 | 40/40 | 40 |
| `kimi-k3` | einfra | 0.109 | 0.812 | 4.98 | 1.000 | 0.364 | 40/40 | 40 |
| `mistral-medium-3.5` | einfra | 0.186 | 0.815 | 4.87 | 1.000 | 0.182 | 40/40 | 40 |
| `qwen3.5-122b` | einfra | 0.140 | 0.815 | 4.76 | 1.000 | 0.273 | 40/40 | 40 |
| `qwen3.5-int4` | einfra | 0.182 | 0.818 | 4.97 | 1.000 | 0.091 | 40/40 | 40 |
| `qwen3.8-27b` | einfra | 0.186 | 0.819 | 4.95 | 1.000 | 0.273 | 40/40 | 40 |

*Deliberately not ranked: these columns measure different things and the source paper found they disagree.*
- **ROUGE-L** (0-1) — Longest-common-subsequence overlap with the expert note, F-measure. Rewards using the same words in the same order. Not the source paper's ROUGE-L and not comparable with their published table. Theirs compares the whole rendered note, which puts our own field labels and every `Nil` the expert wrote on both sides -- a note where the model wrote nothing at all scores 0.379 that way, above most real notes. This compares the field values of the sections the expert answered, where the same empty note scores 0.000, and every model's figure fell by about a third. It also cannot tell a good paraphrase from a wrong answer, and the source paper found it disagrees with what clinicians preferred.
- **BERTScore** (0-1) — Embedding similarity to the expert note. Tolerates paraphrase. A fluent note about the wrong session still scores well.
- **TRACE** (1-5) — Trustworthiness, relevance, accuracy, comprehensiveness and expression, each rated 1-5 by a judge and averaged. A re-implementation with no human anchor: the authors never published their ratings, so unlike the TN-Eval track this number is not calibrated against anybody.
- **Looks back** (0-1) — Section 5 only -- what happened in the previous session. The fraction of the 34 sessions whose expert note answered it where the model did too. Kept out of any average. Every model scores 0.97-1.00 here, so this column separates nobody -- it is shown because its twin does.
- **Looks forward** (0-1) — Section 17 only -- what happens at the next session. The fraction of the 11 sessions whose expert note answered it where the model did too. This is where the source paper reports every model it tested failing, and ours do too: 0.00 to 0.55. Reported apart from its twin because averaging the two turned 1.00 and 0.09 into 0.78 and hid exactly this.

**iCARE / iHOPE · 17 sections per session** — scored by gpt-5.6-terra (backend openai, effort medium, max_output_tokens 672)

| Model | Provider | ROUGE-L (0-1) | BERTScore (0-1) | TRACE (1-5) | Looks back (0-1) | Looks forward (0-1) | Notes | Scored |
|---|---|---|---|---|---|---|---|---|
| `deepseek-v4-flash` | einfra | 0.168 | 0.816 | 3.58 | 1.000 | 0.091 | 40/40 | 40 |
| `deepseek-v4-flash-thinking` | einfra | 0.170 | 0.811 | 3.74 | 1.000 | 0.182 | 40/40 | 40 |
| `gemma4` | einfra | 0.202 | 0.820 | 3.92 | 1.000 | 0.364 | 40/40 | 40 |
| `glm-5` | einfra | 0.179 | 0.820 | 3.81 | 1.000 | 0.364 | 40/40 | 40 |
| `glm-5.2` | einfra | 0.173 | 0.820 | 3.85 | 1.000 | 0.364 | 40/40 | 40 |
| `google_gemini-3.1-pro-preview` | vertex | 0.182 | 0.817 | 3.92 | 1.000 | 0.455 | 40/40 | 40 |
| `google_gemini-3.7-flash` | vertex | 0.186 | 0.819 | 3.99 | 0.971 | 0.364 | 40/40 | 40 |
| `gpt-5.6-luna` | openai | 0.150 | 0.811 | 3.96 | 1.000 | 0.273 | 40/40 | 40 |
| `gpt-5.6-sol` | openai | 0.169 | 0.816 | 4.11 | 1.000 | 0.545 | 40/40 | 40 |
| `gpt-5.6-terra` | openai | 0.155 | 0.815 | 4.04 | 0.971 | 0.455 | 40/40 | 40 |
| `gpt-oss-120b` | einfra | 0.159 | 0.808 | 3.67 | 1.000 | 0.000 | 40/40 | 40 |
| `kimi-k3` | einfra | 0.109 | 0.812 | 3.90 | 1.000 | 0.364 | 40/40 | 40 |
| `mistral-medium-3.5` | einfra | 0.186 | 0.815 | 3.75 | 1.000 | 0.182 | 40/40 | 40 |
| `qwen3.5-122b` | einfra | 0.140 | 0.815 | 3.58 | 1.000 | 0.273 | 40/40 | 40 |
| `qwen3.5-int4` | einfra | 0.182 | 0.818 | 3.87 | 1.000 | 0.091 | 40/40 | 40 |
| `qwen3.8-27b` | einfra | 0.186 | 0.819 | 3.99 | 1.000 | 0.273 | 40/40 | 40 |

*Deliberately not ranked: these columns measure different things and the source paper found they disagree.*
- **ROUGE-L** (0-1) — Longest-common-subsequence overlap with the expert note, F-measure. Rewards using the same words in the same order. Not the source paper's ROUGE-L and not comparable with their published table. Theirs compares the whole rendered note, which puts our own field labels and every `Nil` the expert wrote on both sides -- a note where the model wrote nothing at all scores 0.379 that way, above most real notes. This compares the field values of the sections the expert answered, where the same empty note scores 0.000, and every model's figure fell by about a third. It also cannot tell a good paraphrase from a wrong answer, and the source paper found it disagrees with what clinicians preferred.
- **BERTScore** (0-1) — Embedding similarity to the expert note. Tolerates paraphrase. A fluent note about the wrong session still scores well.
- **TRACE** (1-5) — Trustworthiness, relevance, accuracy, comprehensiveness and expression, each rated 1-5 by a judge and averaged. A re-implementation with no human anchor: the authors never published their ratings, so unlike the TN-Eval track this number is not calibrated against anybody.
- **Looks back** (0-1) — Section 5 only -- what happened in the previous session. The fraction of the 34 sessions whose expert note answered it where the model did too. Kept out of any average. Every model scores 0.97-1.00 here, so this column separates nobody -- it is shown because its twin does.
- **Looks forward** (0-1) — Section 17 only -- what happens at the next session. The fraction of the 11 sessions whose expert note answered it where the model did too. This is where the source paper reports every model it tested failing, and ours do too: 0.00 to 0.55. Reported apart from its twin because averaging the two turned 1.00 and 0.09 into 0.78 and hid exactly this.

**Do the two judges agree?** (TN-Eval SOAP · AnnoMI conversations)

`gemini-3.1-pro-preview` and `gpt-5.6-terra` agree on the shape of the ranking on conciseness (+0.905) and place 11 of 19 systems differently on it anyway. They agree least on faithfulness (+0.733, 15 of 19 moved). The tables can say who is near the top and who is near the bottom. They cannot say who is ninth and who is tenth. 14 system(s) beat at least one other on every measure under both judges, which needs no weighting to be true: `google_gemini-3.1-pro-preview` beats 4. 12 of 19 systems are beaten outright by nobody. That is a result too, and it is the reason this page does not name a single winner. Ordering by completeness says little about conciseness (`gemini-3.1-pro-preview` -0.38, `gpt-5.6-terra` -0.33). Ordering by completeness says different things to the two judges about faithfulness (`gemini-3.1-pro-preview` +0.56, `gpt-5.6-terra` +0.04). The two judges disagree about whether those columns are related at all, so neither reading is this benchmark's answer.

**Do the two judges agree?** (iCARE / iHOPE · 17 sections per session)

`gemini-3.1-pro-preview` and `gpt-5.6-terra` agree on the shape of the ranking on trace (+0.809) and place 11 of 16 systems differently on it anyway. The tables can say who is near the top and who is near the bottom. They cannot say who is ninth and who is tenth. 9 system(s) beat at least one other on every measure under both judges, which needs no weighting to be true: `gpt-5.6-sol` beats 6. 8 of 16 systems are beaten outright by nobody. That is a result too, and it is the reason this page does not name a single winner.

*16 icare row(s) of generation coverage at harness `0.1.0` are no longer shown: the measures were redefined in `0.2.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gemini-3.1-pro-preview` at harness `0.1.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument and the measures were redefined in `0.2.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gemini-3.1-pro-preview` at harness `0.2.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gpt-5.6-terra` at harness `0.2.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument. They stay in `results/rows.jsonl`.*

*16 tneval-soap row(s) of generation coverage at harness `0.1.0` are no longer shown: the measures were redefined in `0.2.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*14 tneval-soap row(s) scored by `gemini-2.5-pro` at harness `0.1.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument and the measures were redefined in `0.2.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gemini-3.1-pro-preview` at harness `0.1.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument and the measures were redefined in `0.2.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gpt-5.6-terra` at harness `0.1.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument and the measures were redefined in `0.2.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gemini-3.1-pro-preview` at harness `0.2.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument. They stay in `results/rows.jsonl`.*

See the [full leaderboard](https://jannehyba.github.io/therapy-note-bench/) for per-section detail, the reference systems and the published numbers.
<!-- LEADERBOARD:END -->

Numbers are only ever combined across runs that agree on all six of track,
harness version, prompt version, judge model, judge prompt version and the
settings the judge ran at. Changing the referee — or the budget it thinks with
— starts a new table rather than rewriting the old one — see
[docs/methodology.md](docs/methodology.md#comparability-over-time).

## Judge calibration

<!-- CALIBRATION:BEGIN -->
Judge **`gemini-3.1-pro-preview`** (prompts `tneval-rubric-v1`) against the two therapists TN-Eval had rate the same notes.

| Measure | Statistic | Judge vs therapist | Therapist vs therapist | Alpha, judge | Alpha, therapists | n |
|---|---|---|---|---|---|---|
| rubric completeness | Cohen's kappa | 0.60 | 0.50 | 0.60 | 0.50 | 3448 |
| likert completeness | Spearman rho | 0.24 | 0.13 | 0.11 | 0.13 | 600 |
| likert conciseness | Spearman rho | 0.11 | 0.19 | 0.03 | 0.19 | 600 |
| likert faithfulness | Spearman rho | 0.09 | 0.18 | 0.09 | 0.18 | 600 |

**The therapist-vs-therapist columns are the ceiling, not a target to beat.** Two trained therapists disagree with each other about these notes; a judge that agrees with a therapist as often as the other therapist does has done as well as the task allows.

**Why two statistics.** Cohen's kappa suits a yes/no criterion and Spearman suits a 1–5 scale, so each measure is reported under the one a reader expects. But those two are different quantities and an inequality between them means nothing, so the rubric-versus-Likert comparison below is made on **Krippendorff's alpha**, which is defined for both — nominal for the rubric, ordinal for the scales — and is the statistic TN-Eval used to reach the finding in the first place.

The judge reproduces TN-Eval's central finding: criterion checklists agree far better than 1–5 scales (alpha 0.60 against 0.11). That is why the leaderboard ranks on the rubric and reports the Likert columns with a caveat.
<!-- CALIBRATION:END -->

---

## What is measured

| Track | Corpus | Protocol | Reference needed |
|---|---|---|---|
| **TN-Eval SOAP** | 50 AnnoMI conversations | 23 completeness criteria, per-sentence conciseness, faithfulness | No |
| **iCARE / iHOPE** | 40 held-out sessions, 17 sections | ROUGE-L + BERTScore, TRACE, and two temporal columns -- looking back and looking forward | Yes |

The iCARE track reports automatic metrics and a TRACE judge **side by side
because the source paper found they disagree** — experts preferred a smaller
Mistral model over the automatic-score leader. That disagreement is a result, and
it is reported rather than averaged away.

**Two temporal columns, not one.** Looking back at the last session is something
every model does; saying what happens at the next one is something almost none of
them does. Averaged together those became a single respectable-looking number,
and the expert notes answer the backward-looking section three times as often as
the forward-looking one, so the mean was weighted towards the easy half. Split
apart, the finding the source paper reports is visible again.

**Our ROUGE-L is not comparable with the paper's table.** Theirs compares the
whole rendered note, which means both sides share the 17 field labels and every
`Nil` the expert wrote: a note where the model wrote *nothing at all* scores
0.379 that way. Ours compares the field values of the sections the expert
answered, and that same empty note scores 0.000. Losing comparability with a
published figure is the smaller of the two costs.

Full detail: [docs/methodology.md](docs/methodology.md).

## What is *not* measured

Both corpora are transcripts of public YouTube demonstration videos, not real
clinical sessions. Human agreement in the source data is weak (Krippendorff's
alpha of 0.08 on Likert completeness between trained therapists). Nothing here is
in Czech, and nothing here measures payer compliance. Small gaps between adjacent
models are noise.

Read [docs/limitations.md](docs/limitations.md) before quoting a number.

For **general medicine** rather than therapy, see
[Omi-Health/medical-note-eval](https://github.com/Omi-Health/medical-note-eval) —
a well-built maintained leaderboard that states explicitly that mental-health
notes are not tested. This repository covers the ground they exclude.

## Why the model list is not in this repository

No provider guarantees that a model version stays available — e-INFRA's
documentation says so outright. A hard-coded list would therefore be wrong
within weeks, so there is none: every run queries the provider's `/v1/models`
and filters it through rules in [`models.yaml`](models.yaml). When `glm-5.2`
becomes `glm-5.3`, the next run picks it up without anyone editing anything.

Names cannot be trusted either. `command-a` sounds like Cohere Command A and
returns `gemma4`'s exact output; six other ids turned out to be second names
for models already in the set, and three of the seven point at `gemma4`. `tnb models --probe` establishes identity by
asking each model a fixed question and comparing answers, rather than by
reading its name.

Last captured snapshot: [docs/models-snapshot.md](docs/models-snapshot.md).

## Running it

### From the Actions tab

Actions → **Benchmark** → *Run workflow*. Inputs: which providers and models
(blank means every discovered one), which tasks, and an optional session limit.

**It writes notes and rebuilds the page. It does not score them.** Scoring
needs a judge, and this workflow has only ever held one secret — the e-INFRA
token. It commits the new coverage rows and the regenerated page; the scores
come from `tnb score` and `tnb score-icare` run locally, and until those are
run the page says a model is generated and not yet judged.

This section used to say the workflow "commits the new results and regenerates
the table above", from a single `tnb run`. `tnb run` is a stub that exits 2:
the step could only ever fail, and it exported a key nothing reads and none of
the four a judge needs.

There is **no scheduled run.** The `schedule:` trigger sits commented out in
[`.github/workflows/benchmark.yml`](.github/workflows/benchmark.yml); uncomment
two lines to enable it. Nothing spends anything without a click.

### Locally

```sh
uv sync --all-groups
cp .env.example .env      # generation needs EINFRA_API_TOKEN; scoring needs a judge
make models               # what is deployed right now
uv run tnb models --probe # which ids are secretly the same model
make smoke                # 3 sessions x 2 models, e-INFRA quota only
make bench                # everything
```

An e-INFRA token comes from <https://chat.ai.e-infra.cz> → Account → API keys
and needs a MetaCentrum account or Masaryk University affiliation.

## Roadmap

| Phase | | |
|---|---|---|
| 0 | Repository, survey, model discovery | **done** |
| 1 | Dataset adapters (AnnoMI + iHOPE → common schema) | **done** |
| 2 | Generation against every discovered model | **done**, both tracks |
| 3 | Scoring: rubric, reference metrics, TRACE, temporal | **done**, both tracks, two judges |
| 4 | Judge calibration against TN-Eval's human annotators | **done** |
| 5 | Leaderboard generation | **done** |
| 6 | One-click workflow | |

## Data and licensing

The MIT licence covers **this repository's code only.** No corpus is
redistributed here. Checked repository by repository on 2026-08-24 — licence
field, file tree and README — **one of the five inputs carries a licence:**

| Source | Used for | Licence |
|---|---|---|
| [TN-Eval](https://github.com/amazon-science/TN-Eval) (code) | SOAP prompt, scoring prompts, 23-item rubric | **Apache-2.0** |
| [TN-Eval-Data](https://github.com/amazon-science/TN-Eval-Data) | 150 notes, two annotators' ratings | none published |
| [AnnoMI](https://github.com/uccollab/AnnoMI) | 133 transcripts, 50 scored | none published, citation requested |
| [iCARE](https://github.com/proadhikary/iCARE) | the 17 section instructions | none published |
| [TheraFuse](https://github.com/ai4mhx/TheraFuse) | iHOPE transcripts and expert notes | MIT badge, no `LICENSE` file |

So: prompts under Apache-2.0 are reproduced in source with attribution;
everything else is fetched from its origin when a run needs it, checksummed, and
cited. The published page shows scores and field names — never a transcript, a
note, or somebody else's prompt. Detail and the two corrections this table
records: [docs/datasets.md](docs/datasets.md), [NOTICE](NOTICE).

### The two tracks are annotated differently, and it changes what they can claim

| | TN-Eval | iCARE |
|---|---|---|
| Expert-written reference note | 50, by therapists | 174, by named clinicians |
| **Human ratings of what a model wrote** | **2 annotators × 150 notes** | **none published** |

That second row is why the judge can be calibrated on one track and not the
other. TN-Eval's annotators disagree with each other — Cohen's kappa 0.50 on the
rubric, and *negative* correlation on some Likert scales — and our judge is
measured against that ceiling rather than against an imagined truth. The iCARE
TRACE column has no such anchor and is labelled as a re-implementation
everywhere it appears.

## Credits

This benchmark is a harness around other people's work. The rubric, the prompts
and the human annotations are theirs.

- **TN-Eval** — Shah, Xu, Liu, Burnsky, Bertagnolli, Shivade. *TN-Eval: Rubric
  and Evaluation Protocols for Measuring the Quality of Behavioral Therapy
  Notes.* ACL 2025, Industry Track.
- **AnnoMI** — Wu, Balloccu, Kumar, Helaoui, Reiter, Reforgiato Recupero,
  Riboni. *Anno-MI: A Dataset of Expert-Annotated Counselling Dialogues.*
  ICASSP 2022.
- **iCARE / iHOPE** — Adhikary et al. *Clinically Grounded AI-Scribing in
  Psychotherapy: Benchmarking LLMs Against Expert Documentation in the iCARE
  Framework.* medRxiv 2025.06.25.25330252.
