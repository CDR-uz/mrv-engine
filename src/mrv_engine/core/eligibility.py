"""Whether this biomass could support a carbon removal project at all.

The screener answers before any money is spent on laboratory work: is there a
reason this feedstock cannot qualify, is there something that needs a human to
look at it, or is there simply not enough information to say.

The last of those is a real answer and is ranked accordingly. A rule that could
not be evaluated because the batch does not record the field it asks about is
reported as undetermined, never quietly as a pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from mrv_engine.core.models import Batch
from mrv_engine.core.rules import Rule, RulePack, Severity, evaluate


class Verdict(StrEnum):
    POTENTIALLY_ELIGIBLE = "potentially_eligible"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_ELIGIBLE = "not_eligible"


class Outcome(StrEnum):
    FIRED = "fired"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    severity: Severity
    outcome: Outcome
    message: str


@dataclass(frozen=True)
class EligibilityResult:
    verdict: Verdict
    findings: tuple[Finding, ...]

    @property
    def blocking(self) -> tuple[Finding, ...]:
        return tuple(
            f
            for f in self.findings
            if f.severity is Severity.BLOCKING and f.outcome is Outcome.FIRED
        )

    @property
    def undetermined(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.outcome is Outcome.UNDETERMINED)


def screen(batch: Batch, pack: RulePack) -> EligibilityResult:
    findings = tuple(
        finding for rule in pack.eligibility_rules if (finding := _apply(rule, batch))
    )
    return EligibilityResult(verdict=_verdict(findings), findings=findings)


def _apply(rule: Rule, batch: Batch) -> Finding | None:
    """Return a finding when a rule fires or cannot be decided, else nothing."""
    result = evaluate(rule.when, batch)
    if result is False:
        return None
    return Finding(
        rule_id=rule.id,
        title=rule.title,
        severity=rule.severity,
        outcome=Outcome.FIRED if result is True else Outcome.UNDETERMINED,
        message=rule.message,
    )


def _verdict(findings: tuple[Finding, ...]) -> Verdict:
    """Most conservative applicable verdict wins.

    not_eligible > insufficient_data > needs_review > potentially_eligible.
    Unknowns outrank review items deliberately: a question nobody has answered
    is a worse position to take to an auditor than one that has been looked at.
    """
    if any(f.severity is Severity.BLOCKING and f.outcome is Outcome.FIRED for f in findings):
        return Verdict.NOT_ELIGIBLE
    if any(f.outcome is Outcome.UNDETERMINED for f in findings):
        return Verdict.INSUFFICIENT_DATA
    if findings:
        return Verdict.NEEDS_REVIEW
    return Verdict.POTENTIALLY_ELIGIBLE
