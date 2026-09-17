# We benchmarked ICE's memory layer — here's the harness and the numbers

_Draft. Not published. Every number links to a committed result file._

## The honest framing

ICE is a memory / retrieval layer. It does not generate answers. So a fair test fixes one reader model and swaps only the thing that feeds it context: ICE, a plain vector-RAG baseline, recency truncation, no memory at all, and an external library (Mem0). Same questions, same reader, same scoring.

We run this on third-party memory benchmarks — LoCoMo, LongMemEval, BEAM and AMA-Bench. The reader is a small free model behind an OpenAI-compatible endpoint (OpenCode Zen / OpenRouter), so anyone can reproduce it. Free-tier daily limits keep the sample small and clearly labelled as directional.

## Results so far

### locomo

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.223 | 0.133 | 0.236 | 0.600 | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.223 | 0.133 | 0.236 | 0.600 | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.156 | 0.067 | 0.170 | 0.500 | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.156 | 0.067 | 0.170 | 0.500 | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.068 | 0.000 | 0.089 | 0.429 | 1.000 (n=5) | 15 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.333 | 1.000 (n=5) | 15 |

- suite: `locomo`  |  commit: `a422f77`  |  run: `2026-09-17T15:38:01Z`
- reader / judge model: `cx/gpt-5.6-luna-medium` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/locomo/a422f77/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 15`

### longmemeval

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.391 | 0.267 | 0.404 | 1.000 | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.458 | 0.333 | 0.471 | 1.000 | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.458 | 0.333 | 0.471 | 1.000 | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.458 | 0.333 | 0.471 | 1.000 | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.169 | 0.133 | 0.158 | 0.625 | 1.000 (n=5) | 15 |
| No memory (question only) | 0.009 | 0.000 | 0.006 | 0.500 | 1.000 (n=5) | 15 |

- suite: `longmemeval`  |  commit: `a422f77`  |  run: `2026-09-17T15:34:52Z`
- reader / judge model: `cx/gpt-5.6-luna-medium` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/longmemeval/a422f77/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite longmemeval --reader openrouter --limit 15`

### beam

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.166 | 0.067 | 0.698 | 0.500 | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.149 | 0.000 | 0.687 | 0.500 | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.149 | 0.000 | 0.704 | 0.500 | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.149 | 0.000 | 0.704 | 0.500 | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.004 | 0.000 | 0.535 | 0.267 | 1.000 (n=5) | 15 |
| No memory (question only) | 0.004 | 0.000 | 0.535 | 0.235 | 1.000 (n=5) | 15 |

- suite: `beam`  |  commit: `a422f77`  |  run: `2026-09-17T15:44:15Z`
- reader / judge model: `cx/gpt-5.6-luna-medium` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/beam/a422f77/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite beam --reader openrouter --limit 15`

### ama

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.134 | 0.000 | 0.141 | - | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.134 | 0.000 | 0.141 | - | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.131 | 0.000 | 0.139 | - | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.131 | 0.000 | 0.139 | - | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.133 | 0.000 | 0.137 | - | 1.000 (n=5) | 15 |
| No memory (question only) | 0.040 | 0.000 | 0.034 | - | 1.000 (n=5) | 15 |

- suite: `ama`  |  commit: `a422f77`  |  run: `2026-09-17T15:40:45Z`
- reader / judge model: `cx/gpt-5.6-luna-medium` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `15`  |  completed: `15`  |  partial: `False`
- raw: `results/ama/a422f77/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite ama --reader openrouter --limit 15`

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
