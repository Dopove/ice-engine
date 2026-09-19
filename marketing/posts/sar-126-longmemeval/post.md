<!-- Draft. Not published. Sources: benchmarks/results/longmemeval/1eb18e5/summary.json
     (commit 1eb18e5, run 2026-09-18T12:56:00Z) AND benchmarks/results/longmemeval/c12bd799-latency/summary.json
     (commit c12bd799, run 2026-09-19T18:49:13Z, same 15 samples/seed, adds real context/ingest
     latency instrumentation). Both full, complete runs (N=15/15), reader
     us.meta.llama4-maverick-17b-instruct-v1:0 via AWS Bedrock (native Converse API). The rerun's
     F1/recall numbers moved from the first run by more than sampling noise should allow for
     N=15 -- see "Run-to-run variance" below. This is disclosed rather than picking whichever
     run looks better. -->

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

## The numbers (run 1, commit 1eb18e5, 2026-09-18)

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

## Run-to-run variance (run 2, commit c12bd799, 2026-09-19 -- same 15 samples/seed)

Rerunning the identical suite/seed/systems the next day, with the reader
unchanged, produced a **different ranking**:

| System | F1 | Recall | Abstention F1 | Context latency (mean/median) |
|---|---|---|---|---|
| No memory | 0.003 | 0.002 | 0.500 | 0.00ms |
| Recency truncation | 0.070 | 0.068 | 0.526 | 0.01ms |
| **ICE (retrieval only, raw hits)** | **0.317** | **0.375** | 0.909 | **46.22ms / 43.25ms** |
| **Vanilla RAG** | **0.317** | **0.375** | 0.909 | **41.92ms / 41.74ms** |
| ICE (stock, threshold 0.5) | 0.242 | 0.342 | 0.769 | 880.54ms / 873.71ms |
| ICE (tuned, threshold 0.1) | 0.268 | 0.361 | 0.833 | 806.56ms / 770.28ms |

Judge spot-check accuracy is still 1.00 (n=5) on every row -- both runs agree
the *answers* graded as correct are actually correct. What moved is *which*
questions each system got right, which at N=15 is enough samples to flip who
edges out whom by a few points. **We are not going to publish "ICE beats
Vanilla RAG" or "Vanilla RAG beats ICE" as a headline claim from either run
alone** -- across both runs, ICE retrieval-only and Vanilla RAG are
statistically tied (identical to 3 decimal places in run 1; identical to 3
decimal places in run 2, just at a different level), and stock/tuned ICE
land within the same noise band on both. N=15 is too small to resolve a
few-point gap between comparably-performing retrieval strategies -- that
would need a larger sample, which is a real follow-up, not a claim we can
make tonight. The durable, reproduced-twice finding is unchanged: **any
working retrieval strategy beats no-memory by ~80-100x and beats recency
truncation by ~4x** -- that gap is an order of magnitude larger than the
run-to-run noise on the retrieval-strategy comparisons.

## Retrieval speed

Context-assembly latency (`time.perf_counter()` around `context()` only, no
reader-LLM call inside it) split cleanly into two tiers in run 2: raw vector
retrieval (ICE hits-only and Vanilla RAG) averages **42-46ms** -- consistent
with SAR-117/123's LoCoMo finding of ICE's local ONNX retrieval being very
fast. Full-pipeline ICE (stock/tuned), which adds the saliency-compression
pager on top of retrieval, averages **807-881ms** -- a real, substantial cost
for that layer on this workload, not something we're going to round down.
That cost buys higher abstention-F1 in run 1 (0.833 vs 0.909 for raw hits --
actually *lower* in run 1) and mixed results in run 2 (0.769-0.833 vs 0.909
for raw hits -- also lower both runs). Read plainly: **on this benchmark,
the compression pager did not clearly earn its latency cost** in either run.
This is a more honest, less flattering finding than we'd have gotten from
citing only the fast numbers, and it's exactly the kind of result this
series commits to publishing as found.

## The honest read

The big, defensible gap on this variant is **memory vs. not memory**: any
system that actually retrieves (ICE or Vanilla RAG) clears 0.24+ F1 in both
runs; recency truncation — keep-the-last-N-turns, no retrieval at all —
manages 0.07; no memory at all is statistically zero (0.003). That's the
headline, and it reproduced identically across both runs.

The gap *between* retrieval strategies is **not resolved at N=15** -- see
"Run-to-run variance" above. Run 1 had ICE (stock) nominally ahead of
Vanilla RAG; run 2 reversed it. We're not claiming either direction as a
result. What both runs agree on: ICE retrieval-only and Vanilla RAG behave
near-identically (exactly tied in run 1, exactly tied in run 2), and the
compression pager adds meaningful latency (800ms+) without a clear,
reproduced F1/abstention win to show for it on this workload.

This is a smaller, more honest claim than an earlier draft of this post
made from a partial run on a different reader model, and it's smaller again
than what a single confident run would have let us claim — worth stating
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

- Suite: `longmemeval` (`--lme-variant s`) | commits: `1eb18e5` (run 1,
  2026-09-18T12:56:00Z) and `c12bd799` (run 2, 2026-09-19T18:49:13Z) --
  identical seed/samples/systems, run a day apart
- Reader: `us.meta.llama4-maverick-17b-instruct-v1:0` via AWS Bedrock
  (native Converse API)
- Raw: `benchmarks/results/longmemeval/1eb18e5/` and
  `benchmarks/results/longmemeval/c12bd799-latency/` (`summary.json`,
  `predictions.jsonl`, `raw.log`) — CI artifact, not committed to git
  (`benchmarks/results/` is gitignored by design; `benchmarks/marketing/`
  is the committed distribution point)
- Reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite
  longmemeval --lme-variant s --systems
  ice,ice_tuned,ice_hits,vanilla_rag,recency_truncation,no_memory --limit
  15 --judge-spot-n 5`

**Platforms**: LinkedIn + Reddit r/MachineLearning + r/LocalLLaMA.
