# We benchmarked ICE's memory layer — here's the harness and the numbers

_Draft. Not published. Every number links to a committed result file._

## The honest framing

ICE is a memory / retrieval layer. It does not generate answers. So a fair test fixes one reader model and swaps only the thing that feeds it context: ICE, a plain vector-RAG baseline, recency truncation, no memory at all, and an external library (Mem0). Same questions, same reader, same scoring.

We run this on third-party memory benchmarks — LoCoMo, LongMemEval, BEAM and AMA-Bench. The reader is a small free model behind an OpenAI-compatible endpoint (OpenCode Zen / OpenRouter), so anyone can reproduce it. Free-tier daily limits keep the sample small and clearly labelled as directional.

## Results so far

### locomo

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.157 | 0.111 | 0.222 | 0.750 | 1.000 (n=6) | 9 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.141 | 0.111 | 0.222 | 0.600 | 1.000 (n=6) | 9 |
| ICE retrieval only (raw hits, no ContextPager) | 0.190 | 0.111 | 0.222 | 0.667 | 1.000 (n=6) | 9 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.190 | 0.111 | 0.222 | 0.667 | 1.000 (n=6) | 9 |
| Recency truncation (no retrieval) | 0.067 | 0.000 | 0.056 | 0.545 | 1.000 (n=6) | 9 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.545 | 1.000 (n=6) | 8 |

- suite: `locomo`  |  commit: `9ce21d79`  |  run: `2026-09-07T14:50:32Z`
- reader / judge model: `minimax/minimax-m3:free` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `20`  |  completed: `8`  |  partial: `True`
- raw: `results/locomo/9ce21d79/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 20`

### longmemeval

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.460 | 0.364 | 0.502 | 1.000 | - | 11 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.407 | 0.273 | 0.535 | 0.667 | - | 11 |
| ICE retrieval only (raw hits, no ContextPager) | 0.364 | 0.182 | 0.533 | 0.857 | - | 11 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.524 | 0.364 | 0.661 | 0.857 | - | 11 |
| Recency truncation (no retrieval) | 0.252 | 0.091 | 0.312 | 0.615 | - | 11 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.571 | - | 10 |

- suite: `longmemeval`  |  commit: `8144b0ac`  |  run: `2026-09-02T23:23:31Z`
- reader / judge model: `ling-3.0-flash-fin-free` via `openrouter`
- ICE substrate: `sandbox`  |  sample limit: `12`  |  completed: `11`  |  partial: `True`
- raw: `results/longmemeval/8144b0ac/` (`summary.json`, `predictions.jsonl`, `raw.log`)
- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite longmemeval --reader openrouter --limit 12`

## What the sample shows so far

- The results are **mixed by benchmark**. On LoCoMo (long multi-session chats, retrieval is the hard part) ICE's tuned pipeline leads. On LongMemEval-oracle (the relevant sessions are pre-selected, so there is little to retrieve) plain vector RAG is ahead and ICE's re-ranking / anchoring layer adds noise.
- ICE ships with an over-aggressive context-compression default (`ICE_COMPRESSION_THRESHOLD` ~0.5) that discards most retrieved evidence; setting it to ~0.1 roughly doubles ICE's LoCoMo score. That knob is the single biggest lever we found.

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
