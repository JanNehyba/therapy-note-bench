"""Research provenance and operational registries; no model vote is a human review."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .schema import PROFILES, MeasurementSpec, MethodSpec, decode, digest, plain, require, unique


def subject_digest(value) -> str:
    """Bind the reviewed content, excluding workflow labels (never its provenance)."""
    body = plain(value)
    return digest(
        {
            k: v
            for k, v in body.items()
            if k not in {"status", "reviewed_by", "human_checked_by", "decision_reason"}
        }
    )


@dataclass(frozen=True)
class ReviewDecision:
    subject: str
    subject_digest: str
    decision: Literal["accept", "exclude", "revise", "unresolved", "merge"]
    reviewer: str
    role: str
    decided_at: str
    mode: Literal["human", "human_with_ai", "delegated"]
    reason: str
    response_id: str
    supersedes: tuple[str, ...] = ()

    def __post_init__(self):
        require(
            all(
                (
                    self.subject,
                    self.subject_digest,
                    self.reviewer,
                    self.role,
                    self.decided_at,
                    self.reason,
                    self.response_id,
                )
            ),
            "Incomplete human decision",
        )
        require(
            self.mode in ("human", "human_with_ai", "delegated"),
            "AI output is not a human decision",
        )

    @property
    def id(self):
        return digest(self)


@dataclass(frozen=True)
class SupportingSource:
    id: str
    title: str
    locator: str
    layer: Literal[
        "direct", "transfer", "requirements", "methodology", "inductive", "expert", "unclassified"
    ]
    publication_type: Literal[
        "article",
        "preprint",
        "guideline",
        "software",
        "local_observation",
        "expert_proposal",
        "unverified",
    ]
    verification: Literal["candidate", "metadata_checked", "full_text_checked", "local_checked"]
    limitations: str
    version: str = "source-v1"


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    source_id: str
    location: str
    interpretation: str
    relationship: Literal[
        "direct_validation", "method_transfer", "requirement", "observation", "hypothesis"
    ]
    population: str = "not established"
    languages: tuple[str, ...] = ()
    raters: str = "not established"
    unit: str = "not established"
    response_format: str = "not established"
    validation: str = "not established"
    limitations: str = "Requires human source verification"
    human_checked_by: str | None = None
    source_artifact_digest: str = ""
    excerpt: str = ""


@dataclass(frozen=True)
class ConstructDefinition:
    id: str
    name: str
    definition: str
    families: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    relevance: dict[str, str]
    unit: str
    required_inputs: tuple[str, ...]
    examples: dict[str, str]
    candidate_formats: tuple[str, ...]
    applicability: str
    error_consequences: str
    status: Literal["candidate", "pilot", "unresolved", "excluded"] = "candidate"
    decision_reason: str = "Awaiting human review"
    reviewed_by: str | None = None
    origin: Literal["unclassified", "literature", "prior_proposal", "inductive"] = "unclassified"
    origin_reference: str = ""

    def __post_init__(self):
        require(set(self.relevance) == set(PROFILES), "Construct must address every purpose")
        require(
            set(self.examples) == {"positive", "negative", "boundary"}, "Missing construct examples"
        )
        require(
            bool(self.definition and self.evidence_ids and self.candidate_formats),
            "Incomplete construct",
        )


@dataclass(frozen=True)
class InstrumentRegistry:
    sources: tuple[SupportingSource, ...]
    evidence: tuple[EvidenceRecord, ...]
    constructs: tuple[ConstructDefinition, ...]
    measurements: tuple[MeasurementSpec, ...]
    protocol_revision: str
    version: str = "registry-v2"
    literature_freeze: str | None = None
    methods: tuple[str, ...] = ()
    method_evidence: dict[str, tuple[str, ...]] = field(default_factory=dict)
    methods_reviewed_by: str | None = None
    method_specs: tuple[MethodSpec, ...] = ()
    reviews: tuple[ReviewDecision, ...] = ()
    assessment_scope: str = ""
    required_methods: tuple[str, ...] = ()
    research_snapshot: str | None = None

    def subjects(self) -> dict:
        subjects = {
            f"{kind}:{v.id}": plain(v)
            for kind, values in (
                ("source", self.sources),
                ("evidence", self.evidence),
                ("construct", self.constructs),
                ("measurement", self.measurements),
                ("method", self.method_specs),
            )
            for v in values
        }
        for kind, values in (("measurement", self.measurements), ("method", self.method_specs)):
            for v in values:
                for language, variant in v.language_variants.items():
                    subjects[f"language:{language}:{kind}:{v.id}"] = variant
        subjects["scope"] = {
            "assessment_scope": self.assessment_scope,
            "required_methods": self.required_methods,
            "methods": self.methods,
            "protocol_revision": self.protocol_revision,
        }
        return subjects

    def require_review(self, subject: str, value) -> None:
        superseded = {key for r in self.reviews for key in r.supersedes}
        current = [r for r in self.reviews if r.subject == subject and r.id not in superseded]
        require(
            bool(current)
            and all(
                r.decision == "accept" and r.subject_digest == subject_digest(value)
                for r in current
            ),
            "Missing, disputed or stale human decision: " + subject,
        )

    def delegated_subjects(self) -> tuple[str, ...]:
        """Subjects accepted on the assistant's reading by a recorded delegation.

        A delegation is a human decision, but not a verification: the person
        chose not to check each subject and said so. Whatever is built on these
        subjects may not be reported as human-verified evidence, so the list is
        kept where a frozen snapshot and a report can print it.
        """
        superseded = {key for r in self.reviews for key in r.supersedes}
        current = [r for r in self.reviews if r.id not in superseded]
        return tuple(sorted({r.subject for r in current if r.mode == "delegated"}))

    def check_language(self, language: str) -> None:
        for kind, values in (("method", self.method_specs), ("measurement", self.measurements)):
            for value in values:
                if language == "cs":
                    require("cs" in value.language_variants, "Missing Czech operational wording")
                if language in value.language_variants:
                    variant = value.language_variants[language]
                    fields = (
                        ("definition", "outcomes", "severity_rules", "applicability")
                        if kind == "method"
                        else ("definition", "question", "anchors", "examples")
                    )
                    require(all(variant.get(k) for k in fields), "Incomplete localized rules")
                    if kind == "method":
                        require(
                            set(variant["outcomes"]) == set(value.outcomes)
                            and set(variant["severity_rules"]) == set(value.severity_rules),
                            "Localized method changes outcome or severity categories",
                        )
                    self.require_review(f"language:{language}:{kind}:{value.id}", variant)

    @property
    def revision(self) -> str:
        return digest(self)

    def check(self, *, pilot: bool = False) -> None:
        for group in (
            self.sources,
            self.evidence,
            self.constructs,
            self.measurements,
            self.method_specs,
        ):
            unique((v.id for v in group), "Duplicate registry identifier")
        unique((r.id for r in self.reviews), "Duplicate human decision")
        by_review = {r.id: r for r in self.reviews}
        for review in self.reviews:
            require(
                all(
                    k in by_review and by_review[k].subject == review.subject
                    for k in review.supersedes
                ),
                "Unknown or unrelated superseded review",
            )
        sources = {v.id: v for v in self.sources}
        evidence = {v.id: v for v in self.evidence}
        constructs = {v.id: v for v in self.constructs}
        require(bool(self.protocol_revision), "Registry has no protocol revision")
        for record in self.evidence:
            require(
                record.source_id in sources and bool(record.location),
                "Evidence has no source location",
            )
        for construct in self.constructs:
            require(set(construct.evidence_ids) <= set(evidence), "Construct has unknown evidence")
        for item in self.measurements:
            require(item.construct_id in constructs, "Measurement has no construct")
            require(set(item.sources) <= set(evidence), "Measurement has unknown evidence")
        for method in self.method_specs:
            require(set(method.construct_ids) <= set(constructs), "Method has unknown constructs")
            require(set(method.evidence_ids) <= set(evidence), "Method has unknown evidence")
        if not pilot:
            return
        require(
            self.version == "registry-v2", "Legacy registry needs explicit review, not relabelling"
        )
        require(
            bool(self.methods) and set(self.methods) <= {"qa", "claims", "items", "citations"},
            "Pilot needs explicit methods",
        )
        require(
            set(self.methods) == {m.id for m in self.method_specs},
            "Every selected method needs operational rules",
        )
        require(
            bool(self.assessment_scope and self.required_methods)
            and set(self.required_methods) <= {"qa", "claims", "items", "citations"},
            "Pilot needs an explicit assessment scope",
        )
        self.require_review("scope", self.subjects()["scope"])
        require(
            "items" not in self.methods or bool(self.measurements),
            "Item scoring requires operational items",
        )
        require("items" in self.methods or not self.measurements, "Unselected operational items")
        used_constructs = {k for m in self.method_specs for k in m.construct_ids}
        used_constructs.update(m.construct_id for m in self.measurements)
        require(bool(used_constructs), "Pilot has no operational constructs")
        used_evidence = {k for m in self.method_specs for k in m.evidence_ids}
        used_evidence.update(k for m in self.measurements for k in m.sources)
        for key in used_constructs:
            c = constructs[key]
            require(
                c.origin != "unclassified" and bool(c.origin_reference),
                "Pilot construct origin is unclassified or lacks an origin record",
            )
            require(c.status == "pilot", "Construct is not selected for this pilot")
            self.require_review("construct:" + key, c)
            used_evidence.update(c.evidence_ids)
        for key in used_evidence:
            record = evidence[key]
            source = sources[record.source_id]
            self.require_review("evidence:" + key, record)
            self.require_review("source:" + source.id, source)
            require(
                source.layer != "unclassified" and source.publication_type != "unverified",
                "Pilot source type and evidence layer need human classification",
            )
            require(
                source.verification in ("full_text_checked", "local_checked"),
                "Pilot evidence source is unverified",
            )
        for item in self.measurements:
            require(item.status == "pilot_reviewed", "Pilot item has not passed human selection")
            self.require_review("measurement:" + item.id, item)
        for method in self.method_specs:
            self.require_review("method:" + method.id, method)
        # Even QA-only and claims-only registries must have language-reviewed operational rules.
        self.check_language("en")


def load_registry(value: dict, *, pilot: bool = False) -> InstrumentRegistry:
    registry = decode(InstrumentRegistry, value)
    registry.check(pilot=pilot)
    return registry


def default_measurements() -> tuple[MeasurementSpec, ...]:
    """Original development definitions, explicitly not selected by a completed review."""
    definitions = (
        (
            "clinical",
            "clinical_appropriateness",
            "source",
            "Clinical wording preserves the source's epistemic status and level of specificity.",
            "Does the note avoid unsupported diagnostic certainty, intervention labels, "
            "and agreements?",
            "A proposed exercise remains a suggestion.",
            "A suggestion becomes an agreed treatment plan.",
            "A clearly marked hypothesis has source premises but is not an established diagnosis.",
        ),
        (
            "privacy",
            "necessary_disclosure",
            "source",
            "Sensitive detail is limited to what the specified recipient needs "
            "without changing meaning.",
            "Are identifiers and third-party details necessary for this purpose, "
            "with faithful generalization?",
            "An unnecessary name is generalized to a relationship.",
            "An irrelevant identifying detail is retained.",
            "A sensitive detail is necessary for the stated clinical purpose.",
        ),
        (
            "language",
            "recipient_comprehension",
            "note_only",
            "The intended recipient can understand the note without access to the transcript.",
            "Is the note understandable, respectful, coherent and appropriate for the recipient?",
            "Terms needed by the recipient are explained.",
            "The recipient cannot resolve an unexplained acronym.",
            "A specialist term may be suitable for supervision but need explanation for a client.",
        ),
        (
            "instructions",
            "task_adherence",
            "norm",
            "The note follows its explicit purpose, language, format and length specification.",
            "Does the note satisfy the supplied task specification? "
            "Do not invent external legal requirements.",
            "Required headings and language follow the specification.",
            "A required section is absent.",
            "Unavailable source information is acknowledged "
            "rather than invented to fill a section.",
        ),
    )
    return tuple(
        MeasurementSpec(
            id=key,
            construct_id=construct,
            definition=definition,
            question=question,
            reference_mode=mode,
            sources=("gen2-development",),
            anchors={
                "pass": "No violation of this defined item was found after complete assessment.",
                "fail": "At least one evidenced violation of this defined item was found.",
            },
            examples={"positive": good, "negative": bad, "boundary": boundary},
            deterministic_checks=("word_limit", "required_headings")
            if key == "instructions"
            else (),
        )
        for key, construct, mode, definition, question, good, bad, boundary in definitions
    )
