"""One batch in, one dossier out.

This is the module that makes the other four add up to something. A calculator,
a screener, a gap register and a timeline sitting side by side are four demos;
assembled into a single document, addressed by batch, stamped with the rule
pack and factor set that produced it, they are the pre-validation package the
project actually has to hand to somebody.

The stamp matters as much as the contents. A removal figure without the version
of the rules and factors behind it cannot be reproduced, and a number that
cannot be reproduced is not evidence of anything.
"""

from __future__ import annotations

from dataclasses import dataclass

from mrv_engine.core import evidence, timeline
from mrv_engine.core.calculator import calculate
from mrv_engine.core.eligibility import EligibilityResult, screen
from mrv_engine.core.evidence import GapRegister
from mrv_engine.core.factors import FactorSet
from mrv_engine.core.identity import BatchId
from mrv_engine.core.models import Batch
from mrv_engine.core.rules import RulePack
from mrv_engine.core.timeline import Timeline
from mrv_engine.core.trace import Calculation

DISCLAIMER = (
    "Preliminary project-development estimate. Not a certified carbon credit "
    "calculation and not a methodology-compliant quantification. Final figures "
    "depend on the selected methodology, laboratory results and independent "
    "validation and verification."
)


@dataclass(frozen=True)
class Provenance:
    """What produced this dossier, so that it can be reproduced."""

    rule_pack: str
    rule_pack_version: str
    factor_set_version: str
    unsourced_factors: int


@dataclass(frozen=True)
class Dossier:
    batch_id: str
    parsed_id: BatchId | None
    provenance: Provenance
    eligibility: EligibilityResult
    calculation: Calculation
    gaps: GapRegister
    timeline: Timeline
    disclaimer: str = DISCLAIMER

    @property
    def net_removal_t_co2e(self) -> float | None:
        return self.calculation.net_removal_t_co2e

    @property
    def provisional(self) -> bool:
        """True when anything here rests on a factor with no documented source."""
        return self.calculation.provisional

    @property
    def blocking_gap_count(self) -> int:
        return len(self.gaps.blocking_gaps)

    @property
    def notes(self) -> tuple[str, ...]:
        """Things a reader should be told before they quote a number from this."""
        notes: list[str] = []
        if self.parsed_id is None:
            notes.append(
                f"batch identifier '{self.batch_id}' does not follow the "
                "OPERATOR-CC-REG-FDS-YYYY-NNNNN convention"
            )
        if self.provisional:
            notes.append(
                f"{self.provenance.unsourced_factors} of the factors applied have no "
                "documented source — every figure here is provisional"
            )
        if self.calculation.net_removal_t_co2e is None:
            notes.append(
                "no net removal could be computed: "
                + ", ".join(self.calculation.missing)
            )
        notes.extend(f"timeline: {problem}" for problem in self.timeline.inconsistencies)
        return tuple(notes)


def build(batch: Batch, factors: FactorSet, pack: RulePack) -> Dossier:
    return Dossier(
        batch_id=batch.batch_id,
        parsed_id=BatchId.parse(batch.batch_id),
        provenance=Provenance(
            rule_pack=pack.name,
            rule_pack_version=pack.version,
            factor_set_version=factors.version,
            unsourced_factors=len(factors.unsourced),
        ),
        eligibility=screen(batch, pack),
        calculation=calculate(batch, factors),
        gaps=evidence.assess(batch, pack),
        timeline=timeline.build(batch),
    )
