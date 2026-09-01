from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import Asset, PublishResult


class Publisher:
    """Publishes immutable versions using a staging directory and atomic rename."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def publish(self, asset: Asset, comment: str = "") -> PublishResult:
        target_root = self.root / asset.project / asset.kind / asset.name
        target_root.mkdir(parents=True, exist_ok=True)
        version = self._next_version(target_root)
        destination = target_root / f"v{version:03d}"
        staging = Path(tempfile.mkdtemp(prefix=".publishing-", dir=target_root))
        try:
            payload = staging / "payload"
            shutil.copytree(asset.source, payload)
            manifest = self._manifest(asset, version, payload, comment)
            manifest_path = staging / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            os.replace(staging, destination)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return PublishResult(asset, version, destination, destination / "manifest.json")

    @staticmethod
    def _next_version(root: Path) -> int:
        versions = [int(path.name[1:]) for path in root.glob("v[0-9][0-9][0-9]")]
        return max(versions, default=0) + 1

    @staticmethod
    def _manifest(asset: Asset, version: int, payload: Path, comment: str) -> dict[str, object]:
        files = []
        for path in sorted(p for p in payload.rglob("*") if p.is_file()):
            files.append({
                "path": path.relative_to(payload).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        return {
            "schema": 1,
            "asset": asset.key,
            "version": version,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "comment": comment,
            "files": files,
        }

