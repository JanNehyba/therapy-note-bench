# e-INFRA model snapshot

The authoritative list of what can be benchmarked is the live endpoint, not this
file and not e-INFRA's documentation. This page is a dated record so that a
result from six months ago can be read in the context of what was deployed then.

Refresh it with `make models`, or:

```sh
curl -s -H "Authorization: Bearer $EINFRA_API_TOKEN" \
  https://llm.ai.e-infra.cz/v1/models | jq -r '.data[].id' | sort
```

---

## 2026-08-23 — live capture

`GET /v1/models` reported **31 ids**, which reduce to **11 distinct
benchmarkable models**. The other twenty are embedding or speech models,
duplicates under a second name, or unversioned labels.

### Benchmark set

| Model id | Note |
|---|---|
| `deepseek-v4-flash` | 1M input context, 8192 output (the only id publishing metadata) |
| `deepseek-v4-flash-thinking` | reasoning variant, distinct output |
| `gemma4` | |
| `glm-5` | distinct model, not an older label for glm-5.2 |
| `glm-5.2` | newest GLM deployed |
| `gpt-oss-120b` | |
| `kimi-k3` | |
| `mistral-medium-3.5` | |
| `qwen3.5-122b` | |
| `qwen3.5-int4` | |
| `qwen3.8-27b` | |

**As of this capture there was no `glm-5.3` and no `DeepSeek-V4` proper.** The
newest GLM on the endpoint was `glm-5.2`; the DeepSeek was `deepseek-v4-flash`.
That has changed and this capture has not been retaken: `glm-5.3-flash` and
`qwen3.8-flash-next` have been writing notes since 2026-08-27, and `glm-5` and
`qwen3.5-122b` no longer appear in any run. **This file is dated; read the date,
not the tense.** Note also the
casing: the documentation writes `DeepSeek-V4-Flash`, the endpoint serves
`deepseek-v4-flash`.

### Excluded, and why

| Id | Reason |
|---|---|
| `auto-llm`, `auto-llm-heuristic`, `command-a` | same model as `gemma4` |
| `deepseek` | same model as `deepseek-v4-flash` |
| `thinker` | same model as `deepseek-v4-flash-thinking` |
| `qwen3.5` | same model as `qwen3.5-int4` |
| `mini` | same model as `gpt-oss-120b` |
| `glm`, `kimi`, `coder`, `agentic`, `deepseek-thinking` | distinct models, but unversioned names |
| `whisper-large-v3` | speech recognition |
| `multilingual-e5-large-instruct`, `mxbai-embed-large:latest`, `nomic-embed-text-v1.5`, `nomic-embed-text-v2-moe`, `qwen3-embedding-4b` | embeddings |
| `qwen3-reranker-4b` | reranker |
| `all-proxy-models` | meta-entry; rejects generation with HTTP 400 |

### How the duplicates were established

Not by reading names. The endpoint publishes almost no metadata — of 31 models,
exactly one (`deepseek-v4-flash`) carried a `mode` field, and none of the others
reported context limits — so identity had to be measured.

Each id was asked one fixed question at temperature 0 and the answers compared.
Byte-identical answer means the same model. Reproduce with `tnb models --probe`.

Two things had to be right for this to mean anything:

- **Determinism was checked first.** Three consecutive calls to each of six
  models returned byte-identical text every time.
- **The prompt has to allow stylistic freedom.** A first attempt asked for the
  first eight prime numbers; every model answered `2, 3, 5, 7, 11, 13, 17, 19`,
  which grouped seven unrelated models together. The current prompt asks for a
  one-sentence description of a lighthouse at night.

`command-a` is the case that justifies the whole exercise. The name reads like
Cohere Command A; it returns `gemma4`'s exact output. Trusting the name would
have put one model in the leaderboard twice under two vendors' names.

### Operational findings

- **Rate limiting is per API key, not per model, and the limit is 4.** Six
  concurrent requests drew HTTP 429 on roughly a third of calls. The endpoint
  states the number in the 429 body itself, which is where it was read rather
  than guessed: `Limit type: max_parallel_requests. Current limit: 4`.
  `models.yaml` runs at concurrency 2 — half the allowance, leaving room for
  whatever else the same key is doing — and the client retries 429 with backoff.
  One 429 in the ~9600 calls of the first generation run.
- **Reasoning models need a generous `max_tokens`.** At 64 tokens, several
  returned empty `content` because the budget went entirely on thinking — they
  look broken rather than slow. The generation cap is 4096.
- **4096 is not always enough either.** In the first generation run,
  `deepseek-v4-flash-thinking` spent all 4096 tokens on 20k characters of
  reasoning for one iCARE section and returned no content, with
  `finish_reason: length`. A call that stops that way without a usable answer is
  asked once more at `escalate_max_tokens` (16384); the record says which budget
  produced the answer. Without this the leaderboard would carry our token budget
  under the model's name.
- **Temperature 0 is not reproducible across runs.** The same
  (model, prompt, budget) pair failed on budget in one run and answered within
  4096 tokens in the next. Determinism held *within* a run when fingerprinting on
  2026-08-23, but it does not hold across them, so a re-generated note is not
  guaranteed to equal the cached one. This is one more reason the cache is the
  record rather than a convenience.
- **`gpt-oss-120b` will not write a flat dictionary.** It answered 37 of 50
  TN-Eval conversations with `Plan` as a nested object; TN-Eval's parser slices
  to the first closing brace and truncates it. Their repair loop rescued 29,
  and 8 stayed unparseable after all five attempts. See
  [limitations.md](limitations.md#coverage-is-bounded) — the model's notes are
  fine, its output shape is not, and the table has to say so.
- **Throughput, measured on the first run** (2 models, 3 sessions, 108 calls):
  `deepseek-v4-flash` answered an iCARE section in about 1 s and a SOAP note in
  6 s; `deepseek-v4-flash-thinking` took 9 s and 20 s; `gemma4` took 2 s and
  29 s. A full pass is 730 calls per model, so budget roughly 20–120 minutes of
  model time per model, halved by running at concurrency 2.

### Aliases are excluded on purpose

e-INFRA maintains moving aliases (`glm`, `kimi`, `deepseek`) for users who want
stability of *name*. A benchmark needs stability of *model*, which is the
opposite property: an alias silently changes what it points at, so a row
labelled `glm` would compare two different models across runs.

Note that `glm`, `kimi`, `coder` and `agentic` are **not** duplicates — each
answered differently from every versioned id. They are real models reachable
only under a name that will move. They are excluded for that reason, not for
being copies.

## Access and terms

- Endpoint: `https://llm.ai.e-infra.cz/v1/` (OpenAI-compatible, LiteLLM-fronted)
- Status page: <https://llm.ai.e-infra.cz/status/>
- Usage dashboard: <https://llm.ai.e-infra.cz/usage>
- Inference through **this endpoint** runs inside e-INFRA CZ infrastructure.
  Not all of the benchmark does: 38% of the published notes were written
  elsewhere — 17% OpenAI, 11% Vertex, and the 10% that are TN-Eval's released
  reference notes, which are not inference at all — and **both judges run
  outside e-INFRA**. What may be sent where is in
  [datasets.md](datasets.md).
- **API keys must not be shared.** In CI the token lives in a repository secret,
  which GitHub does not expose to forks or to pull requests from forks — and the
  benchmark workflow has no `pull_request` trigger for that reason.
