<!-- Website 'Benchmarks' section. Draft copy. -->

## Benchmarks

ICE is measured as a memory layer: one fixed reader model, context supplied by ICE vs. baselines vs. Mem0, on public benchmarks (LoCoMo, LongMemEval). Reader is a free, reproducible model. Current numbers are a directional sample — full runs accumulate over time under the free-tier budget.

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.125 | 0.000 | 0.083 | - | - | 4 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.250 | 0.250 | 0.250 | - | - | 4 |
| ICE retrieval only (raw hits, no ContextPager) | 0.250 | 0.250 | 0.250 | - | - | 4 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.125 | 0.000 | 0.083 | - | - | 4 |
| Recency truncation (no retrieval) | 0.000 | 0.000 | 0.000 | - | - | 4 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | - | - | 4 |

_Source: `results/locomo/c31fdb0/summary.json` · commit `c31fdb0`_

[Full methodology, raw logs and reproduction steps →](../benchmarks/marketing/BENCHMARKS.md)
