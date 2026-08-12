"""The audit trail.

The trace is the product, not a debugging aid. A bare number is worthless to
an auditor: what has to survive the trip from this engine to a validation body
is the derivation — which formula, on which inputs, with which factor, taken
from which document.

So the calculator does not return a float. It returns an ordered list of
`Step`, each of which either carries a value and everything used to reach it,
or carries nothing and says what was missing. The final removal figure is one
of those steps, not a privileged return value.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mrv_engine.core.factors import Factor


@dataclass(frozen=True)
class Step:
    key: str
    label: str
    unit: str
    value: float | None = None
    formula: str | None = None
    inputs: dict[str, float] = field(default_factory=dict)
    factors: tuple[Factor, ...] = ()
    # Names of the data the step needed and did not get. Empty when computed.
    missing: tuple[str, ...] = ()
    note: str | None = None

    @property
    def computed(self) -> bool:
        return self.value is not None

    @property
    def provisional(self) -> bool:
        """True when any factor applied here has no documented source."""
        return any(not f.sourced for f in self.factors)


@dataclass(frozen=True)
class Calculation:
    steps: tuple[Step, ...]

    def step(self, key: str) -> Step | None:
        return next((s for s in self.steps if s.key == key), None)

    def value(self, key: str) -> float | None:
        step = self.step(key)
        return step.value if step else None

    @property
    def net_removal_t_co2e(self) -> float | None:
        """The headline figure, or None when the chain could not be completed."""
        return self.value("net_removal")

    @property
    def missing(self) -> tuple[str, ...]:
        """Every distinct input that blocked a step, in the order encountered."""
        seen: list[str] = []
        for step in self.steps:
            for name in step.missing:
                if name not in seen:
                    seen.append(name)
        return tuple(seen)

    @property
    def provisional(self) -> bool:
        """True when any computed step rests on an unsourced factor."""
        return any(s.provisional for s in self.steps if s.computed)
