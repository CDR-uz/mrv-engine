from pathlib import Path

import pytest
from pydantic import ValidationError

from cacarbon_mrv.adapters.io import load_batch
from cacarbon_mrv.core.models import BaselineFate, Batch, EvidenceStatus, MassRecord

EXAMPLE = Path(__file__).parent.parent / "examples" / "cotton-stalk-samarkand.yaml"


def test_example_batch_loads():
    batch = load_batch(EXAMPLE)
    assert batch.batch_id == "CAC-UZ-SAM-COT-2026-00001"
    assert batch.feedstock.baseline_fate is BaselineFate.BURNED_IN_FIELD
    assert batch.mass.wet_mass_kg == 10000


def test_dry_mass_is_derived_from_moisture():
    assert MassRecord(wet_mass_kg=10000, moisture_fraction=0.18).dry_mass_kg == 8200


def test_dry_mass_is_unknown_without_moisture():
    assert MassRecord(wet_mass_kg=10000).dry_mass_kg is None


def test_batch_is_valid_with_feedstock_alone():
    """An incomplete batch has to load — reporting the gaps is the product."""
    batch = Batch.model_validate(
        {"batch_id": "CAC-UZ-SAM-COT-2026-00002", "feedstock": {"feedstock_type": "rice_husk"}}
    )
    assert batch.mass is None
    assert batch.lab is None
    assert batch.evidence == []


def test_unknown_field_is_rejected():
    """Typos in a batch file must fail loudly rather than be silently ignored."""
    with pytest.raises(ValidationError):
        Batch.model_validate(
            {
                "batch_id": "CAC-UZ-SAM-COT-2026-00003",
                "feedstock": {"feedstock_type": "cotton_stalk"},
                "mositure": 0.18,
            }
        )


def test_example_records_missing_laboratory_report():
    batch = load_batch(EXAMPLE)
    lab = next(e for e in batch.evidence if e.kind == "laboratory_report")
    assert lab.status is EvidenceStatus.MISSING
