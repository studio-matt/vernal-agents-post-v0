"""Typed data models for the portable content machine asset pack."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

VALID_MODES: tuple[str, ...] = ("memoir", "reform", "epistemic", "live")
VALID_AUDIENCES: tuple[str, ...] = (
    "general",
    "practitioner",
    "scholar",
    "live",
)


@dataclass(slots=True)
class SourceSpec:
    """Provenance for a text sample included in an author profile."""

    path: str
    mode: str
    audience: str

    def validate(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode: {self.mode}")
        if self.audience not in VALID_AUDIENCES:
            raise ValueError(f"Unsupported audience: {self.audience}")
        if not Path(self.path).name:
            raise ValueError("Source path must include a file or slug name")


@dataclass(slots=True)
class LexiconBank:
    """Collection of lexicon hints derived from the author's corpus."""

    core_verbs: list[str] = field(default_factory=list)
    core_nouns: list[str] = field(default_factory=list)
    evaluatives: list[str] = field(default_factory=list)
    metaphor_stems: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Iterable[str]]) -> LexiconBank:
        return cls(
            core_verbs=list(payload.get("core_verbs", [])),
            core_nouns=list(payload.get("core_nouns", [])),
            evaluatives=list(payload.get("evaluatives", [])),
            metaphor_stems=list(payload.get("metaphor_stems", [])),
            avoid=list(payload.get("avoid", [])),
        )

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "core_verbs": list(self.core_verbs),
            "core_nouns": list(self.core_nouns),
            "evaluatives": list(self.evaluatives),
            "metaphor_stems": list(self.metaphor_stems),
            "avoid": list(self.avoid),
        }


@dataclass(slots=True)
class ControlDefaults:
    pronoun_distance: str
    cadence_pattern: str
    evidence_density: float
    empathy_target: str
    cta_style: str

    def to_dict(self) -> dict[str, object]:
        return {
            "pronoun_distance": self.pronoun_distance,
            "cadence_pattern": self.cadence_pattern,
            "evidence_density": self.evidence_density,
            "empathy_target": self.empathy_target,
            "cta_style": self.cta_style,
        }


@dataclass(slots=True)
class ToleranceConfig:
    liwc_z: float
    sentence_length_max_run: int

    def to_dict(self) -> dict[str, object]:
        return {
            "liwc_z": float(self.liwc_z),
            "sentence_length_max_run": int(self.sentence_length_max_run),
        }


@dataclass(slots=True)
class LIWCScore:
    mean: float
    stdev: float
    z: float

    def to_dict(self) -> dict[str, float]:
        return {"mean": float(self.mean), "stdev": float(self.stdev), "z": float(self.z)}


@dataclass(slots=True)
class LIWCProfile:
    categories: dict[str, LIWCScore]
    domain_mode: str

    def to_dict(self) -> dict[str, object]:
        return {
            "categories": {key: value.to_dict() for key, value in self.categories.items()},
            "domain_mode": self.domain_mode,
        }


@dataclass(slots=True)
class AuthorProfile:
    author_id: str
    sources: list[SourceSpec]
    liwc_profile: LIWCProfile
    lexicon: LexiconBank
    default_controls: ControlDefaults
    tolerance: ToleranceConfig
    mbti: dict[str, float] | None = None
    ocean: dict[str, float] | None = None
    hexaco: dict[str, float] | None = None
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "author_id": self.author_id,
            "sources": [source.__dict__ for source in self.sources],
            "liwc_profile": self.liwc_profile.to_dict(),
            "lexicon": self.lexicon.to_dict(),
            "default_controls": self.default_controls.to_dict(),
            "tolerance": self.tolerance.to_dict(),
            "schema_version": self.schema_version,
        }
        if self.mbti:
            payload["mbti"] = dict(self.mbti)
        if self.ocean:
            payload["ocean"] = dict(self.ocean)
        if self.hexaco:
            payload["hexaco"] = dict(self.hexaco)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> AuthorProfile:
        sources = [SourceSpec(**spec) for spec in payload.get("sources", [])]
        for source in sources:
            source.validate()
        liwc_categories = {
            key: LIWCScore(**value)
            for key, value in (payload.get("liwc_profile", {}).get("categories", {}) or {}).items()
        }
        liwc_profile = LIWCProfile(
            categories=liwc_categories, domain_mode=str(payload.get("liwc_profile", {}).get("domain_mode", ""))
        )
        lexicon = LexiconBank.from_dict(payload.get("lexicon", {}))
        default_controls = ControlDefaults(**payload.get("default_controls", {}))
        tolerance_payload = payload.get("tolerance", {})
        tolerance = ToleranceConfig(
            liwc_z=float(tolerance_payload.get("liwc_z", 0.0)),
            sentence_length_max_run=int(tolerance_payload.get("sentence_length_max_run", 0)),
        )
        return cls(
            author_id=str(payload.get("author_id")),
            sources=sources,
            liwc_profile=liwc_profile,
            lexicon=lexicon,
            default_controls=default_controls,
            tolerance=tolerance,
            mbti=payload.get("mbti"),
            ocean=payload.get("ocean"),
            hexaco=payload.get("hexaco"),
            schema_version=str(payload.get("schema_version", "1.0.0")),
        )


