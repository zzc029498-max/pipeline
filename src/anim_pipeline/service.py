from __future__ import annotations

from pathlib import Path

from .models import Asset, Finding, PublishResult
from .publisher import Publisher
from .validator import Validator


class PipelineService:
    def __init__(self, publish_root: Path) -> None:
        self.validator = Validator()
        self.publisher = Publisher(publish_root)

    def inspect(self, asset: Asset) -> list[Finding]:
        return self.validator.validate(asset)

    def publish(self, asset: Asset, comment: str = "") -> PublishResult:
        findings = self.inspect(asset)
        if not self.validator.can_publish(findings):
            messages = "; ".join(f.message for f in findings if f.severity.value == "error")
            raise ValueError(f"Publish blocked: {messages}")
        return self.publisher.publish(asset, comment)

