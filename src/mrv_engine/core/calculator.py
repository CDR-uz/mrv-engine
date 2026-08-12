"""Preliminary net carbon removal for one batch.

The chain:

    wet biomass -> dry biomass -> biochar -> carbon in biochar -> CO2 equivalent
    -> durable fraction after 100 years
    -> minus transport, process and uncertainty deductions
    -> preliminary net removal

Every link is emitted as a `Step` whether or not it could be computed. A link
that fails does not raise and does not silently produce zero: it records what
was missing and everything downstream of it stays uncomputed. A batch with no
laboratory report therefore yields a partial trace ending in a named gap,
which is the correct answer for that batch.

This produces a preliminary project-development estimate. It is not a
methodology-compliant quantification and it is not a carbon credit.
"""

from __future__ import annotations

from dataclasses import replace

from mrv_engine.core.factors import Factor, FactorSet
from mrv_engine.core.models import Batch
from mrv_engine.core.trace import Calculation, Step

KG_PER_TONNE = 1000.0


def calculate(batch: Batch, factors: FactorSet) -> Calculation:
    steps: list[Step] = []

    def emit(step: Step) -> float | None:
        steps.append(step)
        return step.value

    dry_mass_t = emit(_dry_mass(batch))
    biochar_t = emit(_biochar_mass(batch, factors, dry_mass_t))
    carbon_t = emit(_biochar_carbon(batch, biochar_t))
    gross_co2_t = emit(_carbon_as_co2(factors, carbon_t))
    durable_co2_t = emit(_durable_co2(batch, factors, gross_co2_t))
    transport_t = emit(_transport_emissions(batch, factors))
    process_t = emit(_process_emissions(batch, factors))
    deduction_t = emit(_uncertainty_deduction(factors, durable_co2_t))
    emit(_net_removal(durable_co2_t, transport_t, process_t, deduction_t))

    return Calculation(steps=tuple(steps))


def _dry_mass(batch: Batch) -> Step:
    step = Step(key="dry_mass", label="Dry biomass", unit="t")
    if batch.mass is None:
        return replace(step, missing=("mass",))
    if batch.mass.moisture_fraction is None:
        return replace(step, missing=("mass.moisture_fraction",))
    return replace(
        step,
        value=batch.mass.dry_mass_kg / KG_PER_TONNE,
        formula="wet_mass_kg * (1 - moisture_fraction) / 1000",
        inputs={
            "wet_mass_kg": batch.mass.wet_mass_kg,
            "moisture_fraction": batch.mass.moisture_fraction,
        },
    )


def _biochar_mass(batch: Batch, factors: FactorSet, dry_mass_t: float | None) -> Step:
    """Measured output wins over an estimate, and the trace says which was used.

    Estimating from a yield factor is fine for screening a prospective batch;
    it is not fine for a batch that has already been produced and weighed. The
    distinction is worth carrying into the dossier, because an auditor will ask.
    """
    step = Step(key="biochar_mass", label="Biochar produced", unit="t")

    if batch.pyrolysis is not None and batch.pyrolysis.biochar_mass_kg is not None:
        return replace(
            step,
            value=batch.pyrolysis.biochar_mass_kg / KG_PER_TONNE,
            formula="biochar_mass_kg / 1000",
            inputs={"biochar_mass_kg": batch.pyrolysis.biochar_mass_kg},
            note="measured at the facility",
        )

    if dry_mass_t is None:
        return replace(step, missing=("pyrolysis.biochar_mass_kg", "dry_mass"))

    key = batch.feedstock.feedstock_type
    factor = factors.get("biochar_yield_dry_basis", key)
    if factor is None:
        return replace(step, missing=(_factor_ref("biochar_yield_dry_basis", key),))

    return replace(
        step,
        value=dry_mass_t * factor.value,
        formula="dry_mass_t * biochar_yield_dry_basis",
        inputs={"dry_mass_t": dry_mass_t},
        factors=(factor,),
        note="estimated from yield — no measured output recorded",
    )


def _biochar_carbon(batch: Batch, biochar_t: float | None) -> Step:
    step = Step(key="biochar_carbon", label="Organic carbon in biochar", unit="t C")
    if biochar_t is None:
        return replace(step, missing=("biochar_mass",))
    if batch.lab is None or batch.lab.organic_carbon_fraction is None:
        return replace(step, missing=("lab.organic_carbon_fraction",))
    return replace(
        step,
        value=biochar_t * batch.lab.organic_carbon_fraction,
        formula="biochar_t * organic_carbon_fraction",
        inputs={
            "biochar_t": biochar_t,
            "organic_carbon_fraction": batch.lab.organic_carbon_fraction,
        },
    )


def _carbon_as_co2(factors: FactorSet, carbon_t: float | None) -> Step:
    step = Step(key="carbon_as_co2", label="CO2 equivalent of that carbon", unit="t CO2")
    if carbon_t is None:
        return replace(step, missing=("biochar_carbon",))
    factor = factors.get("co2_per_carbon")
    if factor is None:
        return replace(step, missing=(_factor_ref("co2_per_carbon", None),))
    return replace(
        step,
        value=carbon_t * factor.value,
        formula="carbon_t * co2_per_carbon",
        inputs={"carbon_t": carbon_t},
        factors=(factor,),
    )


