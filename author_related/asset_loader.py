"""Utility helpers for loading portable content machine assets.

All paths resolve relative to this folder so the asset pack can be
mounted as-is in downstream projects without extra dependencies.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from pathlib import Path

ASSET_ROOT = Path(__file__).resolve().parent


class AssetLoader:
    """Typed helpers for reading JSON/CSV/Markdown assets with validation."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or ASSET_ROOT

    def _resolve(self, file_name: str | Path) -> Path:
        candidate = (self.root / file_name).resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"Asset not found: {candidate}")
        if ASSET_ROOT not in candidate.parents and candidate != ASSET_ROOT:
            raise ValueError("Asset resolution must remain within the content_machine directory")
        return candidate

    def read_text(self, file_name: str | Path) -> str:
        path = self._resolve(file_name)
        return path.read_text(encoding="utf-8")

    def read_json(self, file_name: str | Path) -> MutableMapping[str, object]:
        return json.loads(self.read_text(file_name))

    def read_csv(self, file_name: str | Path, required_columns: Iterable[str] | None = None) -> list[dict[str, str]]:
        path = self._resolve(file_name)
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [dict(row) for row in reader]
        if required_columns:
            for column in required_columns:
                if column not in reader.fieldnames:
                    raise ValueError(f"Missing required column '{column}' in {file_name}")
        return rows

    def load_context_legend(self) -> list[dict[str, object]]:
        payload = self.read_json("context_domains.json")
        legend: list[dict[str, object]] = []
        for entry in payload:
            missing = [key for key in ("code", "label", "description") if key not in entry]
            if missing:
                raise ValueError(f"Context legend entry missing keys: {missing}")
            legend.append(
                {
                    "code": entry["code"],
                    "label": entry["label"],
                    "description": entry.get("description", ""),
                    "tags": entry.get("tags", []),
                }
            )
        return legend

    def load_adapters(self) -> Mapping[str, Mapping[str, object]]:
        adapters = self.read_json("adapters.json")
        if not isinstance(adapters, Mapping):
            raise ValueError("Adapters payload must be a mapping of adapter key to overlay")
        return adapters

    def load_vectorization(self) -> Mapping[str, Mapping[str, object]]:
        payload = self.read_json("HighLow_Vectorization.json")
        if not isinstance(payload, Mapping):
            raise ValueError("Vectorization payload must be a mapping")
        return payload

    def load_trait_mapping(self) -> Mapping[str, Mapping[str, list[str]]]:
        payload = self.read_json("Trait_Mapping.json")
        if not isinstance(payload, Mapping):
            raise ValueError("Trait mapping payload must be a mapping")
        return payload

    def load_domain_baselines(self) -> Mapping[str, tuple[float, float]]:
        payload = self.read_json("LWC_TextAnalysis.json")
        domain_data: Mapping[str, object] = payload.get("Textual Self-Expression Legend By Domain", {})  # type: ignore[index]
        baselines: dict[str, tuple[float, float]] = {}
        for code, value in domain_data.items():
            if not code.startswith("LWC") or not isinstance(value, list) or len(value) < 2:
                continue
            try:
                stdev, mean = float(value[0]), float(value[1])
            except (TypeError, ValueError):
                continue
            baselines[code] = (mean, stdev)
        return baselines

    def load_liwc_baselines(self) -> dict[str, dict[str, float]]:
        means = {
            row["Category"]: float(row["Total_Mean"]) for row in self.read_csv("LIWC_Mean_Table.csv", ["Category", "Total_Mean"])
        }
        stdevs = {
            row["Category"]: float(row["Total_StdDev"])
            for row in self.read_csv("LIWC_StdDev_Mean_Table.csv", ["Category", "Total_StdDev"])
        }
        baselines: dict[str, dict[str, float]] = {}
        for category, mean_value in means.items():
            baselines[category] = {"mean": mean_value, "stdev": stdevs.get(category, 1.0)}
        return baselines

    def list_assets(self) -> Sequence[Path]:
        return sorted(path for path in self.root.iterdir() if path.is_file())
