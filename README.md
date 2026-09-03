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

> **Status: both tracks are measured.** **18 models** have written notes on 50
> AnnoMI conversations and on 40 iHOPE sessions, scored by two independent LLM
> judges. On the TN-Eval track each judge is first checked against the two
> therapists who annotated the source data; TRACE, on the iCARE track, has no
> human anchor and says so wherever it appears.
>
> Every model scores higher on completeness than both models TN-Eval released
> notes for — Llama 3.1 70B and Mistral Large v2, both from 2024 — *and* than
> the therapist-written note, under either judge. Completeness rewards
> coverage, which is not the same as writing a better note: on conciseness,
> most of the models fall below at least one of those same rows.
>
> **The two judges agree on the shape of the ranking and not on the order**, so
> "near the top" is a claim this benchmark supports and "ninth rather than
> tenth" is not. Every table is ordered by the mean of each system's places over
> its instrument's columns — a declared convention, with what other weightings
> do printed beside it — and a Group column says what the evidence separates
> once every comparison is resampled: on the table the page opens with,
> 16 of 21 systems share the top group, which is why no single winner is
> named. The figures are on the methods page, where a run keeps them current. See
> [Roadmap](#roadmap).

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
**TN-Eval SOAP · AnnoMI conversations** — scored by gemini-3.1-pro-preview (max_output_tokens 288, temperature 0, thinking_budget 256)

| Place | Model | Group | Provider | Completeness (0-1) | Conciseness (0-1) | Faithfulness (1-5) | Notes | Scored |
|---|---|---|---|---|---|---|---|---|
| 1 | `google_gemini-3.7-flash` *(judge's own google)* | 1 | vertex | 0.526 | 0.933 | 4.98 | 50/50 | 50 |
| 2 | `kimi-k3` | 1 | einfra | 0.550 | 0.887 | 4.98 | 50/50 | 49 of 50 *(1 part-answered)* |
| 3 | `google_gemini-3.1-pro-preview` *(judge's own google)* | 1 | vertex | 0.534 | 0.890 | 4.97 | 50/50 | 49 of 50 *(1 part-answered)* |
| 4 | `glm-5.3` | 1 | einfra | 0.535 | 0.888 | 4.97 | 50/50 | 47 of 50 *(3 part-answered)* |
| 5 | `gpt-5.6-terra` | 1 | openai | 0.497 | 0.891 | 5.00 | 50/50 | 49 of 50 *(1 part-answered)* |
| 6 | `qwen3.5-122b` | 1 | einfra | 0.529 | 0.905 | 4.77 | 50/50 | 48 of 50 *(2 part-answered)* |
| 7 | `gpt-5.6-sol` | 1 | openai | 0.502 | 0.887 | 4.96 | 50/50 | 48 of 50 *(2 part-answered)* |
| 8 | `glm-5.2` | 1 | einfra | 0.500 | 0.875 | 4.97 | 50/50 | 50 |
| 8 | `qwen3.5-int4` | 1 | einfra | 0.536 | 0.877 | 4.92 | 50/50 | 50 |
| 10 | `glm-5` | 1 | einfra | 0.504 | 0.865 | 4.96 | 50/50 | 50 |
| 11 | `gemma4` *(judge's own google)* | 1 | einfra | 0.472 | 0.895 | 4.95 | 50/50 | 48 of 50 *(2 part-answered)* |
| 11 | `gpt-5.6-luna` | 1 | openai | 0.482 | 0.889 | 4.93 | 50/50 | 50 |
| 11 | `mistral-medium-3.5` | 2 | einfra | 0.457 | 0.909 | 4.89 | 50/50 | 50 |
| 14 | `deepseek-v4-flash` | 1 | einfra | 0.445 | 0.920 | 4.88 | 50/50 | 50 |
| 15 | `gpt-oss-120b` | 1 | einfra | 0.482 | 0.905 | 4.29 | 42/50 (8 unusable) | 41 of 42 *(1 part-answered)* |
| 16 | `deepseek-v4-flash-thinking` | 1 | einfra | 0.473 | 0.901 | 4.83 | 50/50 | 48 of 50 *(2 part-answered)* |
| 17 | `qwen3.8-27b` | 2 | einfra | 0.477 | 0.835 | 4.94 | 50/50 | 49 of 50 *(1 part-answered)* |
| 18 | `qwen3.8-flash-next` | 2 | einfra | 0.477 | 0.854 | 4.88 | 48/50 (2 unreached) | 48 |

*Ordered by **mean place** over the 3 columns of this instrument, every column counting once — a convention, not a measurement: the columns do not predict each other. Under the other weightings tried (each column counted twice, and the reference rows removed) first place is held by `google_gemini-3.7-flash`; at most 18 of 21 systems change place and none by more than 7 ([how the order was built](https://jannehyba.github.io/therapy-note-bench/methods.html#ordering)). Places are among all 21 rows of the table, the reference systems included, so the models' places can have gaps.* *Group: what the evidence separates. A system stands above another only when it is at least as good on every column under both judges in 0.95 of the resampled conversations; 3 group(s) for 21 systems, 16 of them beaten by no tested comparison ([how the comparisons were tested](https://jannehyba.github.io/therapy-note-bench/methods.html#groups)).* ***Completeness** is the only column checked against people; it counts once in the order, like every other.*
- **Completeness** (0-1) — The equal-weighted mean of the note's four SOAP section fractions. Per section, the fraction of that section's criteria the judge found present. Counts coverage of a checklist, not judgement. All 23 rubric items are asked of every note, whatever the session was about, so an item the session never called for counts as absent exactly like one the note forgot. The figure is the equal-weighted mean of the note's four section fractions, not the fraction of all 23 items, so a four-item section counts as much as an eight-item one. It is the only column here checked against two therapists' ratings; the table's order is a mean of places over all its columns.
- **Conciseness** (0-1) — The equal-weighted mean of the note's four section fractions: per section, the fraction of that section's sentences that fit at least one rubric item. 1.00 means nothing is off-topic; it does not mean the note is short. Not a length measure, despite the name: a note twice as long scores the same if every added sentence is on topic. It is also the measure most moved by the judge's own settings -- raising the thinking budget from 128 to 256 tokens shifted all nineteen systems on the table as it stood in August 2026 and reordered sixteen of them. The two systems added since were never scored at the lower budget, so the measurement is not re-run when the table grows. The higher budget is what the table above is scored at; it was the budget-128 rows it was compared against that are gone -- not in results/rows.jsonl in any revision and not re-derivable, see docs/limitations.md.
- **Faithfulness** (1-5) — Whether the note contradicts the transcript, rated 1 to 5, where 5 is no inaccuracies. TN-Eval's protocol has no criterion-based version of this one, so it stays a Likert scale. A different scale from the two columns beside it, and a weak one: TN-Eval published Krippendorff's alpha 0.18 between its two therapist annotators on this rating, and recomputing it here from their released annotations gives the same. Read it as a flag for gross invention, not as a ranking.

**iCARE form on the iHOPE corpus · 17 sections per session** — scored by gemini-3.1-pro-preview (max_output_tokens 288, temperature 0, thinking_budget 256)

| Place | Model | Group | Provider | ROUGE-L (0-1) | BERTScore (0-1) | TRACE (1-5) | Looks back (0-1) | Looks forward (0-1) | Notes | Scored |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `qwen3.8-flash-next` | 1 | einfra | 0.192 | 0.821 | 4.98 | 1.00 | 0.27 | 39/40 (1 unreached) | 39 |
| 2 | `gemma4` *(judge's own google)* | 1 | einfra | 0.202 | 0.820 | 4.83 | 1.00 | 0.36 | 40/40 | 40 |
| 2 | `gpt-5.6-sol` | 1 | openai | 0.169 | 0.816 | 4.99 | 1.00 | 0.55 | 40/40 | 40 |
| 4 | `google_gemini-3.1-pro-preview` *(judge's own google)* | 1 | vertex | 0.182 | 0.817 | 4.96 | 1.00 | 0.45 | 40/40 | 40 |
| 5 | `glm-5.2` | 1 | einfra | 0.173 | 0.820 | 4.92 | 1.00 | 0.36 | 40/40 | 40 |
| 6 | `glm-5` | 1 | einfra | 0.179 | 0.820 | 4.88 | 1.00 | 0.36 | 40/40 | 40 |
| 6 | `qwen3.8-27b` | 1 | einfra | 0.186 | 0.819 | 4.95 | 1.00 | 0.27 | 40/40 | 40 |
| 8 | `qwen3.5-int4` | 1 | einfra | 0.183 | 0.818 | 4.97 | 1.00 | 0.09 | 39/40 (1 unreached) | 39 |
| 9 | `google_gemini-3.7-flash` *(judge's own google)* | 1 | vertex | 0.186 | 0.819 | 4.97 | 0.97 | 0.36 | 40/40 | 40 |
| 10 | `glm-5.3` | 1 | einfra | 0.113 | 0.814 | 4.96 | 1.00 | 0.73 | 40/40 | 40 |
| 11 | `kimi-k3` | 1 | einfra | 0.109 | 0.812 | 4.98 | 1.00 | 0.36 | 40/40 | 40 |
| 12 | `mistral-medium-3.5` | 1 | einfra | 0.186 | 0.815 | 4.87 | 1.00 | 0.18 | 40/40 | 40 |
| 13 | `gpt-5.6-terra` | 1 | openai | 0.155 | 0.815 | 4.97 | 0.97 | 0.45 | 40/40 | 40 |
| 14 | `gpt-5.6-luna` | 2 | openai | 0.150 | 0.811 | 4.92 | 1.00 | 0.27 | 40/40 | 40 |
| 15 | `deepseek-v4-flash` | 1 | einfra | 0.168 | 0.816 | 4.78 | 1.00 | 0.09 | 40/40 | 40 |
| 16 | `deepseek-v4-flash-thinking` | 1 | einfra | 0.170 | 0.811 | 4.87 | 1.00 | 0.09 | 40/40 | 40 |
| 17 | `qwen3.5-122b` | 2 | einfra | 0.140 | 0.815 | 4.76 | 1.00 | 0.27 | 40/40 | 40 |
| 18 | `gpt-oss-120b` | 2 | einfra | 0.159 | 0.808 | 4.79 | 1.00 | 0.00 | 40/40 | 40 |

*Ordered by **mean place** over the 5 columns of this instrument, every column counting once — a convention, not a measurement: the columns do not predict each other. Under the other weightings tried (each column counted twice, and the reference rows removed) first place is held by `gpt-5.6-sol`, `qwen3.8-flash-next`; at most 14 of 18 systems change place and none by more than 6 ([how the order was built](https://jannehyba.github.io/therapy-note-bench/methods.html#ordering)). Places are among all 18 rows of the table, the reference systems included, so the models' places can have gaps.* *Group: what the evidence separates. A system stands above another only when it is at least as good on every column under both judges in 0.95 of the resampled conversations; 2 group(s) for 18 systems, 15 of them beaten by no tested comparison ([how the comparisons were tested](https://jannehyba.github.io/therapy-note-bench/methods.html#groups)).*
- **ROUGE-L** (0-1) — Longest-common-subsequence overlap with the expert note, F-measure. Rewards using the same words in the same order. Not the source paper's ROUGE-L and not comparable with their published table. Theirs compares the whole rendered note, which puts our own field labels and every Nil the expert wrote on both sides -- a note where the model wrote nothing at all scores 0.379 that way, above most real notes. This compares the field values of the sections the expert answered, where the same empty note scores 0.000, and every model's figure fell by about a third. It also cannot tell a good paraphrase from a wrong answer, and the source paper found it disagrees with what clinicians preferred. It also falls as notes get longer; where this table has a Words column, the correlation between the two is printed under it.
- **BERTScore** (0-1) — Embedding similarity to the expert note. Tolerates paraphrase. A fluent note about the wrong session still scores well.
- **TRACE** (1-5) — Trustworthiness, relevance, accuracy, comprehensiveness and expression, each rated 1-5 by a judge and averaged. A re-implementation with no human anchor: the authors never published their ratings, so unlike the TN-Eval track this number is not calibrated against anybody.
- **Looks back** (0-1) — Section 5 only -- what happened in the previous session. The fraction of the 34 sessions whose expert note answered it where the model did too. Counts once in the order like every column, and moves it little: the models are packed at the top of it, so it separates nobody -- it is shown because its twin does.
- **Looks forward** (0-1) — Section 17 only -- what happens at the next session. The fraction of the 11 sessions whose expert note answered it where the model did too. This is where the source paper reports every model it tested failing, and ours do too -- the column beside this note is the whole spread. Reported apart from its twin because averaging the two turned 1.00 and 0.09 into 0.78 and hid exactly this.

**PDSQI-9 · the SOAP notes on AnnoMI, rated for quality** — scored by gemini-3.1-pro-preview (max_output_tokens 288, temperature 0, thinking_budget 256)

| Place | Model | Group | Provider | Accurate (1-5) | Thorough (1-5) | Useful (1-5) | Organized (1-5) | Comprehensible (1-5) | Succinct (1-5) | Synthesized (1-5) | Free of stigmatizing language (0-1) | Notes | Scored |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `gpt-5.6-sol` | 1 | openai | 5.00 | 5.00 | 5.00 | 5.00 | 5.00 | 3.88 | 5.00 | 1.000 | 50/50 | 50 |
| 2 | `qwen3.8-flash-next` | 1 | einfra | 5.00 | 4.96 | 5.00 | 5.00 | 5.00 | 3.55 | 5.00 | 1.000 | 48/50 (2 unreached) | 47 of 48 *(1 part-answered)* |
| 3 | `google_gemini-3.7-flash` *(judge's own google)* | 1 | vertex | 5.00 | 4.96 | 5.00 | 5.00 | 5.00 | 4.00 | 5.00 | 0.957 | 50/50 | 47 of 50 *(3 part-answered)* |
| 4 | `gpt-5.6-terra` | 1 | openai | 5.00 | 4.98 | 5.00 | 5.00 | 5.00 | 3.35 | 5.00 | 1.000 | 50/50 | 49 of 50 *(1 part-answered)* |
| 5 | `qwen3.8-27b` | 1 | einfra | 5.00 | 4.92 | 5.00 | 5.00 | 5.00 | 3.55 | 5.00 | 0.980 | 50/50 | 49 of 50 *(1 part-answered)* |
| 6 | `gemma4` *(judge's own google)* | 1 | einfra | 5.00 | 4.80 | 5.00 | 5.00 | 5.00 | 4.02 | 5.00 | 0.940 | 50/50 | 50 |
| 6 | `glm-5.2` | 1 | einfra | 5.00 | 4.96 | 5.00 | 5.00 | 5.00 | 3.73 | 5.00 | 0.939 | 50/50 | 49 of 50 *(1 part-answered)* |
| 8 | `gpt-5.6-luna` | 1 | openai | 5.00 | 4.96 | 5.00 | 5.00 | 5.00 | 3.43 | 5.00 | 0.959 | 50/50 | 49 of 50 *(1 part-answered)* |
| 9 | `google_gemini-3.1-pro-preview` *(judge's own google)* | 1 | vertex | 4.98 | 4.94 | 5.00 | 5.00 | 5.00 | 3.84 | 5.00 | 0.940 | 50/50 | 50 |
| 10 | `qwen3.5-int4` | 1 | einfra | 4.94 | 4.90 | 5.00 | 5.00 | 5.00 | 4.00 | 5.00 | 0.940 | 50/50 | 50 |
| 11 | `kimi-k3` | 1 | einfra | 4.98 | 4.98 | 5.00 | 5.00 | 5.00 | 2.90 | 5.00 | 0.959 | 50/50 | 49 of 50 *(1 part-answered)* |
| 12 | `glm-5` | 1 | einfra | 4.94 | 4.96 | 5.00 | 5.00 | 5.00 | 3.73 | 5.00 | 0.939 | 50/50 | 49 of 50 *(1 part-answered)* |
| 13 | `mistral-medium-3.5` | 1 | einfra | 4.86 | 4.90 | 5.00 | 5.00 | 5.00 | 3.76 | 5.00 | 0.960 | 50/50 | 50 |
| 14 | `glm-5.3` | 1 | einfra | 4.98 | 4.98 | 5.00 | 5.00 | 5.00 | 2.84 | 5.00 | 0.940 | 50/50 | 50 |
| 15 | `deepseek-v4-flash` | 1 | einfra | 4.63 | 4.78 | 5.00 | 5.00 | 5.00 | 3.78 | 5.00 | 0.980 | 50/50 | 49 of 50 *(1 part-answered)* |
| 17 | `deepseek-v4-flash-thinking` | 1 | einfra | 4.80 | 4.86 | 5.00 | 5.00 | 5.00 | 3.44 | 5.00 | 0.980 | 50/50 | 50 |
| 18 | `qwen3.5-122b` | 1 | einfra | 4.72 | 4.94 | 5.00 | 5.00 | 5.00 | 3.18 | 5.00 | 0.920 | 50/50 | 50 |
| 19 | `gpt-oss-120b` | 2 | einfra | 4.22 | 4.63 | 5.00 | 5.00 | 4.98 | 3.63 | 5.00 | 1.000 | 42/50 (8 unusable) | 41 of 42 *(1 part-answered)* |

*Ordered by **mean place** over the 8 columns of this instrument, every column counting once — a convention, not a measurement: the columns do not predict each other. Under the other weightings tried (each column counted twice, and the reference rows removed) first place is held by `gpt-5.6-sol`; at most 16 of 21 systems change place and none by more than 7 ([how the order was built](https://jannehyba.github.io/therapy-note-bench/methods.html#ordering)). Places are among all 21 rows of the table, the reference systems included, so the models' places can have gaps.* *Group: what the evidence separates. A system stands above another only when it is at least as good on every column under both judges in 0.95 of the resampled conversations; 2 group(s) for 21 systems, 20 of them beaten by no tested comparison ([how the comparisons were tested](https://jannehyba.github.io/therapy-note-bench/methods.html#groups)).*
- **PDSQI-9 columns** — The instrument was validated on multi-note clinical summaries from a corpus that excluded psychiatry, not on notes written from a single session. Its authors report Krippendorff's alpha 0.575 between trained physicians on that material -- a published ceiling, not a measurement of this judge on these notes. Three of the eight -- accurate, succinct and free of stigmatising language -- can be won by saying nothing: an empty note scores 5.00, 5.00 and 1.00 on them, so read them as things a note can fail, never as things it can win.
- **Accurate** (1-5) — The note is true and free of incorrect information. PDSQI-9 item 2, rated 1 (not at all) to 5 (extremely).
- **Thorough** (1-5) — The note should thoroughly cover all critical patient issues. PDSQI-9 item 3, rated 1 (not at all) to 5 (extremely).
- **Useful** (1-5) — All the information is in there that is useful to the target provider/intended audience. The note is extremely relevant, providing valuable information and/or analysis. PDSQI-9 item 4, rated 1 (not at all) to 5 (extremely).
- **Organized** (1-5) — The note is well-formed and structured in a way that helps the reader understand the patient's clinical course. PDSQI-9 item 5, rated 1 (not at all) to 5 (extremely).
- **Comprehensible** (1-5) — The note is clear, without ambiguity or sections that are difficult to understand. PDSQI-9 item 6, rated 1 (not at all) to 5 (extremely).
- **Succinct** (1-5) — The note is brief, to the point, and without redundancy. PDSQI-9 item 7, rated 1 (not at all) to 5 (extremely).
- **Synthesized** (1-5) — The note reflects an understanding of the patient's status and ability to develop a plan of care. PDSQI-9 item 8, rated 1 (not at all) to 5 (extremely).
- **Free of stigmatizing language** (0-1) — The note is free of discrediting or exaggerated words, of judgment or labelling, and uses person-first language. PDSQI-9 item 9, answered yes or no and reported as the fraction of notes free of it.

**Do the two judges agree?** (TN-Eval SOAP · AnnoMI conversations)

`gemini-3.1-pro-preview` and `gpt-5.6-terra` agree on the shape of the ranking on completeness (+0.894) and place 16 of 21 systems differently on it anyway. They agree least on faithfulness (+0.695, 19 of 21 moved). The tables can say who is near the top and who is near the bottom. They cannot say who is ninth and who is tenth. Systems beating at least one other on every measure under both judges, which needs no weighting to be true: 16. `google_gemini-3.7-flash` beats 11. 9 of 21 systems are beaten outright by nobody on the figures as printed. The Group column asks the same question of the same comparisons and keeps a lead only where it also survives resampling, which is the stricter test: its top group is larger than this count, because a lead too small to survive leaves both systems unseparated. Completeness says little about conciseness (`gemini-3.1-pro-preview` -0.05, `gpt-5.6-terra` +0.10). Completeness says different things to the two judges about faithfulness (`gemini-3.1-pro-preview` +0.61, `gpt-5.6-terra` +0.01). The two judges disagree about whether those columns are related at all, so neither reading is this benchmark's answer.

**Do the two judges agree?** (iCARE form on the iHOPE corpus · 17 sections per session)

`gemini-3.1-pro-preview` and `gpt-5.6-terra` agree on the shape of the ranking on trace (+0.769) and place 12 of 18 systems differently on it anyway. The tables can say who is near the top and who is near the bottom. They cannot say who is ninth and who is tenth. Systems beating at least one other on every measure under both judges, which needs no weighting to be true: 10. `qwen3.8-flash-next` beats 8. 8 of 18 systems are beaten outright by nobody on the figures as printed. The Group column asks the same question of the same comparisons and keeps a lead only where it also survives resampling, which is the stricter test: its top group is larger than this count, because a lead too small to survive leaves both systems unseparated.

**Do the two judges agree?** (PDSQI-9 · the SOAP notes on AnnoMI, rated for quality)

`gemini-3.1-pro-preview` and `gpt-5.6-terra` agree on the shape of the ranking on thorough (+0.766) and place 18 of 21 systems differently on it anyway. They agree least on succinct (+0.490, 21 of 21 moved). The tables can say who is near the top and who is near the bottom. They cannot say who is ninth and who is tenth. No agreement figure is given for comprehensible (20 of 21 share one value), organized (20 of 21 share one value), synthesized (20 of 21 share one value), useful (20 of 21 share one value): most systems print the same number there, so there are no orderings for the two judges to agree about, and a correlation over them would be decided by the few that differ. Systems beating at least one other on every measure under both judges, which needs no weighting to be true: 4. `gpt-5.6-sol` beats 8. 12 of 21 systems are beaten outright by nobody on the figures as printed. The Group column asks the same question of the same comparisons and keeps a lead only where it also survives resampling, which is the stricter test: its top group is larger than this count, because a lead too small to survive leaves both systems unseparated.

**Is there one ranking? Only as a profile.** [All six rankings, one row per model](https://jannehyba.github.io/therapy-note-bench/) puts every one of the 18 models beside the rank each of the 6 tables gives it, and adds nothing up. A total over the three instruments would have to say what a SOAP rubric is worth against a 17-field form, which is a clinical judgement and not a measurement these numbers can be asked for.

The two judges rank one instrument alike at Spearman +0.819 to +0.951; two different instruments reach −0.278 to +0.715. iCARE against TN-Eval rubric reaches −0.278 to +0.047, which is no relation at all.

It is not the corpora that differ: PDSQI-9 and TN-Eval rubric are scored on the identical notes from the identical conversations, and their orders still agree only +0.038 to +0.361.

Only the wider claim is published, because the sharper one does not survive: with each of the 18 models left out in turn, one instrument under two judges never falls below +0.758 and iCARE against TN-Eval rubric never rises above +0.229, so those two bands never meet.

**And the disagreement is not the instruments measuring different things.** Between individual columns, where no ordering rule is involved, columns of different instruments predict each other about as well as columns of the same one: median |rho| 0.406 against 0.180 under `gemini-3.1-pro-preview`; 0.395 against 0.344 under `gpt-5.6-terra`. Whatever separates the six orders happens in the averaging of places, not in the measurements.

Pooled over all three instruments nothing is separated at all: no model is at least as good as another on every one of the 32 column-legs under both judges, 0 of 306 ordered pairs. Part of that is arithmetic rather than a finding, and the same count inside one instrument shows it (TN-Eval rubric separates 20 of 306 on 6; iCARE separates 40 of 306 on 10; PDSQI-9 separates 11 of 306 on 16). 12 of the 18 models are left undominated by every instrument, which is this benchmark's honest answer to “which model”.

**Rows that were published and are no longer shown** — 795 in 47 group(s), every one still in `results/rows.jsonl`.

| Rows | Track | Judge | At harness | Why |
|---|---|---|---|---|
| 80 | icare | *generation coverage* | `0.1.0`, `0.2.0`, `0.4.0`, `0.5.0`, `0.6.0` | the measures were redefined in `0.7.0` and the two are not comparable |
| 80 | icare | `gemini-3.1-pro-preview` | `0.2.0`, `0.3.0`, `0.4.0`, `0.5.0`, `0.6.0` | the measures were redefined in `0.7.0` and the two are not comparable |
| 32 | icare | `gemini-3.1-pro-preview` | `0.1.0`, `0.2.0` | the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.7.0` and the two are not comparable |
| 80 | icare | `gpt-5.6-terra` | `0.2.0`, `0.3.0`, `0.4.0`, `0.5.0`, `0.6.0` | the measures were redefined in `0.7.0` and the two are not comparable |
| 16 | icare | `gpt-5.6-terra` | `0.2.0` | the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.7.0` and the two are not comparable |
| 76 | pdsqi-soap | `gemini-3.1-pro-preview` | `0.3.0`, `0.4.0`, `0.5.0`, `0.6.0` | the measures were redefined in `0.7.0` and the two are not comparable |
| 76 | pdsqi-soap | `gpt-5.6-terra` | `0.3.0`, `0.4.0`, `0.5.0`, `0.6.0` | the measures were redefined in `0.7.0` and the two are not comparable |
| 80 | tneval-soap | *generation coverage* | `0.1.0`, `0.2.0`, `0.4.0`, `0.5.0`, `0.6.0` | the measures were redefined in `0.7.0` and the two are not comparable |
| 14 | tneval-soap | `gemini-2.5-pro` | `0.2.0` | this judge was tried during calibration and is not one of the two the leaderboard publishes from -- every candidate is compared against the two human annotators under *Which judge* on the methods page |
| 14 | tneval-soap | `gemini-2.5-pro` | `0.1.0` | the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.2.0` and the two are not comparable; and this judge was tried during calibration and is not one of the two the leaderboard publishes from -- every candidate is compared against the two human annotators under *Which judge* on the methods page |
| 95 | tneval-soap | `gemini-3.1-pro-preview` | `0.2.0`, `0.3.0`, `0.4.0`, `0.5.0`, `0.6.0` | the measures were redefined in `0.7.0` and the two are not comparable |
| 38 | tneval-soap | `gemini-3.1-pro-preview` | `0.1.0`, `0.2.0` | the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.7.0` and the two are not comparable |
| 95 | tneval-soap | `gpt-5.6-terra` | `0.2.0`, `0.3.0`, `0.4.0`, `0.5.0`, `0.6.0` | the measures were redefined in `0.7.0` and the two are not comparable |
| 19 | tneval-soap | `gpt-5.6-terra` | `0.1.0` | the judge's settings were not recorded, so the rows cannot be shown to have come from one instrument; and the measures were redefined in `0.7.0` and the two are not comparable |

**Also scored, and not printed here.** Two judges are two instruments and two tables; the site draws one at a time and this file cannot, so it shows the one the site opens with.
- **TN-Eval SOAP · AnnoMI conversations**, scored by gpt-5.6-terra (backend openai, effort medium, max_output_tokens 672) — [open it](https://jannehyba.github.io/therapy-note-bench/#tneval-soap-gpt-5.6-terra-tneval-rubric-v1-0.7.0-acf643)
- **iCARE form on the iHOPE corpus · 17 sections per session**, scored by gpt-5.6-terra (backend openai, effort medium, max_output_tokens 672) — [open it](https://jannehyba.github.io/therapy-note-bench/#icare-gpt-5.6-terra-icare-trace-v1-0.7.0-acf643)
- **PDSQI-9 · the SOAP notes on AnnoMI, rated for quality**, scored by gpt-5.6-terra (backend openai, effort medium, max_output_tokens 672) — [open it](https://jannehyba.github.io/therapy-note-bench/#pdsqi-soap-gpt-5.6-terra-pdsqi9-note-v1-0.7.0-acf643)

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

The two SOAP instruments are two tables under one switch and are never
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
| 6 | One-click workflow | **generation only** — the button writes notes; scoring is run by hand, because the workflow holds no judge credential |

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

This benchmark is a harness around other people's work. The rubric, the prompts,
the instruments and the human annotations are theirs. The leaderboard cites them
in the text beside each instrument's description; the works, in APA form:

- Adhikary, P. K., Mukherjee, A., Deb, K. S., Singh, S., Singh, S. M., & Chakraborty, T. (2026). Discourse-guided summarisation of psychotherapy dialogues via graph-fused language models. *IEEE Journal of Biomedical and Health Informatics*. Advance online publication. https://doi.org/10.1109/JBHI.2026.3726138 — the TheraFuse repository, which carries the iHOPE corpus.
- Adhikary, P. K., Singh, S., Singh, S., Sharma, P., Soni, P., Choudhary, R., Saxena, C., Chauhan, P., Gupta, S. K., Deb, K. S., Singh, S. M., & Chakraborty, T. (2026). *Clinically grounded AI-scribing in psychotherapy: Benchmarking LLMs against expert documentation in the iCARE framework* (Version 2) [Preprint]. medRxiv. https://doi.org/10.1101/2025.06.25.25330252 — iCARE, its section instructions, and the iHOPE corpus.
- Croxford, E., Gao, Y., Pellegrino, N., Wong, K., Wills, G., First, E., Schnier, M., Burton, K., Ebby, C., Gorski, J., Kalscheur, M., Khalil, S., Pisani, M., Rubeor, T., Stetson, P., Liao, F., Goswami, C., Patterson, B., & Afshar, M. (2025). Development and validation of the provider documentation summarization quality instrument for large language models. *Journal of the American Medical Informatics Association, 32*(6), 1050–1060. https://doi.org/10.1093/jamia/ocaf068 — PDSQI-9; the wording reproduced here is the arXiv version's, https://arxiv.org/abs/2501.08977, which is CC BY.
- Shah, R. S., Xu, L., Liu, Q., Burnsky, J., Bertagnolli, A., & Shivade, C. (2025). TN-Eval: Rubric and evaluation protocols for measuring the quality of behavioral therapy notes. In *Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics (Volume 6: Industry Track)* (pp. 179–199). Association for Computational Linguistics. https://doi.org/10.18653/v1/2025.acl-industry.14 — the SOAP prompt, the scoring prompts, the completeness rubric and the human-rated notes.
- Wu, Z., Balloccu, S., Kumar, V., Helaoui, R., Reiter, E., Reforgiato Recupero, D., & Riboni, D. (2022). Anno-MI: A dataset of expert-annotated counselling dialogues. In *ICASSP 2022 – 2022 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP)* (pp. 6177–6181). IEEE. https://doi.org/10.1109/ICASSP43922.2022.9746035 — the transcripts.
