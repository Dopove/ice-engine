<!-- Draft. Not published. Sources: benchmarks/results/comparative/mempalace_vs_ice.json (LoCoMo,
     re-verified live 2026-09-19, N=78, adds retrieval-latency + context-size instrumentation),
     benchmarks/results/longmemeval/1eb18e5/ and .../c12bd799-latency/ (LongMemEval-s, N=15/15,
     two full runs a day apart, same seed -- see SAR-126 for the run-to-run variance disclosure).
     Both suites use the same reader, us.meta.llama4-maverick-17b-instruct-v1:0 via AWS Bedrock --
     an earlier draft of this post mixed in a different reader model for a Mem0/LangMem
     oracle-variant row; that row is removed here rather than published inconsistent with the
     rest of the series. -->

# ICE vs MemPalace and baselines — head-to-head, one consistent reader

**LoCoMo: ICE beats MemPalace +44% on retrieval recall, zero LLM calls
either side. LongMemEval-s: any real retrieval strategy — ICE or plain
vector RAG — beats no-memory by ~87x; the retrieval strategies themselves
land within a few points of each other.**

## Head-to-head table

| Benchmark | Metric | No memory | Recency trunc. | Vanilla RAG | ICE (retrieval only) | ICE (stock) | ICE (tuned) | MemPalace |
|---|---|---|---|---|---|---|---|---|
| LoCoMo (N=78) | R@5 | — | — | — | — | **0.667** | — | 0.462 |
| LoCoMo (N=78) | Query latency (mean) | — | — | — | — | **48.6ms** | — | 584.0ms |
| LongMemEval-s (N=15, run 1) | QA F1 | 0.003 | 0.070 | 0.272 | 0.272 | 0.277 | 0.285 | — |
| LongMemEval-s (N=15, run 2) | QA F1 | 0.003 | 0.070 | 0.317 | 0.317 | 0.242 | 0.268 | — |
| LongMemEval-s (N=15, run 2) | Context latency (mean) | 0.0ms | 0.01ms | 41.9ms | 46.2ms | 880.5ms | 806.6ms | — |

(MemPalace is measured on retrieval recall only, per its own headline
metric and SAR-117/123's methodology — it isn't run through the QA-F1
harness. LoCoMo isn't scored on QA-F1 in this comparison; it's
retrieval-only by design. LongMemEval-s F1 is shown for **both** runs
deliberately — see SAR-126's "Run-to-run variance" section: the
ICE-vs-Vanilla-RAG ordering flips between runs at N=15 and neither is
published alone as a winner.)

## The honest read: LoCoMo is decisive, LongMemEval-s is not (yet)

On LoCoMo, ICE's turn-granular indexing gives it a real, sizeable, and
**reproduced** edge over MemPalace's session-level embeddings: +44% relative
R@5, plus roughly **12x faster retrieval** (48.6ms vs 584.0ms mean query
latency, both zero-LLM, same embeddings, same hardware) — see SAR-117/123
for the category breakdown and full latency numbers.

On LongMemEval-s, at N=15 the retrieval-strategy comparison is **not
resolved**: ICE retrieval-only ties Vanilla RAG exactly in both runs, and
stock/tuned ICE land ahead of Vanilla RAG in run 1 but behind it in run 2.
We're publishing both runs rather than the one that flatters ICE. What is
reproduced across both runs: any working retrieval strategy beats recency
truncation by ~4-5x and beats no-memory by ~80-100x — that gap dwarfs the
run-to-run noise on the retrieval-strategy comparisons. On latency, raw
vector retrieval is fast regardless of system (42-46ms), but ICE's
compression pager (stock/tuned) adds 800ms+ on this workload without a
clearly reproduced quality win to justify it. See SAR-126 for the full
breakdown.

## Where MemPalace's weakness actually is

MemPalace's session-level embedding is simpler and cheaper to run, but that
same simplicity is why it falls behind on LoCoMo's multi-hop and
open-domain categories — see SAR-117/123 for the per-category numbers.

## What's not in this table

**Mem0 and LangMem.** Not a budget or reader-reliability issue — Bedrock's
Llama 4 access is fully reliable and this whole comparison cost well under
$1. Both libraries' own extraction LLM calls have to go through Bedrock's
separate OpenAI-compatible endpoint (Llama 4 isn't reachable there), and on
every Bedrock-native model tried there, Mem0's internal extraction pipeline
hits a real bug in its own code (`AttributeError: 'str' object has no
attribute 'get'` at a later ADD/UPDATE-decision stage, past the raw LLM
response). This is documented in SAR-126. A fix has been written and
smoke-tested standalone against live Bedrock (both the shape bug and a
second, separately-discovered issue where a stale `OPENROUTER_API_KEY` in
the environment silently hijacks mem0's provider routing) — not yet run
through the actual harness/CI end-to-end, so still not publishing a row
from it. Follow-up once that full run completes.

Real retrieval-latency numbers per system are now included above (LoCoMo
and LongMemEval-s context/ingest latency, wall-clock, zero-LLM). Storage
write-throughput and infra cost overhead are still not something this
harness measures — that needs the Postgres infra SAR-124/127 are scoped
around (see those posts' stubs).

## Reproducibility

- LoCoMo: `benchmarks/results/comparative/mempalace_vs_ice.json` (re-run
  live 2026-09-18) — `benchmarks/compare_mempalace.py --suite locomo --limit 79`
- LongMemEval-s: `benchmarks/results/longmemeval/1eb18e5/summary.json` (run 1) and
  `benchmarks/results/longmemeval/c12bd799-latency/summary.json` (run 2, adds latency) —
  `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite longmemeval
  --lme-variant s --systems
  ice,ice_tuned,ice_hits,vanilla_rag,recency_truncation,no_memory --limit
  15 --judge-spot-n 5`

**Platforms**: LinkedIn + Reddit r/MachineLearning + r/LocalLLaMA.
