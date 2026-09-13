"""Versioned interchange contracts. Offsets count Unicode code points, end exclusive.

Validation errors name fields, never reproduce clinical text. All source-derived
objects retain their case/revision bindings; a matching quote alone is not proof
of semantic support.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from . import PROTOCOL_VERSION

Profile = Literal["continuity", "supervision", "client", "audit"]
Language = Literal["en", "cs"]
PROFILES = ("continuity", "supervision", "client", "audit")
Severity = Literal["none", "minor", "major", "critical"]
ERROR_TYPES = (
    "speaker",
    "negation",
    "time",
    "certainty",
    "intervention",
    "causality",
    "diagnosis",
    "risk",
    "plan",
    "quotation",
    "omission",
    "privacy",
    "language",
    "instruction",
    "other",
)


class ValidationError(ValueError):
    """An invalid or mismatched artifact; messages contain no source content."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def plain(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            plain(value),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def decode(cls: Any, value: Any, path: str = "artifact") -> Any:
    """Strict recursive decoding: reject unknown fields, bool-as-int and NaN."""
    origin, args = get_origin(cls), get_args(cls)
    if cls is Any:
        json.dumps(value, allow_nan=False)
        return value
    if origin is Literal:
        require(value in args, f"{path}: invalid category")
        return value
    if origin in (Union, types.UnionType):
        for candidate in args:
            try:
                return decode(candidate, value, path)
            except (ValidationError, TypeError, ValueError):
                pass
        raise ValidationError(f"{path}: incompatible type")
    if cls is type(None):
        require(value is None, f"{path}: expected null")
        return None
    if dataclasses.is_dataclass(cls):
        require(isinstance(value, dict), f"{path}: expected object")
        fields = {f.name for f in dataclasses.fields(cls)}
        require(not set(value) - fields, f"{path}: unknown fields")
        hints = get_type_hints(cls)
        kwargs = {k: decode(hints[k], v, f"{path}.{k}") for k, v in value.items()}
        try:
            return cls(**kwargs)
        except TypeError as exc:
            raise ValidationError(f"{path}: required fields missing") from exc
    if origin in (tuple, list):
        require(isinstance(value, (list, tuple)), f"{path}: expected array")
        out = [decode(args[0], v, path + "[]") for v in value]
        return tuple(out) if origin is tuple else out
    if origin is dict:
        require(isinstance(value, dict), f"{path}: expected object")
        return {decode(args[0], k, path): decode(args[1], v, path) for k, v in value.items()}
    if cls is float:
        require(type(value) in (float, int) and math.isfinite(value), f"{path}: invalid number")
        return float(value)
    require(type(value) is cls, f"{path}: incompatible type")
    return value


def unique(values: Any, message: str) -> None:
    items = list(values)
    require(len(items) == len(set(items)), message)


