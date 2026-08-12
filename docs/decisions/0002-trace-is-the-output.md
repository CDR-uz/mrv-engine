# 0002 — The trace is the output, not a log

**Date:** 2026-08-12 · **Status:** accepted

## Context

The natural signature for the calculator is `calculate(batch) -> float`, with
logging bolted on for debugging.

But a bare number is worth nothing to the party this engine exists to serve. An
auditor asked to accept "4.004 t CO₂e" will ask which formula, on which inputs,
with which coefficient, from which document — and if that has to be
reconstructed from log lines after the fact, it will be reconstructed wrongly.

## Decision

`calculate` returns a `Calculation`: an ordered sequence of `Step`, each
carrying its formula, inputs, applied factors and value. The headline figure is
one of those steps, reachable through a convenience property, not a privileged
return value.

A step that cannot be computed is still emitted, carrying the names of what was
missing instead of a value.

## Consequences

The gap register and the calculation stay in agreement by construction: both
are reading the same structure rather than two implementations of the same
knowledge about what is required.

Blocked steps propagate. A missing laboratory ratio does not become a zero
somewhere in the middle and quietly halve the result — it blocks durability,
which blocks the deduction, which blocks the net figure, and the dossier says
so in plain language.

Serialisation gets the derivation for free, so the JSON a frontend consumes
contains everything the terminal shows. A test asserts exactly that.

The cost is verbosity: nine steps of construction where nine lines of
arithmetic would have done, and a `Step` that has to be built even on the
failure path. That is the right trade for the one output that has to survive
contact with a validation body.
