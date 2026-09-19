<!-- Draft. Not published. Opinion piece -- no benchmark tool, per its own spec. -->

# RAG ≠ Memory

**"Every agent framework calls retrieval 'memory.' It's not."**

No benchmark chart for this one — it's a technical-opinion post per its own
spec, not chart-driven. It can lean on real, already-measured evidence
instead of fresh numbers:

- **RAG = stateless lookup.** Same query in, same retrieval out, no notion
  of what's already been established in the conversation.
- **Memory = stateful evolution.** ICE's four memory types: episodic
  (what happened), semantic (what's true), procedural (how to do things),
  working (what's relevant right now).
- **Supporting evidence, not fresh data**: SAR-117/123's real LoCoMo result
  (ICE 0.667 vs MemPalace 0.462 R@5) as the proof point that granularity and
  retrieval strategy matter even within "pure retrieval" systems — and
  SAR-128's LongMemEval-s result as the honest counter-argument: ICE
  stripped down to raw retrieval hits ties plain Vanilla RAG exactly (0.272
  F1 both); the edge ICE has over RAG there comes from what sits on top of
  retrieval (the compression/pager layer), not from retrieval sophistication
  itself. Citing a real weakness in your own argument is the credible move
  here.

## Reproducibility

No new run needed — this post only cites already-published numbers from
SAR-117/123 and SAR-128. Finalize those two first.

**Platforms**: (not specified in the ticket — confirm before scheduling.)
