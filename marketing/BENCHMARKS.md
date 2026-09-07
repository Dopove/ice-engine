# ICE memory benchmarks

> **Read this first.** ICE is a *memory / retrieval layer*, not an answer generator. Every row below is `ICE (or a baseline) assembles context -> the same frozen reader model answers -> the answer is scored`. Numbers are a **small labelled sample (N is shown per row), directional, not a full-suite result.** Every value is copied from a committed `summary.json`; raw predictions and logs sit next to it. Runs on the bundled synthetic fixture are listed separately and are **not** evidence of anything.

## locomo  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.157 | 0.111 | 0.222 | 0.750 | 1.000 (n=6) | 9 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.141 | 0.111 | 0.222 | 0.600 | 1.000 (n=6) | 9 |
| ICE retrieval only (raw hits, no ContextPager) | 0.190 | 0.111 | 0.222 | 0.667 | 1.000 (n=6) | 9 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.190 | 0.111 | 0.222 | 0.667 | 1.000 (n=6) | 9 |
| Recency truncation (no retrieval) | 0.067 | 0.000 | 0.056 | 0.545 | 1.000 (n=6) | 9 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.545 | 1.000 (n=6) | 8 |

**Reproducibility**

- suite: `locomo`  |  commit: `9ce21d79`  |  run: `2026-09-07T14:50:32Z`
- reader / judge model: `minimax/minimax-m3:free` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `20`  |  completed: `8`  |  partial: `True`
- raw: `results/locomo/9ce21d79/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 20`

## longmemeval  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.460 | 0.364 | 0.502 | 1.000 | - | 11 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.407 | 0.273 | 0.535 | 0.667 | - | 11 |
| ICE retrieval only (raw hits, no ContextPager) | 0.364 | 0.182 | 0.533 | 0.857 | - | 11 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.524 | 0.364 | 0.661 | 0.857 | - | 11 |
| Recency truncation (no retrieval) | 0.252 | 0.091 | 0.312 | 0.615 | - | 11 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.571 | - | 10 |

**Reproducibility**

- suite: `longmemeval`  |  commit: `8144b0ac`  |  run: `2026-09-02T23:23:31Z`
- reader / judge model: `ling-3.0-flash-fin-free` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `12`  |  completed: `11`  |  partial: `True`
- raw: `results/longmemeval/8144b0ac/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite longmemeval --reader openrouter --limit 12`

## Appendix: synthetic-fixture runs (NOT evidence)

These exercise the pipeline offline. Do not cite.

### locomo — synthetic

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 1.000 | 1.000 | 1.000 | - | - | 4 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | - | - | 4 |

### locomo — synthetic

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.000 | 0.000 | 0.000 | - | - | 6 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.000 | 0.000 | 0.000 | - | - | 6 |
| Recency truncation (no retrieval) | 0.000 | 0.000 | 0.000 | - | - | 6 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | - | - | 6 |
