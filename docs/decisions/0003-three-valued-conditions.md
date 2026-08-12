# 0003 — Conditions evaluate to true, false or unknown

**Date:** 2026-08-12 · **Status:** accepted

## Context

The eligibility screener asks questions of a batch: was the biomass
purpose-grown, is it declared a residue, where did the biochar end up. Batches
arrive incomplete — that is the normal case, not the exception, and the engine
is built to accept them.

In two-valued logic, a rule asking `feedstock.purpose_grown is true` against a
batch that does not record the field returns false. The rule does not fire. The
screener reports no finding. The batch passes.

That is a lie with a specific shape: it converts an absence of evidence into
evidence of absence, and it does so silently, in favour of the project.

## Decision

Conditions return `True`, `False` or `None`, where `None` means the batch does
not carry the field the condition asks about. A rule whose condition is
undetermined produces a finding with outcome `undetermined` rather than being
skipped.

`is_missing` is the single operator that reads absence directly and is
therefore never undetermined — it is how a pack asks "was this recorded at
all", as distinct from "what does it say".

Composition follows three-valued logic: a false settles a conjunction, a true
settles a disjunction, and unknown propagates otherwise.

## Consequences

The verdict ladder gains a rung. `insufficient_data` sits between
`not_eligible` and `needs_review`, and it deliberately outranks the latter: a
question nobody has answered is a worse position to take to an auditor than one
that has been looked at and flagged.

Rule authors have to think about which of the two they mean, which is the point.
"The baseline is not a productive use" and "nobody recorded the baseline" are
different rules and both belong in a pack.

The cost is that a sparse batch produces a wall of undetermined findings. That
is accurate, and the alternative is a clean report that means nothing.
