from __future__ import annotations

import argparse
from pathlib import Path

from .models import Asset
from .service import PipelineService


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="frameforge", description="Validate and publish 3D assets")
    result.add_argument("source", type=Path)
    result.add_argument("--project", default="demo")
    result.add_argument("--kind", default="asset")
    result.add_argument("--name", required=True)
    result.add_argument("--publish-root", type=Path, default=Path("published"))
    result.add_argument("--publish", action="store_true")
    result.add_argument("--comment", default="")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    asset = Asset(args.project, args.kind, args.name, args.source.resolve())
    service = PipelineService(args.publish_root)
    findings = service.inspect(asset)
    for finding in findings:
        location = f" ({finding.path})" if finding.path else ""
        print(f"[{finding.severity.value.upper():7}] {finding.message}{location}")
    if not service.validator.can_publish(findings):
        print("Publish blocked.")
        return 1
    print("Validation passed.")
    if args.publish:
        result = service.publish(asset, args.comment)
        print(f"Published {asset.key} v{result.version:03d} -> {result.directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

