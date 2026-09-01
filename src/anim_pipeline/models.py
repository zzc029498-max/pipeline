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
class Asset:
    project: str
    kind: str
    name: str
    source: Path

    @property
    def key(self) -> str:
        return f"{self.project}/{self.kind}/{self.name}"


@dataclass(frozen=True, slots=True)
class PublishResult:
    asset: Asset
    version: int
    directory: Path
    manifest: Path

