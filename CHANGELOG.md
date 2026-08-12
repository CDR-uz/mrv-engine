# Changelog

## 0.1.0 — unreleased

First working version. One batch in, one dossier out.

### Added

- Batch data model. Almost every field optional, because reporting what is
  missing is the product; units in field names, fractions always 0..1.
- Nine-step calculation from wet biomass to preliminary net removal. A step
  that cannot be computed records what was missing instead of raising or
  quietly returning zero.
- Factors with mandatory provenance. Unsourced factors mark every step and
  result that depends on them as provisional.
- Rule packs as versioned YAML with a three-valued condition language.
- Eligibility screener returning `potentially_eligible`, `needs_review`,
  `insufficient_data` or `not_eligible`.
- Evidence gap register, weighted, reported next to a blocking-gap count.
- Chain of custody derived from the dates already on the batch, with a check
  for physically impossible ordering.
- Dossier assembly stamped with the rule pack and factor set that produced it.
- `mrv-engine` CLI with `calc`, `assess` and `dossier`, plus `--json`.
- Two demonstration batches: the same production run before and after the
  laboratory reported.

### Known limitations

- All coefficients except the 44/12 stoichiometric ratio are unsourced
  placeholders. See [ROADMAP.md](ROADMAP.md).
- The shipped rule pack is generic and aligned to no named methodology.
- Nothing here has been reviewed by a validation body.
