<!-- Draft. Not published. Numbers from benchmarks/results/comparative/*.json -->

# ICE vs MemPalace — retrieval recall

## What MemPalace actually claims

[MemPalace](https://github.com/MemPalace/mempalace) headlines **"96.6% R@5 on
LongMemEval"**. Their own `benchmarks/BENCHMARKS.md` is explicit that this is
**retrieval recall** — *"is the labelled session for this question inside the
top-5 retrieved candidates?"* — and **not** end-to-end QA accuracy:

> Retrieval recall and QA accuracy are not comparable; a system can have 100%
> retrieval recall and 40% QA accuracy, and vice versa.

MemPalace "raw mode" is zero-LLM: store each session as verbatim text, embed
with ChromaDB's default model (`all-MiniLM-L6-v2`, 384-d), retrieve top-k.

## How this comparison was run

Same metric, same embeddings, same data — retrieval only, **zero API calls**.

- **`mempalace_raw`** — a faithful reimplementation of their
  `benchmarks/longmemeval_bench.py` raw/session mode: one ChromaDB doc per
  session, default embeddings, query with the question, Recall@k over the top-k
  session ids.
- **`ice`** — ICE's `EpisodicManager.search_episodic` over the same turns;
  retrieved turns are mapped back to their session; Recall@k over the distinct
  sessions in rank order. **ICE uses the same embedding model**, so the delta is
  retrieval strategy, not embeddings.

Script: `benchmarks/compare_mempalace.py`. Raw output:
`benchmarks/results/comparative/mempalace_vs_ice_{longmemeval,locomo}.json`.

**Reproduction check** — the reimplemented `mempalace_raw` lands close to
MemPalace's published raw-mode numbers, so the pipeline is faithful:

| | this reimpl | MemPalace published |
|---|---|---|
| LongMemEval R@10 | 0.956 | 0.982 |
| LoCoMo R@10 (session) | 0.595 | 0.603 |

(Small gaps: `longmemeval_s` vs their `_cleaned` split; N=45/79 samples vs the full 500/1986.)

## Results

### LongMemEval-s (session-level retrieval recall, N=45)

| system | R@5 | R@10 | nDCG@10 |
|---|---|---|---|
| MemPalace raw | 0.933 | 0.956 | 0.892 |
| **ICE** | **0.978** | **0.978** | **0.921** |

By question type (R@5): ICE ≥ MemPalace on every type; the gap is on
`multi-session` (1.00 vs 0.92) and `temporal-reasoning` (1.00 vs 0.89).

### LoCoMo (session-level retrieval recall, N=79)

| system | R@5 | R@10 | nDCG@10 |
|---|---|---|---|
| MemPalace raw | 0.456 | 0.595 | 0.398 |
| **ICE** | **0.658** | **0.810** | **0.583** |

By LoCoMo category (R@5): ICE ahead on multi-hop (0.81 vs 0.62), open-domain
(0.67 vs 0.20), single-hop (0.69 vs 0.38); tied on adversarial (0.38).

## Reading this honestly

- **This is retrieval recall, not QA accuracy.** Neither number says the system
  answers correctly — only that the right session was retrieved. MemPalace raw
  has no reader; ICE's end-to-end QA F1 is measured separately (`BENCHMARKS.md`).
- **Granularity differs.** MemPalace raw/session mode embeds a whole session
  (hundreds of turns) as one vector; ICE embeds individual turns and aggregates.
  ICE's finer granularity is part of its advantage here. MemPalace also has a
  `--granularity turn` mode, not compared here.
- **ICE's retrieval is more than vector search.** `search_episodic` adds a
  priority lane for tool results, a keyword lane for critical instructions,
  dedup, and score re-ranking on top of the vector step.
- **Sample sizes are 45 / 79**, not the full sets. Directional, reproducible,
  same seed (`20260902`).

## Bottom line

On MemPalace's own headline metric, with identical embeddings: ICE's retrieval
is **level with MemPalace on LongMemEval** (both near ceiling) and **clearly
ahead on LoCoMo** (0.66 vs 0.46 R@5). The "90% / 96.6%" figure is a retrieval
number, and ICE matches or beats it on the same test.
