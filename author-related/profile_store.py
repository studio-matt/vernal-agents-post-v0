"""Profile persistence helpers constrained to the content_machine folder."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from .asset_loader import ASSET_ROOT, AssetLoader
from .models import AuthorProfile


class SchemaViolationError(ValueError):
    """Raised when a profile payload does not satisfy the bundled schema."""


class ProfileStore:
    """CRUD operations for author profiles serialized to JSON."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or ASSET_ROOT
        self.loader = AssetLoader(self.root)
        self.profile_dir = self.root / "profiles"
        self.profile_dir.mkdir(exist_ok=True)
        self.schema = self.loader.read_json("author_profile.schema.json")

    def _profile_path(self, author_id: str) -> Path:
        safe_id = author_id.replace("/", "_")
        return self.profile_dir / f"{safe_id}.json"

    def _validate_required(self, payload: Mapping[str, object]) -> None:
        required_fields: list[str] = list(self.schema.get("required", []))
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise SchemaViolationError(f"Missing required fields: {', '.join(missing)}")

    def save(self, profile: AuthorProfile) -> Path:
        payload = profile.to_dict()
        self._validate_required(payload)
        target = self._profile_path(profile.author_id)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def load(self, author_id: str) -> AuthorProfile:
        path = self._profile_path(author_id)
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {author_id}")
        payload: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
        self._validate_required(payload)
        return AuthorProfile.from_dict(payload)

    def list_profiles(self) -> list[str]:
        return sorted(path.stem for path in self.profile_dir.glob("*.json"))
