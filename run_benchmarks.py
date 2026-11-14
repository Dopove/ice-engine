#!/usr/bin/env python3
"""ICE memory-benchmark runner.

Examples
--------
Offline plumbing check (no network, no GPU, no license)::

    PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader mock --limit 5

Real free-tier run (needs BENCH_LLM_API_KEY in env)::

    PYTHONPATH=. python benchmarks/run_benchmarks.py \
        --suite locomo --systems ice,recency_truncation,vanilla_rag,mem0 \
        --reader openrouter --limit 30

The run is cache- and budget-aware: when the daily free-tier call budget is
spent it stops cleanly, writes ``partial: true``, and a later invocation extends
the same sample from cache.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make ``benchmarks`` importable when run as a bare script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.harness.runner import run_suite  # noqa: E402

SUITES = ["locomo", "longmemeval", "beam", "ama"]
DEFAULT_SYSTEMS = "ice,ice_tuned,ice_hits,vanilla_rag,recency_truncation,no_memory"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--suite", default="locomo", help="locomo|longmemeval|beam|ama|all")
    ap.add_argument("--systems", default=DEFAULT_SYSTEMS, help="comma list; add 'mem0' for the external row")
    ap.add_argument("--limit", type=int, default=30, help="max samples (the labelled sample size)")
    ap.add_argument("--reader", default="openrouter", help="openrouter|api|mock")
    ap.add_argument("--reader-model", default=None, help="override BENCH_LLM_MODEL")
    ap.add_argument("--mode", default="sandbox", help="ICE substrate: sandbox|production")
    ap.add_argument("--top-k", type=int, default=30, help="retrieved items fed to the reader")
    ap.add_argument("--judge-spot-n", type=int, default=10, help="LLM-judge spot-check size per system (0 disables)")
    ap.add_argument("--sample-seed", type=int, default=20260902, help="reproducible subsample seed")
    ap.add_argument("--lme-variant", default="s", help="LongMemEval variant: s | m | oracle")
    ap.add_argument("--beam-scale", default="100K", help="BEAM token scale: 100K | 500K | 1M | 10M")
    ap.add_argument("--ama-task-types", default="swebench,webarena",
                    help="AMA-Bench task types to include (comma list; empty = all)")
    ap.add_argument("--out", default=None, help="output dir (default: benchmarks/results/<suite>/<commit>)")
    args = ap.parse_args(argv)

    suites = SUITES if args.suite == "all" else [args.suite]
    systems = [s.strip() for s in args.systems.split(",") if s.strip()]

    summaries = []
    for suite in suites:
        print(f"\n=== {suite} ===")
        summary = run_suite(
            suite,
            systems,
            limit=args.limit,
            reader=args.reader,
            reader_model=args.reader_model,
            mode=args.mode,
            top_k=args.top_k,
            judge_spot_n=args.judge_spot_n,
            seed=args.sample_seed,
            variant=args.lme_variant,
            loader_kw={
                "scale": args.beam_scale,
                "task_types": args.ama_task_types or None,
            },
            out_dir=args.out,
        )
        summaries.append(summary)
        print(json.dumps(summary, indent=2))

    return 0 if summaries else 1


if __name__ == "__main__":
    raise SystemExit(main())
