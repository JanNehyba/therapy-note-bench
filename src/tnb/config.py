"""Loading and validating the provider policy.

``models.yaml`` holds rules, never a model list. See ``docs/methodology.md``
for why: no provider guarantees that a model version stays available, so a
pinned list would rot within weeks.

A *provider* is one OpenAI-compatible endpoint, its credentials, and the rules
for turning its ``/v1/models`` into a benchmark set. There can be several. Which
provider served a model is part of that model's identity in the results, not a
footnote: the same name on two endpoints can be two different things —
different quantisation, different weights, a different system prompt — and a
table that merged them would compare two models under one row.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = REPO_ROOT / "models.yaml"


@dataclass(frozen=True)
class DiscoveryPolicy:
    """Rules for turning one endpoint's model list into a benchmark set."""

    exclude: tuple[re.Pattern[str], ...] = ()
    #: When set, *only* ids matching one of these are benchmarked and everything
    #: else is excluded as "not on the include list". For an endpoint that
    #: serves a general catalogue rather than a deployment -- OpenAI reports 132
    #: models, of which three are the ones under test -- naming what is wanted
    #: is honest, where a long exclude list would silently admit whatever is
    #: added next.
    include: tuple[re.Pattern[str], ...] = ()
    exclude_aliases: bool = True
    #: Verified duplicates: alias id -> the concrete model it resolves to.
    #: Established by fingerprinting, not by guessing. See models.yaml.
    aliases: dict[str, str] = field(default_factory=dict)
    max_models: int = 20

    #: Where this provider's catalogue lives, when it is not ``<base_url>/models``.
    #: Vertex's OpenAI-compatible endpoint serves chat completions and nothing
    #: else -- ``/models`` there is a 404 HTML page -- so its list comes from the
    #: publisher catalogue instead.
    catalogue_url: str = ""
    #: Which key in the response holds the list, and which field in each entry
    #: holds the id. ``data``/``id`` is the OpenAI shape.
    catalogue_key: str = "data"
    catalogue_id_field: str = "id"
    #: Prefix the chat endpoint expects on a model id that the catalogue reports
    #: without one. Vertex wants ``google/gemini-3.1-pro-preview``.
    model_prefix: str = ""


@dataclass(frozen=True)
class Dialect:
    """How one provider spells an otherwise identical request.

    Every backend here speaks the OpenAI chat-completions shape, and they
    disagree about it in small ways that are fatal rather than cosmetic. The
    defaults are what e-INFRA accepts, so an existing stanza needs none of this.

    Established by asking the endpoints rather than by reading their docs:

    - OpenAI's reasoning models reject ``max_tokens`` and require
      ``max_completion_tokens``.
    - They also reject every temperature but 1 -- verbatim, *"Unsupported value:
      'temperature' does not support 0 with this model. Only the default (1)
      value is supported."* ``gpt-4.1`` still accepts 0, so this is specific to
      the reasoning family and not a mix-up.
    - They accept a ``reasoning_effort`` that no other provider here has.

    A model generated under a different temperature is a differently-configured
    system, so `effective_temperature` reports what will actually be sent and
    the row records that rather than what `models.yaml` asked for.
    """

    #: `max_tokens` everywhere except OpenAI, which wants `max_completion_tokens`.
    max_tokens_field: str = "max_tokens"
    #: False where the provider rejects any temperature but its own default.
    send_temperature: bool = True
    #: The temperature the provider forces when it will not take ours.
    forced_temperature: float = 1.0
    #: Request field carrying the reasoning effort, where the provider has one.
    effort_field: str = ""