def _durable_co2(batch: Batch, factors: FactorSet, gross_co2_t: float | None) -> Step:
    """The share still stored after 100 years, selected by the H/Corg ratio.

    This is the step that separates a removal from a delay, and it is the one
    that cannot be guessed: without the molar ratio from the laboratory there
    is no defensible durability claim, so the chain stops here rather than
    substituting an assumption.
    """
    step = Step(key="durable_co2", label="Durable stored CO2 (100 yr)", unit="t CO2")
    if gross_co2_t is None:
        return replace(step, missing=("carbon_as_co2",))
    if batch.lab is None or batch.lab.hydrogen_to_organic_carbon_molar_ratio is None:
        return replace(step, missing=("lab.hydrogen_to_organic_carbon_molar_ratio",))

    ratio = batch.lab.hydrogen_to_organic_carbon_molar_ratio
    band = _durability_band(ratio)
    factor = factors.get("durable_fraction", band)
    if factor is None:
        return replace(step, missing=(_factor_ref("durable_fraction", band),))

    return replace(
        step,
        value=gross_co2_t * factor.value,
        formula="gross_co2_t * durable_fraction",
        inputs={"gross_co2_t": gross_co2_t, "h_to_corg": ratio},
        factors=(factor,),
        note=f"H/Corg {ratio} falls in band '{band}'",
    )


def _durability_band(h_to_corg: float) -> str:
    """Bucket the H/Corg ratio into a durability band.

    The thresholds themselves are placeholders pending the methodology text —
    they are here so the shape of the calculation is testable, and the factor
    they select is unsourced, so anything using them reports as provisional.
    """
    if h_to_corg < 0.4:
        return "h_corg_below_0_4"
    if h_to_corg <= 0.7:
        return "h_corg_0_4_to_0_7"
    return "h_corg_above_0_7"


def _transport_emissions(batch: Batch, factors: FactorSet) -> Step:
    step = Step(key="transport_emissions", label="Transport emissions", unit="t CO2e")
    if not batch.transport:
        return replace(step, value=0.0, note="no transport legs recorded")

    total = 0.0
    used: list[Factor] = []
    inputs: dict[str, float] = {}
    for index, leg in enumerate(batch.transport):
        payload_kg = leg.payload_mass_kg or (batch.mass.wet_mass_kg if batch.mass else None)
        if payload_kg is None:
            return replace(step, missing=(f"transport[{index}].payload_mass_kg",))
        factor = factors.get("transport_emission_factor", leg.mode)
        if factor is None:
            return replace(step, missing=(_factor_ref("transport_emission_factor", leg.mode),))
        tonne_km = (payload_kg / KG_PER_TONNE) * leg.distance_km
        total += tonne_km * factor.value
        used.append(factor)
        inputs[f"leg{index}_tonne_km"] = tonne_km

    return replace(
        step,
        value=total,
        formula="sum(payload_t * distance_km * transport_emission_factor)",
        inputs=inputs,
        factors=tuple(used),
    )


def _process_emissions(batch: Batch, factors: FactorSet) -> Step:
    """Grid electricity and any fuel burned by the pyrolysis process itself."""
    step = Step(key="process_emissions", label="Process emissions", unit="t CO2e")
    if batch.pyrolysis is None:
        return replace(step, missing=("pyrolysis",))

    total = 0.0
    used: list[Factor] = []
    inputs: dict[str, float] = {}

    if batch.pyrolysis.electricity_kwh is not None:
        # Selecting a grid factor per country is a roadmap item; for now there
        # is one keyless factor and the trace shows exactly which was applied.
        factor = factors.get("grid_electricity_emission_factor")
        if factor is None:
            return replace(step, missing=(_factor_ref("grid_electricity_emission_factor", None),))
        total += batch.pyrolysis.electricity_kwh * factor.value
        used.append(factor)
        inputs["electricity_kwh"] = batch.pyrolysis.electricity_kwh

    for use in batch.pyrolysis.fuel_use:
        factor = factors.get("fuel_emission_factor", use.fuel)
        if factor is None:
            return replace(step, missing=(_factor_ref("fuel_emission_factor", use.fuel),))
        total += use.quantity * factor.value
        used.append(factor)
        inputs[f"fuel_{use.fuel}"] = use.quantity

    return replace(
        step,
        value=total,
        formula="electricity_kwh * grid_ef + sum(fuel_quantity * fuel_ef)",
        inputs=inputs,
        factors=tuple(used),
    )


def _uncertainty_deduction(factors: FactorSet, durable_co2_t: float | None) -> Step:
    """A flat conservative deduction.

    A real methodology derives this from the spread of the measurements that
    fed the calculation. A single blanket percentage is a stand-in, and it is
    marked as such; replacing it is on the roadmap.
    """
    step = Step(key="uncertainty_deduction", label="Uncertainty deduction", unit="t CO2e")
    if durable_co2_t is None:
        return replace(step, missing=("durable_co2",))
    factor = factors.get("uncertainty_deduction_fraction")
    if factor is None:
        return replace(step, missing=(_factor_ref("uncertainty_deduction_fraction", None),))
    return replace(
        step,
        value=durable_co2_t * factor.value,
        formula="durable_co2_t * uncertainty_deduction_fraction",
        inputs={"durable_co2_t": durable_co2_t},
        factors=(factor,),
    )


def _net_removal(
    durable_co2_t: float | None,
    transport_t: float | None,
    process_t: float | None,
    deduction_t: float | None,
) -> Step:
    step = Step(key="net_removal", label="Preliminary net removal", unit="t CO2e")
    parts = {
        "durable_co2": durable_co2_t,
        "transport_emissions": transport_t,
        "process_emissions": process_t,
        "uncertainty_deduction": deduction_t,
    }
    absent = tuple(name for name, value in parts.items() if value is None)
    if absent:
        return replace(step, missing=absent)
    return replace(
        step,
        value=durable_co2_t - transport_t - process_t - deduction_t,
        formula=(
            "durable_co2 - transport_emissions - process_emissions - uncertainty_deduction"
        ),
        inputs=dict(parts),
    )


def _factor_ref(name: str, key: str | None) -> str:
    return f"factor:{name}[{key}]" if key else f"factor:{name}"
