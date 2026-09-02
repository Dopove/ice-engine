#!/usr/bin/env python3
"""Bar charts from committed benchmark summaries.

One grouped bar chart per suite (F1 + recall per system), written to
``benchmarks/marketing/charts/<suite>.png``. Synthetic-only runs are skipped.
No-op (exit 0) if matplotlib is missing or there is nothing real to plot.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BENCH_DIR / "results"
CHART_DIR = BENCH_DIR / "marketing" / "charts"

_ORDER = ["ice", "ice_hits", "vanilla_rag", "recency_truncation", "no_memory", "mem0"]
_LABEL = {
    "ice": "ICE (full)",
    "ice_hits": "ICE (retrieval)",
    "vanilla_rag": "Vanilla RAG",
    "recency_truncation": "Recency trunc.",
    "no_memory": "No memory",
    "mem0": "Mem0",
}


def main() -> int:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        print(f"make_charts: matplotlib unavailable ({exc}); skipping")
        return 0

    latest: dict[str, dict] = {}
    for f in sorted(RESULTS_DIR.glob("*/*/summary.json")):
        try:
            d = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if d.get("all_synthetic"):
            continue
        latest[d["benchmark"]] = d  # sorted() => last wins

    if not latest:
        print("make_charts: no non-synthetic summaries; nothing to plot")
        return 0

    CHART_DIR.mkdir(parents=True, exist_ok=True)
    for suite, d in latest.items():
        systems = d.get("systems", {})
        names = [n for n in _ORDER if n in systems] + [n for n in systems if n not in _ORDER]
        f1 = [systems[n].get("f1", 0.0) for n in names]
        rec = [systems[n].get("recall", 0.0) for n in names]
        x = range(len(names))
        w = 0.38

        fig, ax = plt.subplots(figsize=(1.6 * len(names) + 2, 4))
        ax.bar([i - w / 2 for i in x], f1, w, label="F1")
        ax.bar([i + w / 2 for i in x], rec, w, label="Recall")
        ax.set_xticks(list(x))
        ax.set_xticklabels([_LABEL.get(n, n) for n in names], rotation=15, ha="right")
        ax.set_ylim(0, 1)
        ax.set_ylabel("score")
        ax.set_title(
            f"{suite} — sample N={d.get('limit')} (completed {d.get('n_completed')}), "
            f"reader {d.get('reader_model')}"
        )
        ax.legend()
        fig.tight_layout()
        out = CHART_DIR / f"{suite}.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
