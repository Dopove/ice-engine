# ICE memory benchmarks

> **Read this first.** ICE is a *memory / retrieval layer*, not an answer generator. Every row below is `ICE (or a baseline) assembles context -> the same frozen reader model answers -> the answer is scored`. Numbers are a **small labelled sample (N is shown per row), directional, not a full-suite result.** Every value is copied from a committed `summary.json`; raw predictions and logs sit next to it. Runs on the bundled synthetic fixture are listed separately and are **not** evidence of anything.

## locomo  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.152 | 0.067 | 0.181 | 0.545 | 0.000 (n=6) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.152 | 0.067 | 0.181 | 0.545 | 0.000 (n=6) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.152 | 0.067 | 0.181 | 0.600 | 0.000 (n=6) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.152 | 0.067 | 0.181 | 0.600 | 0.000 (n=6) | 15 |
| Recency truncation (no retrieval) | 0.046 | 0.000 | 0.078 | 0.429 | 0.000 (n=6) | 15 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.333 | 0.000 (n=6) | 15 |

**Reproducibility**

- suite: `locomo`  |  commit: `7d0a95d3`  |  run: `2026-09-08T17:16:51Z`
- reader / judge model: `bai/glm-5.3-flash` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/locomo/7d0a95d3/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 15`

## longmemeval  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.318 | 0.200 | 0.398 | 0.833 | 0.000 (n=6) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.283 | 0.133 | 0.464 | 0.833 | 0.000 (n=6) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.238 | 0.133 | 0.382 | 0.833 | 0.000 (n=6) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.238 | 0.133 | 0.382 | 0.833 | 0.000 (n=6) | 15 |
| Recency truncation (no retrieval) | 0.169 | 0.133 | 0.158 | 0.588 | 0.167 (n=6) | 15 |
| No memory (question only) | 0.009 | 0.000 | 0.006 | 0.500 | 0.000 (n=6) | 15 |

**Reproducibility**

- suite: `longmemeval`  |  commit: `7d0a95d3`  |  run: `2026-09-08T17:43:41Z`
- reader / judge model: `bai/glm-5.3-flash` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/longmemeval/7d0a95d3/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite longmemeval --reader openrouter --limit 15`

## beam  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.374 | 0.333 | 0.636 | 0.000 | 0.000 (n=6) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.506 | 0.467 | 0.629 | 0.000 | 0.000 (n=6) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.305 | 0.267 | 0.631 | 0.000 | 0.000 (n=6) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.305 | 0.267 | 0.631 | 0.000 | 0.000 (n=6) | 15 |
| Recency truncation (no retrieval) | 0.007 | 0.000 | 0.539 | 0.308 | 0.000 (n=6) | 15 |
| No memory (question only) | 0.007 | 0.000 | 0.539 | 0.235 | 0.000 (n=6) | 15 |

**Reproducibility**

- suite: `beam`  |  commit: `7d0a95d3`  |  run: `2026-09-08T18:07:09Z`
- reader / judge model: `bai/glm-5.3-flash` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/beam/7d0a95d3/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite beam --reader openrouter --limit 15`

## ama  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.047 | 0.000 | 0.056 | - | 0.000 (n=6) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.077 | 0.000 | 0.077 | - | 0.000 (n=6) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.080 | 0.000 | 0.101 | - | 0.000 (n=6) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.080 | 0.000 | 0.101 | - | 0.000 (n=6) | 15 |
| Recency truncation (no retrieval) | 0.042 | 0.000 | 0.038 | - | 0.000 (n=6) | 15 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | - | 0.000 (n=6) | 15 |

**Reproducibility**

- suite: `ama`  |  commit: `7d0a95d3`  |  run: `2026-09-08T18:21:44Z`
- reader / judge model: `bai/glm-5.3-flash` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/ama/7d0a95d3/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite ama --reader openrouter --limit 15`

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
