"""The batch identifier.

`CAC-UZ-SAM-COT-2026-00001` reads as operator, country, region, feedstock,
year, sequence. It is the string that has to survive on a delivery note, in a
laboratory submission form and in an auditor's spreadsheet years later, so it
is fixed-width, uppercase and carries no punctuation beyond the separator.

Parsing is offered, not enforced. A batch whose identifier does not match the
convention still loads and still computes — an operator with their own numbering
is not a reason to refuse the data — but the dossier notes that the identifier
could not be read, because an unparseable ID is one of the cheaper things to
fix early and one of the more annoying to fix late.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PATTERN = re.compile(
    r"^(?P<operator>[A-Z]{2,4})"
    r"-(?P<country>[A-Z]{2})"
    r"-(?P<region>[A-Z]{3})"
    r"-(?P<feedstock>[A-Z]{3})"
    r"-(?P<year>\d{4})"
    r"-(?P<sequence>\d{5})$"
)


@dataclass(frozen=True)
class BatchId:
    operator: str
    country: str
    region: str
    feedstock: str
    year: int
    sequence: int

    @classmethod
    def parse(cls, value: str) -> BatchId | None:
        match = PATTERN.match(value)
        if match is None:
            return None
        return cls(
            operator=match["operator"],
            country=match["country"],
            region=match["region"],
            feedstock=match["feedstock"],
            year=int(match["year"]),
            sequence=int(match["sequence"]),
        )

    def __str__(self) -> str:
        return (
            f"{self.operator}-{self.country}-{self.region}"
            f"-{self.feedstock}-{self.year:04d}-{self.sequence:05d}"
        )
