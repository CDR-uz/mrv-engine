"""Chain of custody, derived rather than stored.

There is no event store in v0.1 and there does not need to be one: the batch
already records when the biomass was collected, when it moved, when it was
pyrolysed, when it was sampled and when it was applied. The timeline is those
dates put in stage order.

What the module adds is the check nobody does by hand — whether the dates are
in a physically possible order. A production run dated before the harvest it
consumed, or an application dated before the run that produced the biochar, is
either a typo or a chain-of-custody problem, and both are far cheaper to find
now than during verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from mrv_engine.core.models import Batch


class Stage(StrEnum):
    COLLECTION = "collection"
    TRANSPORT = "transport"
    PYROLYSIS = "pyrolysis"
    LABORATORY = "laboratory"
    APPLICATION = "application"


# The order the physical world imposes. Sampling is the one that can legitimately
# float: biochar is sometimes sampled after it has already gone to the field.
_PHYSICAL_ORDER = (Stage.COLLECTION, Stage.TRANSPORT, Stage.PYROLYSIS, Stage.APPLICATION)


@dataclass(frozen=True)
class Event:
    stage: Stage
    date: date | None
    label: str
    detail: str | None = None

    @property
    def recorded(self) -> bool:
        return self.date is not None


@dataclass(frozen=True)
class Timeline:
    events: tuple[Event, ...]
    inconsistencies: tuple[str, ...]

    @property
    def recorded(self) -> tuple[Event, ...]:
        return tuple(e for e in self.events if e.recorded)

    @property
    def undated(self) -> tuple[Stage, ...]:
        return tuple(e.stage for e in self.events if not e.recorded)


def build(batch: Batch) -> Timeline:
    events = (
        Event(
            stage=Stage.COLLECTION,
            date=batch.feedstock.collection_date,
            label="Biomass collected",
            detail=batch.feedstock.supplier_id,
        ),
        Event(
            stage=Stage.TRANSPORT,
            date=_first_departure(batch),
            label="Transported to the facility",
            detail=_transport_detail(batch),
        ),
        Event(
            stage=Stage.PYROLYSIS,
            date=batch.pyrolysis.run_date if batch.pyrolysis else None,
            label="Pyrolysis run",
            detail=batch.pyrolysis.facility_id if batch.pyrolysis else None,
        ),
        Event(
            stage=Stage.LABORATORY,
            date=batch.lab.sample_date if batch.lab else None,
            label="Sampled for laboratory analysis",
            detail=batch.lab.report_reference if batch.lab else None,
        ),
        Event(
            stage=Stage.APPLICATION,
            date=batch.end_use.application_date if batch.end_use else None,
            label="Biochar applied",
            detail=batch.end_use.application_type if batch.end_use else None,
        ),
    )
    return Timeline(events=events, inconsistencies=_inconsistencies(events))


def _first_departure(batch: Batch) -> date | None:
    dates = [leg.departure_date for leg in batch.transport if leg.departure_date]
    return min(dates) if dates else None


def _transport_detail(batch: Batch) -> str | None:
    if not batch.transport:
        return None
    total_km = sum(leg.distance_km for leg in batch.transport)
    return f"{len(batch.transport)} leg(s), {total_km:g} km"


def _inconsistencies(events: tuple[Event, ...]) -> tuple[str, ...]:
    """Report every dated stage that precedes a stage that must come before it."""
    by_stage = {e.stage: e for e in events}
    dated = [(stage, by_stage[stage].date) for stage in _PHYSICAL_ORDER if by_stage[stage].date]

    problems = []
    for index, (stage, when) in enumerate(dated):
        for earlier_stage, earlier_when in dated[:index]:
            if when < earlier_when:
                problems.append(
                    f"{stage} ({when}) precedes {earlier_stage} ({earlier_when})"
                )
    return tuple(problems)
