<!-- Draft. Not published. Sources: benchmarks/results/comparative/mempalace_vs_ice.json (LoCoMo,
     re-verified live 2026-09-18, N=78), benchmarks/results/longmemeval/1eb18e5/summary.json
     (LongMemEval-s, N=15/15, complete). Both use the same reader,
     us.meta.llama4-maverick-17b-instruct-v1:0 via AWS Bedrock -- an earlier draft of this post
     mixed in a different reader model for a Mem0/LangMem oracle-variant row; that row is
     removed here rather than published inconsistent with the rest of the series. -->

# ICE vs MemPalace and baselines — head-to-head, one consistent reader

**LoCoMo: ICE beats MemPalace +44% on retrieval recall, zero LLM calls
either side. LongMemEval-s: any real retrieval strategy — ICE or plain
vector RAG — beats no-memory by ~87x; the retrieval strategies themselves
land within a few points of each other.**

## Head-to-head table

| Benchmark | Metric | No memory | Recency trunc. | Vanilla RAG | ICE (retrieval only) | ICE (stock) | ICE (tuned) | MemPalace |
|---|---|---|---|---|---|---|---|---|
| LoCoMo (N=78) | R@5 | — | — | — | — | **0.667** | — | 0.462 |
| LongMemEval-s (N=15) | QA F1 | 0.003 | 0.070 | 0.272 | 0.272 | **0.277** | **0.285** | — |

(MemPalace is measured on retrieval recall only, per its own headline
metric and SAR-117/123's methodology — it isn't run through the QA-F1
harness. LoCoMo isn't scored on QA-F1 in this comparison; it's
retrieval-only by design.)

## The honest read: retrieval strategies converge, memory-vs-none doesn't

On LoCoMo, ICE's turn-granular indexing gives it a real, sizeable edge over
MemPalace's session-level embeddings (+44% relative R@5) — see SAR-117/123
for the category breakdown.

On LongMemEval-s, the story is different: **ICE stripped down to raw
retrieval hits (no compression pager) ties Vanilla RAG exactly** — 0.272 F1,
0.327 recall, both to three decimal places. ICE's edge over plain RAG here
comes from the pager/compression layer on top of retrieval, not from a
smarter retrieval call itself, and that edge is modest (0.277–0.285 vs
0.272, a few points either way) compared to the gap between *any* working
retrieval strategy and recency-truncation (0.070) or no memory at all
(0.003). See SAR-126 for the full breakdown and the tuning tradeoff between
ICE's stock and tuned compression thresholds.

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
response). This is documented in SAR-126 and not yet fixed; we're not
publishing a head-to-head row built on a different, older reader model just
to fill the cell. Follow-up once the bug's fixed upstream or worked around.

Real retrieval-latency and storage-overhead numbers per system are also not
part of this harness — that needs the infra SAR-124/127 are scoped around
(see those posts' stubs).

## Reproducibility

- LoCoMo: `benchmarks/results/comparative/mempalace_vs_ice.json` (re-run
  live 2026-09-18) — `benchmarks/compare_mempalace.py --suite locomo --limit 79`
- LongMemEval-s: `benchmarks/results/longmemeval/1eb18e5/summary.json` —
  `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite longmemeval
  --lme-variant s --systems
  ice,ice_tuned,ice_hits,vanilla_rag,recency_truncation,no_memory --limit
  15 --judge-spot-n 5`

**Platforms**: LinkedIn + Reddit r/MachineLearning + r/LocalLLaMA.
