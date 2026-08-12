"""Golden tests for the calculation chain.

The expected values are written out longhand rather than loaded from a fixture
file so that a reader can check the arithmetic against the trace by eye. If one
of these numbers changes, either a factor changed or the chain did, and both
are things a reviewer should be made to look at.
"""

from pathlib import Path

import pytest

from mrv_engine.adapters.io import load_batch, load_factors
from mrv_engine.core.calculator import calculate
from mrv_engine.core.models import Batch

EXAMPLES = Path(__file__).parent.parent / "examples"
COMPLETE = EXAMPLES / "cotton-stalk-samarkand-complete.yaml"
INCOMPLETE = EXAMPLES / "cotton-stalk-samarkand.yaml"


@pytest.fixture
def factors():
    return load_factors()


def test_complete_batch_runs_the_whole_chain(factors):
    calc = calculate(load_batch(COMPLETE), factors)

    assert calc.value("dry_mass") == pytest.approx(8.2)
    assert calc.value("biochar_mass") == pytest.approx(2.296)
    assert calc.value("biochar_carbon") == pytest.approx(1.65312)
    assert calc.value("carbon_as_co2") == pytest.approx(6.05703, abs=1e-5)
    assert calc.value("durable_co2") == pytest.approx(4.48220, abs=1e-5)
    assert calc.value("transport_emissions") == pytest.approx(0.105)
    assert calc.value("process_emissions") == pytest.approx(0.1488)
    assert calc.value("uncertainty_deduction") == pytest.approx(0.22411, abs=1e-5)
    assert calc.net_removal_t_co2e == pytest.approx(4.00429, abs=1e-5)
    assert calc.missing == ()


def test_result_is_provisional_while_factors_are_placeholders(factors):
    calc = calculate(load_batch(COMPLETE), factors)
    assert calc.provisional


def test_stoichiometric_step_is_not_provisional(factors):
    """co2_per_carbon is a physical constant and carries a real source."""
    calc = calculate(load_batch(COMPLETE), factors)
    assert not calc.step("carbon_as_co2").provisional


def test_incomplete_batch_stops_at_durability(factors):
    """The demonstration batch has no H/Corg, so it has no defensible removal."""
    calc = calculate(load_batch(INCOMPLETE), factors)

    assert calc.value("carbon_as_co2") == pytest.approx(6.05703, abs=1e-5)
    assert calc.step("durable_co2").computed is False
    assert "lab.hydrogen_to_organic_carbon_molar_ratio" in calc.missing
    assert calc.net_removal_t_co2e is None


def test_blocked_step_propagates_instead_of_becoming_zero(factors):
    calc = calculate(load_batch(INCOMPLETE), factors)
    net = calc.step("net_removal")
    assert net.value is None
    assert "durable_co2" in net.missing
    assert "uncertainty_deduction" in net.missing


def test_measured_biochar_mass_beats_the_yield_estimate(factors):
    calc = calculate(load_batch(COMPLETE), factors)
    step = calc.step("biochar_mass")
    assert step.note == "measured at the facility"
    assert step.factors == ()


def test_yield_estimate_is_used_and_labelled_when_nothing_was_weighed(factors):
    batch = Batch.model_validate(
        {
            "batch_id": "CAC-UZ-SAM-COT-2026-00009",
            "feedstock": {"feedstock_type": "cotton_stalk"},
            "mass": {"wet_mass_kg": 10000, "moisture_fraction": 0.18},
        }
    )
    step = calculate(batch, factors).step("biochar_mass")

    assert step.value == pytest.approx(8.2 * 0.28)
    assert "estimated from yield" in step.note
    assert step.provisional


def test_unlisted_transport_mode_falls_back_to_the_generic_factor(factors):
    batch = Batch.model_validate(
        {
            "batch_id": "CAC-UZ-SAM-COT-2026-00010",
            "feedstock": {"feedstock_type": "cotton_stalk"},
            "mass": {"wet_mass_kg": 10000, "moisture_fraction": 0.18},
            "transport": [{"distance_km": 100, "mode": "tractor_trailer_unlisted"}],
        }
    )
    step = calculate(batch, factors).step("transport_emissions")

    assert step.value == pytest.approx(10 * 100 * 0.00012)
    assert step.factors[0].key is None


def test_no_transport_is_zero_not_missing(factors):
    batch = Batch.model_validate(
        {
            "batch_id": "CAC-UZ-SAM-COT-2026-00011",
            "feedstock": {"feedstock_type": "cotton_stalk"},
        }
    )
    step = calculate(batch, factors).step("transport_emissions")

    assert step.value == 0.0
    assert step.missing == ()


def test_empty_batch_blocks_everywhere_without_raising(factors):
    batch = Batch.model_validate(
        {"batch_id": "CAC-UZ-SAM-COT-2026-00012", "feedstock": {"feedstock_type": "rice_husk"}}
    )
    calc = calculate(batch, factors)

    assert calc.net_removal_t_co2e is None
    assert "mass" in calc.missing
    assert len(calc.steps) == 9
