<!-- Website 'Benchmarks' section. Draft copy. -->

## Benchmarks

ICE is measured as a memory layer: one fixed reader model, context supplied by ICE vs. baselines vs. Mem0, on public benchmarks (LoCoMo, LongMemEval). Reader is a free, reproducible model. Current numbers are a directional sample — full runs accumulate over time under the free-tier budget.

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.234 | 0.067 | 0.225 | 0.750 | 1.000 (n=5) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.234 | 0.067 | 0.225 | 0.750 | 1.000 (n=5) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.234 | 0.067 | 0.225 | 0.667 | 1.000 (n=5) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.234 | 0.067 | 0.225 | 0.667 | 1.000 (n=5) | 15 |
| Recency truncation (no retrieval) | 0.067 | 0.000 | 0.067 | 0.429 | 1.000 (n=5) | 15 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.333 | 1.000 (n=5) | 15 |

_Source: `results/locomo/b6d80a5/summary.json` · commit `b6d80a5`_

[Full methodology, raw logs and reproduction steps →](../benchmarks/marketing/BENCHMARKS.md)
