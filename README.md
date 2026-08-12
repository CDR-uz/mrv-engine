# MRV Pre-Assessment Engine

**v0.1 · pre-alpha · under active development**

Takes the description of a single biomass batch and produces two things: a
preliminary carbon-removal estimate with the full derivation shown, and an
honest list of what is still missing before that number could be defended to an
independent auditor.

> **Preliminary project-development estimate. Not a certified carbon credit
> calculation and not a methodology-compliant quantification.** Final figures
> depend on the selected methodology, laboratory results and independent
> validation and verification. This engine does not certify anything, does not
> issue anything, and cannot tell you that a project will succeed.

## Why this exists

A biochar carbon removal project rarely fails on the chemistry. It fails
because the tenth document is missing.

Anyone can state that ten tonnes of cotton stalks removed four tonnes of CO₂.
Turning that into something sellable means proving a long chain of facts to a
validation body: that the biomass was genuinely a residue, that it would not
have been put to better use, who owned it, what it weighed and how wet it was,
how far it travelled and on what, at what temperature it was pyrolysed, what an
accredited laboratory measured, where exactly the biochar ended up, and who
holds the right to claim the removal. Miss one and the carbon is still in the
ground while the claim is worthless.

This engine is the part that keeps score. It computes what can be computed,
refuses to compute what cannot, and names the difference.

## Quickstart

Run it against a batch file of your own, with no clone and no virtualenv:

```bash
uvx --from git+https://github.com/CDR-uz/mrv-engine mrv-engine dossier my-batch.yaml
```

To try the worked example below, take the repository:

```bash
git clone https://github.com/CDR-uz/mrv-engine && cd mrv-engine
uv run mrv-engine dossier examples/cotton-stalk-samarkand-complete.yaml
```

Three commands over one document: `calc` shows the calculation trace, `assess`
shows eligibility and the gap register, `dossier` shows everything. Add
`--json` to any of them to get the machine-readable dossier instead.

## Worked example

Ten tonnes of cotton stalks from the Zarafshan valley, 18% moisture, 75 km to a
screw reactor, laboratory report received:

```
Batch CAC-UZ-SAM-COT-2026-00001
rules generic_biochar 0.1.0 · factors 0.1.0-placeholder

CALCULATION
    Dry biomass                              8.200 t
        wet_mass_kg * (1 - moisture_fraction) / 1000
    Biochar produced                         2.296 t
        biochar_mass_kg / 1000
        measured at the facility
    Organic carbon in biochar                1.653 t C
        biochar_t * organic_carbon_fraction
    CO2 equivalent of that carbon            6.057 t CO2
        carbon_t * co2_per_carbon
  ? Durable stored CO2 (100 yr)              4.482 t CO2
        gross_co2_t * durable_fraction
        H/Corg 0.35 falls in band 'h_corg_below_0_4'
  ? Transport emissions                      0.105 t CO2e
  ? Process emissions                        0.149 t CO2e
  ? Uncertainty deduction                    0.224 t CO2e
    Preliminary net removal                  4.004 t CO2e
        durable_co2 - transport_emissions - process_emissions - uncertainty_deduction

  ?  provisional — rests on a factor with no documented source
  !  not computed

ELIGIBILITY  needs_review
  [review] Competing uses declared for this feedstock

EVIDENCE  87% complete · 2 blocking gap(s)
   ~  Signed assignment of carbon rights to the project   blocking
        draft agreement with supplier, unsigned
   ~  Documented baseline fate of the biomass             blocking
        supplier statement only, no third-party record of field burning

TIMELINE
  2026-03-14  Biomass collected  (SUP-UZ-0007)
  2026-03-16  Transported to the facility  (1 leg(s), 75 km)
  2026-03-19  Pyrolysis run  (PYR-UZ-0002)
  2026-03-24  Sampled for laboratory analysis  (LAB-2026-0418)
  2026-04-02  Biochar applied  (agricultural_soil)
```

Note the shape of that result: **87% of the evidence is in place and the batch
is still blocked**, because the carbon rights agreement is unsigned and the
baseline rests on the supplier's word. A single completeness percentage would
have said "nearly ready". The blocking-gap count says what is actually true.

### The same batch before the laboratory reported

