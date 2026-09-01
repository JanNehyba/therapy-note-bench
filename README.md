# therapy-note-bench

**A reproducible benchmark of LLM-written psychotherapy session notes, scored
on three published instruments — TN-Eval's SOAP rubric, PDSQI-9 and iCARE's 17
sections — and re-run as models change.**

Two datasets exist for turning a therapy transcript into a clinical note. Both
were benchmarked once, on models of the 2023–2024 era, and never re-run. This
repository re-runs them — one command per stage, with generation on a button —
so the table stays true as models change.

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
> Every model scores above both models TN-Eval released notes for — Llama 3.1
> 70B and Mistral Large v2, both from 2024 — *and* above the therapist-written
> note — on a rubric that rewards coverage, which is not the
> same as writing a better note.
>
> **The two judges agree on the shape of the ranking and not on the order**, so
> "near the top" is a claim this benchmark supports and "ninth rather than
> tenth" is not. On the table the page opens with, 8 of 19 systems are beaten
> outright by nobody — a minority, but one with no single system in it that
> beats the rest, which is why no single winner is named. The figures are on the methods page, where a run
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

A briefing on what a leaderboard of these models can and cannot tell you,
written for somebody building or buying one:
**<https://jannehyba.github.io/therapy-note-bench/brief.html>**
([PDF](https://jannehyba.github.io/therapy-note-bench/therapy-note-bench.pdf))

<!-- LEADERBOARD:BEGIN -->
**SOAP notes on AnnoMI · two instruments, the same notes** — scored by gemini-3.1-pro-preview (max_output_tokens 288, temperature 0, thinking_budget 256)

| Model | Provider | Completeness (0-1) | Conciseness (0-1) | Faithfulness (1-5) | Accurate (1-5) | Thorough (1-5) | Useful (1-5) | Organized (1-5) | Comprehensible (1-5) | Succinct (1-5) | Synthesized (1-5) | Free of stigmatizing language (0-1) | Notes | Scored |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `kimi-k3` | einfra | 0.546 | 0.886 | 4.98 | 4.98 | 4.98 | 5.00 | 5.00 | 5.00 | 2.90 | 5.00 | 0.959 | 50/50 | 50 |
| `qwen3.5-int4` | einfra | 0.535 | 0.878 | 4.92 | 4.94 | 4.90 | 5.00 | 5.00 | 5.00 | 4.00 | 5.00 | 0.940 | 50/50 | 50 |
| `qwen3.5-122b` | einfra | 0.526 | 0.904 | 4.76 | 4.72 | 4.94 | 5.00 | 5.00 | 5.00 | 3.18 | 5.00 | 0.920 | 50/50 | 50 |
| `google_gemini-3.1-pro-preview` | vertex | 0.525 | 0.893 | 4.97 | 4.98 | 4.94 | 5.00 | 5.00 | 5.00 | 3.84 | 5.00 | 0.940 | 50/50 | 50 |
| `google_gemini-3.7-flash` | vertex | 0.524 | 0.931 | 4.98 | 5.00 | 4.96 | 5.00 | 5.00 | 5.00 | 4.00 | 5.00 | 0.957 | 50/50 | 50 |
| `glm-5` | einfra | 0.502 | 0.863 | 4.96 | 4.94 | 4.96 | 5.00 | 5.00 | 5.00 | 3.73 | 5.00 | 0.939 | 50/50 | 50 |
| `glm-5.2` | einfra | 0.499 | 0.877 | 4.97 | 5.00 | 4.96 | 5.00 | 5.00 | 5.00 | 3.73 | 5.00 | 0.939 | 50/50 | 50 |
| `gpt-5.6-sol` | openai | 0.497 | 0.882 | 4.96 | 5.00 | 5.00 | 5.00 | 5.00 | 5.00 | 3.88 | 5.00 | 1.000 | 50/50 | 50 |
| `gpt-5.6-terra` | openai | 0.493 | 0.888 | 5.00 | 5.00 | 4.98 | 5.00 | 5.00 | 5.00 | 3.35 | 5.00 | 1.000 | 50/50 | 50 |
| `gpt-oss-120b` | einfra | 0.482 | 0.905 | 4.29 | 4.22 | 4.63 | 5.00 | 5.00 | 4.98 | 3.63 | 5.00 | 1.000 | 42/50 (8 unusable) | 42 |
| `deepseek-v4-flash-thinking` | einfra | 0.477 | 0.900 | 4.84 | 4.80 | 4.86 | 5.00 | 5.00 | 5.00 | 3.44 | 5.00 | 0.980 | 50/50 | 50 |
| `gpt-5.6-luna` | openai | 0.476 | 0.888 | 4.93 | 5.00 | 4.96 | 5.00 | 5.00 | 5.00 | 3.43 | 5.00 | 0.959 | 50/50 | 50 |
| `gemma4` | einfra | 0.475 | 0.897 | 4.95 | 5.00 | 4.80 | 5.00 | 5.00 | 5.00 | 4.02 | 5.00 | 0.940 | 50/50 | 50 |
| `qwen3.8-27b` | einfra | 0.471 | 0.836 | 4.94 | 5.00 | 4.92 | 5.00 | 5.00 | 5.00 | 3.55 | 5.00 | 0.980 | 50/50 | 50 |
| `mistral-medium-3.5` | einfra | 0.456 | 0.908 | 4.89 | 4.86 | 4.90 | 5.00 | 5.00 | 5.00 | 3.76 | 5.00 | 0.960 | 50/50 | 50 |
| `deepseek-v4-flash` | einfra | 0.446 | 0.919 | 4.88 | 4.63 | 4.78 | 5.00 | 5.00 | 5.00 | 3.78 | 5.00 | 0.980 | 50/50 | 50 |

*Ordered by **Completeness**. Every other column is context.*
- **Completeness** (0-1) — The equal-weighted mean of the note's four SOAP section fractions. Per section, the fraction of that section's criteria the judge found present. Counts coverage of a checklist, not judgement. All 23 rubric items are asked of every note, whatever the session was about, so an item the session never called for counts as absent exactly like one the note forgot. The figure is the equal-weighted mean of the note's four section fractions, not the fraction of all 23 items, so a four-item section counts as much as an eight-item one. This is the column the table is ordered by.
- **Conciseness** (0-1) — Fraction of the note's sentences that fit at least one rubric item. 1.00 means nothing is off-topic; it does not mean the note is short. Not a length measure, despite the name: a note twice as long scores the same if every added sentence is on topic. It is also the measure most moved by the judge's own settings -- raising the thinking budget from 128 to 256 tokens shifted all nineteen systems and reordered sixteen of them. The higher budget is what the table above is scored at; it was the budget-128 rows it was compared against that are gone -- not in results/rows.jsonl in any revision and not re-derivable, see docs/limitations.md.
- **Faithfulness** (1-5) — Whether the note contradicts the transcript, rated 1 to 5, where 5 is no inaccuracies. TN-Eval's protocol has no criterion-based version of this one, so it stays a Likert scale. A different scale from the two columns beside it, and a weak one: TN-Eval published Krippendorff's alpha 0.18 between its two therapist annotators on this rating, and recomputing it here from their released annotations gives the same. Read it as a flag for gross invention, not as a ranking.
- **PDSQI-9 columns** — The instrument was validated on multi-note clinical summaries from a corpus that excluded psychiatry, not on notes written from a single session. Its authors report Krippendorff's alpha 0.575 between trained physicians on that material -- a published ceiling, not a measurement of this judge on these notes.
- **Accurate** (1-5) — The note is true and free of incorrect information. PDSQI-9 item 2, rated 1 (not at all) to 5 (extremely).
- **Thorough** (1-5) — The note should thoroughly cover all critical patient issues. PDSQI-9 item 3, rated 1 (not at all) to 5 (extremely).
- **Useful** (1-5) — All the information is in there that is useful to the target provider/intended audience. The note is extremely relevant, providing valuable information and/or analysis. PDSQI-9 item 4, rated 1 (not at all) to 5 (extremely).
- **Organized** (1-5) — The note is well-formed and structured in a way that helps the reader understand the patient's clinical course. PDSQI-9 item 5, rated 1 (not at all) to 5 (extremely).
- **Comprehensible** (1-5) — The note is clear, without ambiguity or sections that are difficult to understand. PDSQI-9 item 6, rated 1 (not at all) to 5 (extremely).
- **Succinct** (1-5) — The note is brief, to the point, and without redundancy. PDSQI-9 item 7, rated 1 (not at all) to 5 (extremely).
- **Synthesized** (1-5) — The note reflects an understanding of the patient's status and ability to develop a plan of care. PDSQI-9 item 8, rated 1 (not at all) to 5 (extremely).
- **Free of stigmatizing language** (0-1) — The note is free of discrediting or exaggerated words, of judgment or labelling, and uses person-first language. PDSQI-9 item 9, answered yes or no and reported as the fraction of notes free of it.

**iCARE form on the iHOPE corpus · 17 sections per session** — scored by gemini-3.1-pro-preview (max_output_tokens 288, temperature 0, thinking_budget 256)

| Place | Model | Provider | ROUGE-L (0-1) | BERTScore (0-1) | TRACE (1-5) | Looks back (0-1) | Looks forward (0-1) | Notes | Scored |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `qwen3.8-27b` | einfra | 0.186 | 0.819 | 4.95 | 1.000 | 0.273 | 40/40 | 40 |
| 2 | `gpt-5.6-sol` | openai | 0.169 | 0.816 | 4.99 | 1.000 | 0.545 | 40/40 | 40 |
| 3 | `glm-5` | einfra | 0.179 | 0.820 | 4.88 | 1.000 | 0.364 | 40/40 | 40 |
| 3 | `glm-5.2` | einfra | 0.173 | 0.820 | 4.92 | 1.000 | 0.364 | 40/40 | 40 |
| 3 | `google_gemini-3.1-pro-preview` | vertex | 0.182 | 0.817 | 4.96 | 1.000 | 0.455 | 40/40 | 40 |
| 6 | `gemma4` | einfra | 0.202 | 0.820 | 4.83 | 1.000 | 0.364 | 40/40 | 40 |
| 6 | `qwen3.5-int4` | einfra | 0.183 | 0.818 | 4.97 | 1.000 | 0.091 | 39/40 (1 unreached) | 39 |
| 8 | `google_gemini-3.7-flash` | vertex | 0.186 | 0.819 | 4.97 | 0.971 | 0.364 | 40/40 | 40 |
| 9 | `mistral-medium-3.5` | einfra | 0.186 | 0.815 | 4.87 | 1.000 | 0.182 | 40/40 | 40 |
| 10 | `gpt-5.6-terra` | openai | 0.155 | 0.815 | 4.97 | 0.971 | 0.455 | 40/40 | 40 |
| 10 | `kimi-k3` | einfra | 0.109 | 0.812 | 4.98 | 1.000 | 0.364 | 40/40 | 40 |
| 12 | `gpt-5.6-luna` | openai | 0.150 | 0.811 | 4.92 | 1.000 | 0.273 | 40/40 | 40 |
| 13 | `deepseek-v4-flash-thinking` | einfra | 0.170 | 0.811 | 4.87 | 1.000 | 0.091 | 40/40 | 40 |
| 14 | `deepseek-v4-flash` | einfra | 0.168 | 0.816 | 4.78 | 1.000 | 0.091 | 40/40 | 40 |
| 14 | `qwen3.5-122b` | einfra | 0.140 | 0.815 | 4.76 | 1.000 | 0.273 | 40/40 | 40 |
| 16 | `gpt-oss-120b` | einfra | 0.159 | 0.808 | 4.79 | 1.000 | 0.000 | 40/40 | 40 |

*No column ranks this: they measure different things and the source paper found they disagree. Ordered instead by how many systems beat each one outright on every column under both judges — 11 places for 16 systems, and rows sharing a place are ones the comparison does not separate.*
- **ROUGE-L** (0-1) — Longest-common-subsequence overlap with the expert note, F-measure. Rewards using the same words in the same order. Not the source paper's ROUGE-L and not comparable with their published table. Theirs compares the whole rendered note, which puts our own field labels and every Nil the expert wrote on both sides -- a note where the model wrote nothing at all scores 0.379 that way, above most real notes. This compares the field values of the sections the expert answered, where the same empty note scores 0.000, and every model's figure fell by about a third. It also cannot tell a good paraphrase from a wrong answer, and the source paper found it disagrees with what clinicians preferred.
- **BERTScore** (0-1) — Embedding similarity to the expert note. Tolerates paraphrase. A fluent note about the wrong session still scores well.
- **TRACE** (1-5) — Trustworthiness, relevance, accuracy, comprehensiveness and expression, each rated 1-5 by a judge and averaged. A re-implementation with no human anchor: the authors never published their ratings, so unlike the TN-Eval track this number is not calibrated against anybody.
- **Looks back** (0-1) — Section 5 only -- what happened in the previous session. The fraction of the 34 sessions whose expert note answered it where the model did too. Kept out of any average. Every model scores 0.97-1.00 here, so this column separates nobody -- it is shown because its twin does.
- **Looks forward** (0-1) — Section 17 only -- what happens at the next session. The fraction of the 11 sessions whose expert note answered it where the model did too. This is where the source paper reports every model it tested failing, and ours do too: 0.00 to 0.55. Reported apart from its twin because averaging the two turned 1.00 and 0.09 into 0.78 and hid exactly this.

**Do the two judges agree?** (TN-Eval SOAP · AnnoMI conversations)

`gemini-3.1-pro-preview` and `gpt-5.6-terra` agree on the shape of the ranking on completeness (+0.895) and place 13 of 19 systems differently on it anyway. They agree least on faithfulness (+0.742, 16 of 19 moved). The tables can say who is near the top and who is near the bottom. They cannot say who is ninth and who is tenth. Systems beating at least one other on every measure under both judges, which needs no weighting to be true: 14. `google_gemini-3.7-flash` beats 10. 8 of 19 systems are beaten outright by nobody. Ordering by completeness says little about conciseness (`gemini-3.1-pro-preview` -0.02, `gpt-5.6-terra` +0.05). Ordering by completeness says different things to the two judges about faithfulness (`gemini-3.1-pro-preview` +0.56, `gpt-5.6-terra` +0.04). The two judges disagree about whether those columns are related at all, so neither reading is this benchmark's answer.

**Do the two judges agree?** (iCARE form on the iHOPE corpus · 17 sections per session)

`gemini-3.1-pro-preview` and `gpt-5.6-terra` agree on the shape of the ranking on trace (+0.826) and place 11 of 16 systems differently on it anyway. The tables can say who is near the top and who is near the bottom. They cannot say who is ninth and who is tenth. Systems beating at least one other on every measure under both judges, which needs no weighting to be true: 9. `qwen3.8-27b` beats 6. 8 of 16 systems are beaten outright by nobody.

**Do the two judges agree?** (PDSQI-9 · the SOAP notes on AnnoMI, rated for quality)

`gemini-3.1-pro-preview` and `gpt-5.6-terra` agree on the shape of the ranking on thorough (+0.833) and place 18 of 19 systems differently on it anyway. They agree least on succinct (+0.446, 18 of 19 moved). The tables can say who is near the top and who is near the bottom. They cannot say who is ninth and who is tenth. No agreement figure is given for comprehensible (18 of 19 share one value), organized (18 of 19 share one value), synthesized (18 of 19 share one value), useful (18 of 19 share one value): most systems print the same number there, so there are no orderings for the two judges to agree about, and a correlation over them would be decided by the few that differ. Systems beating at least one other on every measure under both judges, which needs no weighting to be true: 4. `gpt-5.6-sol` beats 7. 11 of 19 systems are beaten outright by nobody.

*16 icare row(s) of generation coverage at harness `0.1.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gemini-3.1-pro-preview` at harness `0.1.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) of generation coverage at harness `0.2.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gemini-3.1-pro-preview` at harness `0.2.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gpt-5.6-terra` at harness `0.2.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gemini-3.1-pro-preview` at harness `0.2.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gpt-5.6-terra` at harness `0.2.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gemini-3.1-pro-preview` at harness `0.3.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gpt-5.6-terra` at harness `0.3.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gemini-3.1-pro-preview` at harness `0.4.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gpt-5.6-terra` at harness `0.4.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) of generation coverage at harness `0.4.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gemini-3.1-pro-preview` at harness `0.5.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) scored by `gpt-5.6-terra` at harness `0.5.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 icare row(s) of generation coverage at harness `0.5.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 pdsqi-soap row(s) scored by `gemini-3.1-pro-preview` at harness `0.3.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 pdsqi-soap row(s) scored by `gpt-5.6-terra` at harness `0.3.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 pdsqi-soap row(s) scored by `gemini-3.1-pro-preview` at harness `0.4.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 pdsqi-soap row(s) scored by `gpt-5.6-terra` at harness `0.4.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 pdsqi-soap row(s) scored by `gemini-3.1-pro-preview` at harness `0.5.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 pdsqi-soap row(s) scored by `gpt-5.6-terra` at harness `0.5.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 tneval-soap row(s) of generation coverage at harness `0.1.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*14 tneval-soap row(s) scored by `gemini-2.5-pro` at harness `0.1.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.2.0` and the two are not comparable; and this judge was tried during calibration and is not one of the two the leaderboard publishes from -- every candidate is compared against the two human annotators under *Which judge* on the methods page. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gemini-3.1-pro-preview` at harness `0.1.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gpt-5.6-terra` at harness `0.1.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 tneval-soap row(s) of generation coverage at harness `0.2.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gemini-3.1-pro-preview` at harness `0.2.0` are no longer shown: the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gemini-3.1-pro-preview` at harness `0.2.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gpt-5.6-terra` at harness `0.2.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*11 tneval-soap row(s) scored by `gemini-2.5-pro` at harness `0.2.0` are no longer shown: this judge was tried during calibration and is not one of the two the leaderboard publishes from -- every candidate is compared against the two human annotators under *Which judge* on the methods page. They stay in `results/rows.jsonl`.*

*3 tneval-soap row(s) scored by `gemini-2.5-pro` at harness `0.2.0` are no longer shown: this judge was tried during calibration and is not one of the two the leaderboard publishes from -- every candidate is compared against the two human annotators under *Which judge* on the methods page. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gemini-3.1-pro-preview` at harness `0.3.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gpt-5.6-terra` at harness `0.3.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gemini-3.1-pro-preview` at harness `0.4.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gpt-5.6-terra` at harness `0.4.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 tneval-soap row(s) of generation coverage at harness `0.4.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gemini-3.1-pro-preview` at harness `0.5.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*19 tneval-soap row(s) scored by `gpt-5.6-terra` at harness `0.5.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

*16 tneval-soap row(s) of generation coverage at harness `0.5.0` are no longer shown: the measures were redefined in `0.6.0` and the two are not comparable. They stay in `results/rows.jsonl`.*

**Also scored, and not printed here.** Two judges are two instruments and two tables; the site draws one at a time and this file cannot, so it shows the one the site opens with.
- **SOAP notes on AnnoMI · two instruments, the same notes**, scored by gpt-5.6-terra (backend openai, effort medium, max_output_tokens 672) — [open it](https://jannehyba.github.io/therapy-note-bench/#tneval-soap-gpt-5.6-terra-tneval-rubric-v1-0.6.0-acf643)
- **iCARE form on the iHOPE corpus · 17 sections per session**, scored by gpt-5.6-terra (backend openai, effort medium, max_output_tokens 672) — [open it](https://jannehyba.github.io/therapy-note-bench/#icare-gpt-5.6-terra-icare-trace-v1-0.6.0-acf643)

See the [full leaderboard](https://jannehyba.github.io/therapy-note-bench/) for per-section detail, the reference systems and the published numbers, and [how it was measured](https://jannehyba.github.io/therapy-note-bench/methods.html) for the judge, the corpora and what the two judges disagree about.
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
| **PDSQI-9 on the same SOAP notes** | the same 50 AnnoMI conversations | eight of PDSQI-9's nine attributes — seven rated 1-5 and one answered yes/no; item 1 ("cited") is dropped, because a note written from a single transcript has no source documents to cite | No |
| **iCARE / iHOPE** | 40 held-out sessions, 17 sections | ROUGE-L + BERTScore, TRACE, and two temporal columns -- looking back and looking forward | Yes |

The two SOAP instruments are drawn side by side in one table and never
averaged: different questions on different scales, and neither instrument
publishes a total.

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

The two published corpora are transcripts of public YouTube demonstration
videos, not real clinical sessions. Human agreement in the source data is weak:
TN-Eval published a Krippendorff's alpha of 0.08 on Likert completeness between
its two therapists, and recomputing it here from their released annotations
gives 0.13. Nothing here measures payer compliance.

Small gaps between adjacent models are noise.

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
token. It commits the new coverage rows, the refreshed model snapshot and the README
table above. It does **not** commit the regenerated `docs/` pages — `tnb report`
writes `docs/index.html`, `docs/methods.html` and `docs/leaderboard.json`, and
the commit step stages only `results`, `docs/models-snapshot.md` and
`README.md` — so the published site does not change until `tnb report` is run
locally and `docs/` is committed by hand. The scores come from `tnb score` and
`tnb score-icare` run locally, and until those are run the page says a model is
generated and not yet judged.

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
make smoke                # 3 sessions x 2 models *per credentialled provider*
make bench                # everything
```

`--max-models` caps per provider, not in total: with `OPENAI_API_KEY` or
Vertex credentials in `.env`, `make smoke` also generates on those and spends
their money. Add `--providers einfra` to keep a run inside the e-INFRA quota.

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
redistributed here. Checked source by source on 2026-08-24 — licence
field, file tree and README — **two of the six inputs carry a licence:**

| Source | Used for | Licence |
|---|---|---|
| [PDSQI-9](https://arxiv.org/abs/2501.08977) | the nine attributes and their anchors, eight of which are scored | **CC BY 4.0** |
| [TN-Eval](https://github.com/amazon-science/TN-Eval) (code) | SOAP prompt, scoring prompts, 23-item rubric | **Apache-2.0** |
| [TN-Eval-Data](https://github.com/amazon-science/TN-Eval-Data) | 150 notes, two annotators' ratings | none published |
| [AnnoMI](https://github.com/uccollab/AnnoMI) | 133 transcripts, 50 scored | none published, citation requested |
| [iCARE](https://github.com/proadhikary/iCARE) | the 17 section instructions | none published |
| [TheraFuse](https://github.com/ai4mhx/TheraFuse) | iHOPE transcripts and expert notes | MIT badge, no `LICENSE` file |

So: prompts under Apache-2.0 are reproduced in source with attribution;
everything else is fetched from its origin when a run needs it, checksummed, and
cited. The published pages show scores, field names, TN-Eval's prompt and
rubric text (Apache-2.0, reproduced with attribution), and one worked example —
a single iHOPE note section quoted in both the clinician's and one model's
wording, to show that word overlap is not quality. No transcript is
published. Detail and the two corrections this table
records: [docs/datasets.md](docs/datasets.md), [NOTICE](NOTICE).

### The two tracks are annotated differently, and it changes what they can claim

| | TN-Eval | iCARE |
|---|---|---|
| Expert-written reference note | 50, by therapists | 174, by named clinicians |
| **Human ratings of what a model wrote** | **2 annotators × 150 notes, 100 of them model-written** | **none published** |

That second row is why the judge can be calibrated on one track and not the
other. TN-Eval's annotators disagree with each other — Cohen's kappa 0.50 on the
rubric, and weak agreement on the three 1-5 scales (Spearman rho 0.13 to
0.19) — and our judge is
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