@dataclass(frozen=True)
class Model:
    provider: str
    model: str
    family: str
    settings: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        require(bool(self.provider and self.model and self.family), "Model identity is incomplete")

    @property
    def key(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class Turn:
    id: str
    speaker: str
    text: str


@dataclass(frozen=True)
class Source:
    id: str
    kind: Literal["session", "history", "metadata"]
    session_index: int
    turns: tuple[Turn, ...]

    def __post_init__(self):
        require(bool(self.id and self.turns), "Source must have an id and turns")
        unique((t.id for t in self.turns), "Duplicate source turn id")

    @property
    def revision(self) -> str:
        return digest(self)


@dataclass(frozen=True)
class Case:
    id: str
    corpus: str
    language: Language
    origin: Literal["native_real", "public_demo", "translated_demo", "synthetic"]
    group_id: str
    split: Literal["development", "confirmation", "pilot"]
    session_index: int
    sources: tuple[Source, ...]
    allowed_providers: tuple[str, ...]
    translation_group: str | None = None

    def __post_init__(self):
        require(bool(self.id and self.corpus and self.group_id and self.sources), "Incomplete case")
        require(self.language in ("en", "cs"), "Unsupported language")
        require(bool(self.allowed_providers), "An explicit provider policy is required")
        unique((s.id for s in self.sources), "Duplicate source id")
        require(
            all(s.session_index <= self.session_index for s in self.sources),
            "Future sessions must not enter the source window",
        )
        require(
            any(
                s.kind == "session" and s.session_index == self.session_index for s in self.sources
            ),
            "Current session source is missing",
        )
        if self.origin == "native_real":
            require(
                set(self.allowed_providers) <= {"local", "einfra"},
                "Real-session derivatives are confined to local/einfra",
            )

    @property
    def revision(self) -> str:
        return digest(self)

    @property
    def cohort(self) -> tuple[str, str, str]:
        return self.corpus, self.language, self.origin

    def authorize(self, provider: str) -> None:
        require(provider in self.allowed_providers, "Provider is not permitted for this case")


def validate_cases(cases: tuple[Case, ...] | list[Case]) -> None:
    require(bool(cases), "No cases supplied")
    unique((c.id for c in cases), "Duplicate case id")
    groups: dict[str, str] = {}
    for case in cases:
        # Corpus is deliberately not part of this key: translated relatives can
        # live in different corpora. Group identifiers must be globally scoped.
        for group in (case.group_id, case.translation_group):
            if group:
                require(
                    groups.get(group, case.split) == case.split,
                    "Related sessions/translations cross evaluation splits",
                )
                groups[group] = case.split


@dataclass(frozen=True)
class Span:
    unit_id: str
    start: int
    end: int
    quote: str

    def check(self, text: str) -> None:
        require(0 <= self.start < self.end <= len(text), "Evidence offsets are out of bounds")
        require(
            text[self.start : self.end] == self.quote, "Evidence quote does not match its offsets"
        )


@dataclass(frozen=True)
class Evidence:
    source_id: str
    source_revision: str
    span: Span

    def check(self, case: Case) -> None:
        source = next((s for s in case.sources if s.id == self.source_id), None)
        require(source is not None, "Unknown evidence source")
        require(source.revision == self.source_revision, "Stale evidence source revision")
        turn = next((t for t in source.turns if t.id == self.span.unit_id), None)
        require(turn is not None, "Unknown evidence turn")
        self.span.check(turn.text)


@dataclass(frozen=True)
class Relevance:
    importance: Literal["essential", "supplementary", "not_required"]
    disclosure: Literal["retain", "generalize", "omit"]
    reason: str

    def __post_init__(self):
        require(
            not (self.disclosure == "omit" and self.importance != "not_required"),
            "An omitted detail cannot also be required",
        )


@dataclass(frozen=True)
class Information:
    id: str
    text: str
    source_answer: str
    epistemic_status: Literal["explicit", "uncertain", "not_assessed", "conflicting"]
    evidence: tuple[Evidence, ...]
    relevance: dict[str, Relevance]
    critical: bool = False

    def __post_init__(self):
        require(set(self.relevance) == set(PROFILES), "Relevance must cover all four profiles")
        require(bool(self.id and self.text and self.source_answer), "Incomplete information item")
        # A claim that an assessment is absent may require the whole source;
        # absence does not have an extractive positive evidence span.
        require(
            bool(self.evidence) or self.epistemic_status == "not_assessed",
            "Information requires source evidence",
        )


@dataclass(frozen=True)
class Question:
    id: str
    information_id: str
    text: str
    primary: bool = True


@dataclass(frozen=True)
class Bank:
    case_id: str
    case_revision: str
    author: Model
    information: tuple[Information, ...]
    questions: tuple[Question, ...]
    version: str = "bank-v2"
    research_revision: str = "development-default-v3"

    @property
    def revision(self) -> str:
        return digest(self)

    def check(self, case: Case) -> None:
        require(
            (self.case_id, self.case_revision) == (case.id, case.revision), "Bank/case mismatch"
        )
        unique((i.id for i in self.information), "Duplicate information id")
        unique((q.id for q in self.questions), "Duplicate question id")
        ids = {i.id for i in self.information}
        require(
            all(q.information_id in ids and q.text.strip() for q in self.questions),
            "Question has no information item or no text",
        )
        for item in self.information:
            require(
                sum(q.primary and q.information_id == item.id for q in self.questions) == 1,
                "Each information item needs exactly one primary question",
            )
            for evidence in item.evidence:
                evidence.check(case)


@dataclass(frozen=True)
class NoteSpec:
    profile: Profile
    language: Language
    format: Literal["sections", "soap", "dap", "birp"] = "sections"
    word_limit: int = 500
    version: str = "note-spec-v1"
    required_headings: tuple[str, ...] = ()

    def __post_init__(self):
        require(self.profile in PROFILES and self.language in ("en", "cs"), "Invalid note spec")
        require(self.word_limit > 0, "Word limit must be positive")
        require(
            all(h.strip() and "\n" not in h for h in self.required_headings),
            "Invalid required heading",
        )


@dataclass(frozen=True)
class Note:
    id: str
    case_id: str
    case_revision: str
    generator: Model
    spec: NoteSpec
    text: str
    version: str = "generation-v1"

    @property
    def revision(self) -> str:
        return digest(self)

    def check(self, case: Case) -> None:
        require(
            (self.case_id, self.case_revision) == (case.id, case.revision), "Note/case mismatch"
        )
        require(self.spec.language == case.language, "Cross-language generation is a separate task")

    def check_span(self, span: Span) -> None:
        require(span.unit_id == "note", "Unknown note unit")
        span.check(self.text)


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    kind: Literal["client_report", "observation", "hypothesis", "recommendation", "other_fact"]
    actor: str
    time: str
    polarity: Literal["positive", "negative", "uncertain"]
    certainty: str
    spans: tuple[Span, ...]


@dataclass(frozen=True)
class NonClaim:
    span: Span
    reason: Literal["heading", "formatting", "nonassertive"]


@dataclass(frozen=True)
class Segmentation:
    note_id: str
    note_revision: str
    extractor: Model
    claims: tuple[Claim, ...]
    nonclaims: tuple[NonClaim, ...]
    version: str = "atomic-claims-v1"

    @property
    def revision(self) -> str:
        return digest(self)

    def check(self, note: Note) -> None:
        require(
            (self.note_id, self.note_revision) == (note.id, note.revision),
            "Segmentation/note mismatch",
        )
        unique((c.id for c in self.claims), "Duplicate claim id")
        covered: set[int] = set()
        spans = [s for c in self.claims for s in c.spans] + [n.span for n in self.nonclaims]
        require(all(c.spans and c.text.strip() for c in self.claims), "Unanchored claim")
        for span in spans:
            note.check_span(span)
            covered.update(range(span.start, span.end))
        require(
            all(i in covered for i, ch in enumerate(note.text) if ch.isalnum()),
            "Segmentation silently omitted note content",
        )


@dataclass(frozen=True)
class ClaimVerdict:
    claim_id: str
    verdict: Literal["supported", "contradicted", "unsupported", "unassessable"]
    severity: Severity
    error_types: tuple[str, ...]
    evidence: tuple[Evidence, ...]
    citation_support: Literal["supported", "unsupported", "uncertain", "none"]
    rationale: str


@dataclass(frozen=True)
class NoteAnswer:
    question_id: str
    status: Literal["answered", "not_in_note", "ambiguous", "failed"]
    text: str
    evidence: tuple[Span, ...]


@dataclass(frozen=True)
class QAVerdict:
    information_id: str
    verdict: Literal["preserved", "partial", "omitted", "contradicted", "unassessable"]
    severity: Severity
    error_types: tuple[str, ...]
    rationale: str


DIMENSIONS = ("clinical", "privacy", "language", "instructions")


@dataclass(frozen=True)
class MethodSpec:
    """Operational rules for a selected method, including source QA and claim checking."""

    id: str
    construct_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    definition: str
    unit: str
    required_inputs: tuple[str, ...]
    applicability: str
    outcomes: dict[str, str]
    severity_rules: dict[str, str]
    language_variants: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        require(self.id in ("qa", "claims", "items", "citations"), "Unknown method")
        supported = {
            "qa": {"preserved", "partial", "omitted", "contradicted", "unassessable"},
            "claims": {"supported", "contradicted", "unsupported", "unassessable"},
            "items": {"pass", "fail", "rated", "not_applicable", "unassessable"},
            "citations": {"supported", "unsupported", "uncertain", "invalid"},
        }
        require(
            set(self.outcomes) == supported[self.id],
            "Method outcome categories are incompatible with this implementation",
        )
        require(
            bool(
                self.construct_ids
                and self.evidence_ids
                and self.definition
                and self.unit
                and self.required_inputs
                and self.applicability
                and self.outcomes
            ),
            "Incomplete method operationalization",
        )
        require(
            set(self.severity_rules) == {"none", "minor", "major", "critical"}
            and all(self.severity_rules.values()),
            "Missing method severity rules",
        )

    def localized(self, language: str) -> dict:
        return {**plain(self), **self.language_variants.get(language, {})}


@dataclass(frozen=True)
class MeasurementSpec:
    """An operational item, distinct from its construct and its evidence base."""

    id: str
    construct_id: str
    definition: str
    question: str
    reference_mode: Literal["source", "note_only", "norm"]
    response_format: Literal["binary", "ordinal", "categorical"] = "binary"
    labels: tuple[str, ...] = ("pass", "fail")
    anchors: dict[str, str] = field(default_factory=dict)
    sources: tuple[str, ...] = ()
    profiles: tuple[str, ...] = PROFILES
    examples: dict[str, str] = field(default_factory=dict)
    status: Literal["development", "pilot_reviewed"] = "development"
    version: str = "measurement-v1"
    language_variants: dict[str, dict[str, Any]] = field(default_factory=dict)
    deterministic_checks: tuple[str, ...] = ()

    def __post_init__(self):
        require(
            bool(self.id and self.construct_id and self.definition and self.question),
            "Incomplete measurement definition",
        )
        require(bool(self.labels) and bool(self.sources), "Measurement needs labels and provenance")
        unique(self.labels, "Duplicate measurement labels")
        require(
            set(self.deterministic_checks) <= {"word_limit", "required_headings"},
            "Unknown deterministic check",
        )
        require(
            not self.deterministic_checks or self.response_format == "binary",
            "Deterministic vetoes need binary items",
        )
        require(set(self.anchors) == set(self.labels), "Every response needs an explicit anchor")
        require(
            bool(self.profiles) and set(self.profiles) <= set(PROFILES), "Invalid item purposes"
        )
        if self.response_format == "binary":
            require(self.labels == ("pass", "fail"), "Binary items use pass/fail")
        for language, variant in self.language_variants.items():
            require(language in ("en", "cs"), "Unknown item language")
            require(
                {"definition", "question", "anchors", "examples"} <= set(variant)
                and set(variant)
                <= {"definition", "question", "anchors", "examples", "reviewed_by"},
                "Incomplete translated item",
            )
            require(
                set(variant["anchors"]) == set(self.labels),
                "Translated anchors must match the response labels",
            )

    def localized(self, language: str) -> dict:
        return {**plain(self), **self.language_variants.get(language, {})}


def default_measurements() -> tuple[MeasurementSpec, ...]:
    from .registry import default_measurements as defaults

    return defaults()


def implementation_digest() -> str:
    return digest(
        {
            name: Path(__file__).with_name(name).read_text(encoding="utf-8")
            for name in (
                "schema.py",
                "prompts.py",
                "profiles.py",
                "metrics.py",
                "pipeline.py",
                "registry.py",
                "citations.py",
                "deterministic.py",
                "storage.py",
                "report.py",
                "findings.py",
                "development.py",
                "research.py",
                "research_review.py",
                "pilot.py",
                "annotations.py",
                "privacy.py",
                "review.js",
            )
        }
    )


@dataclass(frozen=True)
class DimensionVerdict:
    dimension: str
    verdict: Literal["pass", "fail", "unassessable", "not_applicable", "rated"]
    severity: Severity
    evidence: tuple[Span, ...]
    rationale: str
    value: str | None = None


@dataclass(frozen=True)
class CitationVerdict:
    citation_id: str
    verdict: Literal["supported", "unsupported", "uncertain", "invalid"]
    evidence: tuple[Evidence, ...] = ()
    rationale: str = ""
    severity: Severity | None = None


@dataclass(frozen=True)
class Evaluation:
    case_id: str
    note_id: str
    note_revision: str
    bank_revision: str
    segmentation_revision: str
    judge: Model
    claims: tuple[ClaimVerdict, ...] = ()
    answers: tuple[NoteAnswer, ...] = ()
    qa: tuple[QAVerdict, ...] = ()
    dimensions: tuple[DimensionVerdict, ...] = ()
    segmentation_complete: bool | None = None
    failures: tuple[str, ...] = ()
    protocol: str = PROTOCOL_VERSION
    source_mode: Literal["full_context", "retrieved"] = "full_context"
    retrieved_sources: tuple[str, ...] = ()
    manifest_id: str = ""
    measurements: tuple[MeasurementSpec, ...] = field(default_factory=default_measurements)
    research_revision: str = "development-default-v3"
    citations: tuple[CitationVerdict, ...] = ()
    case_revision: str = ""
    methods: tuple[str, ...] = ("qa", "claims", "items", "citations")
    assessment_scope: str = "development-four-methods"
    required_methods: tuple[str, ...] = ("qa", "claims", "items", "citations")
    method_specs: tuple[MethodSpec, ...] = ()
    replicate_id: str = "primary"

    def check(self, case: Case, note: Note, bank: Bank, segmentation: Segmentation) -> None:
        require(self.protocol == PROTOCOL_VERSION, "Unknown evaluation protocol")
        require(
            bool(self.assessment_scope and self.replicate_id)
            and set(self.required_methods) <= {"qa", "claims", "items", "citations"},
            "Invalid assessment scope or replicate",
        )
        require(self.case_revision == case.revision, "Evaluation case revision mismatch")
        unique((m.id for m in self.measurements), "Duplicate measurement id")
        require(
            bool(self.methods) and set(self.methods) <= {"qa", "claims", "items", "citations"},
            "Unknown or empty method selection",
        )
        require("qa" in self.methods or not (self.qa or self.answers), "Unrequested QA results")
        require(
            "claims" in self.methods or (not self.claims and self.segmentation_complete is None),
            "Unrequested claim results",
        )
        require("items" in self.methods or not self.dimensions, "Unrequested item results")
        require("citations" in self.methods or not self.citations, "Unrequested citation results")
        note.check(case)
        bank.check(case)
        segmentation.check(note)
        require(
            (
                self.case_id,
                self.note_id,
                self.note_revision,
                self.bank_revision,
                self.segmentation_revision,
            )
            == (case.id, note.id, note.revision, bank.revision, segmentation.revision),
            "Evaluation artifact revisions do not match",
        )
        for values, attr, expected in (
            (self.claims, "claim_id", {c.id for c in segmentation.claims}),
            (self.answers, "question_id", {q.id for q in bank.questions if q.primary}),
            (self.qa, "information_id", {i.id for i in bank.information}),
            (self.dimensions, "dimension", {m.id for m in self.measurements}),
        ):
            ids = [getattr(v, attr) for v in values]
            unique(ids, "Duplicate evaluation unit")
            require(set(ids) <= expected, "Unknown evaluation unit")
        for verdict in (*self.claims, *self.qa):
            require(set(verdict.error_types) <= set(ERROR_TYPES), "Unknown error taxonomy label")
        for verdict in self.claims:
            for evidence in verdict.evidence:
                evidence.check(case)
            if verdict.verdict in ("supported", "contradicted"):
                require(
                    bool(verdict.evidence), "Supported or contradicted claim needs source evidence"
                )
            require(
                verdict.verdict not in ("supported", "unassessable") or verdict.severity == "none",
                "No error severity without a finding",
            )
            require(
                bool(verdict.evidence) == (verdict.citation_support != "none"),
                "Citation support requires a citation and vice versa",
            )
        for answer in self.answers:
            for evidence in answer.evidence:
                note.check_span(evidence)
            require(
                answer.status != "answered" or bool(answer.text and answer.evidence),
                "Note answer is not anchored in the note",
            )
            require(
                answer.status not in ("not_in_note", "failed")
                or not (answer.text or answer.evidence),
                "Absent or failed answers cannot contain asserted answers",
            )
        answers = {a.question_id: a for a in self.answers}
        primary = {q.information_id: q.id for q in bank.questions if q.primary}
        information = {i.id: i for i in bank.information}
        for verdict in self.qa:
            answer = answers.get(primary[verdict.information_id])
            require(
                verdict.verdict != "preserved"
                or (answer is not None and answer.status == "answered"),
                "No preservation credit without a note answer",
            )
            require(
                verdict.verdict not in ("preserved", "unassessable") or verdict.severity == "none",
                "Invalid QA error severity",
            )
            relevance = information[verdict.information_id].relevance[note.spec.profile]
            require(
                verdict.verdict != "omitted"
                or relevance.importance != "not_required"
                or verdict.severity == "none",
                "Omission of unneeded information is not an error",
            )
        for verdict in self.dimensions:
            definition = next(m for m in self.measurements if m.id == verdict.dimension)
            require(note.spec.profile in definition.profiles, "Item is outside the note purpose")
            if verdict.verdict == "rated":
                require(
                    definition.response_format != "binary" and verdict.value in definition.labels,
                    "Rating is outside the declared scale",
                )
            else:
                require(verdict.value is None, "Only rated items carry a scale value")
                require(
                    definition.response_format == "binary"
                    or verdict.verdict in ("not_applicable", "unassessable"),
                    "Scale item needs a rating",
                )
            for evidence in verdict.evidence:
                note.check_span(evidence)
            require(
                verdict.verdict == "fail" or verdict.severity == "none",
                "No dimension error severity without a finding",
            )
        from .citations import extract

        citations = {c["id"]: c for c in extract(note, case)}
        unique((c.citation_id for c in self.citations), "Duplicate authored citation judgment")
        for verdict in self.citations:
            require(verdict.citation_id in citations, "Unknown authored citation")
            cited = citations[verdict.citation_id]
            require(cited["valid"] or verdict.verdict == "invalid", "Invalid citation target")
            require(
                verdict.verdict in ("unsupported", "invalid") or verdict.severity in (None, "none"),
                "Citation severity without a finding",
            )
            require(
                verdict.verdict not in ("supported", "unsupported") or bool(verdict.evidence),
                "Citation support needs evidence from its own target",
            )
            for evidence in verdict.evidence:
                evidence.check(case)
                require(
                    (evidence.source_id, evidence.span.unit_id)
                    == (cited["source_id"], cited["unit_id"]),
                    "Citation evidence substitutes target",
                )


@dataclass(frozen=True)
class Manifest:
    """A comparability group, including its planned population, never one model's subset."""

    cases: dict[str, str]
    banks: dict[str, str]
    corpus: str
    origin: str
    split: str
    spec: NoteSpec
    bank_author: Model
    extractor: Model
    judge: Model
    source_mode: Literal["full_context", "retrieved"] = "full_context"
    retrieval_turns: int = 32
    protocol: str = PROTOCOL_VERSION
    prompts_version: str = "prompts-v3"
    profiles_version: str = "profiles-v1"
    segmentation_version: str = "atomic-claims-v1"
    aggregation_version: str = "aggregation-v3"
    implementation_digest: str = field(default_factory=implementation_digest)
    measurements: tuple[MeasurementSpec, ...] = field(default_factory=default_measurements)
    research_revision: str = "development-default-v3"
    methods: tuple[str, ...] = ("qa", "claims", "items", "citations")
    assessment_scope: str = "development-four-methods"
    required_methods: tuple[str, ...] = ("qa", "claims", "items", "citations")
    method_specs: tuple[MethodSpec, ...] = ()
    replicate_id: str = "primary"

    def __post_init__(self):
        require(
            bool(self.cases) and set(self.cases) == set(self.banks),
            "Manifest must freeze banks for every planned case",
        )
        require(self.retrieval_turns > 0, "Retrieval size must be positive")
        unique((m.id for m in self.measurements), "Duplicate measurement id")
        require(bool(self.research_revision), "Missing research instrument")
        require(
            bool(self.assessment_scope and self.replicate_id)
            and set(self.required_methods) <= {"qa", "claims", "items", "citations"},
            "Invalid assessment scope or replicate",
        )
        require(
            bool(self.methods) and set(self.methods) <= {"qa", "claims", "items", "citations"},
            "Invalid measurement methods",
        )
        require("items" not in self.methods or bool(self.measurements), "Missing operational items")

    @property
    def id(self) -> str:
        return digest(self)

    def check(self, case: Case, bank: Bank, note: Note, segmentation: Segmentation) -> None:
        require(self.protocol == PROTOCOL_VERSION, "Unknown manifest protocol")
        require(
            self.implementation_digest == implementation_digest(),
            "Implementation changed; create a derived run, retaining the original artifacts",
        )
        require(
            self.aggregation_version == "aggregation-v3"
            and self.prompts_version == "prompts-v3"
            and self.profiles_version == "profiles-v1",
            "Incompatible scoring versions",
        )
        require(self.spec.language == case.language, "Manifest language mismatch")
        require(
            self.segmentation_version == segmentation.version,
            "Manifest segmentation version mismatch",
        )
        require(
            self.cases.get(case.id) == case.revision and self.banks.get(case.id) == bank.revision,
            "Case/bank outside frozen manifest",
        )
        require(
            (self.corpus, self.origin, self.split) == (case.corpus, case.origin, case.split),
            "Cohorts must be reported separately",
        )
        require(
            self.spec == note.spec
            and self.bank_author == bank.author
            and self.extractor == segmentation.extractor,
            "Instrument configuration mismatch",
        )
        require(
            bank.research_revision == self.research_revision,
            "Source bank was prepared under different research criteria",
        )
