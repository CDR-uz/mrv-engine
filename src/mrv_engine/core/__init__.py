"""Core domain logic.

Nothing in this package performs I/O. No file reads, no network, no printing.
Everything is a pure function over the data model, so that the CLI, the HTTP
API and the future web backend all compute identical results and the tests can
target the arithmetic rather than an interface.
"""
