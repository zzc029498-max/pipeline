from __future__ import annotations

from pathlib import Path

from .errors import ValidationRejected
from .models import Asset, Finding, PublishRequest, PublishResult
from .publisher import Publisher
from .validator import Validator


class PipelineService:
    def __init__(
        self,
        publish_root: Path | None = None,
        *,
        validator: Validator | None = None,
        publisher: Publisher | None = None,
    ) -> None:
        if publisher is None:
            if publish_root is None:
                raise TypeError("publish_root is required when publisher is not provided")
            publisher = Publisher(publish_root)
        self.validator = validator or Validator()
        self.publisher = publisher

    def inspect(self, asset: Asset) -> list[Finding]:
        return self.validator.validate(asset)

    def publish(self, asset: Asset, comment: str = "") -> PublishResult:
        request = PublishRequest.from_asset(asset, comment)
        preflight = self.validator.validate(request)
        if not self.validator.can_publish(preflight):
            raise ValidationRejected(preflight)

        def validate_payload(payload: Path) -> None:
            staged_request = PublishRequest(request.asset, payload, request.comment)
            findings = self.validator.validate(staged_request)
            if not self.validator.can_publish(findings):
                raise ValidationRejected(findings)

        return self.publisher.publish(request, payload_check=validate_payload)
