# ICE memory benchmarks

> **Read this first.** ICE is a *memory / retrieval layer*, not an answer generator. Every row below is `ICE (or a baseline) assembles context -> the same frozen reader model answers -> the answer is scored`. Numbers are a **small labelled sample (N is shown per row), directional, not a full-suite result.** Every value is copied from a committed `summary.json`; raw predictions and logs sit next to it. Runs on the bundled synthetic fixture are listed separately and are **not** evidence of anything.

## locomo  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.234 | 0.067 | 0.225 | 0.750 | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.234 | 0.067 | 0.225 | 0.750 | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.234 | 0.067 | 0.225 | 0.667 | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.234 | 0.067 | 0.225 | 0.667 | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.067 | 0.000 | 0.067 | 0.429 | 1.000 (n=5) | 15 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.333 | 1.000 (n=5) | 15 |

**Reproducibility**

- suite: `locomo`  |  commit: `b6d80a5`  |  run: `2026-09-18T09:13:49Z`
- reader / judge model: `us.meta.llama4-maverick-17b-instruct-v1:0` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/locomo/b6d80a5/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 15`

## longmemeval  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.277 | 0.133 | 0.368 | 0.833 | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.285 | 0.133 | 0.289 | 0.833 | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.272 | 0.133 | 0.327 | 0.909 | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.272 | 0.133 | 0.327 | 0.909 | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.070 | 0.067 | 0.068 | 0.526 | 1.000 (n=5) | 15 |
| No memory (question only) | 0.003 | 0.000 | 0.002 | 0.500 | 1.000 (n=5) | 15 |

**Reproducibility**

- suite: `longmemeval`  |  commit: `1eb18e5`  |  run: `2026-09-18T12:56:00Z`
- reader / judge model: `us.meta.llama4-maverick-17b-instruct-v1:0` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/longmemeval/1eb18e5/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite longmemeval --reader openrouter --limit 15`

## beam  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.150 | 0.000 | 0.663 | 0.667 | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.139 | 0.000 | 0.675 | 0.500 | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.138 | 0.067 | 0.704 | 0.000 | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.138 | 0.067 | 0.704 | 0.000 | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.023 | 0.000 | 0.549 | 0.400 | 1.000 (n=5) | 15 |
| No memory (question only) | 0.004 | 0.000 | 0.535 | 0.235 | 1.000 (n=5) | 15 |

**Reproducibility**

- suite: `beam`  |  commit: `b6d80a5`  |  run: `2026-09-18T09:16:43Z`
- reader / judge model: `us.meta.llama4-maverick-17b-instruct-v1:0` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/beam/b6d80a5/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite beam --reader openrouter --limit 15`

## ama  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.168 | 0.000 | 0.195 | - | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.150 | 0.000 | 0.158 | - | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.178 | 0.000 | 0.201 | - | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.178 | 0.000 | 0.201 | - | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.137 | 0.000 | 0.136 | - | 1.000 (n=5) | 15 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | - | 1.000 (n=5) | 15 |

**Reproducibility**

- suite: `ama`  |  commit: `b6d80a5`  |  run: `2026-09-18T09:13:41Z`
- reader / judge model: `us.meta.llama4-maverick-17b-instruct-v1:0` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/ama/b6d80a5/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite ama --reader openrouter --limit 15`

## Appendix: synthetic-fixture runs (NOT evidence)

These exercise the pipeline offline. Do not cite.

### locomo — synthetic

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| Mem0 | 0.000 | 0.000 | 0.000 | - | - | 1 |
| langmem | 0.000 | 0.000 | 0.000 | - | - | 1 |
