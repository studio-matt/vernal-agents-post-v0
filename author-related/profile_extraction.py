"""Profile extraction pipeline relying solely on bundled assets."""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .asset_loader import AssetLoader
from .models import (
    AuthorProfile,
    ControlDefaults,
    LexiconBank,
    LIWCProfile,
    LIWCScore,
    SourceSpec,
    ToleranceConfig,
)


@dataclass(slots=True)
class Sample:
    text: str
    path: str
    mode: str
    audience: str
    liwc_counts: Mapping[str, float]


class ProfileExtractor:
    """Derives AuthorProfile instances from raw samples and LIWC counts."""

    def __init__(self, loader: AssetLoader | None = None) -> None:
        self.loader = loader or AssetLoader()
        self.baselines = self.loader.load_liwc_baselines()
        self.vectorization = self.loader.load_vectorization()
        self.trait_mapping = self.loader.load_trait_mapping()
        self.context_legend = self.loader.load_context_legend()

    @staticmethod
    def normalize_text(text: str) -> str:
        text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
        text = text.replace("–", "-").replace("—", "-")
        text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _z_score(self, category: str, value: float) -> float:
        baseline = self.baselines.get(category, {"mean": 0.0, "stdev": 1.0})
        stdev = baseline.get("stdev", 1.0) or 1.0
        return (value - baseline.get("mean", 0.0)) / stdev

    def _aggregate_liwc(self, samples: Iterable[Sample]) -> dict[str, LIWCScore]:
        category_values: dict[str, list[float]] = defaultdict(list)
        for sample in samples:
            for category, value in sample.liwc_counts.items():
                category_values[category].append(float(value))
        aggregated: dict[str, LIWCScore] = {}
        for category, values in category_values.items():
            mean_value = statistics.fmean(values) if values else 0.0
            stdev_value = statistics.pstdev(values) if len(values) > 1 else 0.0
            aggregated[category] = LIWCScore(mean=mean_value, stdev=stdev_value, z=self._z_score(category, mean_value))
        return aggregated

    @staticmethod
    def _sanitize_label(label: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", label.lower())

    def _match_trait_key(self, category: str) -> str | None:
        sanitized = self._sanitize_label(category)
        for trait_key, mapping in self.trait_mapping.items():
            trait_label = self._sanitize_label(trait_key)
            abbreviation = self._sanitize_label(str(mapping.get("abbreviation", trait_key)))
            if sanitized in {trait_label, abbreviation} or trait_label in sanitized:
                return trait_key
        for vector_key, details in self.vectorization.items():
            abbreviation = self._sanitize_label(str(details.get("abbreviation", vector_key)))
            vector_label = self._sanitize_label(vector_key)
            if sanitized in {abbreviation, vector_label} or vector_label in sanitized:
                return vector_key
        return None

    @staticmethod
    def _add_score(store: dict[str, list[float]], key: str, value: float) -> None:
        store.setdefault(key, []).append(value)

    @staticmethod
    def _average_scores(store: Mapping[str, list[float]], default: float = 0.5) -> dict[str, float]:
        averaged: dict[str, float] = {}
        for key, values in store.items():
            averaged[key] = statistics.fmean(values) if values else default
        return averaged

    def _project_traits(
        self, liwc_scores: Mapping[str, LIWCScore]
    ) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
        ocean_scores: dict[str, list[float]] = {}
        hexaco_scores: dict[str, list[float]] = {}
        for category, score in liwc_scores.items():
            trait_key = self._match_trait_key(category)
            if not trait_key:
                continue
            slider_value = max(0.0, min(1.0, 0.5 + score.z / 6))
            trait_definition: Mapping[str, Any] = self.trait_mapping.get(trait_key, {})
            for dimension in trait_definition.get("BigFive", []):
                dim_key = self._sanitize_label(dimension)
                invert = dim_key.startswith("low")
                target = dim_key.removeprefix("low")
                mapped = {
                    "openness": "o",
                    "conscientiousness": "c",
                    "extraversion": "e",
                    "agreeableness": "a",
                    "neuroticism": "n",
                }.get(target, target)
                adjusted = 1 - slider_value if invert else slider_value
                self._add_score(ocean_scores, mapped, adjusted)
            for dimension in trait_definition.get("HEXACO", []):
                dim_key = self._sanitize_label(dimension)
                invert = dim_key.startswith("low")
                target = dim_key.removeprefix("low")
                mapped = {
                    "honestyhumility": "h",
                    "emotionality": "e",
                    "extraversion": "x",
                    "agreeableness": "a",
                    "conscientiousness": "c",
                    "openness": "o",
                }.get(target, target)
                adjusted = 1 - slider_value if invert else slider_value
                self._add_score(hexaco_scores, mapped, adjusted)
        ocean = {key: 0.5 for key in ("o", "c", "e", "a", "n")}
        ocean.update(self._average_scores(ocean_scores, default=0.5))
        hexaco = {key: 0.5 for key in ("h", "e", "x", "a", "c", "o")}
        hexaco.update(self._average_scores(hexaco_scores, default=0.5))
        mbti = {
            "e_i": max(0.0, min(1.0, 1 - ocean.get("e", 0.5))),
            "s_n": max(0.0, min(1.0, ocean.get("o", 0.5))),
            "t_f": max(0.0, min(1.0, 1 - ocean.get("a", 0.5))),
            "j_p": max(0.0, min(1.0, ocean.get("c", 0.5))),
        }
        return mbti, ocean, hexaco

    @staticmethod
    def _lexicon_from_samples(samples: Iterable[Sample], limit: int = 30) -> LexiconBank:
        tokens = Counter()
        for sample in samples:
            tokens.update(re.findall(r"\b[a-zA-Z']+\b", sample.text.lower()))
        most_common = [token for token, _ in tokens.most_common(limit)]
        verbs = [word for word in most_common if word.endswith("e") or word.endswith("ing")]
        nouns = [word for word in most_common if word not in verbs]
        return LexiconBank(
            core_verbs=verbs[:10],
            core_nouns=nouns[:10],
            evaluatives=[word for word in most_common if word.endswith("ly")][:10],
            metaphor_stems=[word for word in most_common if len(word) > 6][:8],
            avoid=[word for word in most_common if len(word) <= 3][:5],
        )

    def build_profile(
        self,
        author_id: str,
        samples: Iterable[Sample],
        default_controls: ControlDefaults,
        tolerance: ToleranceConfig,
        mbti: Mapping[str, float] | None = None,
        ocean: Mapping[str, float] | None = None,
        hexaco: Mapping[str, float] | None = None,
    ) -> AuthorProfile:
        normalized_samples = [
            Sample(
                text=self.normalize_text(sample.text),
                path=sample.path,
                mode=sample.mode,
                audience=sample.audience,
                liwc_counts=sample.liwc_counts,
            )
            for sample in samples
        ]
        liwc_scores = self._aggregate_liwc(normalized_samples)
        lexicon = self._lexicon_from_samples(normalized_samples)
        sources = [SourceSpec(path=s.path, mode=s.mode, audience=s.audience) for s in normalized_samples]
        liwc_profile = LIWCProfile(categories=liwc_scores, domain_mode=next(iter(liwc_scores), "reform"))
        projected_mbti, projected_ocean, projected_hexaco = self._project_traits(liwc_scores)
        return AuthorProfile(
            author_id=author_id,
            sources=sources,
            liwc_profile=liwc_profile,
            lexicon=lexicon,
            default_controls=default_controls,
            tolerance=tolerance,
            mbti=dict(mbti) if mbti else projected_mbti,
            ocean=dict(ocean) if ocean else projected_ocean,
            hexaco=dict(hexaco) if hexaco else projected_hexaco,
        )
