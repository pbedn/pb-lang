# Reference materials

`lang.pb` demonstrates a representative subset of PB. Its expected runtime
output is `lang_expected_output.out`; `ref_lang.h` and `ref_lang.c` are the
generated-C snapshots checked by the pipeline tests.

See `spec.md` for current supported behavior, `roadmap.md` for future priorities,
and `branch-consolidation.md` for the origin and recovery of retired branch work.
The original larger Pong design is preserved under `pong/`.

Generate C into the ignored build directory with:

```text
python run.py toc ref/lang.pb
```
