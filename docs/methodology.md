# What the calculation does

> This document describes what the engine computes and on what basis. It is not
> a methodology, does not claim conformity with one, and must not be cited as
> the basis of any carbon claim.

## The chain

Nine steps, in order. Each one is emitted as a traced step at runtime, so what
follows describes the shape rather than substituting for the output.

**1 · Dry biomass.** `wet_mass_kg × (1 − moisture_fraction) ÷ 1000`. Water is
not feedstock, and moisture varies enough between a fresh and a field-dried
residue to move the result by a fifth.

**2 · Biochar produced.** Taken from the measured output when the pyrolysis run
recorded one. Only when nothing was weighed does the engine fall back to a
yield factor applied to dry mass, and the trace says which path was taken.
Estimating is acceptable for screening a prospective batch and not acceptable
for one that has already been produced.

**3 · Organic carbon in biochar.** `biochar_t × organic_carbon_fraction`, from
the laboratory. There is no default: without a report this step blocks.

**4 · CO₂ equivalent.** `carbon_t × 3.664`, the molar mass ratio of CO₂ to
carbon. The only sourced factor in the shipped set, because it is stoichiometry
rather than a methodology choice.

**5 · Durable stored CO₂.** The share still stored after a hundred years,
selected by the hydrogen-to-organic-carbon molar ratio. This is the step that
separates a removal from a delay: biomass left to rot also stores carbon, for a
year. Without H/Corg the chain stops here rather than assuming a value.

**6 · Transport emissions.** Summed over legs as
`payload_t × distance_km × factor`, with the vehicle class selecting the factor
and an unlisted class degrading to a generic road-freight value.

**7 · Process emissions.** Grid electricity and any fuel burned by the run
itself.

**8 · Uncertainty deduction.** A flat conservative percentage of the durable
figure, standing in for propagation over the measurements that fed it.

**9 · Preliminary net removal.**
`durable − transport − process − uncertainty`.

## What is not computed

**Baseline emissions.** What would have happened to the biomass anyway is
treated as a qualitative eligibility question — the screener asks about it and
flags a productive competing use — but it is not quantified and not subtracted.
A methodology-aligned calculation would.

**Leakage.** Diverting biomass from an existing user may simply move the
emissions. Flagged by a rule, not modelled.

**Biochar application effects.** Soil carbon response, avoided fertiliser,
albedo. Out of scope entirely.

**Reversal risk and buffer contributions.** A registry would withhold a share
of issued units against reversal. Not modelled.

## Provenance

Every factor carries a source or an explicit `null`, and `null` propagates: a
step applying an unsourced factor is provisional, and so is any figure derived
from it. This is why the engine currently reports almost everything as
provisional — of the factors in `factors/default.yaml`, only the stoichiometric
ratio is sourced.

Replacing the placeholders is the substantive next change. When it happens,
each factor gains a `source` block naming the document, its version and its
publication date.

**On quoting methodologies.** Parameters are referenced by document, clause and
version. Substantial text from Verra, Puro or any other standard is not copied
into this repository — those documents are their authors' copyright, and a
citation is both sufficient and more useful, because it points at the version
that was actually applied.

## Standing warning

The engine produces a preliminary project-development estimate. Certification,
issuance and any tradeable claim require a selected methodology, complete
primary data, accredited laboratory analysis, and independent validation and
verification by a body accredited for that standard. Nothing computed here
substitutes for any of that.