`examples/cotton-stalk-samarkand.yaml` is the identical production run a
fortnight earlier. It gets as far as the carbon content and stops:

```
    CO2 equivalent of that carbon            6.057 t CO2
  ! Durable stored CO2 (100 yr)                 -- t CO2
        missing: lab.hydrogen_to_organic_carbon_molar_ratio
  ! Preliminary net removal                     -- t CO2e
        missing: durable_co2, uncertainty_deduction
```

It does not fall back to an assumption and it does not report zero. Without the
hydrogen-to-organic-carbon ratio there is no defensible claim that the storage
lasts a century, so there is no removal figure — only a named gap. The two
files are kept side by side because the difference between the two dossiers is
the entire argument for the engine.

## How it works

Four assessments over one `Batch`, assembled into one dossier:

| | |
|---|---|
| **Calculator** | nine steps from wet biomass to net removal, each emitting its formula, inputs and factors |
| **Eligibility screener** | rule pack applied to the batch, returning a verdict and the findings behind it |
| **Gap register** | evidence checklist walked against what the batch carries, weighted |
| **Timeline** | chain of custody derived from the dates already on the batch, checked for impossible ordering |

Three design decisions carry most of the weight, each written up in
[`docs/decisions/`](docs/decisions/):

**Factors carry provenance, and provenance propagates.** Every coefficient has
a source or an explicit `null`. Any step applying an unsourced factor is marked
provisional, and so is any result resting on it. Today only the 44/12
stoichiometric ratio is sourced, so the engine reports nearly everything as
provisional — which is the honest state before methodology numbers are entered.

**The trace is the output, not a log.** What has to survive the trip to a
validation body is the derivation, not the number.

**Conditions are three-valued.** "No evidence the biomass was purpose-grown"
and "evidence that it was not" are different answers. A screener that collapses
them into a pass is lying.

## Rule packs, factor sets, and what is not here

Rules and coefficients are versioned YAML, not Python, because methodologies
get revised and a rule set embedded in code cannot be diffed or swapped.

What ships in this repository is deliberately generic:

- [`rules/generic_biochar.yaml`](rules/generic_biochar.yaml) — the questions
  common to biochar CDR project development. It is **not** a methodology and
  claims conformity with none. There is no pack named after VM0044 or Puro,
  because a file named after a methodology would assert a conformity that does
  not exist.
- [`factors/default.yaml`](factors/default.yaml) — placeholder coefficients,
  every one of them marked and unsourced except the physical constant.

Sourced factor sets and jurisdiction-specific rule packs — the ones carrying
real regulatory pathways and coefficients tied to a methodology document — are
maintained separately and are not part of this distribution. The engine is the
generic half; the packs are where the work accumulates.

Both are swappable at the command line:

```bash
uv run mrv-engine dossier batch.yaml --rules path/to/pack.yaml --factors path/to/factors.yaml
```

## Layout

```
src/mrv_engine/
├── core/       pure functions over the data model — no file, network or console access
│   ├── models.py       the Batch and everything hanging off it
│   ├── calculator.py   the nine-step chain
│   ├── factors.py      coefficients and their provenance
│   ├── trace.py        the audit trail
│   ├── rules.py        rule packs and the condition language
│   ├── eligibility.py  the screener
│   ├── evidence.py     the gap register
│   ├── timeline.py     derived chain of custody
│   ├── identity.py     batch identifiers
│   └── dossier.py      assembly
└── adapters/   everything that touches the outside world
    ├── io.py           loading batches, packs and factor sets
    ├── serialize.py    the dossier JSON contract
    └── cli.py          the command line

rules/     rule packs, versioned
factors/   factor sets, versioned
examples/  demonstration batches
```

The split is enforced by convention and by the tests: `core` takes a `Batch`,
never a path, so the CLI, a future HTTP API and a web backend all compute
identical results.

## Development

```bash
uv sync
uv run pytest
```

Two runtime dependencies, pydantic and pyyaml. The CLI is argparse.

## Status

See [ROADMAP.md](ROADMAP.md) for what is deliberately not built yet and
[CHANGELOG.md](CHANGELOG.md) for what changed. The short version: the shape is
right, the coefficients are placeholders, and nothing here has been reviewed by
a validation body.

## License

Apache-2.0. See [LICENSE](LICENSE).
