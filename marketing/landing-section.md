<!-- Website 'Benchmarks' section. Draft copy. -->

## Benchmarks

ICE is measured as a memory layer: one fixed reader model, context supplied by ICE vs. baselines vs. Mem0, on public benchmarks (LoCoMo, LongMemEval). Reader is a free, reproducible model. Current numbers are a directional sample — full runs accumulate over time under the free-tier budget.

| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |
|---|---|---|---|---|---|---|
| ICE (stock config: compression threshold 0.5) | 0.097 | 0.000 | 0.098 | 0.500 | 0.000 (n=6) | 15 |
| ICE (tuned: ICE_COMPRESSION_THRESHOLD=0.1) | 0.176 | 0.000 | 0.298 | 0.333 | 0.000 (n=6) | 15 |
| ICE retrieval only (raw hits, no ContextPager) | 0.170 | 0.067 | 0.203 | 0.444 | 0.000 (n=6) | 15 |
| Vanilla RAG (same embeddings, no ICE attention layer) | 0.147 | 0.000 | 0.198 | 0.500 | 0.000 (n=6) | 15 |
| Recency truncation (no retrieval) | 0.033 | 0.000 | 0.075 | 0.250 | 0.000 (n=6) | 15 |
| No memory (question only) | 0.000 | 0.000 | 0.000 | 0.333 | 0.000 (n=6) | 15 |

_Source: `results/locomo/964857ad/summary.json` · commit `964857ad`_

[Full methodology, raw logs and reproduction steps →](../benchmarks/marketing/BENCHMARKS.md)
