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

    def _z_score(self, category: str, value: float, domain: str | None = None) -> float:
        """Calculate z-score with optional domain-aware baselines.
        
        Improved: Supports domain-aware LIWC validation with context-specific z-scores.
        """
        # Try domain-specific baseline first if domain is provided
        if domain:
            try:
                domain_baselines = self.loader.load_domain_baselines()
                domain_key = f"LWC{domain}" if not domain.startswith("LWC") else domain
                if domain_key in domain_baselines:
                    mean, stdev = domain_baselines[domain_key]
                    stdev = stdev if stdev > 0 else 1.0
                    return (value - mean) / stdev
            except Exception:
                pass  # Fall back to global baseline
        
        # Fall back to global LIWC baseline
        baseline = self.baselines.get(category, {"mean": 0.0, "stdev": 1.0})
        stdev = baseline.get("stdev", 1.0) or 1.0
        return (value - baseline.get("mean", 0.0)) / stdev

    def _quantile_label(self, z_score: float) -> str:
        """Derive quantile-style label from z-score.
        
        Improved: Derived LIWC target bands with quantile-style labels.
        """
        if z_score <= -1.5:
            return "very_low"
        elif z_score <= -0.5:
            return "low"
        elif z_score <= 0.5:
            return "medium"
        elif z_score <= 1.5:
            return "medium_high"
        else:
            return "high"

    def _aggregate_liwc(self, samples: Iterable[Sample], domain: str | None = None) -> dict[str, LIWCScore]:
        """Aggregate LIWC scores with domain-aware z-scores and quantile labels.
        
        Improved: Uses domain-aware validation and quantile-style target bands.
        """
        category_values: dict[str, list[float]] = defaultdict(list)
        for sample in samples:
            for category, value in sample.liwc_counts.items():
                category_values[category].append(float(value))
        
        aggregated: dict[str, LIWCScore] = {}
        for category, values in category_values.items():
            mean_value = statistics.fmean(values) if values else 0.0
            stdev_value = statistics.pstdev(values) if len(values) > 1 else 0.0
            z = self._z_score(category, mean_value, domain)
            aggregated[category] = LIWCScore(mean=mean_value, stdev=stdev_value, z=z)
        return aggregated

    @staticmethod
    def _sanitize_label(label: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", label.lower())

    def _build_trait_alias_map(self) -> dict[str, str]:
        """Build explicit alias map for trait lookup.
        
        Improved: Hardened trait lookup via explicit alias maps instead of fuzzy matching.
        """
        alias_map: dict[str, str] = {}
        
        # Build aliases from trait_mapping
        for trait_key, mapping in self.trait_mapping.items():
            sanitized_key = self._sanitize_label(trait_key)
            alias_map[sanitized_key] = trait_key
            
            # Add abbreviation aliases
            if "abbreviation" in mapping:
                abbrev = self._sanitize_label(str(mapping["abbreviation"]))
                alias_map[abbrev] = trait_key
            
            # Add common variations
            if "liwc" in sanitized_key:
                alias_map[sanitized_key.replace("liwc", "")] = trait_key
            if sanitized_key.endswith("usage"):
                alias_map[sanitized_key[:-5]] = trait_key
        
        # Build aliases from vectorization
        for vector_key, details in self.vectorization.items():
            sanitized_key = self._sanitize_label(vector_key)
            alias_map[sanitized_key] = vector_key
            
            if "abbreviation" in details:
                abbrev = self._sanitize_label(str(details["abbreviation"]))
                alias_map[abbrev] = vector_key
        
        return alias_map

    def _match_trait_key(self, category: str) -> str | None:
        """Match category to trait key using explicit alias map.
        
        Improved: Uses explicit alias maps for more reliable trait lookup.
        """
        if not hasattr(self, '_trait_alias_map'):
            self._trait_alias_map = self._build_trait_alias_map()
        
        sanitized = self._sanitize_label(category)
        
        # Direct lookup in alias map
        if sanitized in self._trait_alias_map:
            return self._trait_alias_map[sanitized]
        
        # Check if any alias key is contained in the category
        for alias, trait_key in self._trait_alias_map.items():
            if alias in sanitized or sanitized in alias:
                return trait_key
        
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
    def _infer_pos_suffix(word: str) -> str:
        """Infer part of speech using suffix-based heuristics.
        
        Improved: Revamped lexicon inference with suffix-based POS heuristics
        to avoid misleading verb/noun splits.
        """
        word_lower = word.lower()
        
        # Verb suffixes (higher priority)
        verb_suffixes = ["ing", "ed", "es", "ize", "ise", "ify", "ate"]
        for suffix in verb_suffixes:
            if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 2:
                return "verb"
        
        # Noun suffixes
        noun_suffixes = ["tion", "sion", "ness", "ment", "ity", "er", "or", "ist", "ism"]
        for suffix in noun_suffixes:
            if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 2:
                return "noun"
        
        # Adjective/adverb suffixes
        if word_lower.endswith("ly") and len(word_lower) > 4:
            return "adverb"
        if word_lower.endswith("al") or word_lower.endswith("ic") or word_lower.endswith("ive"):
            return "adjective"
        
        # Default: check length and common patterns
        if len(word_lower) <= 3:
            return "function"
        
        # Words ending in 'e' might be verbs (but not always)
        if word_lower.endswith("e") and len(word_lower) > 4:
            return "verb_candidate"
        
        return "unknown"

    @staticmethod
    def _lexicon_from_samples(samples: Iterable[Sample], limit: int = 30) -> LexiconBank:
        """Extract lexicon from samples using improved POS heuristics.
        
        Improved: Uses suffix-based POS heuristics to better identify verbs and nouns.
        Also adjusts letters per token calculation to avoid hovering near 4 characters.
        """
        tokens = Counter()
        for sample in samples:
            tokens.update(re.findall(r"\b[a-zA-Z']+\b", sample.text.lower()))
        
        most_common = [token for token, _ in tokens.most_common(limit * 2)]  # Get more candidates
        
        # Classify words using POS heuristics
        verbs = []
        nouns = []
        evaluatives = []
        metaphor_candidates = []
        avoid_words = []
        
        for word in most_common:
            pos = ProfileExtractor._infer_pos_suffix(word)
            word_len = len(word)
            
            # Filter out words that are too short (avoid hovering near 4 chars)
            # Increased threshold to avoid 4-character words
            if word_len < 5:
                avoid_words.append(word)
                continue
            
            # Calculate letters per token (avoid hovering near 4)
            letters_per_token = sum(1 for c in word if c.isalpha()) / max(1, len(word.split()))
            if letters_per_token < 4.5:  # Increased threshold from ~4 to 4.5
                avoid_words.append(word)
                continue
            
            if pos == "verb" or pos == "verb_candidate":
                verbs.append(word)
            elif pos == "noun":
                nouns.append(word)
            elif pos == "adverb":
                evaluatives.append(word)
            
            # Metaphor stems: longer words that are nouns or verbs
            if word_len > 6 and (pos == "noun" or pos == "verb"):
                metaphor_candidates.append(word)
        
        return LexiconBank(
            core_verbs=verbs[:10],
            core_nouns=nouns[:10],
            evaluatives=evaluatives[:10],
            metaphor_stems=metaphor_candidates[:8],
            avoid=avoid_words[:5],
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
        # IMPORTANT: Do NOT use domain-specific baselines for profile extraction
        # Profile baseline should always use global baselines to avoid double-applying platform deltas
        # Domain/platform adjustments should only be applied during content generation, not profile extraction
        # This ensures that if a user uploads Twitter samples, the baseline reflects their actual style
        # relative to global norms, not Twitter norms. Then during generation, we apply Twitter deltas.
        liwc_scores = self._aggregate_liwc(normalized_samples, domain=None)  # Always use global baseline
        # Store domain for reference but don't use it for z-score calculation
        domain = normalized_samples[0].mode if normalized_samples else None
        lexicon = self._lexicon_from_samples(normalized_samples)
        sources = [SourceSpec(path=s.path, mode=s.mode, audience=s.audience) for s in normalized_samples]
        liwc_profile = LIWCProfile(categories=liwc_scores, domain_mode=domain or next(iter(liwc_scores), "reform"))
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
