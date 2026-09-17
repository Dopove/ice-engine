# ICE memory benchmarks

> **Read this first.** ICE is a *memory / retrieval layer*, not an answer generator. Every row below is `ICE (or a baseline) assembles context -> the same frozen reader model answers -> the answer is scored`. Numbers are a **small labelled sample (N is shown per row), directional, not a full-suite result.** Every value is copied from a committed `summary.json`; raw predictions and logs sit next to it. Runs on the bundled synthetic fixture are listed separately and are **not** evidence of anything.

## locomo  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.223 | 0.133 | 0.236 | 0.600 | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.223 | 0.133 | 0.236 | 0.600 | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.156 | 0.067 | 0.170 | 0.500 | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.156 | 0.067 | 0.170 | 0.500 | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.068 | 0.000 | 0.089 | 0.429 | 1.000 (n=5) | 15 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.333 | 1.000 (n=5) | 15 |

**Reproducibility**

- suite: `locomo`  |  commit: `a422f77`  |  run: `2026-09-17T15:38:01Z`
- reader / judge model: `cx/gpt-5.6-luna-medium` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/locomo/a422f77/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 15`

## longmemeval  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.391 | 0.267 | 0.404 | 1.000 | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.458 | 0.333 | 0.471 | 1.000 | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.458 | 0.333 | 0.471 | 1.000 | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.458 | 0.333 | 0.471 | 1.000 | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.169 | 0.133 | 0.158 | 0.625 | 1.000 (n=5) | 15 |
| No memory (question only) | 0.009 | 0.000 | 0.006 | 0.500 | 1.000 (n=5) | 15 |

**Reproducibility**

- suite: `longmemeval`  |  commit: `a422f77`  |  run: `2026-09-17T15:34:52Z`
- reader / judge model: `cx/gpt-5.6-luna-medium` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/longmemeval/a422f77/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite longmemeval --reader openrouter --limit 15`

## beam  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.166 | 0.067 | 0.698 | 0.500 | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.149 | 0.000 | 0.687 | 0.500 | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.149 | 0.000 | 0.704 | 0.500 | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.149 | 0.000 | 0.704 | 0.500 | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.004 | 0.000 | 0.535 | 0.267 | 1.000 (n=5) | 15 |
| No memory (question only) | 0.004 | 0.000 | 0.535 | 0.235 | 1.000 (n=5) | 15 |

**Reproducibility**

- suite: `beam`  |  commit: `a422f77`  |  run: `2026-09-17T15:44:15Z`
- reader / judge model: `cx/gpt-5.6-luna-medium` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/beam/a422f77/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite beam --reader openrouter --limit 15`

## ama  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.134 | 0.000 | 0.141 | - | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.134 | 0.000 | 0.141 | - | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.131 | 0.000 | 0.139 | - | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.131 | 0.000 | 0.139 | - | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.133 | 0.000 | 0.137 | - | 1.000 (n=5) | 15 |
| No memory (question only) | 0.040 | 0.000 | 0.034 | - | 1.000 (n=5) | 15 |

**Reproducibility**

- suite: `ama`  |  commit: `a422f77`  |  run: `2026-09-17T15:40:45Z`
- reader / judge model: `cx/gpt-5.6-luna-medium` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/ama/a422f77/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite ama --reader openrouter --limit 15`

## Appendix: synthetic-fixture runs (NOT evidence)

These exercise the pipeline offline. Do not cite.

### locomo — synthetic

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| Mem0 | 0.000 | 0.000 | 0.000 | - | - | 1 |
| langmem | 0.000 | 0.000 | 0.000 | - | - | 1 |
