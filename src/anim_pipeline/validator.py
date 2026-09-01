from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .models import Asset, Finding, Severity

Rule = Callable[[Asset], Iterable[Finding]]
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
SCENE_EXTENSIONS = {".abc", ".blend", ".fbx", ".ma", ".mb", ".obj", ".usd", ".usda", ".usdc"}
TEXTURE_EXTENSIONS = {".exr", ".hdr", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".tx"}


def naming_rule(asset: Asset) -> Iterable[Finding]:
    for field, value in (("project", asset.project), ("kind", asset.kind), ("name", asset.name)):
        if not NAME_PATTERN.fullmatch(value):
            yield Finding("naming", Severity.ERROR, f"{field} must use snake_case: {value!r}")


def source_rule(asset: Asset) -> Iterable[Finding]:
    if not asset.source.exists():
        yield Finding("source", Severity.ERROR, "Source path does not exist", asset.source)
        return
    if not asset.source.is_dir():
        yield Finding("source", Severity.ERROR, "Source must be a directory", asset.source)
        return
    files = [path for path in asset.source.rglob("*") if path.is_file()]
    if not files:
        yield Finding("source", Severity.ERROR, "Source directory is empty", asset.source)
    elif not any(path.suffix.lower() in SCENE_EXTENSIONS for path in files):
        yield Finding("scene", Severity.ERROR, "No supported 3D scene found", asset.source)


def texture_rule(asset: Asset) -> Iterable[Finding]:
    if not asset.source.is_dir():
        return
    textures = [
        path for path in asset.source.rglob("*")
        if path.is_file() and path.suffix.lower() in TEXTURE_EXTENSIONS
    ]
    if not textures:
        yield Finding("textures", Severity.WARNING, "No textures found", asset.source)
    for texture in textures:
        if " " in texture.name:
            yield Finding("textures", Severity.ERROR, "Texture name contains spaces", texture)
        if texture.suffix.lower() not in {".exr", ".tx"}:
            yield Finding(
                "textures", Severity.WARNING,
                "Consider EXR/TX for production rendering", texture,
            )


class Validator:
    """Runs independent pipeline checks concurrently and returns deterministic output."""

    def __init__(self, rules: Iterable[Rule] | None = None) -> None:
        self.rules = tuple(rules or (naming_rule, source_rule, texture_rule))

    def validate(self, asset: Asset) -> list[Finding]:
        with ThreadPoolExecutor(max_workers=len(self.rules), thread_name_prefix="validation") as pool:
            groups = pool.map(lambda rule: list(rule(asset)), self.rules)
        findings = [finding for group in groups for finding in group]
        return sorted(findings, key=lambda f: (f.severity != Severity.ERROR, f.rule, f.message))

    @staticmethod
    def can_publish(findings: Iterable[Finding]) -> bool:
        return all(finding.severity != Severity.ERROR for finding in findings)

