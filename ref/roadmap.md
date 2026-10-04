# PB roadmap

Updated October 4, 2026. Priorities are ordered; no delivery dates are promised.

## Completed in this consolidation

- Refreshed the spec and reconciled the branch backlog.
- Added iterable code generation with independent nested state and evaluation once.
- Consolidated list method implementations through macros.
- Replaced unsafe local cleanup with documented tracked allocation ownership.
- Added string concatenation, stable conversions, typed enums and imports, and
  multi-argument printing with built-in containers.
- Corrected exception inheritance, re-raise payloads, context balancing, and finally.
- Added a buildable, asset-free Pong example and automated headless gameplay checks.
- Repaired benchmarks to compare actual handwritten C, generated PB, and Python
  with checked outputs and matched optimization flags.
- Added Linux/Windows CI at two optimization levels and 76 regression tests,
  reactivating two older checks that the implementation now supports.

## Next: reliable core semantics

1. Maintain compiler/runtime checks on Linux and Windows, including optimized builds.
2. Complete owned f-strings and string elements in containers. Remove fixed-buffer
   lifetime limitations and define early reclamation for long-running programs.
3. Decide between C value semantics and shared Python-like container identity
   before expanding mutation APIs.
4. Complete optional lowering, range steps, negative indexing, and defined numeric
   overflow/floor-division behavior.
5. Improve module cycles, imported class metadata, and diagnostics.

## Then: native integration and standard library

- Keep the curated Raylib subset verified. Add native struct/value ABI support,
  pointer types, and callbacks through explicit wrappers.
- Add portable Raylib packaging and metadata for Linux and macOS.
- Extend Pong with optional audio, menus, and AI once dependencies are reproducible.
  The original larger C design is preserved in `ref/pong/`.
- Expand the PB stdlib and implement relative imports.

## Performance

Use `python benchmark/pb_bench.py --quick --repeats 1` for output validation and
`python benchmark/pb_bench.py --repeats 3 --optimization=-O2` for larger workloads.
Compilation is excluded; process startup is included. Record platform, compiler,
optimization, and workload alongside results. Add broader workloads and allocation
measurements before publishing general performance claims.
