# ICE memory benchmarks

> **Read this first.** ICE is a *memory / retrieval layer*, not an answer generator. Every row below is `ICE (or a baseline) assembles context -> the same frozen reader model answers -> the answer is scored`. Numbers are a **small labelled sample (N is shown per row), directional, not a full-suite result.** Every value is copied from a committed `summary.json`; raw predictions and logs sit next to it. Runs on the bundled synthetic fixture are listed separately and are **not** evidence of anything.

## Status: no non-synthetic runs yet

The harness is in place and validated on the bundled synthetic fixture. Real-dataset runs (LoCoMo, LongMemEval) are pending -- they need the OpenRouter free-tier key wired into CI and accumulate over several days because of the 50-calls/day free-tier cap.

## Appendix: synthetic-fixture runs (NOT evidence)

These exercise the pipeline offline. Do not cite.

### locomo — synthetic

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (memory layer) | 1.000 | 1.000 | 1.000 | - | - | 4 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | - | - | 4 |

### locomo — synthetic

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (memory layer) | 0.000 | 0.000 | 0.000 | - | - | 6 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.000 | 0.000 | 0.000 | - | - | 6 |
| Recency truncation (no retrieval) | 0.000 | 0.000 | 0.000 | - | - | 6 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | - | - | 6 |
