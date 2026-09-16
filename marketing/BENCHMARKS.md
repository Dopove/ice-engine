# ICE memory benchmarks

> **Read this first.** ICE is a *memory / retrieval layer*, not an answer generator. Every row below is `ICE (or a baseline) assembles context -> the same frozen reader model answers -> the answer is scored`. Numbers are a **small labelled sample (N is shown per row), directional, not a full-suite result.** Every value is copied from a committed `summary.json`; raw predictions and logs sit next to it. Runs on the bundled synthetic fixture are listed separately and are **not** evidence of anything.

## locomo  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.125 | 0.000 | 0.083 | - | - | 4 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.250 | 0.250 | 0.250 | - | - | 4 |
| ICE retrieval only (raw hits, no ContextPager) | 0.250 | 0.250 | 0.250 | - | - | 4 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.125 | 0.000 | 0.083 | - | - | 4 |
| Recency truncation (no retrieval) | 0.000 | 0.000 | 0.000 | - | - | 4 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | - | - | 4 |

**Reproducibility**

- suite: `locomo`  |  commit: `c31fdb0`  |  run: `2026-09-16T14:47:02Z`
- reader / judge model: `qwen/qwen3.8-27b` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `4`  |  completed: `4`  |  partial: `False`
- raw: `results/locomo/c31fdb0/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 4`

## longmemeval  (sample)

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.000 | 0.000 | 0.000 | 1.000 | - | 2 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.000 | 0.000 | 0.000 | 1.000 | - | 1 |
| ICE retrieval only (raw hits, no ContextPager) | 0.000 | 0.000 | 0.000 | 1.000 | - | 1 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.000 | 0.000 | 0.000 | 1.000 | - | 1 |
| Recency truncation (no retrieval) | 0.000 | 0.000 | 0.000 | 1.000 | - | 1 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 1.000 | - | 1 |

**Reproducibility**

- suite: `longmemeval`  |  commit: `c31fdb0`  |  run: `2026-09-16T15:10:51Z`
- reader / judge model: `qwen/qwen3.8-27b` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `4`  |  completed: `1`  |  partial: `True`
- raw: `results/longmemeval/c31fdb0/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite longmemeval --reader openrouter --limit 4`

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
| ICE (stock config: compression threshold 0.5) | 0.000 | 0.000 | 0.000 | - | - | 2 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.000 | 0.000 | 0.000 | - | - | 1 |
| ICE retrieval only (raw hits, no ContextPager) | 0.000 | 0.000 | 0.000 | - | - | 1 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.000 | 0.000 | 0.000 | - | - | 1 |
| Recency truncation (no retrieval) | 0.000 | 0.000 | 0.000 | - | - | 1 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | - | - | 1 |

**Reproducibility**

- suite: `ama`  |  commit: `c31fdb0`  |  run: `2026-09-16T15:16:30Z`
- reader / judge model: `qwen/qwen3.8-27b` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `4`  |  completed: `1`  |  partial: `True`
- raw: `results/ama/c31fdb0/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite ama --reader openrouter --limit 4`

## Appendix: synthetic-fixture runs (NOT evidence)

These exercise the pipeline offline. Do not cite.

### locomo — synthetic

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| Mem0 | 0.000 | 0.000 | 0.000 | - | - | 1 |
| langmem | 0.000 | 0.000 | 0.000 | - | - | 1 |
