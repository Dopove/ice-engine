"""Dataset loaders for the memory benchmarks.

Each ``load_*`` returns ``list[Sample]``. If the third-party data is not present
it raises :class:`DatasetUnavailable` -- the runner turns that into a recorded
``skipped.json`` rather than a crash or a fabricated result.

Layout expected under ``benchmarks/harness/datasets/data/``::

    locomo/locomo10.json          # snap-research/locomo   (vendored; small)
    longmemeval/longmemeval_s.json# xiaowu0162/LongMemEval  (CI download; large)
    beam/*.json                   # BEAM tracks             (attempt; often absent)
    ama/*.json                    # AMA-Hub trajectories    (attempt; often absent)

A tiny **synthetic** LoCoMo-shaped fixture is bundled so the whole pipeline can
be exercised offline. It is labelled ``synthetic=True`` on every sample and must
never appear in a published result.
"""

from __future__ import annotations

import dataclasses
import json
import random
import re
from pathlib import Path
from typing import Any, Iterable

DATA_DIR = Path(__file__).resolve().parent / "datasets" / "data"


class DatasetUnavailable(RuntimeError):
    """The benchmark's data files are not present locally."""


def _subsample(samples: list["Sample"], limit: int | None, seed: int | None) -> list["Sample"]:
    """Reproducible sample of ``limit`` items, spread across categories.

    Round-robins the seed-shuffled per-category buckets so a small ``limit``
    still touches every question type instead of the first conversation only.
    """
    if not limit or limit >= len(samples):
        return samples
    if seed is None:
        return samples[:limit]
    rng = random.Random(seed)
    buckets: dict[str, list[Sample]] = {}
    for s in samples:
        buckets.setdefault(s.category, []).append(s)
    for b in buckets.values():
        rng.shuffle(b)
    order = sorted(buckets)
    out: list[Sample] = []
    while len(out) < limit and any(buckets[c] for c in order):
        for c in order:
            if buckets[c]:
                out.append(buckets[c].pop())
                if len(out) >= limit:
                    break
    # Group by conversation so a system ingests each conversation once.
    out.sort(key=lambda s: s.conversation.conv_id)
    return out


# --------------------------------------------------------------------------- #
# In-memory types
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class Turn:
    speaker: str
    text: str
    ts: str | None = None


@dataclasses.dataclass
class Conversation:
    conv_id: str
    turns: list[Turn]

    @property
    def n_turns(self) -> int:
        return len(self.turns)


@dataclasses.dataclass
class Sample:
    sample_id: str
    conversation: Conversation
    question: str
    answers: list[str]
    category: str = "qa"
    is_unanswerable: bool = False
    synthetic: bool = False


# --------------------------------------------------------------------------- #
# LoCoMo
# --------------------------------------------------------------------------- #

# LoCoMo category 5 == adversarial / "no information in the conversation".
_LOCOMO_UNANSWERABLE_CATEGORIES = {"5", 5}


def _locomo_sessions(conv: dict[str, Any]) -> list[Turn]:
    turns: list[Turn] = []
    # Sessions are keyed session_1, session_2, ... with session_<n>_date_time siblings.
    sess_keys = sorted(
        (k for k in conv if re.fullmatch(r"session_\d+", k)),
        key=lambda k: int(k.split("_")[1]),
    )
    for sk in sess_keys:
        ts = conv.get(f"{sk}_date_time")
        for msg in conv[sk]:
            turns.append(
                Turn(
                    speaker=str(msg.get("speaker", "")),
                    text=str(msg.get("text", msg.get("clean_text", ""))),
                    ts=ts,
                )
            )
    return turns


