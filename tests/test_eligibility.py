from pathlib import Path

import pytest

from mrv_engine.adapters.io import load_batch, load_rules
from mrv_engine.core.eligibility import Outcome, Verdict, screen
from mrv_engine.core.models import Batch
from mrv_engine.core.rules import Condition, Severity, evaluate

EXAMPLES = Path(__file__).parent.parent / "examples"


@pytest.fixture
def pack():
    return load_rules()


def batch_from(**feedstock) -> Batch:
    return Batch.model_validate(
        {"batch_id": "CAC-UZ-SAM-COT-2026-09999", "feedstock": {"feedstock_type": "cotton_stalk", **feedstock}}
    )


# --- the three-valued condition language ------------------------------------


def test_condition_on_absent_field_is_undetermined_not_false():
    """The distinction the whole screener rests on."""
    condition = Condition.model_validate({"field": "feedstock.purpose_grown", "is": True})
    assert evaluate(condition, batch_from()) is None


def test_condition_on_present_field_is_decided():
    condition = Condition.model_validate({"field": "feedstock.purpose_grown", "is": True})
    assert evaluate(condition, batch_from(purpose_grown=True)) is True
    assert evaluate(condition, batch_from(purpose_grown=False)) is False


def test_is_missing_reads_absence_directly_and_is_never_undetermined():
    condition = Condition.model_validate({"field": "feedstock.is_residue", "is_missing": True})
    assert evaluate(condition, batch_from()) is True
    assert evaluate(condition, batch_from(is_residue=True)) is False


def test_unknown_poisons_a_conjunction_but_a_false_settles_it():
    unknown = {"field": "feedstock.purpose_grown", "is": True}
    false = {"field": "feedstock.feedstock_type", "is": "rice_husk"}

    assert evaluate(Condition.model_validate({"all_of": [unknown]}), batch_from()) is None
    assert evaluate(Condition.model_validate({"all_of": [unknown, false]}), batch_from()) is False


def test_a_true_settles_a_disjunction_even_with_unknowns():
    unknown = {"field": "feedstock.purpose_grown", "is": True}
    true = {"field": "feedstock.feedstock_type", "is": "cotton_stalk"}

    assert evaluate(Condition.model_validate({"any_of": [unknown, true]}), batch_from()) is True
    assert evaluate(Condition.model_validate({"any_of": [unknown]}), batch_from()) is None


def test_negation_leaves_unknown_alone():
    unknown = {"field": "feedstock.purpose_grown", "is": True}
    assert evaluate(Condition.model_validate({"not": unknown}), batch_from()) is None


def test_condition_naming_a_field_the_model_does_not_have_fails_loudly():
    condition = Condition.model_validate({"field": "feedstock.colour", "is": "brown"})
    with pytest.raises(KeyError):
        evaluate(condition, batch_from())


# --- verdicts ----------------------------------------------------------------


def test_purpose_grown_biomass_is_blocked(pack):
    result = screen(batch_from(purpose_grown=True, is_residue=True, baseline_fate="burned_in_field"), pack)

    assert result.verdict is Verdict.NOT_ELIGIBLE
    assert [f.rule_id for f in result.blocking] == ["purpose_grown_biomass"]


def test_unanswered_questions_outrank_review_items(pack):
    """A question nobody has answered is a worse position than one that was."""
    result = screen(batch_from(is_residue=True, baseline_fate="animal_feed"), pack)

    assert result.verdict is Verdict.INSUFFICIENT_DATA
    fired = {f.rule_id for f in result.findings if f.outcome is Outcome.FIRED}
    assert "baseline_is_productive_use" in fired
    assert result.undetermined


def test_complete_batch_needs_review_for_its_declared_competing_use(pack):
    result = screen(load_batch(EXAMPLES / "cotton-stalk-samarkand-complete.yaml"), pack)

    assert result.verdict is Verdict.NEEDS_REVIEW
    assert {f.rule_id for f in result.findings} == {"competing_uses_declared"}


def test_incomplete_batch_is_short_of_data(pack):
    result = screen(load_batch(EXAMPLES / "cotton-stalk-samarkand.yaml"), pack)

    assert result.verdict is Verdict.INSUFFICIENT_DATA
    assert "end_use_not_recorded" not in {f.rule_id for f in result.findings}
    assert "h_corg_above_durability_threshold" in {f.rule_id for f in result.undetermined}


def test_clean_batch_passes_with_no_findings(pack):
    batch = Batch.model_validate(
        {
            "batch_id": "CAC-UZ-SAM-COT-2026-09998",
            "feedstock": {
                "feedstock_type": "cotton_stalk",
                "is_residue": True,
                "purpose_grown": False,
                "baseline_fate": "burned_in_field",
            },
            "mass": {"wet_mass_kg": 10000, "moisture_fraction": 0.18},
            "lab": {"organic_carbon_fraction": 0.72, "hydrogen_to_organic_carbon_molar_ratio": 0.35},
            "end_use": {"application_type": "agricultural_soil"},
        }
    )
    result = screen(batch, pack)

    assert result.verdict is Verdict.POTENTIALLY_ELIGIBLE
    assert result.findings == ()


def test_burning_the_biochar_blocks_regardless_of_everything_else(pack):
    batch = Batch.model_validate(
        {
            "batch_id": "CAC-UZ-SAM-COT-2026-09997",
            "feedstock": {
                "feedstock_type": "cotton_stalk",
                "is_residue": True,
                "purpose_grown": False,
                "baseline_fate": "burned_in_field",
            },
            "mass": {"wet_mass_kg": 10000, "moisture_fraction": 0.18},
            "lab": {"organic_carbon_fraction": 0.72, "hydrogen_to_organic_carbon_molar_ratio": 0.35},
            "end_use": {"application_type": "combustion"},
        }
    )
    result = screen(batch, pack)

    assert result.verdict is Verdict.NOT_ELIGIBLE
    assert [f.rule_id for f in result.blocking] == ["non_durable_end_use"]


def test_every_rule_in_the_shipped_pack_is_wired_to_a_real_field(pack):
    """Guards against a typo in the rule pack silently disabling a rule."""
    batch = load_batch(EXAMPLES / "cotton-stalk-samarkand-complete.yaml")
    for rule in pack.eligibility_rules:
        evaluate(rule.when, batch)


def test_shipped_pack_declares_severities_we_understand(pack):
    assert {r.severity for r in pack.eligibility_rules} <= {Severity.BLOCKING, Severity.REVIEW}
