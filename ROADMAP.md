# Roadmap

What v0.1 deliberately does not do, roughly in the order it matters.

## Blocking a serious release

- [ ] **Replace the placeholder factors.** Every coefficient in
      `factors/default.yaml` except the 44/12 stoichiometric ratio is a
      plausible working number with `source: null`. Until they carry a document
      reference, version and date, every figure the engine produces is
      provisional and says so.
- [ ] **Verify the durability bands.** The H/Corg thresholds in
      `calculator._durability_band` were chosen to give the calculation a
      testable shape, not because a methodology says so.
- [ ] **Uncertainty deduction derived rather than flat.** A single blanket
      percentage stands in for propagation over the measurements that actually
      fed the calculation.

## Rule packs

- [ ] A pack aligned to a named methodology, carrying the document reference
      and version in its header. Not attempted while VM0044 is under revision.
- [ ] Aggregate conditions. The condition language addresses single fields by
      dotted path; rules like "total transport distance over 200 km" or "any
      leg missing a date" cannot currently be expressed.
- [ ] Feedstock taxonomy as data. `feedstock_type` is a free string today;
      the vocabulary belongs in the pack.

## Engine

- [ ] Per-country grid electricity factors. One keyless global factor applies
      today and the trace says so.
- [ ] Baseline emissions. The engine computes project emissions but treats the
      baseline as a qualitative eligibility question, not a quantity.
- [ ] Multiple batches. Everything is scoped to one batch; a project is many.
- [ ] Corporate scope mapping. Given a reporting entity, show which parts of
      the chain land in its Scope 1, 2 and 3. Buyer-facing and strictly
      separate from the removal quantification, which does not use scopes.

## Interfaces

- [ ] HTTP adapter over the same core functions.
- [ ] Document extraction: pull batch fields off a delivery note or laboratory
      report instead of typing them.
- [ ] Persistence. There is no store — a batch is a file and a dossier is
      computed fresh every time.

## Explicitly out of scope

Certification, verification, registry integration, credit issuance, trading,
and anything that would imply this engine can substitute for a validation body.
