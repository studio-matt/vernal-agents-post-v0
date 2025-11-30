"""Planner utilities that assemble STYLE_CONFIG blocks and lexicon hints."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .asset_loader import AssetLoader
from .models import AuthorProfile, PlannerMetadata, PlannerOutput, StyleConfig

REQUIRED_STYLE_KEYS = {"mode", "audience", "goal", "cadence_pattern", "pronoun_distance"}


class Planner:
    """Builds portable planning artifacts from author profiles and adapters."""

    def __init__(self, loader: AssetLoader | None = None) -> None:
        self.loader = loader or AssetLoader()
        self.adapters = self.loader.load_adapters()
        self.context_legend = {entry["code"]: entry for entry in self.loader.load_context_legend()}

    def _apply_adapter(self, adapter_key: str, base: dict[str, object]) -> dict[str, object]:
        if adapter_key not in self.adapters:
            raise KeyError(f"Unknown adapter: {adapter_key}")
        overlay = self.adapters[adapter_key]
        merged = {**base}
        merged.update(overlay)
        return merged

    def _lexicon_hints(
        self, lexicon: Mapping[str, Iterable[str]], liwc_targets: Mapping[str, str]
    ) -> dict[str, list[str]]:
        hints: dict[str, list[str]] = {}
        for key, values in lexicon.items():
            if key.startswith("lexicon_"):
                hints[key.removeprefix("lexicon_")] = list(values)
            else:
                hints[key] = list(values)
        hints.setdefault("metaphor_stems", [])
        hints.setdefault("evaluatives", [])
        if liwc_targets:
            hints["liwc_targets"] = [f"{k}:{v}" for k, v in liwc_targets.items()]
        return hints

    def _prepare_ltw_targets(self, profile: AuthorProfile) -> dict[str, str]:
        liwc_targets: dict[str, str] = {}
        for category, score in profile.liwc_profile.categories.items():
            descriptor = "high" if score.z >= profile.tolerance.liwc_z else "medium"
            liwc_targets[category] = descriptor
        return liwc_targets

    def build_style_config(
        self,
        profile: AuthorProfile,
        goal: str,
        target_audience: str,
        adapter_key: str,
        scaffold: str,
    ) -> PlannerOutput:
        liwc_targets = self._prepare_ltw_targets(profile)
        base_controls = profile.default_controls.to_dict()
        adapted = self._apply_adapter(adapter_key, base_controls)
        style_config = StyleConfig(
            mode=profile.liwc_profile.domain_mode or "reform",
            audience=target_audience,
            goal=goal,
            cadence_pattern=str(adapted.get("cadence_pattern", profile.default_controls.cadence_pattern)),
            pronoun_distance=str(adapted.get("pronoun_distance", profile.default_controls.pronoun_distance)),
            evidence_density=float(adapted.get("evidence_density", profile.default_controls.evidence_density)),
            metaphor_sets=adapted.get("metaphor_sets", profile.lexicon.metaphor_stems),
            cta_style=str(adapted.get("cta_style", profile.default_controls.cta_style)),
            empathy_target=str(adapted.get("empathy_target", profile.default_controls.empathy_target)),
            liwc_targets=liwc_targets,
            lexicon_hints={
                "core_verbs": profile.lexicon.core_verbs,
                "core_nouns": profile.lexicon.core_nouns,
                "evaluatives": profile.lexicon.evaluatives,
                "metaphor_stems": profile.lexicon.metaphor_stems,
                "avoid": profile.lexicon.avoid,
            },
        )
        lexicon_hints = self._lexicon_hints(style_config.lexicon_hints or {}, liwc_targets)
        metadata = PlannerMetadata(
            adapter_key=adapter_key,
            lexicon_strategy="profile_top_terms",
            liwc_source=profile.liwc_profile.domain_mode,
            tolerance_window=profile.tolerance.liwc_z,
        )
        return PlannerOutput(
            style_config_block=style_config.to_header_block(),
            lexicon_hints=lexicon_hints,
            scaffold=scaffold,
            metadata=metadata,
        )

    def parse_style_block(self, block: str) -> dict[str, str]:
        lines = [line.strip() for line in block.splitlines() if line.strip() and not line.startswith("[")]
        pairs: dict[str, str] = {}
        for line in lines:
            if "=" not in line:
                raise ValueError(f"Invalid STYLE_CONFIG line: {line}")
            key, value = line.split("=", maxsplit=1)
            if key not in REQUIRED_STYLE_KEYS and not key.startswith("lexicon_") and key != "liwc_targets":
                raise ValueError(f"Unknown STYLE_CONFIG key: {key}")
            pairs[key] = value
        missing = REQUIRED_STYLE_KEYS - set(pairs)
        if missing:
            raise ValueError(f"STYLE_CONFIG missing required keys: {sorted(missing)}")
        return pairs
