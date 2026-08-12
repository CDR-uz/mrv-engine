# 0001 — Rules and factors are versioned data, not code

**Date:** 2026-08-12 · **Status:** accepted

## Context

The engine has to encode two kinds of knowledge that change on somebody else's
schedule: the eligibility questions a methodology asks, and the coefficients it
applies. Both are revised by standards bodies without reference to our release
cycle. VM0044 is under revision as this is written.

The obvious implementation is Python — an `if` per rule, a module of constants.

## Decision

Rule packs and factor sets are YAML files, each carrying its own version,
loaded at runtime and selectable per run.

## Consequences

A methodology revision is a diff against a data file, reviewable by somebody
who does not read Python. Two packs can be applied to the same batch and the
results compared. A dossier can be stamped with the exact pack and factor
versions that produced it, which is what makes the figure reproducible.

The cost is a condition language, which we now own and have to keep small. It
is deliberately underpowered — dotted field paths, a handful of operators,
`all_of`/`any_of`/`not` — and aggregate conditions are on the roadmap rather
than in it. The moment it grows an escape hatch into Python, the benefit is
gone.

The second cost is that a typo in a pack disables a rule silently. That is
covered by a test which evaluates every rule in the shipped pack against a
batch, so an unresolvable field path fails the suite rather than passing
quietly in production.
