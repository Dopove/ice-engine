<!-- Website 'Benchmarks' section. Draft copy. -->

## Benchmarks

ICE is measured as a memory layer: one fixed reader model, context supplied by ICE vs. baselines vs. Mem0, on public benchmarks (LoCoMo, LongMemEval). Reader is a free, reproducible model. Current numbers are a directional sample — full runs accumulate over time under the free-tier budget.

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.094 | 0.000 | 0.125 | 0.286 | - | 8 |
| ICE retrieval only (raw hits, no ContextPager) | 0.125 | 0.125 | 0.125 | 0.400 | - | 8 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.125 | 0.125 | 0.125 | 0.400 | - | 8 |
| Recency truncation (no retrieval) | 0.000 | 0.000 | 0.000 | 0.250 | - | 8 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.222 | - | 8 |

_Source: `results/locomo/0fa152ea/summary.json` · commit `0fa152ea`_

[Full methodology, raw logs and reproduction steps →](../benchmarks/marketing/BENCHMARKS.md)
