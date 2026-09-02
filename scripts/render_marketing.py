#!/usr/bin/env python3
"""Render marketing drafts from committed benchmark results.

Reads every ``benchmarks/results/<suite>/<commit>/summary.json`` and (re)writes
three drafts under ``benchmarks/marketing/``:

* ``BENCHMARKS.md``      -- results tables + methodology + reproducibility appendix
* ``blog-draft.md``      -- narrative post
* ``landing-section.md`` -- short website "Benchmarks" copy block

Every number is taken verbatim from a ``summary.json``. Runs flagged
``all_synthetic`` are listed separately and never counted as evidence. Nothing
is published -- these are drafts for human review.
"""

from __future__ import annotations

import json
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BENCH_DIR / "results"
MKT_DIR = BENCH_DIR / "marketing"

_SYS_LABEL = {
    "ice": "ICE (memory layer)",
    "vanilla_rag": "Vanilla RAG (same embeddings, no ICE attention layer)",
    "recency_truncation": "Recency truncation (no retrieval)",
    "no_memory": "No memory (question only)",
    "mem0": "Mem0",
}

_CAVEAT = (
    "> **Read this first.** ICE is a *memory / retrieval layer*, not an answer "
    "generator. Every row below is `ICE (or a baseline) assembles context -> the "
    "same frozen reader model answers -> the answer is scored`. Numbers are a "
    "**small labelled sample (N is shown per row), directional, not a full-suite "
    "result.** Every value is copied from a committed `summary.json`; raw "
    "predictions and logs sit next to it. Runs on the bundled synthetic fixture "
    "are listed separately and are **not** evidence of anything."
)


def _load_all() -> list[dict]:
    out = []
    for f in sorted(RESULTS_DIR.glob("*/*/summary.json")):
        try:
            d = json.loads(f.read_text())
            d["_path"] = str(f.relative_to(BENCH_DIR))
            out.append(d)
        except (json.JSONDecodeError, OSError):
            continue
    return out


def _table(summary: dict) -> str:
    rows = ["| System | F1 | EM | Recall | Abstention F1 | Judge spot-acc | N |",
            "|---|---|---|---|---|---|---|"]
    systems = summary.get("systems", {})
    judge = summary.get("judge_spot", {})
    order = ["ice", "vanilla_rag", "recency_truncation", "no_memory", "mem0"]
    for name in order + [s for s in systems if s not in order]:
        s = systems.get(name)
        if not s:
            continue
        j = judge.get(name, {})
        rows.append(
            "| {label} | {f1:.3f} | {em:.3f} | {rec:.3f} | {abf1} | {jacc} | {n} |".format(
                label=_SYS_LABEL.get(name, name),
                f1=s.get("f1", 0.0),
                em=s.get("em", 0.0),
                rec=s.get("recall", 0.0),
                abf1=f"{s['abstention_f1']:.3f}" if "abstention_f1" in s else "-",
                jacc=f"{j['accuracy']:.3f} (n={j['n']})" if j else "-",
                n=s.get("n", 0),
            )
        )
    return "\n".join(rows)


def _repro(summary: dict) -> str:
    return (
        f"- suite: `{summary.get('benchmark')}`  |  commit: `{summary.get('commit')}`  |  "
        f"run: `{summary.get('ts')}`\n"
        f"- reader / judge model: `{summary.get('reader_model')}` via `{summary.get('reader', '?')}`\n"
        f"- ICE substrate: `{summary.get('mode')}`  |  sample limit: `{summary.get('limit')}`  |  "
        f"completed: `{summary.get('n_completed')}`  |  partial: `{summary.get('partial')}`\n"
        f"- raw: `{summary['_path'].rsplit('/', 1)[0]}/` (`summary.json`, `predictions.jsonl`, `raw.log`)\n"
        f"- reproduce: `PYTHONPATH=. python benchmarks/run_benchmarks.py --suite "
        f"{summary.get('benchmark')} --reader {summary.get('reader', 'openrouter')} "
        f"--limit {summary.get('limit')}`"
    )


