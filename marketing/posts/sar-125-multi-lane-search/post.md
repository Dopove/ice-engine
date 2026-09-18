<!-- Draft. Not published. Architecture mismatch found -- see below before writing any copy. -->

# Multi-lane search architecture

**Status: blocked — the architecture this post describes doesn't match the
code as it exists today.**

I read `ice/core/episodic.py`'s `search_episodic` end to end looking for the
four lanes (Priority/recency, Keyword/BM25, Vector/HNSW, Re-rank/cross-encoder)
this post is supposed to ablate. What's actually there:

- **Phase 0**: fetches recent `role='tool'` rows for the current session — a
  fixed lookup, not a general keyword search over the query.
- **Phase 0.5**: literally commented `[DEMO HOTFIX]` — a SQL `LIKE` match on
  three hardcoded strings (`CRITICAL INSTRUCTION`, `SYSTEM FACT`,
  `CRITICAL_OVERRIDE_CODE`). Not a BM25/keyword lane.
- **Phase 1**: real vector search (`search_local_episodic`).
- **Phase 2**: federated search across enterprise peer nodes — a
  multi-node clustering feature, not a retrieval "lane" in the sense this
  post means.
- **Final step**: dedupe + sort by pre-assigned score. **No cross-encoder
  re-ranker exists anywhere in this path.**

So there's no keyword/BM25 lane and no re-ranker to ablate, no fusion
formula to document, and no "one query, four lanes" story to tell honestly
as currently written.

## Two ways forward

1. **Build it first.** If a real keyword lane + cross-encoder re-ranker is
   wanted, that's engine work in `ice/core/episodic.py`, not a benchmarking
   task — then this post's ablation table becomes possible.
2. **Rewrite the post around what's real.** The priority lane (tool
   results) + vector search + enterprise federation is a genuine, different
   architecture story — just not the one in the ticket spec.

Either way, this needs a decision before any chart or copy gets written —
publishing the planned ablation table would describe a system that isn't
built.

**Platforms**: LinkedIn + Reddit r/MachineLearning + r/LocalLLaMA + r/VibeCoding.
