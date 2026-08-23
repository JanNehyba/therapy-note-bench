# e-INFRA model snapshot

The authoritative list of what can be benchmarked is the live endpoint, not this
file and not e-INFRA's documentation. This page is a dated record so that a
result from six months ago can be read in the context of what was deployed then.

Refresh it with:

```sh
curl -s -H "Authorization: Bearer $EINFRA_API_TOKEN" \
  https://llm.ai.e-infra.cz/v1/models | jq -r '.data[].id' | sort
```

or, once the harness is installed, `make models`.

---

## 2026-08-23 — not yet captured

**Status: pending an API token.** The live endpoint requires a bearer token from
<https://chat.ai.e-infra.cz> → Account → API keys, which in turn requires a
MetaCentrum account or Masaryk University affiliation. Until a run happens, this
section is empty on purpose rather than filled in from documentation.

For reference only — **this is what the CERIT-SC documentation claimed on
2026-08-23, and it has not been verified against the endpoint**:

| Model | API name | Size | Note |
|---|---|---|---|
| Kimi K3 | `kimi-k3` | 2.8T MoE | multimodal, 1M context |
| GLM 5.2 | `glm-5.2` | 756B | |
| GPT-OSS-120B | `gpt-oss-120b` | 120B | |
| DeepSeek-V4-Flash | `DeepSeek-V4-Flash` | 304B | |
| Qwen3.5 (int4) | `qwen3.5-int4` | 397B / A17B | |
| Qwen3.5 122B | `qwen3.5-122b` | 122B / A10B | |
| Qwen3.8 27B | `qwen3.8-27b` | 27B | multimodal |
| Mistral Medium 3.5 | `mistral-medium-3.5` | 128B | |
| Gemma 4 | `gemma4` | 31B | |
| Whisper Large v3 | `whisper-large-v3` | 1.55B | ASR — excluded by `models.yaml` |

Documentation drift is expected and is the reason this benchmark discovers
models at run time. Treat any mismatch between the table above and the endpoint
as the table being wrong.

### Aliases are excluded on purpose

e-INFRA maintains moving aliases (`kimi`, `glm`, `deepseek`) for users who want
stability of *name*. A benchmark needs stability of *model*, which is the
opposite property: an alias silently changes what it points at, so a row labelled
`glm` would mix two different models across runs. `models.yaml` excludes them and
benchmarks concrete versioned ids only.

## Access and terms

- Endpoint: `https://llm.ai.e-infra.cz/v1/` (OpenAI-compatible)
- Status page: <https://llm.ai.e-infra.cz/status/>
- Usage dashboard: <https://llm.ai.e-infra.cz/usage>
- Inference runs entirely inside e-INFRA CZ infrastructure.
- **API keys must not be shared.** In CI the token lives in a repository secret,
  which GitHub does not expose to forks or to pull requests from forks — and the
  benchmark workflow has no `pull_request` trigger for that reason.