def render() -> None:
    MKT_DIR.mkdir(parents=True, exist_ok=True)
    all_runs = _load_all()
    real = [r for r in all_runs if not r.get("all_synthetic")]
    synth = [r for r in all_runs if r.get("all_synthetic")]

    # ---- BENCHMARKS.md -------------------------------------------------- #
    lines = ["# ICE memory benchmarks", "", _CAVEAT, ""]
    if not real:
        lines += [
            "## Status: no non-synthetic runs yet",
            "",
            "The harness is in place and validated on the bundled synthetic fixture. "
            "Real-dataset runs (LoCoMo, LongMemEval) are pending -- they need the "
            "OpenRouter free-tier key wired into CI and accumulate over several days "
            "because of the 50-calls/day free-tier cap.",
            "",
        ]
    for r in real:
        lines += [
            f"## {r['benchmark']}  (sample)",
            "",
            _table(r),
            "",
            "**Reproducibility**",
            "",
            _repro(r),
            "",
        ]
    if synth:
        lines += [
            "## Appendix: synthetic-fixture runs (NOT evidence)",
            "",
            "These exercise the pipeline offline. Do not cite.",
            "",
        ]
        for r in synth:
            lines += [f"### {r['benchmark']} — synthetic", "", _table(r), ""]
    (MKT_DIR / "BENCHMARKS.md").write_text("\n".join(lines))

    # ---- blog-draft.md ----------------------------------------------------- #
    blog = [
        "# We benchmarked ICE's memory layer — here's the harness and the numbers",
        "",
        "_Draft. Not published. Every number links to a committed result file._",
        "",
        "## The honest framing",
        "",
        "ICE is a memory / retrieval layer. It does not generate answers. So a fair "
        "test fixes one reader model and swaps only the thing that feeds it context: "
        "ICE, a plain vector-RAG baseline, recency truncation, no memory at all, and "
        "an external library (Mem0). Same questions, same reader, same scoring.",
        "",
        "We run this on third-party memory benchmarks — LoCoMo and LongMemEval — plus "
        "BEAM and AMA-Bench when their datasets are public. The reader is a free model "
        "on OpenRouter, so anyone can reproduce it. The free tier caps us at ~50 calls "
        "a day, so the current sample is small and clearly labelled as directional.",
        "",
        "## Results so far",
        "",
    ]
    if real:
        for r in real:
            blog += [f"### {r['benchmark']}", "", _table(r), "", _repro(r), ""]
    else:
        blog += ["_Pending first non-synthetic run._", ""]
    blog += [
        "## What we are NOT claiming",
        "",
        "- Not \"ICE beats GPT-4\". The reader is a small free model, held constant.",
        "- Not a full-suite score. N is a sample; it grows as the daily budget allows.",
        "- Not the marketing numbers from older ICE docs (\"sub-millisecond voxel "
        "paging\" etc.) — those are not produced by this harness and are not repeated here.",
        "",
        "## Reproduce it",
        "",
        "```",
        "git checkout benchmarks",
        "pip install -e \".[test]\" -r benchmarks/requirements-bench.txt",
        "export BENCH_LLM_API_KEY=...   # OpenRouter",
        "PYTHONPATH=. python benchmarks/run_benchmarks.py --suite locomo --reader openrouter --limit 20",
        "```",
        "",
    ]
    (MKT_DIR / "blog-draft.md").write_text("\n".join(blog))

    # ---- landing-section.md ---------------------------------------------- #
    land = [
        "<!-- Website 'Benchmarks' section. Draft copy. -->",
        "",
        "## Benchmarks",
        "",
        "ICE is measured as a memory layer: one fixed reader model, context supplied "
        "by ICE vs. baselines vs. Mem0, on public benchmarks (LoCoMo, LongMemEval). "
        "Reader is a free, reproducible model. Current numbers are a directional "
        "sample — full runs accumulate over time under the free-tier budget.",
        "",
    ]
    if real:
        land += [_table(real[0]), "", f"_Source: `{real[0]['_path']}` · commit `{real[0]['commit']}`_", ""]
    else:
        land += ["_First sample pending._", ""]
    land += ["[Full methodology, raw logs and reproduction steps →](../benchmarks/marketing/BENCHMARKS.md)", ""]
    (MKT_DIR / "landing-section.md").write_text("\n".join(land))

    print(f"wrote {MKT_DIR}/BENCHMARKS.md, blog-draft.md, landing-section.md "
          f"({len(real)} real run(s), {len(synth)} synthetic)")


if __name__ == "__main__":
    render()
