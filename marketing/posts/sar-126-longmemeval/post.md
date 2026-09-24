<!-- Draft. Not published. BLOCKED on a real LongMemEval-m run.
     Previous draft of this file was built on the `s` variant (session
     pre-narrowed to a single haystack) commits 1eb18e5 / c12bd799 -- `s` is
     the easier variant (smaller haystack per question) and is being dropped
     as the headline per direction: use `m` (full multi-session haystack,
     not pre-narrowed) as the real test, and report ICE as a single line
     (tuned config only), not three ICE variants side by side.
     No run has actually happened yet -- see "Status" below for why, and
     what has to be true before this post gets real numbers. -->

# LongMemEval-m deep-dive: ICE vs. no-retrieval baselines

## Status: waiting on the real run

This post is blocked on a real `longmemeval --lme-variant m` result. `m` is
the harder, non-easy variant — the full multi-session haystack per question,
not `oracle`'s pre-selected session or `s`'s smaller haystack — so this is
the number worth publishing, and no earlier `s`-variant table is being
carried forward as if it were `m`.

**No run is live yet.** `--lme-variant` was wired into the CI
`workflow_dispatch` inputs (it was previously hardcoded to `s`, and
`longmemeval_m.json` wasn't even fetched) and the dataset-fetch step now
pulls `longmemeval_m` alongside `_s`/`_oracle`. But that workflow file
(`.github/workflows/benchmarks.yml`) is not currently wired into this
repo's live GitLab pipeline — `.gitlab-ci.yml` only defines lint/test/
security stages today; its own comment says the benchmark pipeline was
removed and would need to be re-added. A prior benchmark pipeline existed
in `.gitlab-ci.yml` history (commit `c7978468`) and was deliberately
removed (`1668349c`, "Remove dead GitLab CI config"). Needs a decision:
re-add a `benchmark:full` stage to `.gitlab-ci.yml`, or run
`run_benchmarks.py` locally with a real reader key — either way, real
infra/cost, so not doing it without a go-ahead.

Once a real run lands (`all_synthetic: false`, `n_completed > 0` in
`benchmarks/results/longmemeval/<commit>/summary.json`), this post gets:

- One ICE line (`ice_tuned` — the shipped config, not stock/retrieval-only
  variants side by side)
- F1 / Recall / Abstention F1 vs. `vanilla_rag`, `recency_truncation`,
  `no_memory`
- A single-ICE headline chart (same style as the bar chart already used in
  this folder, rebuilt from the `m` numbers)

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