@dataclass(frozen=True)
class GenerationPolicy:
    temperature: float = 0.0
    max_tokens: int = 2048
    #: Second-chance budget for a call that stopped on `length` with nothing
    #: usable in it -- a reasoning model that thought until it ran out.
    escalate_max_tokens: int = 0
    #: Providers rate-limit per API key rather than per model, so this is a
    #: ceiling over the whole run against one provider. Six concurrent requests
    #: drew HTTP 429 on a third of calls against e-INFRA; two is well behaved.
    concurrency: int = 2
    timeout_s: int = 180
    retries: int = 3
    #: 429 is routine rather than exceptional. Waits grow as backoff_s * attempt.
    backoff_s: int = 6

    #: How this provider spells a request. Defaults to what e-INFRA accepts.
    dialect: Dialect = field(default_factory=Dialect)
    #: Reasoning effort, for providers that have the control. Part of a system's
    #: identity: the same model at two efforts produces two rows, never an
    #: average of both under one name.
    effort: str = ""

    @property
    def effective_temperature(self) -> float:
        """The temperature that will actually be sent.

        Not the one configured: a provider that refuses ours substitutes its
        own, and the row has to record what happened rather than what was asked.
        """
        return (
            self.temperature if self.dialect.send_temperature else self.dialect.forced_temperature
        )


@dataclass(frozen=True)
class Provider:
    """One endpoint: where to reach it, how to authenticate, what to benchmark.

    Everything the harness needs to talk to a backend lives here, so adding a
    second provider is a stanza in ``models.yaml`` rather than a code change.
    """

    name: str
    base_url: str
    token_env: str
    #: What to tell someone whose token is missing or rejected. Providers differ
    #: in how a key is obtained, and "401" on its own helps nobody.
    token_help: str = ""
    #: How the bearer token is obtained. ``static`` reads ``token_env``;
    #: ``google`` mints a short-lived one from the service-account key that
    #: ``token_env`` points at. Vertex has no static key, so a provider served
    #: from there cannot use the first mode -- and the token expires mid-run,
    #: which is why this is a mode rather than a value read once at startup.
    auth: str = "static"
    discovery: DiscoveryPolicy = field(default_factory=DiscoveryPolicy)
    generation: GenerationPolicy = field(default_factory=GenerationPolicy)

    @property
    def url(self) -> str:
        """``base_url`` with ``{project}`` and ``{location}`` filled in.

        Vertex puts the project id in the path. That id is an account
        identifier, so it is interpolated from the environment at call time and
        never written into this repository -- which is a public one, and which
        has a test that fails if it ever appears in a tracked file.

        A provider whose URL has no placeholders is returned unchanged, so this
        costs the ordinary case nothing.
        """
        if "{" not in self.base_url:
            return self.base_url
        return self.base_url.format(
            project=os.environ.get("VERTEX_PROJECT", ""),
            location=os.environ.get("VERTEX_LOCATION", ""),
        )

    def token(self, *, force_refresh: bool = False) -> str:
        """A bearer token, with an error message that says what to do.

        ``force_refresh`` matters only in ``google`` mode and only after a 401:
        the library believes the token is valid, the server does not, and the
        server is the one that decides.
        """
        value = os.environ.get(self.token_env, "").strip()
        if not value:
            raise RuntimeError(
                f"{self.token_env} is not set for provider '{self.name}'."
                + (f" {self.token_help}" if self.token_help else "")
            )
        if self.auth == "google":
            from tnb import google_auth

            return google_auth.token(force_refresh=force_refresh, path=value)
        return value

    def has_token(self) -> bool:
        """Whether this provider is usable at all. A missing one is skipped.

        In ``google`` mode the variable names a key *file*, so its presence is
        not enough -- a stale path would fail every call in the run instead of
        skipping the provider once, at the start, where it can be read.
        """
        value = os.environ.get(self.token_env, "").strip()
        if not value:
            return False
        if self.auth == "google":
            return Path(value).is_file()
        return True


@dataclass(frozen=True)
class Policy:
    """Every configured provider, in the order ``models.yaml`` lists them."""

    providers: tuple[Provider, ...] = ()

    def get(self, name: str) -> Provider:
        for provider in self.providers:
            if provider.name == name:
                return provider
        known = ", ".join(provider.name for provider in self.providers) or "none configured"
        raise RuntimeError(f"Unknown provider '{name}'. Configured in models.yaml: {known}.")

    def resolve(self, names: str | None) -> list[Provider]:
        """Turn a comma-separated ``--providers`` value into providers.

        With no names, every provider that has a token. A provider configured
        but not credentialled is skipped rather than failing the run: the point
        of several providers is that one can be unavailable.
        """
        if names:
            return [self.get(name.strip()) for name in names.split(",") if name.strip()]

        usable = [provider for provider in self.providers if provider.has_token()]
        if not usable:
            missing = ", ".join(provider.token_env for provider in self.providers)
            raise RuntimeError(
                f"No provider has a token. Set one of: {missing} (see .env.example)."
            )
        return usable


