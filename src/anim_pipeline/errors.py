from __future__ import annotations

from collections.abc import Iterable

from .models import Finding, Severity


class PipelineError(Exception):
    """Base class for expected pipeline failures."""


class InvalidPublishRequest(PipelineError, ValueError):
    """The request cannot be mapped to a safe publish operation."""


class ValidationRejected(PipelineError, ValueError):
    def __init__(self, findings: Iterable[Finding]) -> None:
        self.findings = tuple(f for f in findings if f.severity is Severity.ERROR)
        messages = "; ".join(f.message for f in self.findings)
        super().__init__(f"Publish blocked: {messages}")
