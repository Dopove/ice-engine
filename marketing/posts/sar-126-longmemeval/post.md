<!-- Draft. Not published. Source: benchmarks/results/longmemeval/1eb18e5/summary.json,
     commit 1eb18e5, run 2026-09-18T12:56:00Z. Full, complete run (N=15/15, not partial),
     reader us.meta.llama4-maverick-17b-instruct-v1:0 via AWS Bedrock (native Converse API)
     -- same reader model as every other suite in this series, unlike the earlier draft of
     this post which mixed in a different reader (cx/gpt-5.6-luna-medium via omniroute). -->

# LongMemEval deep-dive: memory beats no-memory by 87x — the retrieval strategies are closer than we expected

**On the harder `s` variant (no pre-selected session, real retrieval over the
full haystack): any working retrieval strategy — ICE or plain vector RAG —
beats naive recency truncation by ~4x F1 and beats no memory at all by ~87x.
The gap *between* retrieval strategies is much smaller than that.**

## Why `s`, not `oracle`

LongMemEval-oracle pre-selects the relevant session for each question — it's
the easy variant, and it masks retrieval differences (every system gets
handed the right context, so there's nothing for a retrieval strategy to
prove). `s` is the harder, originally-intended variant: no pre-selection,
real retrieval over the full haystack pool. This is what "128k context" in
the original hook refers to. All numbers below are `s`.

## The numbers

| System | F1 | Recall | Abstention F1 |
|---|---|---|---|
| No memory | 0.003 | 0.002 | 0.500 |
| Recency truncation (no retrieval) | 0.070 | 0.068 | 0.526 |
| ICE (retrieval only, raw hits) | 0.272 | 0.327 | 0.909 |
| Vanilla RAG (same embeddings, no ICE layer) | 0.272 | 0.327 | 0.909 |
| **ICE (stock, threshold 0.5)** | **0.277** | **0.368** | 0.833 |
| **ICE (tuned, threshold 0.1)** | **0.285** | 0.289 | 0.833 |

N=15/15 (complete, not partial), judge spot-check accuracy 1.00 (n=5) on
every row.

## The honest read

The big, defensible gap on this variant is **memory vs. not memory**: any
system that actually retrieves (ICE or Vanilla RAG) clears 0.27+ F1; recency
truncation — keep-the-last-N-turns, no retrieval at all — manages 0.07; no
memory at all is statistically zero (0.003). That's the headline.

The gap *between* retrieval strategies is real but modest here: ICE (stock)
edges Vanilla RAG by +12.7% relative on recall (0.368 vs 0.327) but the F1
gap is within a couple points either way, and **ICE retrieval-only ties
Vanilla RAG exactly** (0.272 F1, 0.327 recall, both to three decimal places)
— on this sample, stripping ICE down to raw retrieval hits with no
compression pager makes it behave identically to plain vector RAG, which is
itself informative: ICE's edge over RAG on this variant comes from the
pager/compression layer (compare stock vs retrieval-only), not from the
underlying retrieval call. Tuning the compression threshold (0.5 → 0.1)
trades recall for F1 (0.289 recall / 0.285 F1 vs 0.368 recall / 0.277 F1) —
a real tradeoff, not a strict win.

This is a smaller, more honest claim than an earlier draft of this post
made from a partial run on a different reader model — worth stating
plainly rather than quietly keeping the bigger number.

## Mem0 and LangMem: deferred, not skipped

Mem0 and LangMem rows are **not included** in this result. Not a budget or
rate-limit issue this time — Bedrock's Llama 4 Converse API access is fully
reliable and inexpensive (this whole run cost well under $1). The real
blocker: both libraries' own extraction LLM calls have to go through
Bedrock's separate OpenAI-compatible endpoint (Llama 4 isn't reachable
there), and on that path Mem0's internal extraction pipeline hits a real
bug in its own code — a later processing stage (deciding ADD/UPDATE per
extracted fact) crashes with `AttributeError: 'str' object has no attribute
'get'` against the output shape of every Bedrock-native model we tried
(`nvidia.nemotron-super-3-120b`, after first ruling out `openai.gpt-oss-20b`
for a separate reasoning-wrapper incompatibility). This crashes mid-run
rather than failing gracefully, so rather than block tonight's post on
debugging a third-party library's internals, we're shipping the complete,
real ICE-vs-baselines result now and will add Mem0/LangMem in a follow-up
once that's fixed.

## Reproducibility

- Suite: `longmemeval` (`--lme-variant s`) | commit: `1eb18e5` | run:
  `2026-09-18T12:56:00Z`
- Reader: `us.meta.llama4-maverick-17b-instruct-v1:0` via AWS Bedrock
  (native Converse API)
- Raw: `benchmarks/results/longmemeval/1eb18e5/` (`summary.json`,
  `predictions.jsonl`, `raw.log`) — CI artifact, not committed to git
  (`benchmarks/results/` is gitignored by design; `benchmarks/marketing/`
  is the committed distribution point)
- Reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite
  longmemeval --lme-variant s --systems
  ice,ice_tuned,ice_hits,vanilla_rag,recency_truncation,no_memory --limit
  15 --judge-spot-n 5`

**Platforms**: LinkedIn + Reddit r/MachineLearning + r/LocalLLaMA.
