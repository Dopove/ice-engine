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
    dia_id: str | None = None  # LoCoMo dialogue id, e.g. "D1:3"
    session_id: str | None = None  # LongMemEval haystack session id


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
    evidence: list[str] = dataclasses.field(default_factory=list)  # gold dia_ids
    answer_session_ids: list[str] = dataclasses.field(default_factory=list)  # LongMemEval gold sessions
    session_ids: list[str] = dataclasses.field(default_factory=list)  # all haystack session ids


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
                    dia_id=msg.get("dia_id"),
                )
            )
    return turns


def load_locomo(
    limit: int | None = None, allow_synthetic: bool = True, seed: int | None = 20260902, **_: Any
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
                    evidence=[str(e) for e in qa.get("evidence", [])],
                )
            )
    return _subsample(samples, limit, seed)


# --------------------------------------------------------------------------- #
# LongMemEval
# --------------------------------------------------------------------------- #


def load_longmemeval(
    limit: int | None = None, variant: str = "s", seed: int | None = 20260902, **_: Any
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
        sessions = entry.get("haystack_sessions", [])
        sess_ids = [str(s) for s in entry.get("haystack_session_ids", [])]
        turns: list[Turn] = []
        for i, sess in enumerate(sessions):
            sid = sess_ids[i] if i < len(sess_ids) else f"sess_{i}"
            for msg in sess:
                turns.append(
                    Turn(
                        speaker=str(msg.get("role", "")),
                        text=str(msg.get("content", "")),
                        session_id=sid,
                    )
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
                answer_session_ids=[str(s) for s in entry.get("answer_session_ids", [])],
                session_ids=sess_ids,
            )
        )
        if limit and len(samples) >= limit:
            break
    return samples


# --------------------------------------------------------------------------- #
# BEAM / AMA-Bench
# --------------------------------------------------------------------------- #

_BEAM_SCALES = ("100K", "500K", "1M", "10M")


def _beam_turns(chat_json: Any) -> list[Turn]:
    turns: list[Turn] = []
    batches = chat_json if isinstance(chat_json, list) else [chat_json]
    for batch in batches:
        for group in batch.get("turns", []):
            for msg in group if isinstance(group, list) else [group]:
                turns.append(
                    Turn(
                        speaker=str(msg.get("role", "")),
                        text=str(msg.get("content", "")),
                        ts=msg.get("time_anchor"),
                    )
                )
    return turns


def load_beam(
    limit: int | None = None, seed: int | None = 20260902, scale: str = "100K", **_: Any
) -> list[Sample]:
    """BEAM (ICLR 2026), mohammadtavakoli78/BEAM.

    Expects the vendored tree ``data/beam/chats/<scale>/<id>/`` with ``chat.json``
    and ``probing_questions/probing_questions.json``. ``scale`` in 100K / 500K /
    1M / 10M -- pick per the token budget you can actually ingest.
    """
    root = DATA_DIR / "beam" / "chats" / scale
    ids = sorted((p for p in root.glob("*") if p.is_dir()), key=lambda p: int(p.name) if p.name.isdigit() else p.name) if root.exists() else []
    if not ids:
        raise DatasetUnavailable(
            f"BEAM scale {scale} not found under {root}/. Vendor "
            f"mohammadtavakoli78/BEAM `chats/{scale}/<id>/` (chat.json + "
            f"probing_questions/probing_questions.json). The run will record a skip."
        )
    samples: list[Sample] = []
    for d in ids:
        chat_p = d / "chat.json"
        pq_p = d / "probing_questions" / "probing_questions.json"
        if not (chat_p.exists() and pq_p.exists()):
            continue
        convo = Conversation(conv_id=f"{scale}/{d.name}", turns=_beam_turns(json.loads(chat_p.read_text())))
        pq = json.loads(pq_p.read_text())
        for task_type, items in (pq.items() if isinstance(pq, dict) else []):
            unans = task_type == "abstention"
            for i, qa in enumerate(items):
                ans = qa.get("ideal_response", qa.get("answer", ""))
                samples.append(
                    Sample(
                        sample_id=f"{convo.conv_id}::{task_type}::{i}",
                        conversation=convo,
                        question=str(qa.get("question", "")),
                        answers=[str(ans)] if ans and not unans else [],
                        category=str(task_type),
                        is_unanswerable=unans,
                    )
                )
    if not samples:
        raise DatasetUnavailable(f"BEAM scale {scale}: no usable chat/probing pairs under {root}/.")
    return _subsample(samples, limit, seed)


def load_ama(
    limit: int | None = None,
    seed: int | None = 20260902,
    task_types: str | None = None,
    **_: Any,
) -> list[Sample]:
    """AMA-Bench (ICML 2026), AMA-bench/AMA-bench on HuggingFace.

    Expects ``data/ama/open_end_qa_set.jsonl`` (the released test split). Each
    line is an agentic *episode*: a ``trajectory`` of ``{action, observation}``
    steps plus 12 ``qa_pairs``. ``task_types`` (comma list) filters to e.g.
    ``swebench,webarena`` -- the tool-call-heavy agentic tracks.
    """
    path = DATA_DIR / "ama" / "open_end_qa_set.jsonl"
    if not path.exists():
        raise DatasetUnavailable(
            f"AMA-Bench not found at {path}. `huggingface-cli download "
            f"AMA-bench/AMA-bench --repo-type dataset` and place "
            f"`test/open_end_qa_set.jsonl` there. The run will record a skip."
        )
    wanted = {t.strip() for t in task_types.split(",")} if task_types else None
    samples: list[Sample] = []
    for line in path.read_text().splitlines():
        try:
            ep = json.loads(line)
        except json.JSONDecodeError:
            continue  # a few released rows are malformed; skip, don't fabricate
        tt = str(ep.get("task_type", "ama"))
        if wanted and tt not in wanted:
            continue
        turns: list[Turn] = []
        for step in ep.get("trajectory", []):
            if step.get("action") is not None:
                turns.append(Turn(speaker="agent", text=f"action: {step['action']}"))
            if step.get("observation") is not None:
                turns.append(Turn(speaker="env", text=f"observation: {step['observation']}"))
        convo = Conversation(conv_id=f"{tt}/{ep.get('episode_id')}", turns=turns)
        for i, qa in enumerate(ep.get("qa_pairs", [])):
            ans = qa.get("answer", "")
            samples.append(
                Sample(
                    sample_id=f"{convo.conv_id}::q{qa.get('question_uuid', i)}",
                    conversation=convo,
                    question=str(qa.get("question", "")),
                    answers=[str(ans)] if ans else [],
                    category=tt,
                )
            )
    if not samples:
        raise DatasetUnavailable(
            f"AMA-Bench: no episodes matched (task_types={task_types!r}) in {path}."
        )
    return _subsample(samples, limit, seed)


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
