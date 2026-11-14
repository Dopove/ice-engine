<!-- Draft. Not published. Rewritten around the actual architecture in
     ice/core/episodic.py -- the ticket's four-lane (Priority/Keyword/Vector/
     Re-rank) design doesn't exist in code; see the git history on this file
     for the original audit. This version describes what's real. -->

# Search architecture: what actually runs on every query

**No fabricated four-lane ablation table here -- this is what `search_episodic` actually does, read straight from the source.**

## What's real

Every query runs through, in order:

1. **Tool-result priority fetch** -- the 5 most recent `role='tool'` rows for
   the current session, always included, always scored 1.0 (max priority).
   This isn't a general keyword search; it's a fixed recency query scoped to
   one message type.
2. **Critical-instruction fast path** -- a `LIKE` match against a small set
   of hardcoded markers (`CRITICAL INSTRUCTION`, `SYSTEM FACT`,
   `CRITICAL_OVERRIDE_CODE`). It's in the code as `[DEMO HOTFIX]`, and that's
   an honest description of what it is: a targeted patch for a specific
   failure mode, not a general-purpose keyword lane.
3. **Vector search** (`search_local_episodic`) -- the actual semantic
   retrieval step, and the one this benchmark series' real numbers
   (SAR-117/123, SAR-126) measure.
4. **Enterprise federation** -- for multi-node deployments, the same query
   fans out to peer nodes and merges results. A clustering feature, not a
   ranking lane.
5. **Dedupe + sort by score.** No cross-encoder re-ranker exists anywhere in
   this path.

## Why this framing is fine

The load-bearing claim in this whole series isn't "four lanes beat one" --
it's "turn-granular vector retrieval beats session-level retrieval"
(SAR-117/123: +44% R@5) and "any real memory beats none" (SAR-126: up to
+53% F1 on LongMemEval-s). Both of those are real, measured, and don't
depend on a keyword lane or re-ranker existing. The priority fetch and the
critical-instruction fast path are real, useful, narrower mechanisms --
they're just not "four lanes with a fusion formula," and this post
shouldn't claim they are.

## What would need to be true to write the originally planned post

A genuine keyword/BM25 lane over arbitrary queries (not hardcoded markers),
and a cross-encoder re-ranking step, would both need to be built into
`ice/core/episodic.py` before an ablation table comparing lane combinations
means anything. That's engine work, tracked separately from this
benchmarking series.

**Platforms**: LinkedIn + Reddit r/MachineLearning + r/LocalLLaMA + r/VibeCoding.