@dataclass(slots=True)
class StyleConfig:
    mode: str
    audience: str
    goal: str
    cadence_pattern: str
    pronoun_distance: str
    evidence_density: float | None = None
    metaphor_sets: list[str] | None = None
    cta_style: str | None = None
    empathy_target: str | None = None
    liwc_targets: dict[str, str] | None = None
    lexicon_hints: dict[str, list[str]] | None = None

    def to_header_block(self) -> str:
        lines = ["[STYLE_CONFIG]"]
        lines.append(f"mode={self.mode}")
        lines.append(f"audience={self.audience}")
        lines.append(f"goal={self.goal}")
        lines.append(f"cadence_pattern={self.cadence_pattern}")
        lines.append(f"pronoun_distance={self.pronoun_distance}")
        if self.evidence_density is not None:
            lines.append(f"evidence_density={self.evidence_density}")
        if self.metaphor_sets:
            lines.append(f"metaphor_sets={','.join(self.metaphor_sets)}")
        if self.cta_style:
            lines.append(f"cta_style={self.cta_style}")
        if self.empathy_target:
            lines.append(f"empathy_target={self.empathy_target}")
        if self.liwc_targets:
            targets = [f"{key}:{value}" for key, value in self.liwc_targets.items()]
            lines.append(f"liwc_targets={','.join(targets)}")
        if self.lexicon_hints:
            for key, values in self.lexicon_hints.items():
                lines.append(f"lexicon_{key}={','.join(values)}")
        lines.append("[/STYLE_CONFIG]")
        return "\n".join(lines)


@dataclass(slots=True)
class PlannerMetadata:
    adapter_key: str
    lexicon_strategy: str
    liwc_source: str
    tolerance_window: float


@dataclass(slots=True)
class PlannerOutput:
    style_config_block: str
    lexicon_hints: dict[str, list[str]]
    scaffold: str
    metadata: PlannerMetadata


@dataclass(slots=True)
class ValidationFinding:
    category: str
    message: str
    severity: str
    offsets: list[int] | None = None


@dataclass(slots=True)
class ValidationReport:
    findings: list[ValidationFinding]
    liwc_deltas: dict[str, float]
    cadence_errors: int
    pronoun_errors: int
    metaphor_errors: int
    empathy_gaps: int
    schema_version: str = "1.0.0"

    def is_clean(self) -> bool:
        return not self.findings and not any(
            [self.liwc_deltas, self.cadence_errors, self.pronoun_errors, self.metaphor_errors, self.empathy_gaps]
        )


@dataclass(slots=True)
class GenerationResult:
    text: str
    prompt_id: str
    token_count: int
    planner_metadata: PlannerMetadata


@dataclass(slots=True)
class ReportBundle:
    validation: ValidationReport
    generation: GenerationResult
    style_config: StyleConfig

    def to_json(self) -> dict[str, object]:
        return {
            "style_config": self.style_config.to_header_block(),
            "generation": {
                "text": self.generation.text,
                "prompt_id": self.generation.prompt_id,
                "token_count": self.generation.token_count,
                "planner_metadata": self.generation.planner_metadata.__dict__,
            },
            "validation": {
                "findings": [finding.__dict__ for finding in self.validation.findings],
                "liwc_deltas": dict(self.validation.liwc_deltas),
                "cadence_errors": self.validation.cadence_errors,
                "pronoun_errors": self.validation.pronoun_errors,
                "metaphor_errors": self.validation.metaphor_errors,
                "empathy_gaps": self.validation.empathy_gaps,
                "schema_version": self.validation.schema_version,
            },
        }
