"""Numeric factors and where each of them came from.

A factor without provenance is not a factor, it is a rumour. Every value the
calculator applies carries a `Provenance` or an explicit `None`, and `None`
propagates: any step that consumes an unsourced factor is marked provisional
in the trace, and so is the result that depends on it.

This is deliberately uncomfortable. v0.1 ships with mostly unsourced
placeholders, so almost the whole chain currently reports as provisional. That
is the honest state of the engine before the methodology factors are entered,
and it should stay visible rather than be papered over with plausible numbers.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reference: str
    kind: str = "document"
    version: str | None = None
    published: str | None = None
    url: str | None = None


class Factor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    value: float
    unit: str
    # `key` selects among variants of the same factor — a transport factor per
    # vehicle class, a yield per feedstock. Absent means the factor is global.
    key: str | None = None
    source: Provenance | None = None
    note: str | None = None

    @property
    def sourced(self) -> bool:
        return self.source is not None


class FactorSet(BaseModel):
    """A versioned collection of factors, addressed by name and optional key."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    factors: list[Factor] = Field(default_factory=list)

    def get(self, name: str, key: str | None = None) -> Factor | None:
        """Return the factor for `name`/`key`, falling back to the keyless one.

        The fallback matters: a transport factor for an unlisted vehicle class
        should degrade to the generic road-freight value rather than blocking
        the calculation, and the trace will show which one was applied.
        """
        if key is not None:
            for factor in self.factors:
                if factor.name == name and factor.key == key:
                    return factor
        for factor in self.factors:
            if factor.name == name and factor.key is None:
                return factor
        return None

    @property
    def unsourced(self) -> list[Factor]:
        return [f for f in self.factors if not f.sourced]
