# ICE memory benchmarks

Reproducible, third-party memory benchmarks for **ICE EP** (the `ice/` engine),
run through the repo's Gitea Actions CI. The point is public trust: every number
traces to a committed `summary.json` with the raw predictions and logs beside it.

## What this measures (and what it does not)

ICE EP is a **memory / retrieval layer**. Its `/v1/chat/completions` returns an
*assembled context*, not an answer. So the harness is:

```
<system> ingests a conversation  ->  <system>.context(question)  ->  frozen reader model answers  ->  score
```

The reader model is identical for every system — that is the apples-to-apples
control. Rows compare **ICE + reader** vs **baseline + the same reader**, never
"ICE vs GPT-4".

Systems:

| name | what it feeds the reader |
|---|---|
| `ice` | real EP engine: episodic pgvector/ONNX retrieval + `ContextPager` U-Shape reorder + saliency compression + anchor injection |
| `vanilla_rag` | same ONNX embeddings + same top-k, ICE's attention layer **off** (isolates what that layer adds) |
| `recency_truncation` | no retrieval; most recent turns that fit a budget |
| `no_memory` | question only (floor) |
| `mem0` | external lib [Mem0](https://github.com/mem0ai/mem0); its own extraction LLM runs on **local Ollama**, never the benchmark's API budget |

Benchmarks: **LoCoMo**, **LongMemEval** (incl. the abstention subset), and
**BEAM** / **AMA-Bench** when their datasets are public — until then those record
a clean `skipped.json`, never a fabricated number.

## Honesty rules baked into the harness

- No hand-written numbers. Marketing text is generated from `summary.json` by
  `scripts/render_marketing.py`.
- Small sample. The OpenRouter free tier allows ~50 calls/day, so runs are capped
  (`--limit`) and **labelled `N≈…, directional`**. A persistent cache
  (`results/cache/`) means daily CI runs accumulate the sample instead of
  re-spending calls.
- Losses are reported. If ICE trails a baseline the table shows it.
- The bundled synthetic fixture is flagged `all_synthetic: true` and is excluded
  from every marketing artifact.
- Older ICE marketing claims ("sub-millisecond voxel paging", VMM, C-kernel perf)
  are **not** produced here and **not** repeated.

## Run it

```bash
pip install -e ".[test]" -r benchmarks/requirements-bench.txt

# offline plumbing check — no network, no key, no GPU
PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader mock --limit 5

# real free-tier run
cp benchmarks/.env.example benchmarks/.env    # fill in BENCH_LLM_API_KEY
set -a; . benchmarks/.env; set +a
PYTHONPATH=. python benchmarks/run_benchmarks.py \
  --suite locomo --systems ice,recency_truncation,vanilla_rag,no_memory \
  --reader openrouter --limit 20
```

Outputs land in `benchmarks/results/<suite>/<commit>/`:
`summary.json`, `predictions.jsonl`, `raw.log` (or `skipped.json`).

### Datasets

| suite | where the harness expects the data |
|---|---|
| LoCoMo | `data/locomo/locomo10.json` — vendor from [`snap-research/locomo`](https://github.com/snap-research/locomo) (~3 MB). Absent ⇒ synthetic fixture (flagged). |
| LongMemEval | `data/longmemeval/longmemeval_{s,oracle}.json` — HF `xiaowu0162/LongMemEval` (`s` ≈ 280 MB, `oracle` ≈ 15 MB and fast; `--lme-variant` picks). |
| BEAM | `data/beam/chats/<scale>/<id>/{chat.json, probing_questions/probing_questions.json}` — from [`mohammadtavakoli78/BEAM`](https://github.com/mohammadtavakoli78/BEAM). `--beam-scale` in `100K` / `500K` / `1M` / `10M`. |
| AMA-Bench | `data/ama/open_end_qa_set.jsonl` — HF `AMA-bench/AMA-bench` (~50 MB). `--ama-task-types` filters (default `swebench,webarena`). |

(all paths relative to `benchmarks/harness/datasets/data/`; the CI full lane fetches each automatically)

### License gate

`harness/core.bootstrap_ice()` sets `ice.build_config.ICE_SKU = "ICE-UNLIMITED"`
in `sys.modules` before `import ice` (same technique the repo's own licensing
tests use) and forces `ICE_MODE=sandbox` + `ICE_USE_ARQ=0`. No product code is
modified. Use `--mode production` with a real `DATABASE_URL` (see
`docker-compose.ci.yml`) for a pgvector run of record.

## CI

`.github/workflows/benchmarks.yml`:

- **smoke** — every push to `benchmarks`. Offline mock run + skip-path check. No secrets.
- **full** — `workflow_dispatch` (inputs: `suite`, `systems`, `limit`,
  `judge_spot_n`). Needs secret `BENCH_LLM_API_KEY` and optional vars
  `BENCH_LLM_BASE_URL` / `BENCH_LLM_MODEL`. Fetches datasets, runs, regenerates
  `marketing/`, uploads `benchmark-results`, and commits non-synthetic summaries
  back to the branch with `[skip ci]`.
