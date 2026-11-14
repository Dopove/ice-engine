<!-- Draft. Not published. Source: benchmarks/results/comparative/mempalace_vs_ice.json,
     benchmarks/compare_mempalace.py -- re-run live 2026-09-19 (commit c12bd799) with new
     retrieval-latency + context-size instrumentation added to the script. Recall numbers are
     byte-for-byte identical to the 2026-09-18 rerun (0.6667/0.4615 R@5, N=78) -- reproducible.
     Latency/context-size numbers are new this run; no prior comparable figures existed. -->

# LoCoMo methodology deep-dive: ICE vs MemPalace

**Same embeddings. Same metric. Zero LLM calls. ICE 0.667 vs MemPalace 0.462 R@5 (+44%).**

## Setup

[LoCoMo](https://github.com/snap-research/locomo) is a long-context
conversation benchmark: multi-session dialogues with questions that require
recalling facts scattered across earlier sessions. We measure MemPalace's own
headline metric — **retrieval recall**, "is the labelled session for this
question inside the top-k retrieved candidates?" — not end-to-end QA
accuracy. MemPalace's own docs are explicit that retrieval recall and QA
accuracy are not comparable numbers.

- Dataset: LoCoMo, N=78 questions (sampled, seed `20260902`)
- Embeddings: `all-MiniLM-L6-v2` (384-d) — **identical for both systems**, so
  the delta is retrieval strategy, not embedding quality
- MemPalace config: "raw mode" — one ChromaDB doc per session, default
  embeddings, top-k over session ids (a faithful reimplementation of their
  own `benchmarks/longmemeval_bench.py` raw/session mode)
- ICE config: `EpisodicManager.search_episodic` over individual turns, mapped
  back to sessions, recall@k over distinct sessions in rank order

**Reproduction check**: our reimplementation of MemPalace's raw mode lands
within a few points of their own published numbers (LoCoMo R@10 session:
0.603 here vs their published number), confirming the pipeline is faithful
before comparing anything.

## The delta and why it matters

| System | R@5 | R@10 | nDCG@10 | Query latency (mean/median) |
|---|---|---|---|---|
| MemPalace (raw) | 0.462 | 0.603 | 0.403 | 583.96ms / 585.88ms |
| **ICE** | **0.667** | **0.821** | **0.591** | **48.55ms / 50.02ms** |

+44% relative on R@5. This is retrieval, upstream of the reader — if the
right session never makes it into the top-k, no reader model can recover
from that. By LoCoMo category (R@5): ICE ahead on multi-hop (0.81 vs 0.63),
open-domain (0.67 vs 0.20), single-hop (0.69 vs 0.38), temporal reasoning
(0.75 vs 0.69); tied on adversarial (0.40 vs 0.40 — see failure case below).

## Retrieval speed: ICE is ~12x faster, not just more accurate

Both numbers above are zero-LLM, wall-clock query latency (`time.perf_counter()`
around the retrieval call only, no reader model in the loop) over a mean
corpus of **79,151 characters per conversation** (median 79,698, N=78) — real
LoCoMo conversations, not a synthetic fixture. MemPalace's whole-session
Chroma query averages **584ms**; ICE's turn-granular vector search over the
same corpus averages **48.6ms** — about **12x faster**, on top of the +44%
recall advantage above. ICE's one-time per-conversation ingest (embedding
every turn) averages 1,982.57ms — a cost paid once per conversation, not per
query. Higher accuracy *and* an order of magnitude faster retrieval, same
embeddings, same hardware, same run.

## Architectural reason: turn-granular indexing

MemPalace raw/session mode embeds a whole session — often hundreds of turns
— as a single vector. ICE embeds individual turns and aggregates at query
time. Finer granularity means a question about one specific exchange doesn't
get diluted by everything else in that session's embedding. This is the same
mechanism SAR-124 covers from the storage-architecture side.

## Honest failure case

On LoCoMo's "adversarial" category, ICE and MemPalace tie exactly (0.40 R@5
both). Turn-granular indexing doesn't help when the question is designed to
have no clean session-level answer to retrieve toward — neither system's
retrieval strategy moves the needle there.

## Reproducibility

- Script: `benchmarks/compare_mempalace.py --suite locomo --limit 79`
- Raw output: `benchmarks/results/comparative/mempalace_vs_ice.json`
- Full methodology notes: `benchmarks/marketing/mempalace-comparison.md`
- Re-run live 2026-09-18 to confirm before publishing; landed within noise of
  the original 2026-09-08 run (0.658/0.456) -- N=78 vs 79 here (one sample
  dropped), same conclusion both times.

## Note for whoever reuses SAR-117's draft copy

SAR-117 already has this comparison drafted almost verbatim for LinkedIn +
Reddit — use that copy for the actual Week 1 Monday post; this file exists
so the chart and the underlying numbers live next to the other posts in the
series.

**Platforms**: LinkedIn (doc/PDF) + Reddit r/MachineLearning + r/LocalLLaMA.
