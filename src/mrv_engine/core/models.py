"""Data model for a single biomass batch.

Everything the engine reasons about is derived from `Batch`.

The model is deliberately permissive: almost every field below the batch
identifier is optional. That is not sloppiness — the entire purpose of the
engine is to say what is missing, so it has to accept an incomplete batch and
report on it rather than refuse to load it. A batch with nothing but a
feedstock type is a valid input; it simply produces a very short calculation
and a very long gap register.

Units are part of the field name (`_kg`, `_km`, `_c`, `_kwh`) and fractions are
always 0..1, never percentages. There is no unit conversion layer and there is
not going to be one: ambiguous units are how quantification errors get in.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GeoPoint(_Model):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class BaselineFate(StrEnum):
    """What would have happened to the biomass without the project.

    This drives both eligibility and the baseline emissions, and it is the
    single field most likely to be asserted without evidence. It is recorded
    here as a claim; whether it is *documented* is tracked separately as an
    evidence item.
    """

    BURNED_IN_FIELD = "burned_in_field"
    LEFT_TO_DECAY = "left_to_decay"
    LANDFILLED = "landfilled"
    ANIMAL_FEED = "animal_feed"
    ENERGY_RECOVERY = "energy_recovery"
    OTHER_PRODUCTIVE_USE = "other_productive_use"
    UNKNOWN = "unknown"


class Feedstock(_Model):
    # Free-form on purpose: the feedstock taxonomy belongs in the rule packs,
    # not in the code, so that adding a feedstock does not require a release.
    feedstock_type: str
    region: str | None = None
    supplier_id: str | None = None
    is_residue: bool | None = None
    purpose_grown: bool | None = None
    baseline_fate: BaselineFate = BaselineFate.UNKNOWN
    competing_uses: list[str] = Field(default_factory=list)
    collection_date: date | None = None
    collection_site: GeoPoint | None = None


class MassRecord(_Model):
    wet_mass_kg: float = Field(gt=0)
    moisture_fraction: float | None = Field(default=None, ge=0, lt=1)

    @property
    def dry_mass_kg(self) -> float | None:
        if self.moisture_fraction is None:
            return None
        return self.wet_mass_kg * (1 - self.moisture_fraction)


class TransportLeg(_Model):
    distance_km: float = Field(ge=0)
    mode: str
    payload_mass_kg: float | None = Field(default=None, gt=0)


class FuelUse(_Model):
    fuel: str
    quantity: float = Field(ge=0)
    unit: str


class PyrolysisRun(_Model):
    facility_id: str | None = None
    technology: str | None = None
    peak_temperature_c: float | None = Field(default=None, gt=0)
    residence_time_min: float | None = Field(default=None, gt=0)
    biochar_mass_kg: float | None = Field(default=None, gt=0)
    electricity_kwh: float | None = Field(default=None, ge=0)
    fuel_use: list[FuelUse] = Field(default_factory=list)
    run_date: date | None = None


class LabResult(_Model):
    """Laboratory characterisation of the biochar.

    `organic_carbon_fraction` sets how much carbon there is; the H/Corg molar
    ratio is what methodologies use to decide how much of it still counts after
    a hundred years. Without a lab report neither is known, and no defensible
    removal figure exists — which is exactly what the gap register should say.
    """

    laboratory_id: str | None = None
    report_reference: str | None = None
    sample_date: date | None = None
    organic_carbon_fraction: float | None = Field(default=None, gt=0, le=1)
    hydrogen_to_organic_carbon_molar_ratio: float | None = Field(default=None, gt=0)
    ash_fraction: float | None = Field(default=None, ge=0, lt=1)


class EndUse(_Model):
    application_type: str | None = None
    application_site: GeoPoint | None = None
    application_date: date | None = None


class EvidenceStatus(StrEnum):
    PRESENT = "present"
    PARTIAL = "partial"
    MISSING = "missing"


class EvidenceItem(_Model):
    """A document backing one factual claim about the batch.

    `kind` is matched against the evidence checklist in the active rule pack,
    so the vocabulary lives there rather than here.
    """

    kind: str
    status: EvidenceStatus = EvidenceStatus.MISSING
    document_reference: str | None = None
    note: str | None = None


class Batch(_Model):
    batch_id: str
    feedstock: Feedstock
    mass: MassRecord | None = None
    transport: list[TransportLeg] = Field(default_factory=list)
    pyrolysis: PyrolysisRun | None = None
    lab: LabResult | None = None
    end_use: EndUse | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
