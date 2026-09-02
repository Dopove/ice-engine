"""Systems under test.

Every system implements the same tiny protocol so the runner treats them
identically::

    sys.ingest(conversation)        -> None      # load a conversation's turns
    sys.context(question)          -> str        # produce the context block
    sys.reset()                    -> None       # drop state before next convo

The reader model (see :mod:`benchmarks.harness.core`) is applied by the runner
on top of ``context(question)`` -- identical for ICE and every baseline, which
is the apples-to-apples control.

* :class:`ICEAdapter`         -- the real ICE EP engine (pgvector/ONNX retrieval
  + U-Shape attention reorder + saliency compression + anchor injection).
* :class:`VanillaRAGBaseline` -- same ONNX embeddings + same top-k, but ICE's
  enterprise attention layer OFF. Isolates what the attention layer adds.
* :class:`TruncationBaseline` -- no retrieval; most recent turns that fit.
* :class:`NoMemoryBaseline`   -- question only. Floor.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from typing import Any, Protocol

from .core import bootstrap_ice
from .datasets import Conversation

# ICE is imported lazily inside _ensure_kernel() so bootstrap runs first.
_KERNEL: Any = None
_LOOP: asyncio.AbstractEventLoop | None = None


def _loop() -> asyncio.AbstractEventLoop:
    global _LOOP
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
    return _LOOP


def _run(coro):
    return _loop().run_until_complete(coro)


def _ensure_kernel(mode: str = "sandbox"):
    """Boot a single shared ICEKernel for the whole run."""
    global _KERNEL
    if _KERNEL is not None:
        return _KERNEL
    bootstrap_ice(mode)
    from ice.config import settings

    settings.ICE_MODE = mode
    settings.ICE_SKU = "ICE-ENTERPRISE"  # enables U-Shape / compression in the pager
    if mode == "sandbox":
        settings.DATABASE_URL = None
        settings.REDIS_URL = None
    try:
        settings.ICE_USE_ARQ = False
    except Exception:  # noqa: BLE001 - attribute may be read-only in some builds
        pass
    from ice.kernel import ICEKernel

    k = ICEKernel()
    _run(k.connect())
    _KERNEL = k
    return k


def shutdown() -> None:
    global _KERNEL
    if _KERNEL is not None:
        try:
            _run(_KERNEL.disconnect())
        except Exception:  # noqa: BLE001
            pass
        _KERNEL = None


# --------------------------------------------------------------------------- #
# Protocol
# --------------------------------------------------------------------------- #


class System(Protocol):
    name: str

    def ingest(self, conversation: Conversation) -> None: ...
    def context(self, question: str) -> str: ...
    def reset(self) -> None: ...


# --------------------------------------------------------------------------- #
# ICE EP
# --------------------------------------------------------------------------- #


class ICEAdapter:
    """Drives the real ICE EP engine through its public retrieval + pager API."""

    def __init__(
        self,
        mode: str = "sandbox",
        top_k: int = 6,
        model_id: str = "gpt-4o",
        max_input_tokens: int = 16000,
        context_mode: str = "packed",
    ) -> None:
        self.name = "ice"
        self.mode = mode
        self.top_k = top_k
        self.model_id = model_id
        self.max_input_tokens = max_input_tokens
        self.context_mode = context_mode  # "packed" (ContextPager) | "hits" (raw retrieved)
        self.kernel = _ensure_kernel(mode)
        self.tenant = str(uuid.uuid4())
        self.session = "conv"
        self.user = "bench-user"
        self._turns: list[dict[str, str]] = []

    # -- ingestion ---------------------------------------------------------- #
    def ingest(self, conversation: Conversation) -> None:
        async def _go() -> None:
            emb = self.kernel.embedder
            for turn in conversation.turns:
                text = f"{turn.speaker}: {turn.text}" if turn.speaker else turn.text
                vec = await emb.embed_async(text)
                await self.kernel.episodic._save_to_db(
                    self.tenant, self.session, "default", "user", text, vec, self.user, {}
                )
                self._turns.append({"role": "user", "content": text})

        _run(_go())

    # -- retrieval + packing --------------------------------------------------- #
    def _retrieve(self, question: str):
        async def _go():
            emb = self.kernel.embedder
            qv = await emb.embed_async(question)
            hits = await self.kernel.episodic.search_episodic(
                self.tenant, qv, self.session, user_id=self.user, limit=self.top_k
            )
            hist = await self.kernel.episodic.get_history(
                self.tenant, self.session, user_id=self.user, limit=50
            )
            return qv, hits, hist

        return _run(_go())

    def context(self, question: str) -> str:
        qv, hits, hist = self._retrieve(question)
        if self.context_mode == "hits":
            # Feed the reader ICE's retrieved turns directly, skipping the
            # ContextPager compression/truncation stage.
            return "\n".join(f"- {h.get('content', '')}" for h in hits).strip()
        messages, _tokens, _budget = self.kernel.pager.assemble_prompt(
            current_request=[{"role": "user", "content": question}],
            historical_messages=hist,
            retrieved_insights=hits,
            model_id=self.model_id,
            max_input_tokens=self.max_input_tokens,
            query_vector=qv,
        )
        # The pager returns [system_instruction, context_message, ...history, user].
        # Keep only the organised context payload, not ICE's answer-scaffold
        # instruction. The payload is the system message carrying the context
        # markers ("### PROVIDED CONTEXT ###" / "PROVIDED CONTEXT").
        sys_msgs = [m.get("content", "") for m in messages if m.get("role") == "system"]
        payload = ""
        for c in sys_msgs:
            if "### PROVIDED CONTEXT" in c or c.lstrip().startswith("###"):
                payload = c
                break
        if not payload and len(sys_msgs) > 1:
            payload = "\n\n".join(sys_msgs[1:])
        payload = re.sub(r"#+\s*(END\s+)?(PROVIDED\s+)?CONTEXT\s*#+", "", payload, flags=re.I)
        payload = re.sub(r"#+\s*FRAGMENT[0-9a-f-]*\s*#+", "", payload, flags=re.I)
        if not payload.strip():
            # Fall back to the raw hits so ICE is never handed an empty context.
            payload = "\n".join(f"- {h.get('content', '')}" for h in hits)
        return payload.strip()

    def reset(self) -> None:
        async def _go() -> None:
            try:
                await self.kernel.episodic.purge_user(self.tenant, self.user)
            except Exception:  # noqa: BLE001 - best effort between conversations
                pass

        _run(_go())
        self.tenant = str(uuid.uuid4())
        self._turns.clear()


# --------------------------------------------------------------------------- #
# Baselines
# --------------------------------------------------------------------------- #


class NoMemoryBaseline:
    name = "no_memory"

    def ingest(self, conversation: Conversation) -> None:  # noqa: D401 - no-op
        pass

    def context(self, question: str) -> str:
        return ""

    def reset(self) -> None:
        pass


class TruncationBaseline:
    """Most-recent turns that fit a character budget (~ a context window)."""

    def __init__(self, char_budget: int = 12_000) -> None:
        self.name = "recency_truncation"
        self.char_budget = char_budget
        self._turns: list[str] = []

    def ingest(self, conversation: Conversation) -> None:
        for t in conversation.turns:
            self._turns.append(f"{t.speaker}: {t.text}" if t.speaker else t.text)

    def context(self, question: str) -> str:
        out, total = [], 0
        for line in reversed(self._turns):
            if total + len(line) > self.char_budget:
                break
            out.append(line)
            total += len(line)
        return "\n".join(reversed(out))

    def reset(self) -> None:
        self._turns.clear()


class VanillaRAGBaseline:
    """Same ONNX embeddings + same top-k as ICE, no attention/compression layer.

    Reuses ICE's embedder and episodic vector search, then concatenates the raw
    hits newest-first. The delta between this and :class:`ICEAdapter` is exactly
    ICE's U-Shape reorder + saliency compression + anchor injection.
    """

    def __init__(self, mode: str = "sandbox", top_k: int = 6) -> None:
        self.name = "vanilla_rag"
        self.top_k = top_k
        self.kernel = _ensure_kernel(mode)
        self.tenant = str(uuid.uuid4())
        self.session = "conv"
        self.user = "bench-user"

    def ingest(self, conversation: Conversation) -> None:
        async def _go() -> None:
            emb = self.kernel.embedder
            for turn in conversation.turns:
                text = f"{turn.speaker}: {turn.text}" if turn.speaker else turn.text
                vec = await emb.embed_async(text)
                await self.kernel.episodic._save_to_db(
                    self.tenant, self.session, "default", "user", text, vec, self.user, {}
                )

        _run(_go())

    def context(self, question: str) -> str:
        async def _go():
            emb = self.kernel.embedder
            qv = await emb.embed_async(question)
            return await self.kernel.episodic.search_episodic(
                self.tenant, qv, self.session, user_id=self.user, limit=self.top_k
            )

        hits = _run(_go())
        return "\n".join(f"- {h.get('content', '')}" for h in hits)

    def reset(self) -> None:
        async def _go() -> None:
            try:
                await self.kernel.episodic.purge_user(self.tenant, self.user)
            except Exception:  # noqa: BLE001
                pass

        _run(_go())
        self.tenant = str(uuid.uuid4())


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #

_BUILTIN = {
    "ice": lambda **kw: ICEAdapter(**kw),
    "vanilla_rag": lambda **kw: VanillaRAGBaseline(mode=kw.get("mode", "sandbox"), top_k=kw.get("top_k", 6)),
    "recency_truncation": lambda **kw: TruncationBaseline(),
    "no_memory": lambda **kw: NoMemoryBaseline(),
}


def build_systems(names: list[str], *, mode: str = "sandbox", top_k: int = 6) -> list[System]:
    out: list[System] = []
    for n in names:
        if n == "mem0":
            try:
                from .mem0_adapter import Mem0Adapter  # optional dep

                out.append(Mem0Adapter(top_k=top_k))
            except RuntimeError as exc:
                print(f"[build_systems] skipping 'mem0': {exc}")
        elif n in _BUILTIN:
            out.append(_BUILTIN[n](mode=mode, top_k=top_k))
        else:
            raise KeyError(f"unknown system {n!r}; known: {sorted(_BUILTIN) + ['mem0']}")
    return out