def load_locomo(
    limit: int | None = None, allow_synthetic: bool = True, seed: int | None = 20260902
) -> list[Sample]:
    path = DATA_DIR / "locomo" / "locomo10.json"
    if not path.exists():
        alt = DATA_DIR / "locomo" / "locomo.json"
        path = alt if alt.exists() else path
    if not path.exists():
        if allow_synthetic:
            return _synthetic_locomo(limit)
        raise DatasetUnavailable(
            f"LoCoMo data not found at {path}. Vendor snap-research/locomo "
            f"`data/locomo10.json` into {path.parent}/."
        )

    raw = json.loads(path.read_text())
    samples: list[Sample] = []
    for entry in raw:
        conv = entry["conversation"]
        turns = _locomo_sessions(conv)
        convo = Conversation(conv_id=str(entry.get("sample_id", len(samples))), turns=turns)
        for i, qa in enumerate(entry.get("qa", [])):
            cat = qa.get("category", "qa")
            ans = qa.get("answer", qa.get("adversarial_answer", ""))
            samples.append(
                Sample(
                    sample_id=f"{convo.conv_id}::q{i}",
                    conversation=convo,
                    question=qa["question"],
                    answers=[str(ans)] if ans != "" else [],
                    category=str(cat),
                    is_unanswerable=cat in _LOCOMO_UNANSWERABLE_CATEGORIES,
                )
            )
    return _subsample(samples, limit, seed)


# --------------------------------------------------------------------------- #
# LongMemEval
# --------------------------------------------------------------------------- #


