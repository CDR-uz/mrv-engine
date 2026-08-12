"""The dossier as JSON.

Written out by hand rather than reflected off the dataclasses. The JSON is a
contract — it is what a downstream system, a web frontend or an auditor's tool
would consume — and a contract that is an accident of internal attribute names
breaks every time somebody renames a field.
"""

from __future__ import annotations

from typing import Any

from mrv_engine.core.dossier import Dossier
from mrv_engine.core.evidence import GapRegister
from mrv_engine.core.factors import Factor
from mrv_engine.core.eligibility import EligibilityResult
from mrv_engine.core.timeline import Timeline
from mrv_engine.core.trace import Calculation


def dossier_to_dict(dossier: Dossier) -> dict[str, Any]:
    return {
        "batch_id": dossier.batch_id,
        "identifier_parsed": dossier.parsed_id is not None,
        "provenance": {
            "rule_pack": dossier.provenance.rule_pack,
            "rule_pack_version": dossier.provenance.rule_pack_version,
            "factor_set_version": dossier.provenance.factor_set_version,
            "unsourced_factors": dossier.provenance.unsourced_factors,
        },
        "result": {
            "net_removal_t_co2e": dossier.net_removal_t_co2e,
            "provisional": dossier.provisional,
            "blocking_gaps": dossier.blocking_gap_count,
            "evidence_completeness": round(dossier.gaps.completeness, 4),
            "eligibility_verdict": dossier.eligibility.verdict.value,
        },
        "calculation": _calculation(dossier.calculation),
        "eligibility": _eligibility(dossier.eligibility),
        "evidence": _evidence(dossier.gaps),
        "timeline": _timeline(dossier.timeline),
        "notes": list(dossier.notes),
        "disclaimer": dossier.disclaimer,
    }


def _calculation(calculation: Calculation) -> dict[str, Any]:
    return {
        "net_removal_t_co2e": calculation.net_removal_t_co2e,
        "provisional": calculation.provisional,
        "missing": list(calculation.missing),
        "steps": [
            {
                "key": step.key,
                "label": step.label,
                "unit": step.unit,
                "value": step.value,
                "formula": step.formula,
                "inputs": step.inputs,
                "factors": [_factor(f) for f in step.factors],
                "missing": list(step.missing),
                "provisional": step.provisional,
                "note": step.note,
            }
            for step in calculation.steps
        ],
    }


def _factor(factor: Factor) -> dict[str, Any]:
    return {
        "name": factor.name,
        "key": factor.key,
        "value": factor.value,
        "unit": factor.unit,
        "source": factor.source.model_dump() if factor.source else None,
        "note": factor.note,
    }


def _eligibility(result: EligibilityResult) -> dict[str, Any]:
    return {
        "verdict": result.verdict.value,
        "findings": [
            {
                "rule_id": finding.rule_id,
                "title": finding.title,
                "severity": finding.severity.value,
                "outcome": finding.outcome.value,
                "message": " ".join(finding.message.split()),
            }
            for finding in result.findings
        ],
    }


def _evidence(register: GapRegister) -> dict[str, Any]:
    return {
        "completeness": round(register.completeness, 4),
        "blocking_gap_count": len(register.blocking_gaps),
        "items": [
            {
                "kind": item.kind,
                "label": item.label,
                "status": item.status.value,
                "blocking": item.blocking,
                "weight": item.weight,
                "document_reference": item.document_reference,
                "note": item.note,
            }
            for item in register.items
        ],
    }


def _timeline(timeline: Timeline) -> dict[str, Any]:
    return {
        "events": [
            {
                "stage": event.stage.value,
                "date": event.date.isoformat() if event.date else None,
                "label": event.label,
                "detail": event.detail,
            }
            for event in timeline.events
        ],
        "inconsistencies": list(timeline.inconsistencies),
    }
