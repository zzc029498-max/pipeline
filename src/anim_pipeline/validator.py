from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from .models import Asset, AssetRef, Finding, PublishRequest, Severity


@dataclass(frozen=True, slots=True)
class FileInventory:
    root: Path
    files: tuple[Path, ...]

    @classmethod
    def scan(cls, root: Path) -> FileInventory:
        if not root.is_dir():
            return cls(root, ())
        files = tuple(sorted(path for path in root.rglob("*") if path.is_file()))
        return cls(root, files)


@dataclass(frozen=True, slots=True)
class ValidationContext:
    asset: AssetRef
    source: Path
    inventory: FileInventory


Rule = Callable[[ValidationContext], Iterable[Finding]]
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
SCENE_EXTENSIONS = {".abc", ".blend", ".fbx", ".ma", ".mb", ".obj", ".usd", ".usda", ".usdc"}
TEXTURE_EXTENSIONS = {".exr", ".hdr", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".tx"}


def naming_rule(context: ValidationContext) -> Iterable[Finding]:
    asset = context.asset
    for field, value in (("project", asset.project), ("kind", asset.kind), ("name", asset.name)):
        if not NAME_PATTERN.fullmatch(value):
            yield Finding("naming", Severity.ERROR, f"{field} must use snake_case: {value!r}")


def source_rule(context: ValidationContext) -> Iterable[Finding]:
    source = context.source
    if not source.exists():
        yield Finding("source", Severity.ERROR, "Source path does not exist", source)
        return
    if not source.is_dir():
        yield Finding("source", Severity.ERROR, "Source must be a directory", source)
        return
    files = context.inventory.files
    if not files:
        yield Finding("source", Severity.ERROR, "Source directory is empty", source)
    elif not any(path.suffix.lower() in SCENE_EXTENSIONS for path in files):
        yield Finding("scene", Severity.ERROR, "No supported 3D scene found", source)


def texture_rule(context: ValidationContext) -> Iterable[Finding]:
    if not context.source.is_dir():
        return
    textures = [
        path for path in context.inventory.files if path.suffix.lower() in TEXTURE_EXTENSIONS
    ]
    if not textures:
        yield Finding("textures", Severity.WARNING, "No textures found", context.source)
    for texture in textures:
        if " " in texture.name:
            yield Finding("textures", Severity.ERROR, "Texture name contains spaces", texture)
        if texture.suffix.lower() not in {".exr", ".tx"}:
            yield Finding(
                "textures",
                Severity.WARNING,
                "Consider EXR/TX for production rendering",
                texture,
            )


class Validator:
    """Runs independent pipeline checks concurrently and returns deterministic output."""

    def __init__(self, rules: Iterable[Rule] | None = None) -> None:
        defaults = (naming_rule, source_rule, texture_rule)
        self.rules = tuple(defaults if rules is None else rules)

    def validate(self, request: PublishRequest | Asset) -> list[Finding]:
        if isinstance(request, Asset):
            request = PublishRequest.from_asset(request)
        context = ValidationContext(
            request.asset,
            request.source,
            FileInventory.scan(request.source),
        )
        if not self.rules:
            return []
        with ThreadPoolExecutor(
            max_workers=len(self.rules), thread_name_prefix="validation"
        ) as pool:
            groups = pool.map(lambda rule: list(rule(context)), self.rules)
        findings = [finding for group in groups for finding in group]
        return sorted(findings, key=lambda f: (f.severity != Severity.ERROR, f.rule, f.message))

    @staticmethod
    def can_publish(findings: Iterable[Finding]) -> bool:
        return all(finding.severity != Severity.ERROR for finding in findings)
