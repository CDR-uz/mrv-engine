import json
from pathlib import Path

import pytest

from mrv_engine.adapters.cli import main
from mrv_engine.adapters.io import load_batch, load_factors, load_rules
from mrv_engine.adapters.serialize import dossier_to_dict
from mrv_engine.core.dossier import build
from mrv_engine.core.eligibility import Verdict
from mrv_engine.core.identity import BatchId
from mrv_engine.core.models import Batch
from mrv_engine.core.timeline import Stage
from mrv_engine.core.timeline import build as build_timeline

EXAMPLES = Path(__file__).parent.parent / "examples"
COMPLETE = EXAMPLES / "cotton-stalk-samarkand-complete.yaml"
INCOMPLETE = EXAMPLES / "cotton-stalk-samarkand.yaml"


@pytest.fixture
def dossier():
    return build(load_batch(COMPLETE), load_factors(), load_rules())


# --- identifier --------------------------------------------------------------


def test_batch_id_round_trips():
    parsed = BatchId.parse("CAC-UZ-SAM-COT-2026-00001")
    assert (parsed.country, parsed.region, parsed.sequence) == ("UZ", "SAM", 1)
    assert str(parsed) == "CAC-UZ-SAM-COT-2026-00001"


def test_unparseable_identifier_is_noted_but_does_not_stop_the_run():
    """An operator with their own numbering is not a reason to refuse the data."""
    batch = Batch.model_validate(
        {"batch_id": "batch 7 (north yard)", "feedstock": {"feedstock_type": "cotton_stalk"}}
    )
    result = build(batch, load_factors(), load_rules())

    assert result.parsed_id is None
    assert any("does not follow" in note for note in result.notes)


# --- timeline ----------------------------------------------------------------


def test_timeline_orders_the_stages_from_the_dates_already_on_the_batch():
    timeline = build_timeline(load_batch(COMPLETE))

    assert [e.stage for e in timeline.recorded] == [
        Stage.COLLECTION,
        Stage.TRANSPORT,
        Stage.PYROLYSIS,
        Stage.LABORATORY,
        Stage.APPLICATION,
    ]
    assert timeline.inconsistencies == ()


def test_timeline_catches_a_run_dated_before_its_harvest():
    batch = Batch.model_validate(
        {
            "batch_id": "CAC-UZ-SAM-COT-2026-07777",
            "feedstock": {"feedstock_type": "cotton_stalk", "collection_date": "2026-03-20"},
            "pyrolysis": {"run_date": "2026-03-19"},
        }
    )
    timeline = build_timeline(batch)

    assert len(timeline.inconsistencies) == 1
    assert "pyrolysis" in timeline.inconsistencies[0]


def test_sampling_after_application_is_not_an_inconsistency():
    """Biochar is sometimes sampled after it has already gone to the field."""
    batch = Batch.model_validate(
        {
            "batch_id": "CAC-UZ-SAM-COT-2026-07776",
            "feedstock": {"feedstock_type": "cotton_stalk"},
            "lab": {"sample_date": "2026-04-10"},
            "end_use": {"application_date": "2026-04-02"},
        }
    )
    assert build_timeline(batch).inconsistencies == ()


def test_undated_stages_are_reported():
    batch = Batch.model_validate(
        {"batch_id": "CAC-UZ-SAM-COT-2026-07775", "feedstock": {"feedstock_type": "cotton_stalk"}}
    )
    assert len(build_timeline(batch).undated) == 5


# --- assembly ----------------------------------------------------------------


def test_dossier_stamps_what_produced_it(dossier):
    """A number without the versions behind it cannot be reproduced."""
    assert dossier.provenance.rule_pack == "generic_biochar"
    assert dossier.provenance.rule_pack_version == "0.1.0"
    assert dossier.provenance.factor_set_version == "0.1.0-placeholder"


def test_dossier_gathers_all_four_assessments(dossier):
    assert dossier.net_removal_t_co2e == pytest.approx(4.00429, abs=1e-5)
    assert dossier.eligibility.verdict is Verdict.NEEDS_REVIEW
    assert dossier.blocking_gap_count == 2
    assert len(dossier.timeline.recorded) == 5


def test_provisional_result_says_so_in_the_notes(dossier):
    assert dossier.provisional
    assert any("provisional" in note for note in dossier.notes)


def test_incomplete_batch_reports_why_there_is_no_number():
    result = build(load_batch(INCOMPLETE), load_factors(), load_rules())

    assert result.net_removal_t_co2e is None
    assert any("no net removal could be computed" in note for note in result.notes)


# --- serialisation and CLI ---------------------------------------------------


def test_dossier_json_is_serialisable_and_carries_the_headline(dossier):
    payload = json.loads(json.dumps(dossier_to_dict(dossier)))

    assert payload["result"]["net_removal_t_co2e"] == pytest.approx(4.00429, abs=1e-5)
    assert payload["result"]["blocking_gaps"] == 2
    assert payload["provenance"]["factor_set_version"] == "0.1.0-placeholder"
    assert payload["disclaimer"].startswith("Preliminary")


def test_every_calculation_step_survives_into_the_json(dossier):
    payload = dossier_to_dict(dossier)
    assert len(payload["calculation"]["steps"]) == len(dossier.calculation.steps)
    assert payload["calculation"]["steps"][0]["formula"]


def test_factor_sources_survive_into_the_json(dossier):
    payload = dossier_to_dict(dossier)
    step = next(s for s in payload["calculation"]["steps"] if s["key"] == "carbon_as_co2")

    assert step["factors"][0]["source"]["kind"] == "physical_constant"
    assert step["provisional"] is False


def test_cli_prints_the_headline_figure(capsys):
    assert main(["calc", str(COMPLETE)]) == 0
    assert "4.004 t CO2e" in capsys.readouterr().out


def test_cli_json_matches_the_library(capsys):
    """Nothing on screen may exist that the JSON does not contain."""
    assert main(["dossier", str(COMPLETE), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload == dossier_to_dict(build(load_batch(COMPLETE), load_factors(), load_rules()))


def test_cli_marks_the_blocked_batch_instead_of_printing_a_number(capsys):
    assert main(["dossier", str(INCOMPLETE)]) == 0
    out = capsys.readouterr().out

    assert "Preliminary net removal" in out
    assert "no net removal could be computed" in out
