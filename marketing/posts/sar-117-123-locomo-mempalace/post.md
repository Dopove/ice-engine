<!-- Draft. Not published. Source: benchmarks/results/comparative/mempalace_vs_ice_locomo.json, benchmarks/compare_mempalace.py -->

# LoCoMo methodology deep-dive: ICE vs MemPalace

**Same embeddings. Same metric. Zero LLM calls. ICE 0.658 vs MemPalace 0.456 R@5 (+44%).**

## Setup

[LoCoMo](https://github.com/snap-research/locomo) is a long-context
conversation benchmark: multi-session dialogues with questions that require
recalling facts scattered across earlier sessions. We measure MemPalace's own
headline metric — **retrieval recall**, "is the labelled session for this
question inside the top-k retrieved candidates?" — not end-to-end QA
accuracy. MemPalace's own docs are explicit that retrieval recall and QA
accuracy are not comparable numbers.

- Dataset: LoCoMo, N=79 questions (sampled, seed `20260902`)
- Embeddings: `all-MiniLM-L6-v2` (384-d) — **identical for both systems**, so
  the delta is retrieval strategy, not embedding quality
- MemPalace config: "raw mode" — one ChromaDB doc per session, default
  embeddings, top-k over session ids (a faithful reimplementation of their
  own `benchmarks/longmemeval_bench.py` raw/session mode)
- ICE config: `EpisodicManager.search_episodic` over individual turns, mapped
  back to sessions, recall@k over distinct sessions in rank order

**Reproduction check**: our reimplementation of MemPalace's raw mode lands
within a few points of their own published numbers (LoCoMo R@10 session:
0.595 here vs 0.603 published), confirming the pipeline is faithful before
comparing anything.

## The delta and why it matters

| System | R@5 | R@10 | nDCG@10 |
|---|---|---|---|
| MemPalace (raw) | 0.456 | 0.595 | 0.398 |
| **ICE** | **0.658** | **0.810** | **0.583** |

+44% relative on R@5. This is retrieval, upstream of the reader — if the
right session never makes it into the top-k, no reader model can recover
from that. By LoCoMo category (R@5): ICE ahead on multi-hop (0.81 vs 0.62),
open-domain (0.67 vs 0.20), single-hop (0.69 vs 0.38); tied on adversarial
(0.38 vs 0.38 — see failure case below).

## Architectural reason: turn-granular indexing

MemPalace raw/session mode embeds a whole session — often hundreds of turns
— as a single vector. ICE embeds individual turns and aggregates at query
time. Finer granularity means a question about one specific exchange doesn't
get diluted by everything else in that session's embedding. This is the same
mechanism SAR-124 covers from the storage-architecture side.

## Honest failure case

On LoCoMo's "adversarial" category, ICE and MemPalace tie exactly (0.375 R@5
both). Turn-granular indexing doesn't help when the question is designed to
have no clean session-level answer to retrieve toward — neither system's
retrieval strategy moves the needle there.

## Reproducibility

- Script: `benchmarks/compare_mempalace.py`
- Raw output: `benchmarks/results/comparative/mempalace_vs_ice_locomo.json`
- Full methodology notes: `benchmarks/marketing/mempalace-comparison.md`

## Note for whoever reuses SAR-117's draft copy

SAR-117 already has this comparison drafted almost verbatim for LinkedIn +
Reddit — use that copy for the actual Week 1 Monday post; this file exists
so the chart and the underlying numbers live next to the other posts in the
series.

**Platforms**: LinkedIn (doc/PDF) + Reddit r/MachineLearning + r/LocalLLaMA.
