"""Rule packs and the small condition language they are written in.

Rules are data, not code. Methodologies get revised — VM0044 is under revision
as this is written — and a rule set that lives in Python cannot be versioned,
diffed or swapped for a different standard without a release. So a rule pack is
a YAML file carrying its own version, and the engine is the thing that reads it.

Conditions evaluate to three values, not two: true, false, and unknown. Unknown
is what a condition returns when the field it asks about is absent, and it is
the reason this module exists in its present shape. "We have no evidence that
the biomass was purpose-grown" and "we have evidence that it was not" are
different answers, and collapsing them into one is exactly the error the engine
is built to avoid.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mrv_engine.core.models import Batch


class Severity(StrEnum):
    BLOCKING = "blocking"
    REVIEW = "review"


class Condition(BaseModel):
    """One node of a condition tree.

    A leaf names a `field` by dotted path and one operator. A branch composes
    other conditions with `all_of`, `any_of` or `not`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    field_path: str | None = Field(default=None, alias="field")
    equals: Any = Field(default=None, alias="is")
    one_of: list[Any] | None = Field(default=None, alias="in")
    contains_any: list[Any] | None = None
    is_missing: bool | None = None
    less_than: float | None = Field(default=None, alias="lt")
    greater_than: float | None = Field(default=None, alias="gt")
    all_of: list[Condition] | None = None
    any_of: list[Condition] | None = None
    negated: Condition | None = Field(default=None, alias="not")


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    severity: Severity
    when: Condition
    message: str


class EvidenceRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str
    label: str
    # Blocking evidence is what a validation body will refuse to proceed
    # without; the rest lowers confidence but does not stop the project.
    blocking: bool = False
    weight: float = Field(default=1.0, gt=0)


class RulePack(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    version: str
    description: str | None = None
    eligibility_rules: list[Rule] = Field(default_factory=list)
    evidence_checklist: list[EvidenceRequirement] = Field(default_factory=list)


MISSING = object()


def resolve(path: str, batch: Batch) -> Any:
    """Walk a dotted path from the batch, returning None if anything is absent."""
    current: Any = batch
    for part in path.split("."):
        if current is None:
            return None
        current = getattr(current, part, MISSING)
        if current is MISSING:
            raise KeyError(f"no such field on the batch model: {path}")
    return current


def evaluate(condition: Condition, batch: Batch) -> bool | None:
    """Evaluate a condition against a batch. None means undetermined."""
    if condition.all_of is not None:
        results = [evaluate(c, batch) for c in condition.all_of]
        if any(r is False for r in results):
            return False
        return None if any(r is None for r in results) else True

    if condition.any_of is not None:
        results = [evaluate(c, batch) for c in condition.any_of]
        if any(r is True for r in results):
            return True
        return None if any(r is None for r in results) else False

    if condition.negated is not None:
        inner = evaluate(condition.negated, batch)
        return None if inner is None else not inner

    if condition.field_path is None:
        raise ValueError("a leaf condition must name a field")

    value = resolve(condition.field_path, batch)

    # The one operator that reads absence directly, so it is never undetermined.
    if condition.is_missing is not None:
        absent = value is None or value == []
        return absent is condition.is_missing

    if value is None:
        return None

    if condition.equals is not None:
        return value == condition.equals
    if condition.one_of is not None:
        return value in condition.one_of
    if condition.contains_any is not None:
        return any(item in value for item in condition.contains_any)
    if condition.less_than is not None:
        return value < condition.less_than
    if condition.greater_than is not None:
        return value > condition.greater_than

    raise ValueError(f"condition on '{condition.field_path}' names no operator")
