from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .models import Asset, PublishResult

PayloadCheck = Callable[[Path], None]


class Publisher:
    """Publishes immutable versions using a staging directory and atomic rename."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def publish(
        self,
        asset: Asset,
        comment: str = "",
        payload_check: PayloadCheck | None = None,
    ) -> PublishResult:
        target_root = (self.root / asset.project / asset.kind / asset.name).resolve()
        try:
            target_root.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Asset destination escapes the publish root") from exc
        target_root.mkdir(parents=True, exist_ok=True)
        with self._publish_lock(target_root):
            version = self._next_version(target_root)
            destination = target_root / f"v{version:03d}"
            staging = Path(tempfile.mkdtemp(prefix=".publishing-", dir=target_root))
            try:
                payload = staging / "payload"
                shutil.copytree(asset.source, payload)
                if payload_check:
                    payload_check(payload)
                manifest = self._manifest(asset, version, payload, comment)
                manifest_path = staging / "manifest.json"
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                os.replace(staging, destination)
            except Exception:
                shutil.rmtree(staging, ignore_errors=True)
                raise
        return PublishResult(asset, version, destination, destination / "manifest.json")

    @staticmethod
    @contextmanager
    def _publish_lock(root: Path) -> Iterator[None]:
        """Serialize version allocation across processes; the OS releases locks on crashes."""
        import fcntl

        with (root / ".publish.lock").open("a", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

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
                "sha256": Publisher._checksum(path),
            })
        return {
            "schema": 1,
            "asset": asset.key,
            "version": version,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "comment": comment,
            "files": files,
        }

    @staticmethod
    def _checksum(path: Path, chunk_size: int = 1024 * 1024) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(chunk_size):
                digest.update(chunk)
        return digest.hexdigest()
