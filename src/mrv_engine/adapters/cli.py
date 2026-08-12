"""Command line interface.

argparse rather than a CLI framework: two dependencies is a feature of this
repository, and the interface is three commands over one document.

Everything printed here is a rendering of the dossier. The CLI computes
nothing — if a number appears on screen that the JSON does not contain, that is
a bug in this file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mrv_engine import __version__
from mrv_engine.adapters.io import load_batch, load_factors, load_rules
from mrv_engine.adapters.serialize import dossier_to_dict
from mrv_engine.core.dossier import Dossier, build
from mrv_engine.core.eligibility import Outcome
from mrv_engine.core.models import EvidenceStatus

_STATUS_MARK = {
    EvidenceStatus.PRESENT: "ok",
    EvidenceStatus.PARTIAL: "~",
    EvidenceStatus.MISSING: "--",
}

_SECTIONS = {
    "calc": ("calculation",),
    "assess": ("eligibility", "evidence"),
    "dossier": ("calculation", "eligibility", "evidence", "timeline"),
}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    dossier = build(
        load_batch(args.batch),
        load_factors(args.factors),
        load_rules(args.rules),
    )

    if args.json:
        json.dump(dossier_to_dict(dossier), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    for line in _render(dossier, _SECTIONS[args.command]):
        print(line)

    # A dossier with a blocking gap is not a failure of the run, so the exit
    # code stays 0. Scripts that want to gate on readiness should read the JSON.
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mrv-engine",
        description="Preliminary carbon removal assessment for a biochar batch.",
    )
    parser.add_argument("--version", action="version", version=f"mrv-engine {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("calc", "show the calculation trace"),
        ("assess", "show eligibility and the evidence gap register"),
        ("dossier", "show everything"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("batch", type=Path, help="path to a batch YAML file")
        sub.add_argument("--rules", type=Path, default=None, help="rule pack to apply")
        sub.add_argument("--factors", type=Path, default=None, help="factor set to apply")
        sub.add_argument("--json", action="store_true", help="emit the dossier as JSON")

    return parser


def _render(dossier: Dossier, sections: tuple[str, ...]) -> list[str]:
    builders = {
        "calculation": _calculation,
        "eligibility": _eligibility,
        "evidence": _evidence,
        "timeline": _timeline,
    }
    lines = _header(dossier)
    for name in sections:
        lines.append("")
        lines.extend(builders[name](dossier))
    lines.append("")
    lines.extend(_notes(dossier))
    return lines


def _header(dossier: Dossier) -> list[str]:
    provenance = dossier.provenance
    return [
        f"Batch {dossier.batch_id}",
        f"rules {provenance.rule_pack} {provenance.rule_pack_version}"
        f" · factors {provenance.factor_set_version}",
    ]


def _calculation(dossier: Dossier) -> list[str]:
    lines = ["CALCULATION"]
    for step in dossier.calculation.steps:
        if step.computed:
            value = f"{step.value:>12,.3f} {step.unit}"
            mark = "?" if step.provisional else " "
        else:
            value = f"{'--':>12} {step.unit}"
            mark = "!"
        lines.append(f"  {mark} {step.label:<34}{value}")
        if step.formula:
            lines.append(f"        {step.formula}")
        if step.note:
            lines.append(f"        {step.note}")
        if step.missing:
            lines.append(f"        missing: {', '.join(step.missing)}")

    lines.append("")
    lines.append("  ?  provisional — rests on a factor with no documented source")
    lines.append("  !  not computed")
    return lines


def _eligibility(dossier: Dossier) -> list[str]:
    lines = [f"ELIGIBILITY  {dossier.eligibility.verdict.value}"]
    if not dossier.eligibility.findings:
        lines.append("  no findings")
    for finding in dossier.eligibility.findings:
        tag = finding.severity.value if finding.outcome is Outcome.FIRED else "undetermined"
        lines.append(f"  [{tag}] {finding.title}")
        lines.append(f"        {' '.join(finding.message.split())}")
    return lines


def _evidence(dossier: Dossier) -> list[str]:
    register = dossier.gaps
    lines = [
        f"EVIDENCE  {register.completeness:.0%} complete"
        f" · {len(register.blocking_gaps)} blocking gap(s)"
    ]
    for item in register.items:
        flag = "blocking" if item.blocking and not item.satisfied else ""
        lines.append(f"  {_STATUS_MARK[item.status]:>2}  {item.label:<52}{flag}")
        if item.note:
            lines.append(f"        {item.note}")
    return lines


def _timeline(dossier: Dossier) -> list[str]:
    lines = ["TIMELINE"]
    for event in dossier.timeline.events:
        when = event.date.isoformat() if event.date else "----------"
        detail = f"  ({event.detail})" if event.detail else ""
        lines.append(f"  {when}  {event.label}{detail}")
    lines.extend(f"  ! {problem}" for problem in dossier.timeline.inconsistencies)
    return lines


def _notes(dossier: Dossier) -> list[str]:
    lines = []
    if dossier.notes:
        lines.append("NOTES")
        lines.extend(f"  - {note}" for note in dossier.notes)
        lines.append("")
    lines.append(" ".join(dossier.disclaimer.split()))
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
