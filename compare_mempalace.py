#!/usr/bin/env python3
"""ICE vs MemPalace -- retrieval-recall comparison. Zero LLM / API calls.

MemPalace (github.com/MemPalace/mempalace) headlines "96.6% R@5 on LongMemEval".
That number is **retrieval recall**: for each question, is the gold *session*
inside the top-5 retrieved candidates? Their own BENCHMARKS.md stresses this is
NOT end-to-end QA accuracy.

This script measures the same thing, the same way, for both systems:

* ``mempalace_raw`` -- a faithful reimplementation of their ``longmemeval_bench.py``
  raw mode: one ChromaDB doc per session (verbatim text), ChromaDB default
  embeddings (all-MiniLM-L6-v2, 384-d), query with the question, Recall@k over
  the top-k session ids.
* ``ice``           -- ICE's ``EpisodicManager.search_episodic`` over the same
  turns; retrieved turns are mapped back to their session; Recall@k over the
  distinct sessions in rank order. ICE uses the *same* embedding model, so the
  delta is retrieval strategy, not embeddings.

LongMemEval gold is session-level (``answer_session_ids``). LoCoMo gold
(``evidence`` dia_ids) is mapped to its ``D<n>`` session.

    PYTHONPATH=. python benchmarks/compare_mempalace.py --suite longmemeval --lme-variant oracle --limit 40
    PYTHONPATH=. python benchmarks/compare_mempalace.py --suite locomo --limit 60 --top-k 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from benchmarks.harness.core import RESULTS_DIR
from benchmarks.harness.datasets import load_locomo, load_longmemeval


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "nogit"


def _dcg(rels: list[float], k: int) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(rels[:k]))


def _ndcg(ranked_ids: list[str], gold: set[str], k: int) -> float:
    rels = [1.0 if sid in gold else 0.0 for sid in ranked_ids[:k]]
    ideal = _dcg(sorted(rels, reverse=True), k)
    return _dcg(rels, k) / ideal if ideal else 0.0


def _recall_any(ranked_ids: list[str], gold: set[str], k: int) -> float:
    return float(bool(gold & set(ranked_ids[:k])))


# --------------------------------------------------------------------------- #
# MemPalace raw mode (faithful reimplementation of their longmemeval_bench.py)
# --------------------------------------------------------------------------- #

_CHROMA = None


def _chroma_client():
    global _CHROMA
    if _CHROMA is None:
        import chromadb

        _CHROMA = chromadb.EphemeralClient()
    return _CHROMA


def mempalace_raw_ranked_sessions(session_docs: dict[str, str], question: str) -> list[str]:
    """One doc per session, ChromaDB default embeddings, query -> ranked session ids."""
    client = _chroma_client()
    try:
        client.delete_collection("cmp")
    except Exception:  # noqa: BLE001
        pass
    col = client.create_collection("cmp")
    ids = list(session_docs)
    col.add(ids=ids, documents=[session_docs[i] for i in ids])
    n = min(len(ids), 50)
    res = col.query(query_texts=[question], n_results=n)
    return list(res["ids"][0])


# --------------------------------------------------------------------------- #
# ICE retrieval -> ranked sessions
# --------------------------------------------------------------------------- #


def ice_ranked_sessions(adapter, turns, question: str, turn_k: int = 60) -> list[str]:
    """Retrieve top turn_k turns via ICE, dedupe to sessions in rank order."""
    content_to_sid: dict[str, str] = {}
    for t in turns:
        key = (f"{t.speaker}: {t.text}" if t.speaker else t.text).strip()
        content_to_sid.setdefault(key, t.session_id or "?")
    adapter.top_k = turn_k
    _qv, hits, _hist = adapter._retrieve(question)
    ranked: list[str] = []
    for h in hits:
        c = str(h.get("content", "")).strip()
        for pref in ("[PRIORITY ACTION RESULT]:", "[CRITICAL MEMORY]:"):
            if c.startswith(pref):
                c = c[len(pref):].strip()
        sid = content_to_sid.get(c)
        if sid is None:
            for k, v in content_to_sid.items():
                if c[:60] and c[:60] in k:
                    sid = v
                    break
        if sid and sid not in ranked:
            ranked.append(sid)
    return ranked


# --------------------------------------------------------------------------- #
# Sample -> (session_docs, turns, gold_session_ids, qtype)
# --------------------------------------------------------------------------- #


def prep_longmemeval(sample):
    docs: dict[str, list[str]] = defaultdict(list)
    for t in sample.conversation.turns:
        docs[t.session_id or "?"].append(f"{t.speaker}: {t.text}" if t.speaker else t.text)
    session_docs = {sid: "\n".join(lines) for sid, lines in docs.items()}
    gold = set(sample.answer_session_ids)
    return session_docs, sample.conversation.turns, gold, sample.category


def prep_locomo(sample):
    def sess_of(dia_id: str | None) -> str:
        if not dia_id or ":" not in dia_id:
            return "?"
        return dia_id.split(":")[0]  # "D1:3" -> "D1"

    docs: dict[str, list[str]] = defaultdict(list)
    turns = []
    for t in sample.conversation.turns:
        sid = sess_of(t.dia_id)
        t.session_id = sid
        turns.append(t)
        docs[sid].append(f"{t.speaker}: {t.text}" if t.speaker else t.text)
    session_docs = {sid: "\n".join(lines) for sid, lines in docs.items()}
    gold = {sess_of(e) for e in sample.evidence}
    gold.discard("?")
    return session_docs, turns, gold, sample.category


# --------------------------------------------------------------------------- #


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", default="longmemeval", help="longmemeval | locomo")
    ap.add_argument("--lme-variant", default="oracle", help="s | oracle (oracle is fast)")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20260902)
    ap.add_argument("--ice-turn-k", type=int, default=60, help="turns ICE retrieves before session dedupe")
    ap.add_argument("--out", default=str(RESULTS_DIR / "comparative" / "mempalace_vs_ice.json"))
    args = ap.parse_args()

    if args.suite == "longmemeval":
        samples = load_longmemeval(limit=args.limit, variant=args.lme_variant, seed=args.seed)
        prep = prep_longmemeval
    else:
        samples = load_locomo(limit=args.limit, seed=args.seed)
        prep = prep_locomo

    from benchmarks.harness.adapters import ICEAdapter, _ensure_kernel, _run, shutdown

    _ensure_kernel("sandbox")
    from ice.config import settings

    settings.ICE_SKU = "ICE-ENTERPRISE"

    acc = {
        "mempalace_raw": {5: [], 10: [], "ndcg10": []},
        "ice": {5: [], 10: [], "ndcg10": []},
    }
    by_type: dict[str, dict[str, list]] = defaultdict(lambda: {"mempalace_raw": [], "ice": []})
    n_used = 0

    for idx, sample in enumerate(samples):
        session_docs, turns, gold, qtype = prep(sample)
        if not gold or not any(g in session_docs for g in gold):
            continue
        n_used += 1

        mp_ranked = mempalace_raw_ranked_sessions(session_docs, sample.question)

        ad = ICEAdapter(mode="sandbox", top_k=args.ice_turn_k)
        ad.reset()

        async def _ingest_all():
            emb = ad.kernel.embedder
            for t in turns:
                txt = f"{t.speaker}: {t.text}" if t.speaker else t.text
                v = await emb.embed_async(txt)
                await ad.kernel.episodic._save_to_db(
                    ad.tenant, ad.session, "default", "user", txt, v, ad.user, {}
                )

        _run(_ingest_all())
        ice_ranked = ice_ranked_sessions(ad, turns, sample.question, turn_k=args.ice_turn_k)

        for name, ranked in (("mempalace_raw", mp_ranked), ("ice", ice_ranked)):
            acc[name][5].append(_recall_any(ranked, gold, 5))
            acc[name][10].append(_recall_any(ranked, gold, 10))
            acc[name]["ndcg10"].append(_ndcg(ranked, gold, 10))
            by_type[qtype][name].append(_recall_any(ranked, gold, 5))

        if (idx + 1) % 10 == 0:
            m5 = sum(acc["mempalace_raw"][5]) / len(acc["mempalace_raw"][5])
            i5 = sum(acc["ice"][5]) / len(acc["ice"][5])
            print(f"  [{idx + 1}/{len(samples)}] R@5  mempalace={m5:.3f}  ice={i5:.3f}  (n={n_used})")

    shutdown()

    def _mean(xs):
        return round(sum(xs) / len(xs), 4) if xs else 0.0

    summary = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": _commit(),
        "dataset": args.suite + (f"/{args.lme_variant}" if args.suite == "longmemeval" else ""),
        "metric": "retrieval recall@k -- gold session in top-k (MemPalace's headline metric)",
        "granularity": "session",
        "embed_model": "all-MiniLM-L6-v2 (both systems)",
        "n": n_used,
        "systems": {
            name: {
                "recall_at_5": _mean(acc[name][5]),
                "recall_at_10": _mean(acc[name][10]),
                "ndcg_at_10": _mean(acc[name]["ndcg10"]),
                "n": len(acc[name][5]),
            }
            for name in acc
        },
        "by_type_recall_at_5": {
            qt: {name: _mean(v[name]) for name in ("mempalace_raw", "ice")}
            for qt, v in sorted(by_type.items())
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    print("\n" + json.dumps(summary["systems"], indent=2))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
