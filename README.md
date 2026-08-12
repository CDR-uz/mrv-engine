# MRV Pre-Assessment Engine

**Status: v0.1 · pre-alpha · under active development**

Takes the description of a single biomass batch and produces two things: a
preliminary carbon-removal estimate with the full derivation shown, and an
honest list of what is still missing before that number could be proven to an
independent auditor.

> **Preliminary estimate — not a certified carbon credit calculation.**
> Final quantification depends on the selected methodology, laboratory results
> and independent validation and verification.

## Scope of v0.1

Biochar carbon dioxide removal, one batch at a time, Uzbekistan as the first
jurisdiction. The engine is a library first; the CLI and the HTTP API are thin
adapters over the same functions.

## Layout

```
src/mrv_engine/
├── core/       pure functions, no I/O
├── adapters/   CLI and (later) HTTP
rules/          methodology rule packs, versioned, as data
```

## License

Apache-2.0.
