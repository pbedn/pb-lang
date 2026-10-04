# Branch consolidation record

October 4, 2026. Work was extracted into master after review; whole stale branches
were not merged indiscriminately. The original heads are recoverable from the
verified local Git bundle `.branch-backups/2026-10-03-feature-branches.bundle`.
Keep that file when moving or deleting this checkout.

## Source branch heads

| Branch | Preserved commit |
| --- | --- |
| `bench` | `d1f97a704c6f026b81e556315c9c3abbf02d7bcc` |
| `codex/add-enum-support-in-pb-language` | `b4952619ab6aca484e8e24a6161d3b733f13f6ed` |
| `codex/add-improved-list-support-in-pb` | `a6d27b9c38d4c5bcb5ee62fe32a5c39253a04904` |
| `codex/complete-pong-in-pb-and-raylib-stubs` | `b501cd21242e2dd722dc5c98f16673a51a18450b` |
| `codex/fix-pb-snippet-and-add-tests` | `daf25ffc9773af8a5de59ee65029a0d61bce8b36` |
| `codex/fix-runtimeerror-handling-and-add-tests` | `37374404c748419c182cecc087f3ff205306a055` |
| `codex/implement-list-cleanup-policy-in-pb-language` | `81ffba551bc3164241f5428fb945448432b2f9ee` |
| `codex/implement-python-like-enums-in-pb` | `3b998f144652cc45cb2a71044a9a85d6e8343faf` |
| `codex/make-strings-dynamic-like-python` | `490d05da00796cb8bbc223b71b81e6154bb44d12` |
| `codex/reanalyse-language-state-and-update-spec.md` | `a2a4bf8f14a088df752051c9fdb6e477611ad47c` |
| `codex/update-pb-lang-for-consistent-output` | `7cfc334f4213bf2b2972aded69ed05c50e168bc2` |
| `codex/use-generic-macros-for-list-methods` | `b2caca752f6fe7177ced04d71aa696e26643b444` |

The imports branch was already contained in master. The earlier `pong` commit
`7867b5c94bf28fd338affc5ebaa23a580f597c0b` is contained in the preserved completed-Pong
branch. Both names were already deleted remotely at the final consolidation fetch.

## What was retained

- List-method macros and iterable work from PRs 45/46, corrected for ownership,
  nested indices, UTF-8 characters, and evaluating iterable sources once.
- Typed enum validation/printing from PR 49 and enum export/import concepts from
  PR 48, combined into a single implementation with module-qualified C symbols.
- String concatenation from PR 47 with tracked storage, stable numeric conversions,
  and bool-to-string behavior recovered from the earlier conversion work.
- Multi-argument printing from PR 29, with actual evaluation-order and container
  handling fixes. Existing len and strict assignment implementations were retained.
- BaseException/inherited constructor concepts from PR 51, plus payload-preserving
  re-raises, balanced try contexts, ancestor matching, and finally on exits.
- The memory-lifetime concern from PR 50. Its unsafe scope cleanup code was replaced
  with documented tracked allocation ownership and safe escaped-container copies.
- Benchmark workloads and handwritten C from `bench`; the runner was replaced to
  compare the actual three implementations and propagate compiler/program errors.
- Pong gameplay and callback-filtering concepts from PR 52. A smaller runnable
  asset-free PB game replaces the unbuildable scaffolding; the original C reference
  is preserved in `ref/pong/`. Experimental stub generation never overwrites the
  curated native API.
- Documentation topics from PR 44, rewritten against the final implementation.

The committed conflict markers and stale duplicate implementations in PR 24,
unsafe cleanup in PR 50, invalid enum code generation, and misleading benchmark
measurements were not retained. Existing compiler and reference tests were kept
and updated where the generated C intentionally changed; executable regressions
were added for the recovered functionality.

## Recovery

Inspect the backup with `git bundle list-heads .branch-backups/2026-10-03-feature-branches.bundle`.
A deleted source branch can be restored locally from its preserved remote ref:

```text
git fetch .branch-backups/2026-10-03-feature-branches.bundle refs/remotes/origin/bench:refs/heads/recovered-bench
```

## Validation

The original baseline was 532 passing tests and three skips. The consolidation
adds 76 tests and reactivates two existing checks for functionality now supported.
Final local runs on Windows, Python 3.14.5, GCC 16.2:

- `PB_CFLAGS=-O0`: 610 passed, one existing lexer skip.
- `PB_CFLAGS=-O2`: 610 passed, the same one skip.
- Thirty independently launched reference executables in each suite matched
  CPython output; the Windows exception fix also passed 100 consecutive runs.
- Headless Pong ran 600 frames, checking bounds, scoring, pause, and closing.
- The real bundled Windows Raylib Pong executable compiled successfully.
- Quick benchmark outputs agreed across PB, handwritten C, and Python at both
  optimization levels (6765 for Fibonacci; 1875025002 for arithmetic).
- Source compilation and Git whitespace checks passed.

The regression tests cover enum ranges/aliases/import isolation, iterable
evaluation and nesting, escaped container storage, allocation cleanup/reuse,
string lifetime, print ordering, dictionary errors, exception restoration,
finally exits, repeated context unwinding, build failures, native stub filtering,
and custom output names. CI checks Linux/Windows with Python 3.13 at both `-O0`
and `-O2`, including benchmarks and the Windows native build.

Memory is still retained until process shutdown; retained f-strings and deep
ownership of string container elements require further work. See `spec.md` and
`roadmap.md` for the remaining limits.

## Retirement

The reviewed source heads will be deleted after publishing the consolidated
master and verifying its cross-platform CI. The local bundle above preserves
their complete history independently of remote branch deletion.
