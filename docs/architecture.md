# Architecture

## One rule

`core` takes a `Batch` and returns a value. It never takes a path, never opens
a file, never prints and never makes a request. Everything that touches the
outside world lives in `adapters`.

This is not tidiness for its own sake. The engine has to produce identical
numbers whether it is driven from a terminal, an HTTP request or a batch job
over a thousand records, and the only way to guarantee that is to have one
implementation that none of them can reach around. It also means the tests
target arithmetic rather than an interface: adding the HTTP adapter will not
require rewriting a single calculation test.

## Flow

```
batch.yaml ──> adapters.io ──> Batch ─┬─> core.calculator ──> Calculation
                                      ├─> core.eligibility ─> EligibilityResult
                                      ├─> core.evidence ────> GapRegister
                                      └─> core.timeline ────> Timeline
                                                 │
rules/pack.yaml ─────> RulePack ─────────────────┤
factors/set.yaml ────> FactorSet ────────────────┤
                                                 ▼
                                          core.dossier.build
                                                 │
                              ┌──────────────────┴──────────────────┐
                              ▼                                     ▼
                      adapters.cli (text)              adapters.serialize (JSON)
```

Both outputs are renderings of the same `Dossier`. A test asserts they agree:
a figure printed on screen that the JSON does not contain is a failing test.

## The four assessments

**`calculator`** walks nine steps from wet mass to net removal. Each emits a
`Step` carrying its formula, inputs, applied factors and value — or no value
and the names of what was missing. Downstream steps of a blocked step block in
turn, so a gap propagates to the headline figure instead of being absorbed.

**`eligibility`** applies a rule pack. Conditions evaluate to true, false or
unknown; a rule that fires and a rule that could not be decided both produce a
finding, distinguished by outcome. Verdicts rank conservatively, and unknowns
outrank review items.

**`evidence`** walks the pack's checklist against the batch. An item the batch
never mentions counts as missing. Completeness is weighted and always reported
next to the blocking-gap count.

**`timeline`** derives the chain of custody from dates already on the batch —
there is no event store — and flags orderings the physical world does not
allow.

## The dossier

`dossier.build` is the only function that needs all four. It stamps the result
with the rule pack name and version, the factor set version, and how many
applied factors lack a source. Without that stamp the number is not
reproducible, and an irreproducible number is not evidence.

`Dossier.notes` is the plain-language summary of everything a reader should be
told before quoting a figure from it: an unparseable batch identifier, a
provisional result, an uncomputable removal and why, timeline inconsistencies.

## Data, not code

Rule packs and factor sets are versioned YAML loaded at runtime. Methodologies
change; a rule set embedded in Python cannot be diffed, versioned independently
or swapped for a different standard without a release. See
[`decisions/0001-rules-as-data.md`](decisions/0001-rules-as-data.md).

## The JSON contract

`adapters/serialize.py` writes the dossier dictionary out by hand rather than
reflecting over the dataclasses. The JSON is what a frontend or a downstream
tool consumes, so it is a contract; a contract that is an accident of internal
attribute names breaks on every rename.

## What there is not

No database, no authentication, no persistence, no scheduler, no queue. A batch
is a file, a dossier is computed fresh, and adding any of the above before the
coefficients are sourced would be building the second floor first.
