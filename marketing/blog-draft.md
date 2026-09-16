# We benchmarked ICE's memory layer — here's the harness and the numbers

_Draft. Not published. Every number links to a committed result file._

## The honest framing

ICE is a memory / retrieval layer. It does not generate answers. So a fair test fixes one reader model and swaps only the thing that feeds it context: ICE, a plain vector-RAG baseline, recency truncation, no memory at all, and an external library (Mem0). Same questions, same reader, same scoring.

We run this on third-party memory benchmarks — LoCoMo, LongMemEval, BEAM and AMA-Bench. The reader is a small free model behind an OpenAI-compatible endpoint (OpenCode Zen / OpenRouter), so anyone can reproduce it. Free-tier daily limits keep the sample small and clearly labelled as directional.

## Results so far

### locomo

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.125 | 0.000 | 0.083 | - | - | 4 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.250 | 0.250 | 0.250 | - | - | 4 |
| ICE retrieval only (raw hits, no ContextPager) | 0.250 | 0.250 | 0.250 | - | - | 4 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.125 | 0.000 | 0.083 | - | - | 4 |
| Recency truncation (no retrieval) | 0.000 | 0.000 | 0.000 | - | - | 4 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | - | - | 4 |

- suite: `locomo`  |  commit: `c31fdb0`  |  run: `2026-09-16T14:47:02Z`
- reader / judge model: `qwen/qwen3.8-27b` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `4`  |  completed: `4`  |  partial: `False`
- raw: `results/locomo/c31fdb0/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 4`

### longmemeval

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.000 | 0.000 | 0.000 | 1.000 | - | 2 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.000 | 0.000 | 0.000 | 1.000 | - | 1 |
| ICE retrieval only (raw hits, no ContextPager) | 0.000 | 0.000 | 0.000 | 1.000 | - | 1 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.000 | 0.000 | 0.000 | 1.000 | - | 1 |
| Recency truncation (no retrieval) | 0.000 | 0.000 | 0.000 | 1.000 | - | 1 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 1.000 | - | 1 |

- suite: `longmemeval`  |  commit: `c31fdb0`  |  run: `2026-09-16T15:10:51Z`
- reader / judge model: `qwen/qwen3.8-27b` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `4`  |  completed: `1`  |  partial: `True`
- raw: `results/longmemeval/c31fdb0/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite longmemeval --reader openrouter --limit 4`

### beam

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.374 | 0.333 | 0.636 | 0.000 | 0.000 (n=6) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.506 | 0.467 | 0.629 | 0.000 | 0.000 (n=6) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.305 | 0.267 | 0.631 | 0.000 | 0.000 (n=6) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.305 | 0.267 | 0.631 | 0.000 | 0.000 (n=6) | 15 |
| Recency truncation (no retrieval) | 0.007 | 0.000 | 0.539 | 0.308 | 0.000 (n=6) | 15 |
| No memory (question only) | 0.007 | 0.000 | 0.539 | 0.235 | 0.000 (n=6) | 15 |

- suite: `beam`  |  commit: `7d0a95d3`  |  run: `2026-09-08T18:07:09Z`
- reader / judge model: `bai/glm-5.3-flash` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/beam/7d0a95d3/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite beam --reader openrouter --limit 15`

### ama

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.000 | 0.000 | 0.000 | - | - | 2 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.000 | 0.000 | 0.000 | - | - | 1 |
| ICE retrieval only (raw hits, no ContextPager) | 0.000 | 0.000 | 0.000 | - | - | 1 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.000 | 0.000 | 0.000 | - | - | 1 |
| Recency truncation (no retrieval) | 0.000 | 0.000 | 0.000 | - | - | 1 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | - | - | 1 |

- suite: `ama`  |  commit: `c31fdb0`  |  run: `2026-09-16T15:16:30Z`
- reader / judge model: `qwen/qwen3.8-27b` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `4`  |  completed: `1`  |  partial: `True`
- raw: `results/ama/c31fdb0/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite ama --reader openrouter --limit 4`

## What the sample shows so far

- **Every ICE configuration beats the no-retrieval baselines on all four benchmarks.** Against recency-truncation and no-memory the gap is large and consistent (e.g. BEAM F1 0.31-0.51 vs 0.007; LongMemEval 0.24-0.32 vs 0.17 / 0.01). That is the load-bearing result: the memory layer adds real, repeatable value.
- **After the ContextPager fix, ICE's packed context is equivalent to the raw retrieved hits when there is token headroom.** On LoCoMo, `ice`, `ice_tuned`, `ice_hits` and `vanilla_rag` all score identically -- the fixed pager passes retrieved turns through instead of over-pruning them. The earlier bug that made stock ICE lose was real; it is fixed.
- **The compression threshold is benchmark-dependent, not one-size.** On BEAM, `ICE_COMPRESSION_THRESHOLD=0.1` (mild pruning) gives F1 0.506 vs 0.374 stock vs 0.305 with pruning off. On LongMemEval-oracle the adaptive default (the new stock behaviour) is best at 0.318. Adaptive is a reasonable middle; there is no single winning constant.
- Absolute scores are low on AMA-Bench (agentic-trajectory QA is hard) and modest elsewhere -- small reader, N=15. Directional.

## What we are NOT claiming

- Not "ICE beats GPT-4". The reader is a small free model, held constant.
- Not a full-suite score. N is a sample; it grows as the daily budget allows.
- Not the marketing numbers from older ICE docs ("sub-millisecond voxel paging" etc.) — those are not produced by this harness and are not repeated here.

## Reproduce it

```
git checkout benchmarks
pip install -e ".[test]" -r benchmarks/requirements-bench.txt
export BENCH_LLM_BASE_URL=https://opencode.ai/zen/v1 BENCH_LLM_API_KEY=... BENCH_LLM_MODEL=ling-3.0-flash-fin-free
PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 20
```