def load_longmemeval(
    limit: int | None = None, variant: str = "s", seed: int | None = 20260902
) -> list[Sample]:
    path = DATA_DIR / "longmemeval" / f"longmemeval_{variant}.json"
    if not path.exists():
        raise DatasetUnavailable(
            f"LongMemEval not found at {path}. Download longmemeval_{variant}.json from the "
            f"official release (HuggingFace: xiaowu0162/LongMemEval) into {path.parent}/. "
            f"Too large to vendor; CI fetches it."
        )
    raw = json.loads(path.read_text())
    # Sample raw entries before building (haystacks are large) -- keep the
    # abstention subset over-represented so it is actually measured.
    if limit and seed is not None and limit < len(raw):
        rng = random.Random(seed)
        abs_idx = [i for i, e in enumerate(raw) if str(e.get("question_id", "")).endswith("_abs")]
        oth_idx = [i for i in range(len(raw)) if i not in set(abs_idx)]
        rng.shuffle(abs_idx)
        rng.shuffle(oth_idx)
        take_abs = min(len(abs_idx), max(1, limit // 3))
        pick = sorted(abs_idx[:take_abs] + oth_idx[: limit - take_abs])
        raw = [raw[i] for i in pick]
    samples: list[Sample] = []
    for entry in raw:
        qid = str(entry["question_id"])
        is_abs = qid.endswith("_abs") or entry.get("question_type") == "knowledge_update_abstention"
        turns: list[Turn] = []
        for sess in entry.get("haystack_sessions", []):
            for msg in sess:
                turns.append(
                    Turn(speaker=str(msg.get("role", "")), text=str(msg.get("content", "")))
                )
        convo = Conversation(conv_id=qid, turns=turns)
        samples.append(
            Sample(
                sample_id=qid,
                conversation=convo,
                question=entry["question"],
                answers=[str(entry.get("answer", ""))] if entry.get("answer") else [],
                category=str(entry.get("question_type", "qa")),
                is_unanswerable=bool(is_abs),
            )
        )
        if limit and len(samples) >= limit:
            break
    return samples


# --------------------------------------------------------------------------- #
# BEAM / AMA-Bench  (attempt; usually not released yet)
# --------------------------------------------------------------------------- #


def _load_generic_dir(name: str, limit: int | None) -> list[Sample]:
    d = DATA_DIR / name
    files = sorted(d.glob("*.json")) if d.exists() else []
    if not files:
        raise DatasetUnavailable(
            f"{name} data not found under {d}/. This benchmark's dataset does not "
            f"appear to be publicly released yet; the run will be recorded as skipped."
        )
    samples: list[Sample] = []
    for fp in files:
        raw = json.loads(fp.read_text())
        for i, entry in enumerate(raw if isinstance(raw, list) else [raw]):
            turns = [
                Turn(speaker=str(m.get("role", m.get("speaker", ""))), text=str(m.get("content", m.get("text", ""))))
                for m in entry.get("context", entry.get("messages", entry.get("trajectory", [])))
            ]
            convo = Conversation(conv_id=f"{fp.stem}-{i}", turns=turns)
            q = entry.get("question", entry.get("query", ""))
            a = entry.get("answer", entry.get("gold", ""))
            if not q:
                continue
            samples.append(
                Sample(
                    sample_id=f"{fp.stem}-{i}",
                    conversation=convo,
                    question=str(q),
                    answers=[str(a)] if a else [],
                    category=str(entry.get("track", entry.get("category", name))),
                    is_unanswerable=bool(entry.get("is_unanswerable", False)),
                )
            )
            if limit and len(samples) >= limit:
                return samples
    return samples


def load_beam(limit: int | None = None, seed: int | None = None) -> list[Sample]:
    return _load_generic_dir("beam", limit)


def load_ama(limit: int | None = None, seed: int | None = None) -> list[Sample]:
    return _load_generic_dir("ama", limit)


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

LOADERS = {
    "locomo": load_locomo,
    "longmemeval": load_longmemeval,
    "beam": load_beam,
    "ama": load_ama,
}


def load_suite(name: str, limit: int | None = None, **kw: Any) -> list[Sample]:
    if name not in LOADERS:
        raise KeyError(f"unknown suite {name!r}; known: {sorted(LOADERS)}")
    return LOADERS[name](limit=limit, **kw)


# --------------------------------------------------------------------------- #
# Synthetic fixture (offline plumbing only -- never publish)
# --------------------------------------------------------------------------- #

_SYNTH_TURNS = [
    ("Alice", "Hey Bob, I just adopted a rescue greyhound. Named her Comet."),
    ("Bob", "Amazing! How old is Comet?"),
    ("Alice", "About four. She's retired from racing."),
    ("Bob", "Nice. Are you still training for the Lisbon half marathon in October?"),
    ("Alice", "Yeah, race is October 12th. Aiming for sub-1:45."),
    ("Bob", "Solid goal. How's the new job at the mapping startup going?"),
    ("Alice", "Good -- I lead the routing team now. My manager is Priya."),
    ("Bob", "Congrats on the promotion. Did you move closer to the office?"),
    ("Alice", "Not yet, still in Alfama. The commute is 25 minutes by tram."),
    ("Bob", "We should grab dinner. You still vegetarian?"),
    ("Alice", "Pescatarian actually since last year. I eat fish now."),
    ("Bob", "Got it. Friday at the seafood place near the river then?"),
    ("Alice", "Perfect. 8pm. Comet can come, they have a patio."),
]

_SYNTH_QA = [
    ("What is the name of Alice's dog?", ["Comet"], "single_hop", False),
    ("When is the Lisbon half marathon Alice is running?", ["October 12th", "October 12"], "temporal", False),
    ("Who is Alice's manager?", ["Priya"], "single_hop", False),
    ("What dietary preference does Alice currently follow?", ["Pescatarian", "pescatarian, eats fish"], "knowledge_update", False),
    ("Which neighbourhood does Alice live in?", ["Alfama"], "single_hop", False),
    ("What is Alice's target finish time for the half marathon?", ["sub-1:45", "under 1:45"], "single_hop", False),
    ("What team does Alice lead at the mapping startup?", ["the routing team", "routing"], "single_hop", False),
    ("How long is Alice's commute by tram?", ["25 minutes"], "single_hop", False),
    ("What is the name of Bob's partner?", [], "adversarial", True),
    ("What car does Alice drive to work?", [], "adversarial", True),
]


def _synthetic_locomo(limit: int | None) -> list[Sample]:
    convo = Conversation(
        conv_id="synthetic-0",
        turns=[Turn(speaker=s, text=t, ts="10:00 am on 3 March, 2026") for s, t in _SYNTH_TURNS],
    )
    out: list[Sample] = []
    for i, (q, a, cat, unans) in enumerate(_SYNTH_QA):
        out.append(
            Sample(
                sample_id=f"synthetic-0::q{i}",
                conversation=convo,
                question=q,
                answers=a,
                category=cat,
                is_unanswerable=unans,
                synthetic=True,
            )
        )
        if limit and len(out) >= limit:
            break
    return out


def is_all_synthetic(samples: Iterable[Sample]) -> bool:
    samples = list(samples)
    return bool(samples) and all(s.synthetic for s in samples)
