<!-- Website 'Benchmarks' section. Draft copy. -->

## Benchmarks

ICE is measured as a memory layer: one fixed reader model, context supplied by ICE vs. baselines vs. Mem0, on public benchmarks (LoCoMo, LongMemEval). Reader is a free, reproducible model. Current numbers are a directional sample — full runs accumulate over time under the free-tier budget.

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.157 | 0.111 | 0.222 | 0.750 | 1.000 (n=6) | 9 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.141 | 0.111 | 0.222 | 0.600 | 1.000 (n=6) | 9 |
| ICE retrieval only (raw hits, no ContextPager) | 0.190 | 0.111 | 0.222 | 0.667 | 1.000 (n=6) | 9 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.190 | 0.111 | 0.222 | 0.667 | 1.000 (n=6) | 9 |
| Recency truncation (no retrieval) | 0.067 | 0.000 | 0.056 | 0.545 | 1.000 (n=6) | 9 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.545 | 1.000 (n=6) | 8 |

_Source: `results/locomo/9ce21d79/summary.json` · commit `9ce21d79`_

[Full methodology, raw logs and reproduction steps →](../benchmarks/marketing/BENCHMARKS.md)
