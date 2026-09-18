<!-- Draft. Not published. Sources: benchmarks/results/longmemeval/a422f77/summary.json (oracle),
     local run 2026-09-18 (s-variant, N=15, reader cx/gpt-5.6-luna-medium) -->

# LongMemEval deep-dive: why the easy variant lied to us

**Real find: on the harder, correct LongMemEval-s variant, stock ICE beats Vanilla RAG by +53% F1 (0.218 vs 0.142) — no tuning needed.**

## Two charts, because the story has two parts

### 1. Oracle variant — complete, all four systems (`chart-oracle-variant.png`)

LongMemEval-oracle pre-selects the relevant session for each question. It's
the easy version — and on it, ICE ties Vanilla RAG exactly (both 0.458 F1;
they retrieve byte-identical context once there's token headroom for the
pager to pass through). The real, honest signal on this variant is memory
vs. no memory, not ICE vs. RAG:

| System | F1 |
|---|---|
| No memory | 0.01 |
| LangMem | 0.32 |
| Mem0 | 0.43 |
| ICE | 0.46 |

### 2. `s` variant — in progress, ICE-only so far (`chart-s-variant-partial.png`)

LongMemEval-s is the harder, originally-intended variant: no pre-selected
session, real retrieval over the full haystack pool (this is what "128k
context" in the original hook refers to). Here the numbers actually
differentiate:

| System | F1 |
|---|---|
| No memory | 0.003 |
| Vanilla RAG | 0.142 |
| **ICE (stock)** | **0.218** |

Stock ICE — no compression tuning, the out-of-the-box config — beats
Vanilla RAG by +53% relative. This is the honest, harder-variant version of
the story the original hook ("+5% coherence") was reaching for, and it's a
bigger, more defensible number than the placeholder.

**Mem0 and LangMem rows on `s` are not in yet.** The reader
(`cx/gpt-5.6-luna-medium`, via a local omniroute proxy) hit an 11-day quota
wall mid-run on that pass. Re-running once the Bedrock key is live (see cost
estimate already worked out: under $0.20 for the full run on Nova Micro/Lite).

## The delta and why it matters

"+5% coherence" was never a real metric this harness computes — we measure
F1/EM/recall on QA, not consistency/factual-recall/reasoning-chain
sub-scores. The real, measured claim is F1 on QA, and on the variant that
actually stresses retrieval, it's a +53% relative gap, not +5%.

## Architectural reason

On oracle, every system gets handed the right session, so ICE's retrieval
strategy has nothing to prove. On `s`, ICE has to actually find the right
context in a much larger pool — this is where its retrieval (not a
compression trick; `ice_tuned`, at threshold=0.1, actually scores *lower*
than stock at threshold=0.5 on this variant) earns its gap over plain vector
similarity.

## Honest failure case

Single-turn factual lookups (LongMemEval's `single-session-*` categories) are
where ICE, Vanilla RAG, Mem0, and LangMem all converge — see SAR-128 for the
category breakdown. Memory systems differentiate on multi-session and
temporal-reasoning questions, not simple single-turn QA.

## Reproducibility

- Oracle: `benchmarks/results/longmemeval/a422f77/summary.json`
- `s`-variant (partial, complete on core systems): re-run locally this
  session, not yet committed as a tracked result (`benchmarks/results/` is
  gitignored by design — CI artifacts are the distribution mechanism)
- Reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite longmemeval --lme-variant s --systems ice,vanilla_rag,no_memory,mem0,langmem --limit 15 --judge-spot-n 0`

**Platforms**: LinkedIn + Reddit r/MachineLearning + r/LocalLLaMA.
