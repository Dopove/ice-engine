<!-- Draft. Not published. BLOCKED on a real LongMemEval-m run.
     Previous draft of this file was built on the `s` variant (session
     pre-narrowed to a single haystack) commits 1eb18e5 / c12bd799 -- `s` is
     the easier variant (smaller haystack per question) and is being dropped
     as the headline per direction: use `m` (full multi-session haystack,
     not pre-narrowed) as the real test, and report ICE as a single line
     (tuned config only), not three ICE variants side by side.
     A `longmemeval --lme-variant m` CI run (systems: ice_tuned,vanilla_rag,
     recency_truncation,no_memory) has been triggered -- see "Status" below
     for the run to watch. No numbers below until that run lands. -->

# LongMemEval-m deep-dive: ICE vs. no-retrieval baselines

## Status: waiting on the real run

This post is blocked on a real `longmemeval --lme-variant m` result. `m` is
the harder, non-easy variant — the full multi-session haystack per question,
not `oracle`'s pre-selected session or `s`'s smaller haystack — so this is
the number worth publishing, and no earlier `s`-variant table is being
carried forward as if it were `m`.

A CI run has been triggered:
`suite=longmemeval, lme_variant=m, systems=ice_tuned,vanilla_rag,recency_truncation,no_memory`.
Once it completes with a real (`all_synthetic: false`, `n_completed > 0`)
`benchmarks/results/longmemeval/<commit>/summary.json`, this post gets:

- One ICE line (`ice_tuned` — the shipped config, not stock/retrieval-only
  variants side by side)
- F1 / Recall / Abstention F1 vs. `vanilla_rag`, `recency_truncation`,
  `no_memory`
- A single-ICE headline chart (same style as the bar chart already in this
  folder, rebuilt from the `m` numbers)

## Reproducibility

- Suite: `longmemeval` (`--lme-variant m`)
- Systems: `ice_tuned,vanilla_rag,recency_truncation,no_memory`
- Reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite
  longmemeval --lme-variant m --systems
  ice_tuned,vanilla_rag,recency_truncation,no_memory --limit 15
  --judge-spot-n 5`
- Raw (once run lands): `benchmarks/results/longmemeval/<commit>/summary.json`
  — CI artifact, not committed to git (`benchmarks/results/` is gitignored
  by design)

**Platforms**: LinkedIn + Reddit r/MachineLearning + r/LocalLLaMA (once real
numbers exist).
