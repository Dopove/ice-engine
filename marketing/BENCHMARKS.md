# ICE memory benchmarks

> **Read this first.** ICE is a *memory / retrieval layer*, not an answer generator. Every row below is `ICE (or a baseline) assembles context -> the same frozen reader model answers -> the answer is scored`. Numbers are a **small labelled sample (N is shown per row), directional, not a full-suite result.** Every value is copied from a committed `summary.json`; raw predictions and logs sit next to it. Runs on the bundled synthetic fixture are listed separately and are **not** evidence of anything.

## locomo  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.097 | 0.000 | 0.098 | 0.500 | 0.000 (n=6) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.176 | 0.000 | 0.298 | 0.333 | 0.000 (n=6) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.170 | 0.067 | 0.203 | 0.444 | 0.000 (n=6) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.147 | 0.000 | 0.198 | 0.500 | 0.000 (n=6) | 15 |
| Recency truncation (no retrieval) | 0.033 | 0.000 | 0.075 | 0.250 | 0.000 (n=6) | 15 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.333 | 0.000 (n=6) | 15 |

**Reproducibility**

- suite: `locomo`  |  commit: `964857ad`  |  run: `2026-09-02T23:04:37Z`
- reader / judge model: `ling-3.0-flash-fin-free` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/locomo/964857ad/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 15`

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
