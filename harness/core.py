"""Foundational primitives for the ICE benchmark harness.

Three concerns live here so the rest of the harness has a single import:

* :func:`bootstrap_ice` -- neutralise the ICE license gate and force the
  in-process sandbox substrate *before* ``ice`` is imported anywhere.
* string-answer metrics -- :func:`score_answer`, :func:`abstention_scores`
  (SQuAD-style normalised F1 / exact-match / recall, plus abstention P/R/F1).
* :class:`LLMClient` -- an OpenAI-compatible chat client (OpenRouter free tier
  by default) with an on-disk response cache and a hard daily call budget, plus
  a zero-cost :class:`MockClient` for plumbing tests.

Nothing here imports ``ice``; :func:`bootstrap_ice` only prepares ``os.environ``
and ``sys.modules`` so the caller can import the engine afterwards.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import os
import re
import string
import sys
import time
import types
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

HARNESS_DIR = Path(__file__).resolve().parent
BENCH_DIR = HARNESS_DIR.parent
REPO_ROOT = BENCH_DIR.parent
RESULTS_DIR = BENCH_DIR / "results"
CACHE_DIR = RESULTS_DIR / "cache"
DATA_DIR = HARNESS_DIR / "datasets" / "data"


def _utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# ICE bootstrap  (license gate bypass + sandbox substrate)
# --------------------------------------------------------------------------- #

_BOOTSTRAPPED = False


def bootstrap_ice(mode: str | None = None) -> None:
    """Prepare the process so ``import ice`` works offline with no license.

    * ``ice.build_config`` is replaced in ``sys.modules`` with ``ICE_SKU =
      "ICE-UNLIMITED"`` so ``SecurityManager.verify_or_exit`` returns instead of
      calling ``sys.exit`` (identical technique to
      ``tests/legacy_broken/test_licensing.py``).
    * ``ICE_MODE`` defaults to ``sandbox`` -> aiosqlite ``:memory:`` +
      ``InMemoryRedis``, so no Postgres / Redis / AWS is touched.
    * ``ICE_USE_ARQ=0`` so ``save_message``'s async flush runs inline instead of
      trying to reach an arq broker.

    Call once, before importing anything from ``ice``. Idempotent.
    """
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    mode = (mode or os.environ.get("ICE_MODE") or "sandbox").lower()
    os.environ["ICE_MODE"] = mode
    os.environ.setdefault("ICE_USE_ARQ", "0")
    os.environ.setdefault("ICE_ENABLE_CRASH_REPORTING", "0")
    os.environ.setdefault("ICE_ENABLE_TRACING", "0")
    if mode == "sandbox":
        # Force the sandbox branch in ICEKernel (`sandbox_mode = ... or not db_url`).
        os.environ["DATABASE_URL"] = ""
        os.environ["REDIS_URL"] = ""

    if "ice.build_config" not in sys.modules:
        bc = types.ModuleType("ice.build_config")
        bc.ICE_SKU = "ICE-UNLIMITED"  # full bypass in verify_or_exit()
        bc.BUILD_VERSION = "3.1.75"
        sys.modules["ice.build_config"] = bc

    # Stub heavy deps that ``import ice`` chains into but the benchmark never
    # calls (multimodal doc ingestion). Avoids installing raganything + torch.
    class _Inert:  # accepts any construction / call / attribute, does nothing
        def __init__(self, *a, **k):
            pass

        def __call__(self, *a, **k):
            return _Inert()

        def __getattr__(self, n):
            return _Inert()

    for name in ("raganything",):
        if name not in sys.modules:
            m = types.ModuleType(name)
            m.__getattr__ = lambda n: _Inert
            sys.modules[name] = m

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    _BOOTSTRAPPED = True


# --------------------------------------------------------------------------- #
# Answer metrics  (SQuAD / LongMemEval style)
# --------------------------------------------------------------------------- #

_ARTICLES = re.compile(r"\b(a|an|the)\b", re.UNICODE)
_WS = re.compile(r"\s+")
_ABSTAIN_PAT = re.compile(
    r"\b(i (do not|don't) know|cannot (be )?(answer|deter)|"
    r"no (information|answer|record|mention)|not (enough|sufficient) (info|context|information)|"
    r"unanswerable|not (stated|provided|mentioned|available|specified)|"
    r"there is no (information|mention|record))\b",
    re.IGNORECASE,
)


def normalize_answer(s: str) -> str:
    """Lowercase, strip punctuation / articles / extra whitespace (SQuAD)."""
    s = s or ""
    s = s.lower()
    s = "".join(ch for ch in s if ch not in string.punctuation)
    s = _ARTICLES.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def _tokens(s: str) -> list[str]:
    return normalize_answer(s).split()


def exact_match(pred: str, gold: str) -> float:
    return float(normalize_answer(pred) == normalize_answer(gold))


def f1_score(pred: str, gold: str) -> float:
    p, g = _tokens(pred), _tokens(gold)
    if not p and not g:
        return 1.0
    if not p or not g:
        return 0.0
    common = Counter(p) & Counter(g)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(p)
    recall = overlap / len(g)
    return 2 * precision * recall / (precision + recall)


def recall_score(pred: str, gold: str) -> float:
    """Fraction of gold tokens present in the prediction (order-free)."""
    p, g = Counter(_tokens(pred)), _tokens(gold)
    if not g:
        return 1.0
    hit = sum(1 for tok in g if p.get(tok, 0) > 0)
    return hit / len(g)


def looks_like_abstention(pred: str) -> bool:
    return bool(_ABSTAIN_PAT.search(pred or ""))


def score_answer(pred: str, gold: str | Sequence[str]) -> dict[str, float]:
    """Best-over-aliases F1 / EM / recall for one prediction."""
    golds = [gold] if isinstance(gold, str) else list(gold)
    golds = [g for g in golds if g is not None] or [""]
    best = max(
        (
            {
                "f1": f1_score(pred, g),
                "em": exact_match(pred, g),
                "recall": recall_score(pred, g),
            }
            for g in golds
        ),
        key=lambda d: (d["f1"], d["em"], d["recall"]),
    )
    best["abstained"] = float(looks_like_abstention(pred))
    return best


def abstention_scores(rows: Iterable[dict[str, Any]]) -> dict[str, float]:
    """Precision / recall / F1 of abstaining on the unanswerable subset.

    ``rows`` items need ``is_unanswerable`` (bool) and ``abstained`` (0/1).
    """
    rows = list(rows)
    tp = sum(1 for r in rows if r["is_unanswerable"] and r["abstained"])
    fp = sum(1 for r in rows if not r["is_unanswerable"] and r["abstained"])
    fn = sum(1 for r in rows if r["is_unanswerable"] and not r["abstained"])
    n_unans = tp + fn
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / n_unans if n_unans else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {
        "abstention_precision": round(prec, 4),
        "abstention_recall": round(rec, 4),
        "abstention_f1": round(f1, 4),
        "n_unanswerable": n_unans,
    }


def aggregate(scores: Sequence[dict[str, float]]) -> dict[str, float]:
    if not scores:
        return {"f1": 0.0, "em": 0.0, "recall": 0.0, "n": 0}
    n = len(scores)
    return {
        "f1": round(sum(s["f1"] for s in scores) / n, 4),
        "em": round(sum(s["em"] for s in scores) / n, 4),
        "recall": round(sum(s["recall"] for s in scores) / n, 4),
        "n": n,
    }


# --------------------------------------------------------------------------- #
# Budget guard
# --------------------------------------------------------------------------- #


class BudgetExceeded(RuntimeError):
    """Raised when the daily API call budget is spent (caught by the runner)."""


class Budget:
    """Persistent per-day counter so repeated CI runs share one free-tier quota.

    State file: ``results/cache/budget-YYYY-MM-DD.json``. A cache *hit* never
    counts; only a real network call calls :meth:`spend`.
    """

    def __init__(self, daily_limit: int | None = None) -> None:
        self.daily_limit = int(
            daily_limit
            if daily_limit is not None
            else os.environ.get("BENCH_DAILY_CALL_BUDGET", "45")
        )
        self.today = _dt.date.today().isoformat()
        self.path = CACHE_DIR / f"budget-{self.today}.json"
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                st = json.loads(self.path.read_text())
                if st.get("date") == self.today:
                    return st
            except (json.JSONDecodeError, OSError):
                pass
        return {"date": self.today, "calls": 0, "limit": self.daily_limit}

    def _save(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._state, indent=2))

    @property
    def used(self) -> int:
        return int(self._state.get("calls", 0))

    @property
    def remaining(self) -> int:
        return max(0, self.daily_limit - self.used)

    def check(self) -> None:
        if self.remaining <= 0:
            raise BudgetExceeded(
                f"daily API budget spent ({self.used}/{self.daily_limit} on {self.today}); "
                f"partial results were written -- re-run tomorrow to extend the sample"
            )

    def spend(self, n: int = 1) -> None:
        self._state["calls"] = self.used + n
        self._save()


# --------------------------------------------------------------------------- #
# LLM clients
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class LLMResult:
    text: str
    usage: dict[str, int]
    cached: bool
    model: str


class MockClient:
    """Deterministic, offline, zero-cost 'reader'.

    Heuristic: echo the shortest sentence in the provided context that shares the
    most content words with the question; otherwise abstain. Good enough to
    exercise the full pipeline (retrieve -> pack -> score -> summary) without a
    network or a GPU. Never use its numbers for anything public.
    """

    model = "mock"

    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def chat(self, prompt: str, system: str | None = None, **_: Any) -> LLMResult:
        # Only look at the CONTEXT block of the runner's prompt, never the
        # system instructions (otherwise the heuristic echoes those).
        m = re.search(r"CONTEXT:\s*(.*?)\s*QUESTION:", prompt, re.DOTALL)
        ctx = m.group(1) if m else prompt
        q_line = prompt.strip().splitlines()[-1] if prompt.strip() else prompt
        q_words = set(_tokens(q_line)) - {
            "what", "when", "who", "where", "why", "how", "is", "are", "was",
            "did", "do", "does", "the", "of", "in", "on", "your", "my",
        }
        sentences = re.split(r"(?<=[.!?])\s+|\n+", ctx)
        best, best_score = None, 0
        for sent in sentences:
            if len(sent) > 400 or not sent.strip():
                continue
            overlap = len(q_words & set(_tokens(sent)))
            if overlap > best_score:
                best, best_score = sent.strip(), overlap
        text = best if best and best_score >= 1 else "I don't know based on the provided context."
        return LLMResult(text=text, usage={"prompt_tokens": 0, "completion_tokens": 0}, cached=True, model=self.model)

    # judge parity with LLMClient -------------------------------------------- #
    def judge(self, question: str, gold: str, pred: str, **_: Any) -> LLMResult:
        ok = bool(set(_tokens(gold)) & set(_tokens(pred))) or (
            looks_like_abstention(pred) and not gold.strip()
        )
        return LLMResult(text="CORRECT" if ok else "INCORRECT", usage={"prompt_tokens": 0, "completion_tokens": 0}, cached=True, model=self.model)


class LLMClient:
    """OpenAI-compatible chat client with disk cache + daily budget.

    Defaults target OpenRouter's free tier. A response is cached by
    ``sha256(model | system | prompt)`` so re-runs (and the CI's daily
    accumulation) never re-spend a call. Set ``BENCH_LLM_API_KEY`` (and
    optionally ``BENCH_LLM_BASE_URL`` / ``BENCH_LLM_MODEL``) in the environment.
    """

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        budget: Budget | None = None,
        max_tokens: int = 256,
        temperature: float = 0.0,
        cache_name: str | None = None,
    ) -> None:
        self.model = model or os.environ.get("BENCH_LLM_MODEL", "minimax/minimax-m3:free")
        self.base_url = base_url or os.environ.get(
            "BENCH_LLM_BASE_URL", "https://openrouter.ai/api/v1"
        )
        self.api_key = api_key or os.environ.get("BENCH_LLM_API_KEY", "")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.budget = budget or Budget()
        slug = re.sub(r"[^a-z0-9]+", "-", (cache_name or self.model).lower()).strip("-")
        self.cache_path = CACHE_DIR / f"llm-{slug}.json"
        self._cache = self._load_cache()
        self._client = None  # lazy openai client

    # -- cache ------------------------------------------------------------- #
    def _load_cache(self) -> dict[str, Any]:
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_cache(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._cache, indent=1, sort_keys=True))
        tmp.replace(self.cache_path)

    @staticmethod
    def _key(model: str, system: str, prompt: str) -> str:
        h = hashlib.sha256()
        h.update(model.encode())
        h.update(b"\x00")
        h.update((system or "").encode())
        h.update(b"\x00")
        h.update(prompt.encode())
        return h.hexdigest()

    # -- transport ------------------------------------------------------------ #
    def _openai(self):
        if self._client is None:
            from openai import OpenAI  # deferred; only needed for real calls

            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "dummy",
                timeout=float(os.environ.get("BENCH_LLM_TIMEOUT", "90")),
                max_retries=0,  # LLMClient._raw_chat owns retry/backoff
            )
        return self._client

    @staticmethod
    def _is_rate_limit(exc: Exception) -> bool:
        s = f"{type(exc).__name__} {exc}".lower()
        return (
            "ratelimit" in s
            or "rate limit" in s
            or "429" in s
            or "freeusagelimit" in s
            or "quota" in s
        )

    def _raw_chat(self, messages: list[dict[str, str]], max_tokens: int) -> LLMResult:
        last_err: Exception | None = None
        for attempt in range(6):
            try:
                resp = self._openai().chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    extra_headers={
                        "HTTP-Referer": "https://github.com/Dopove/ICE",
                        "X-Title": "ICE-benchmarks",
                    },
                )
                choice = resp.choices[0].message.content or ""
                usage = getattr(resp, "usage", None)
                u = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                    "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
                }
                return LLMResult(text=choice.strip(), usage=u, cached=False, model=self.model)
            except Exception as exc:  # noqa: BLE001 - classify below
                last_err = exc
                s = f"{type(exc).__name__} {exc}".lower()
                if any(k in s for k in ("connection", "refused", "name or service", "timed out", "timeout")):
                    # Endpoint unreachable -- don't burn 60s of backoff per call.
                    raise BudgetExceeded(
                        f"reader endpoint unreachable ({self.base_url}): {exc}"
                    ) from exc
                if self._is_rate_limit(exc):
                    # Free-tier daily/window limit. Back off harder; after a
                    # couple of tries give up cleanly (runner writes partial).
                    if attempt >= 1:
                        raise BudgetExceeded(
                            f"provider rate/usage limit reached ({exc}); partial results written"
                        ) from exc
                    time.sleep(45)
                else:
                    time.sleep(2 ** attempt + 0.5)
        raise BudgetExceeded(f"LLM call failed after retries: {last_err!r}")

    def _call(self, system: str | None, prompt: str, max_tokens: int) -> LLMResult:
        key = self._key(self.model, system or "", prompt)
        if key in self._cache:
            c = self._cache[key]
            return LLMResult(text=c["text"], usage=c.get("usage", {}), cached=True, model=self.model)
        self.budget.check()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        res = self._raw_chat(messages, max_tokens)
        self.budget.spend(1)
        self._cache[key] = {"text": res.text, "usage": res.usage, "model": self.model, "ts": _utcnow()}
        self._save_cache()
        return res

    # -- public --------------------------------------------------------------- #
    def chat(self, prompt: str, system: str | None = None, max_tokens: int | None = None) -> LLMResult:
        return self._call(system, prompt, max_tokens or self.max_tokens)

    def judge(self, question: str, gold: str, pred: str) -> LLMResult:
        system = (
            "You are a strict grader for a question-answering benchmark. "
            "Given the QUESTION, the reference GOLD answer, and a candidate ANSWER, "
            "reply with exactly one word: CORRECT if the candidate conveys the same "
            "information as the gold answer (paraphrase is fine), otherwise INCORRECT. "
            "If the gold answer indicates the question is unanswerable, then an answer "
            "that declines / says it doesn't know is CORRECT."
        )
        prompt = f"QUESTION: {question}\nGOLD: {gold}\nANSWER: {pred}\nVERDICT (one word):"
        return self._call(system, prompt, 12)


def make_client(kind: str, **kw: Any):
    """``kind`` in {"openrouter", "api", "mock"}."""
    if kind in ("mock", "offline", "none"):
        return MockClient()
    return LLMClient(**kw)
