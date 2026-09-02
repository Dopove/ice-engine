#!/usr/bin/env python3
"""Retrieval-only tuning for ICE on LoCoMo -- costs zero API calls.

LoCoMo QA rows carry ``evidence`` (gold dialogue ids, e.g. ``["D1:3"]``). This
script asks, for a grid of retrieval configs, whether ICE actually surfaces the
gold turn:

* ``raw_recall@k``    -- gold turn text appears in ``search_episodic(limit=k)``
* ``packed_recall@k`` -- gold turn text survives into ``ContextPager.assemble_prompt``
                         output (i.e. after U-Shape reorder + compression)
* ``mrr``             -- 1/rank of the first gold hit in the raw list

Run this before spending reader budget: if the gold turn never reaches the
context, no reader can answer, and the knob to turn is retrieval -- not the model.

    PYTHONPATH=. python benchmarks/tune_retrieval.py --limit 40 --ks 6,12,20,30,50
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from benchmarks.harness.core import RESULTS_DIR, normalize_answer
from benchmarks.harness.datasets import load_locomo


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "nogit"


def _evidence_texts(sample) -> list[str]:
    by_id = {t.dia_id: t.text for t in sample.conversation.turns if t.dia_id}
    return [by_id[e] for e in sample.evidence if e in by_id]


def _contains(haystack: str, needle: str) -> bool:
    h = normalize_answer(haystack)
    n = normalize_answer(needle)
    if not n:
        return False
    return n[:80] in h or n in h


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=40, help="answerable LoCoMo questions to probe")
    ap.add_argument("--ks", default="6,12,20,30,50", help="comma list of top_k values")
    ap.add_argument("--max-tokens", default="16000", help="comma list of assemble_prompt token budgets")
    ap.add_argument("--seed", type=int, default=20260902)
    ap.add_argument("--out", default=str(RESULTS_DIR / "retrieval_tuning.json"))
    args = ap.parse_args()

    ks = [int(x) for x in args.ks.split(",")]

    pool = load_locomo(limit=None, seed=args.seed)
    usable = []
    for s in pool:
        if s.is_unanswerable:
            continue
        ev = _evidence_texts(s)
        if ev:
            s.evidence_texts = ev  # type: ignore[attr-defined]
            usable.append(s)
    usable = usable[: args.limit]
    if not usable:
        print("no usable evidence-bearing LoCoMo questions found")
        return 1

    by_conv: dict[str, list] = defaultdict(list)
    for s in usable:
        by_conv[s.conversation.conv_id].append(s)

    from benchmarks.harness.adapters import ICEAdapter, _ensure_kernel, shutdown

    _ensure_kernel("sandbox")
    from ice.config import settings

    settings.ICE_SKU = "ICE-ENTERPRISE"  # community path crashes in ICE's own pager

    max_toks = [int(x) for x in args.max_tokens.split(",")]

    results = []
    for k in ks:
        for mt in max_toks:
            raw_hits = packed_hits = hits_mode_hits = 0
            ranks = 0.0
            n = 0
            for _conv_id, samples in by_conv.items():
                ad_p = ICEAdapter(mode="sandbox", top_k=k, max_input_tokens=mt, context_mode="packed")
                ad_h = ICEAdapter(mode="sandbox", top_k=k, max_input_tokens=mt, context_mode="hits")
                for ad in (ad_p, ad_h):
                    ad.reset()
                    ad.ingest(samples[0].conversation)
                for s in samples:
                    n += 1
                    ev_texts = s.evidence_texts  # type: ignore[attr-defined]
                    _qv, hlist, _hist = ad_p._retrieve(s.question)
                    first_rank = 0
                    for i, h in enumerate(hlist, 1):
                        if any(_contains(h.get("content", ""), e) for e in ev_texts):
                            first_rank = i
                            break
                    if first_rank:
                        raw_hits += 1
                        ranks += 1.0 / first_rank
                    if any(_contains(ad_p.context(s.question), e) for e in ev_texts):
                        packed_hits += 1
                    if any(_contains(ad_h.context(s.question), e) for e in ev_texts):
                        hits_mode_hits += 1
            row = {
                "top_k": k,
                "max_input_tokens": mt,
                "n": n,
                "raw_recall": round(raw_hits / n, 4) if n else 0.0,
                "packed_recall": round(packed_hits / n, 4) if n else 0.0,
                "hits_mode_recall": round(hits_mode_hits / n, 4) if n else 0.0,
                "mrr": round(ranks / n, 4) if n else 0.0,
            }
            results.append(row)
            print(
                f"k={k:<3} max_tok={mt:<6}  raw={row['raw_recall']:.3f}  "
                f"packed={row['packed_recall']:.3f}  hits_mode={row['hits_mode_recall']:.3f}  "
                f"mrr={row['mrr']:.3f}  (n={n})"
            )
    shutdown()

    out = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": _commit(),
        "dataset": "locomo",
        "n_questions": len(usable),
        "seed": args.seed,
        "configs": results,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"\nwrote {args.out}")

    best_packed = max(results, key=lambda r: (r["packed_recall"], r["mrr"]))
    best_hits = max(results, key=lambda r: (r["hits_mode_recall"], r["mrr"]))
    print(
        f"\nbest packed (ICE full pipeline): k={best_packed['top_k']} max_tok={best_packed['max_input_tokens']} "
        f"-> {best_packed['packed_recall']:.3f}\n"
        f"best hits  (compression bypassed): k={best_hits['top_k']} max_tok={best_hits['max_input_tokens']} "
        f"-> {best_hits['hits_mode_recall']:.3f}\n"
        f"if hits_mode >> packed at every setting, the fix needs ICE code (compress_context threshold), "
        f"not config."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
