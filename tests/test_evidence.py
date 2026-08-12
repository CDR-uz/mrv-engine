from pathlib import Path

import pytest

from mrv_engine.adapters.io import load_batch, load_rules
from mrv_engine.core.evidence import assess
from mrv_engine.core.models import Batch, EvidenceStatus

EXAMPLES = Path(__file__).parent.parent / "examples"


@pytest.fixture
def pack():
    return load_rules()


def test_incomplete_batch_names_its_blocking_gaps(pack):
    register = assess(load_batch(EXAMPLES / "cotton-stalk-samarkand.yaml"), pack)

    assert {i.kind for i in register.blocking_gaps} == {
        "carbon_rights_assignment",
        "baseline_documentation",
        "pyrolysis_log",
        "laboratory_report",
        "end_use_coordinates",
    }


def test_completed_batch_still_blocks_on_unsigned_carbon_rights(pack):
    """Documents can be 80% there and the project still unfinanceable."""
    register = assess(load_batch(EXAMPLES / "cotton-stalk-samarkand-complete.yaml"), pack)

    assert [i.kind for i in register.blocking_gaps] == [
        "carbon_rights_assignment",
        "baseline_documentation",
    ]
    assert register.completeness > 0.8


def test_evidence_the_batch_never_mentions_counts_as_missing(pack):
    """Silence is not an excuse — an unrecorded item is a gap, not an absence."""
    batch = Batch.model_validate(
        {"batch_id": "CAC-UZ-SAM-COT-2026-08888", "feedstock": {"feedstock_type": "cotton_stalk"}}
    )
    register = assess(batch, pack)

    assert len(register.items) == len(pack.evidence_checklist)
    assert all(i.status is EvidenceStatus.MISSING for i in register.items)
    assert register.completeness == 0.0


def test_partial_evidence_earns_half_weight(pack):
    batch = Batch.model_validate(
        {
            "batch_id": "CAC-UZ-SAM-COT-2026-08887",
            "feedstock": {"feedstock_type": "cotton_stalk"},
            "evidence": [
                {"kind": "mass_record", "status": "present"},
                {"kind": "moisture_measurement", "status": "partial"},
            ],
        }
    )
    register = assess(batch, pack)
    total_weight = sum(i.weight for i in pack.evidence_checklist)

    assert register.completeness == pytest.approx((1 * 1.0 + 1 * 0.5) / total_weight)


def test_completeness_is_weighted_not_a_head_count(pack):
    """Carbon rights is worth three mass records; the score has to reflect that."""
    heavy = Batch.model_validate(
        {
            "batch_id": "CAC-UZ-SAM-COT-2026-08886",
            "feedstock": {"feedstock_type": "cotton_stalk"},
            "evidence": [{"kind": "carbon_rights_assignment", "status": "present"}],
        }
    )
    light = Batch.model_validate(
        {
            "batch_id": "CAC-UZ-SAM-COT-2026-08885",
            "feedstock": {"feedstock_type": "cotton_stalk"},
            "evidence": [{"kind": "mass_record", "status": "present"}],
        }
    )

    assert assess(heavy, pack).completeness > assess(light, pack).completeness


def test_unrecognised_evidence_kind_does_not_inflate_the_score(pack):
    """A document nobody asked for is not progress against the checklist."""
    batch = Batch.model_validate(
        {
            "batch_id": "CAC-UZ-SAM-COT-2026-08884",
            "feedstock": {"feedstock_type": "cotton_stalk"},
            "evidence": [{"kind": "office_lease_agreement", "status": "present"}],
        }
    )
    assert assess(batch, pack).completeness == 0.0
