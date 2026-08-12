"""What is missing before any of this could be proven to an auditor.

The gap register is the half of the output that says no. It walks the evidence
checklist from the active rule pack against what the batch actually carries and
reports, item by item, what is present, what is partial and what is absent.

Completeness is expressed as a fraction, but it is derived and always travels
next to the blocking-gap count. A single percentage invites the question "where
did that number come from", so the weights live in the rule pack where they can
be read, and a project can be 80% complete and still entirely unfinanceable
because one blocking item is missing.
"""

from __future__ import annotations

from dataclasses import dataclass

from mrv_engine.core.models import Batch, EvidenceItem, EvidenceStatus
from mrv_engine.core.rules import EvidenceRequirement, RulePack

_STATUS_CREDIT = {
    EvidenceStatus.PRESENT: 1.0,
    EvidenceStatus.PARTIAL: 0.5,
    EvidenceStatus.MISSING: 0.0,
}


@dataclass(frozen=True)
class GapItem:
    kind: str
    label: str
    status: EvidenceStatus
    blocking: bool
    weight: float
    document_reference: str | None = None
    note: str | None = None

    @property
    def satisfied(self) -> bool:
        return self.status is EvidenceStatus.PRESENT


@dataclass(frozen=True)
class GapRegister:
    items: tuple[GapItem, ...]

    @property
    def blocking_gaps(self) -> tuple[GapItem, ...]:
        return tuple(i for i in self.items if i.blocking and not i.satisfied)

    @property
    def review_items(self) -> tuple[GapItem, ...]:
        return tuple(
            i for i in self.items if not i.blocking and i.status is not EvidenceStatus.PRESENT
        )

    @property
    def completeness(self) -> float:
        """Weighted share of the checklist that is satisfied, 0..1."""
        total = sum(i.weight for i in self.items)
        if total == 0:
            return 0.0
        earned = sum(i.weight * _STATUS_CREDIT[i.status] for i in self.items)
        return earned / total


def assess(batch: Batch, pack: RulePack) -> GapRegister:
    supplied = {item.kind: item for item in batch.evidence}
    return GapRegister(
        items=tuple(
            _item(requirement, supplied.get(requirement.kind))
            for requirement in pack.evidence_checklist
        )
    )


def _item(requirement: EvidenceRequirement, supplied: EvidenceItem | None) -> GapItem:
    """Evidence the batch does not mention at all counts as missing, not absent.

    Silence is not an excuse: a checklist item nobody recorded is exactly the
    kind of gap that surfaces late and expensively.
    """
    return GapItem(
        kind=requirement.kind,
        label=requirement.label,
        status=supplied.status if supplied else EvidenceStatus.MISSING,
        blocking=requirement.blocking,
        weight=requirement.weight,
        document_reference=supplied.document_reference if supplied else None,
        note=supplied.note if supplied else None,
    )
