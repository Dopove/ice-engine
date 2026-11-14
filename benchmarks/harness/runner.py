"""Benchmark run loop.

For each sample: every system ``reset() -> ingest(conversation) -> context(q)``;
the shared reader answers from that context; the answer is scored with
string-metrics (0 API cost). An optional LLM-judge spot-check grades the first
``judge_spot_n`` answers per system.

Cache-aware and budget-aware: a spent daily API budget (see
:class:`benchmarks.harness.core.Budget`) ends the run *cleanly* with
``partial: true`` and whatever was completed written to disk. Re-running on a
later day extends the same cached sample.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

from .core import (
    Budget,
    BudgetExceeded,
    RESULTS_DIR,
    abstention_scores,
    aggregate,
    make_client,
    score_answer,
)
from .datasets import DatasetUnavailable, is_all_synthetic, load_suite

_QA_SYSTEM = (
    "You answer questions using ONLY the provided context, which are excerpts of a "
    "past conversation between two people. Answer in as few words as possible. If the "
    "context does not contain the answer, reply exactly: I don't know."
)


def _commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:  # noqa: BLE001
        return "nogit"


def _prompt(context: str, question: str) -> str:
    ctx = context.strip() or "(no context available)"
    return f"CONTEXT:\n{ctx}\n\nQUESTION: {question}\nANSWER:"


def run_suite(
    suite: str,
    system_names: list[str],
    *,
    limit: int | None = 30,
    reader: str = "openrouter",
    reader_model: str | None = None,
    mode: str = "sandbox",
    top_k: int = 6,
    judge_spot_n: int = 10,
    seed: int | None = 20260902,
    variant: str = "s",
    loader_kw: dict[str, Any] | None = None,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run one benchmark suite; returns the summary dict (also written to disk)."""
    commit = _commit()
    out_dir = Path(out_dir) if out_dir else RESULTS_DIR / suite / commit
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "raw.log"
    log = log_path.open("w")

    def _log(msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line)
        log.write(line + "\n")
        log.flush()

    # -- load data ---------------------------------------------------------- #
    try:
        samples = load_suite(
            suite, limit=limit, seed=seed, variant=variant, **(loader_kw or {})
        )
    except DatasetUnavailable as exc:
        skipped = {"benchmark": suite, "reason": str(exc), "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
        (out_dir / "skipped.json").write_text(json.dumps(skipped, indent=2))
        _log(f"SKIPPED {suite}: {exc}")
        log.close()
        return skipped

    synthetic = is_all_synthetic(samples)
    if synthetic:
        _log("WARNING: running on the SYNTHETIC fixture -- results are for plumbing only, do not publish")
    _log(f"{suite}: {len(samples)} samples, systems={system_names}, reader={reader}, limit={limit}")

    # -- build systems + reader ------------------------------------------------ #
    from .adapters import build_systems, shutdown

    budget = Budget()
    reader_client = make_client(reader, model=reader_model, budget=budget, cache_name=reader_model or None)
    judge_client = make_client(reader, model=reader_model, budget=budget, cache_name=(reader_model or "judge"))
    systems = build_systems(system_names, mode=mode, top_k=top_k)

    preds_path = out_dir / "predictions.jsonl"
    preds = preds_path.open("w")
    per_system: dict[str, list[dict[str, float]]] = {s.name: [] for s in systems}
    abst_rows: dict[str, list[dict[str, Any]]] = {s.name: [] for s in systems}
    judge_rows: dict[str, list[int]] = {s.name: [] for s in systems}
    # Wall-clock latency of context()/ingest() themselves -- no reader LLM
    # call happens inside either, so this is purely retrieval/indexing speed,
    # not confounded by the shared reader's own response time.
    context_latency_ms: dict[str, list[float]] = {s.name: [] for s in systems}
    ingest_latency_ms: dict[str, list[float]] = {s.name: [] for s in systems}
    completed = 0
    partial = False

    last_conv: dict[str, str] = {}
    try:
        for idx, sample in enumerate(samples):
            gold = sample.answers[0] if sample.answers else ""
            for sysobj in systems:
                # Re-ingest only when the conversation changes (samples are
                # grouped by conv_id) -- avoids re-embedding long histories.
                if last_conv.get(sysobj.name) != sample.conversation.conv_id:
                    sysobj.reset()
                    t0 = time.perf_counter()
                    sysobj.ingest(sample.conversation)
                    ingest_latency_ms[sysobj.name].append((time.perf_counter() - t0) * 1000)
                    last_conv[sysobj.name] = sample.conversation.conv_id
                t0 = time.perf_counter()
                ctx = sysobj.context(sample.question)
                context_latency_ms[sysobj.name].append((time.perf_counter() - t0) * 1000)
                res = reader_client.chat(_prompt(ctx, sample.question), system=_QA_SYSTEM)
                sc = score_answer(res.text, sample.answers or [""])
                per_system[sysobj.name].append(sc)
                abst_rows[sysobj.name].append(
                    {"is_unanswerable": sample.is_unanswerable, "abstained": sc["abstained"]}
                )
                if judge_spot_n and len(judge_rows[sysobj.name]) < judge_spot_n:
                    jv = judge_client.judge(sample.question, gold, res.text)
                    judge_rows[sysobj.name].append(int("CORRECT" in jv.text.upper()))
                preds.write(
                    json.dumps(
                        {
                            "system": sysobj.name,
                            "sample_id": sample.sample_id,
                            "category": sample.category,
                            "is_unanswerable": sample.is_unanswerable,
                            "question": sample.question,
                            "gold": gold,
                            "pred": res.text,
                            "f1": round(sc["f1"], 4),
                            "em": sc["em"],
                            "recall": round(sc["recall"], 4),
                            "abstained": sc["abstained"],
                            "cached": res.cached,
                        }
                    )
                    + "\n"
                )
                preds.flush()
            completed += 1
            _log(f"  [{idx + 1}/{len(samples)}] done  (budget used {budget.used}/{budget.daily_limit})")
    except BudgetExceeded as exc:
        partial = True
        _log(f"BUDGET STOP: {exc}")
    finally:
        preds.close()
        shutdown()

    # -- aggregate ---------------------------------------------------------- #
    systems_summary: dict[str, Any] = {}
    for name, scores in per_system.items():
        agg = aggregate(scores)
        if any(r["is_unanswerable"] for r in abst_rows[name]):
            agg.update(abstention_scores(abst_rows[name]))
        if context_latency_ms[name]:
            agg["context_latency_ms"] = {
                "mean": round(statistics.mean(context_latency_ms[name]), 2),
                "median": round(statistics.median(context_latency_ms[name]), 2),
                "n": len(context_latency_ms[name]),
            }
        if ingest_latency_ms[name]:
            agg["ingest_latency_ms"] = {
                "mean": round(statistics.mean(ingest_latency_ms[name]), 2),
                "median": round(statistics.median(ingest_latency_ms[name]), 2),
                "n": len(ingest_latency_ms[name]),
            }
        systems_summary[name] = agg

    judge_spot = {
        name: {"accuracy": round(sum(v) / len(v), 4), "n": len(v)}
        for name, v in judge_rows.items()
        if v
    }

    summary = {
        "benchmark": suite,
        "commit": commit,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reader": reader,
        "reader_model": getattr(reader_client, "model", reader),
        "mode": mode,
        "limit": limit,
        "variant": variant if suite == "longmemeval" else None,
        "sample_seed": seed,
        "n_samples": len(samples),
        "n_completed": completed,
        "partial": partial,
        "all_synthetic": synthetic,
        "systems": systems_summary,
        "judge_spot": judge_spot,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    _log(f"WROTE {out_dir / 'summary.json'}  (partial={partial}, synthetic={synthetic})")
    log.close()
    return summary
