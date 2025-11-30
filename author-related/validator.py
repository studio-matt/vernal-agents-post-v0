"""Validation layer that compares generated text against profile targets."""

from __future__ import annotations

from collections.abc import Mapping

from .asset_loader import AssetLoader
from .deterministic import enforce_all
from .models import AuthorProfile, StyleConfig, ValidationFinding, ValidationReport


class StyleValidator:
    """Validates STYLE_CONFIG blocks and LIWC alignment."""

    def __init__(self, loader: AssetLoader | None = None) -> None:
        self.loader = loader or AssetLoader()
        self.baselines = self.loader.load_liwc_baselines()

    def _z_score(self, category: str, value: float) -> float:
        baseline = self.baselines.get(category, {"mean": 0.0, "stdev": 1.0})
        stdev = baseline.get("stdev", 1.0) or 1.0
        return (value - baseline.get("mean", 0.0)) / stdev

    def validate_style_config(self, config: StyleConfig) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        if config.mode not in {"memoir", "reform", "epistemic", "live"}:
            findings.append(ValidationFinding("mode", "Unsupported mode", "error"))
        if not config.audience:
            findings.append(ValidationFinding("audience", "Audience missing", "error"))
        if not config.goal:
            findings.append(ValidationFinding("goal", "Goal missing", "error"))
        return findings

    def compare_liwc(
        self, profile: AuthorProfile, measured: Mapping[str, float]
    ) -> tuple[dict[str, float], list[ValidationFinding]]:
        deltas: dict[str, float] = {}
        findings: list[ValidationFinding] = []
        for category, expected in profile.liwc_profile.categories.items():
            actual_z = self._z_score(category, measured.get(category, expected.mean))
            delta = abs(actual_z - expected.z)
            deltas[category] = delta
            if delta > profile.tolerance.liwc_z:
                findings.append(
                    ValidationFinding(
                        category,
                        f"LIWC z-score drift {delta:.2f} exceeds tolerance {profile.tolerance.liwc_z}",
                        "warning",
                    )
                )
        return deltas, findings

    def validate_output(
        self,
        text: str,
        config: StyleConfig,
        profile: AuthorProfile,
        measured_liwc: Mapping[str, float],
    ) -> ValidationReport:
        style_findings = self.validate_style_config(config)
        enforced, deterministic_counts, enforcement_findings = enforce_all(
            text,
            config.cadence_pattern,
            config.pronoun_distance,
            config.empathy_target or profile.default_controls.empathy_target,
            config.lexicon_hints.get("metaphor_stems", []) if config.lexicon_hints else profile.lexicon.metaphor_stems,
            profile.tolerance.sentence_length_max_run,
        )
        liwc_deltas, liwc_findings = self.compare_liwc(profile, measured_liwc)
        findings = style_findings + enforcement_findings + liwc_findings
        return ValidationReport(
            findings=findings,
            liwc_deltas=liwc_deltas,
            cadence_errors=deterministic_counts["cadence_errors"],
            pronoun_errors=deterministic_counts["pronoun_errors"],
            metaphor_errors=deterministic_counts["metaphor_errors"],
            empathy_gaps=deterministic_counts["empathy_gaps"],
        )


def parse_style_header(block: str) -> StyleConfig:
    lines = [line.strip() for line in block.splitlines() if line.strip() and not line.startswith("[")]
    values: dict[str, str] = {}
    lexicon_hints: dict[str, list[str]] = {}
    liwc_targets: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            raise ValueError(f"Malformed STYLE_CONFIG line: {line}")
        key, raw_value = line.split("=", maxsplit=1)
        if key.startswith("lexicon_"):
            lexicon_hints[key.removeprefix("lexicon_")] = raw_value.split(",") if raw_value else []
        elif key == "liwc_targets":
            for target in raw_value.split(","):
                if ":" in target:
                    category, level = target.split(":", maxsplit=1)
                    liwc_targets[category] = level
        else:
            values[key] = raw_value
    missing = {"mode", "audience", "goal", "cadence_pattern", "pronoun_distance"} - set(values)
    if missing:
        raise ValueError(f"STYLE_CONFIG missing required keys: {sorted(missing)}")
    return StyleConfig(
        mode=values["mode"],
        audience=values["audience"],
        goal=values["goal"],
        cadence_pattern=values["cadence_pattern"],
        pronoun_distance=values["pronoun_distance"],
        evidence_density=float(values["evidence_density"]) if "evidence_density" in values else None,
        metaphor_sets=values.get("metaphor_sets", "").split(",") if "metaphor_sets" in values else None,
        cta_style=values.get("cta_style"),
        empathy_target=values.get("empathy_target"),
        liwc_targets=liwc_targets or None,
        lexicon_hints=lexicon_hints or None,
    )
