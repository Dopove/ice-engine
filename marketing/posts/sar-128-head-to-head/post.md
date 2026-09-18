<!-- Draft. Not published. Sources: benchmarks/results/comparative/mempalace_vs_ice_locomo.json,
     benchmarks/results/longmemeval/a422f77/predictions.jsonl, /tmp/full_mlm/predictions.jsonl (mem0/langmem, oracle) -->

# ICE vs MemPalace, Mem0, LangMem — head to head, including where ICE loses ground

**ICE +44% retrieval recall on LoCoMo — but every memory system, ICE included, converges on single-turn factual QA.**

## Head-to-head table

| Benchmark | Metric | No memory | Recency trunc. | LangMem | Mem0 | MemPalace | ICE |
|---|---|---|---|---|---|---|---|
| LoCoMo (N=79) | R@5 | — | — | — | — | 0.456 | **0.658** |
| LongMemEval-oracle (N=15) | QA F1 | 0.01 | — | 0.32 | 0.43 | — | **0.46** |
| Single-turn QA slice (N=6) | QA F1 | 0.02 | 0.26 | 0.31 | **0.52** | — | **0.52** |

(MemPalace is only measured on retrieval recall, per its own headline metric
and SAR-117/123's methodology — not run through the QA harness. LoCoMo isn't
run through the QA-F1 harness in this comparison — it's retrieval-only by
design, per MemPalace's own metric.)

## The honest loss: single-turn QA is a tie

Filter LongMemEval down to its `single-session-user`/`single-session-assistant`
categories — questions answerable from a single exchange, no cross-session
reasoning required — and **Mem0 and ICE score identically (0.5175 F1,
N=6)**. LangMem trails a bit (0.31); recency-truncation and no-memory both
collapse, as expected, since even a single-turn answer needs *some* context.

This matches what SAR-125/126 both predicted as the honest failure case:
sophisticated retrieval (turn-granular indexing, multi-lane fusion, whatever
the marketing architecture is) buys nothing when the answer is directly in
front of the reader already. The gap only opens up on multi-session and
cross-turn questions — see SAR-126's full breakdown.

## Where each system's weaknesses actually are

- **MemPalace**: simpler (session-level embedding, no turn granularity), so
  it's cheaper to run and has less storage/indexing overhead — but that same
  simplicity is exactly why it falls behind on LoCoMo's multi-hop and
  open-domain categories (0.62/0.20 vs ICE's 0.81/0.67 R@5).
- **LangMem**: consistently the weakest of the three memory-backed rows in
  every benchmark we've run it on so far (oracle QA F1 0.32 vs Mem0's 0.43
  and ICE's 0.46; single-turn 0.31 vs 0.52).
- **Mem0**: the strongest of the "commonly used" external stacks in every
  comparison so far, close enough to ICE that the real differentiator is the
  harder `s`-variant LongMemEval run (SAR-126), not yet complete for Mem0.
- **ICE**: ahead everywhere memory sophistication matters, tied everywhere it
  doesn't. No claim here that ICE wins across the board — it doesn't need to.

## What's not in this table yet

Mem0/LangMem on LongMemEval-`s` (the harder variant) — blocked on the same
reader-quota issue as SAR-126, pending the Bedrock switch. Real retrieval
latency and storage-overhead numbers per system — not part of this harness,
would need the infra SAR-124/127 are scoped around (see those posts' stubs).

## Reproducibility

- LoCoMo: `benchmarks/results/comparative/mempalace_vs_ice_locomo.json`
- LongMemEval-oracle: `benchmarks/results/longmemeval/a422f77/predictions.jsonl`
- Single-turn slice: filter either predictions file for
  `category in {single-session-user, single-session-assistant}`

**Platforms**: LinkedIn + Reddit r/MachineLearning + r/LocalLLaMA.
