from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    severity: Severity
    message: str
    path: Path | None = None


@dataclass(frozen=True, slots=True)
class AssetRef:
    project: str
    kind: str
    name: str

    @property
    def key(self) -> str:
        return f"{self.project}/{self.kind}/{self.name}"


@dataclass(frozen=True, slots=True)
class Asset:
    """Compatibility model combining an asset identity with a publish source."""

    project: str
    kind: str
    name: str
    source: Path

    @property
    def ref(self) -> AssetRef:
        return AssetRef(self.project, self.kind, self.name)

    @property
    def key(self) -> str:
        return self.ref.key


@dataclass(frozen=True, slots=True)
class PublishRequest:
    asset: AssetRef
    source: Path
    comment: str = ""

    @classmethod
    def from_asset(cls, asset: Asset, comment: str = "") -> PublishRequest:
        return cls(asset.ref, asset.source, comment)


@dataclass(frozen=True, slots=True)
class PublishResult:
    asset: AssetRef
    version: int
    directory: Path
    manifest: Path
