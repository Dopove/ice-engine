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
  (ICE 0.658 vs MemPalace 0.456 R@5) as the proof point that granularity and
  retrieval strategy matter even within "pure retrieval" systems — and
  SAR-128's single-turn convergence result as the honest counter-argument:
  when the task really is just lookup, memory sophistication buys nothing.
  Citing a real weakness in your own argument is the credible move here.

## Reproducibility

No new run needed — this post only cites already-published numbers from
SAR-117/123 and SAR-128. Finalize those two first.

**Platforms**: (not specified in the ticket — confirm before scheduling.)