def _discovery(raw: dict) -> DiscoveryPolicy:
    return DiscoveryPolicy(
        exclude=tuple(re.compile(pattern, re.IGNORECASE) for pattern in raw.get("exclude", [])),
        include=tuple(re.compile(pattern, re.IGNORECASE) for pattern in raw.get("include", [])),
        exclude_aliases=bool(raw.get("exclude_aliases", True)),
        aliases=dict(raw.get("aliases") or {}),
        max_models=int(raw.get("max_models", 20)),
        catalogue_url=str(raw.get("catalogue_url", "")),
        catalogue_key=str(raw.get("catalogue_key", "data")),
        catalogue_id_field=str(raw.get("catalogue_id_field", "id")),
        model_prefix=str(raw.get("model_prefix", "")),
    )


def _dialect(raw: dict, defaults: Dialect) -> Dialect:
    """How this provider spells a request, over the inherited defaults."""
    return replace(
        defaults,
        **{
            name: type(getattr(defaults, name))(raw[name])
            for name in Dialect.__dataclass_fields__
            if name in raw
        },
    )


#: Fields of :class:`GenerationPolicy` that are not plain scalars, so the flat
#: coercion below must not try to build them from a single value.
_NESTED_GENERATION_FIELDS = ("dialect",)


def _generation(raw: dict, defaults: GenerationPolicy) -> GenerationPolicy:
    """Provider-level generation settings, falling back to the shared block.

    Rate limits belong to a provider, not to the benchmark, so a slow endpoint
    can be given a lower concurrency without changing anyone else's. The same
    goes for the request dialect, which is nested and therefore merged field by
    field rather than replaced wholesale -- a provider that overrides only
    ``send_temperature`` keeps the shared value for everything else.
    """
    scalars = {
        name: type(getattr(defaults, name))(raw[name])
        for name in GenerationPolicy.__dataclass_fields__
        if name in raw and name not in _NESTED_GENERATION_FIELDS
    }
    if "dialect" in raw:
        scalars["dialect"] = _dialect(raw["dialect"] or {}, defaults.dialect)
    return replace(defaults, **scalars)


def load_policy(path: Path | None = None) -> Policy:
    """Read ``models.yaml`` into a :class:`Policy`."""
    path = path or DEFAULT_POLICY_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    defaults = _generation(raw.get("generation") or {}, GenerationPolicy())

    providers = []
    for entry in raw.get("providers") or []:
        env_url = os.environ.get(entry.get("base_url_env", ""), "").strip()
        providers.append(
            Provider(
                name=entry["name"],
                base_url=env_url or entry["base_url"],
                token_env=entry["token_env"],
                token_help=entry.get("token_help", ""),
                auth=entry.get("auth", "static"),
                discovery=_discovery(entry.get("discovery") or {}),
                generation=_generation(entry.get("generation") or {}, defaults),
            )
        )

    if not providers:
        raise RuntimeError(f"{path.name} configures no providers under 'providers:'.")
    return Policy(providers=tuple(providers))


def write_published(path: Path, text: str) -> None:
    """Write a file the site serves, or leave the old one untouched.

    `Path.write_text` truncates first and fills after, so a process that dies
    between the two leaves a file of the right length full of NUL bytes. That
    is not hypothetical: `docs/corpus-profile.json` was found on 2026-09-01 at
    3 696 bytes of nothing, having grown from 3 508 -- the length of the write
    that never landed -- and it is a file the briefing links for a reader to
    open. Two `*.stackdump` files in the tree say what killed it.

    Written beside the target and renamed, which is atomic on one filesystem:
    a reader gets the old file or the new one and never a hole. The temporary
    file is removed if the write itself fails, so a crash leaves no litter for
    the next run to trip over.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(f"{path.name}.writing")
    try:
        staged.write_text(text, encoding="utf-8")
        staged.replace(path)
    except BaseException:
        staged.unlink(missing_ok=True)
        raise
