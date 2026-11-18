"""Systems under test.

Every system implements same tiny protocol runner treats them
identically::

sys.ingest(conversation) -> None   # load conversation's turns
sys.context(question) -> str       # produce context block
sys.reset() -> None                # drop state before next convo

The reader model (see :mod:`benchmarks.harness.core`) applied runner
on top ``context(question)`` -- identical for ICE and every baseline, which
is the apples-to-apples control.

* :class:`ICEAdapter`         -- the real ICE engine (pgvector/ONNX retrieval
  + U-Shape attention reorder + saliency compression + anchor injection).
* :class:`CommunityICEAdapter`  -- ICE-COMMUNITY SKU, works on community/oss branch.
  Falls back gracefully when Enterprise features (U-Shape, saliency, anchors) unavailable.
  Registers as "ice_community" in _BUILTIN.
* :class:`OSSICEAdapter`        -- ICE-OSS SKU (same as ICE-COMMUNITY), works on
  ice_nexus package (zero-config). Registers as "ice_oss" in _BUILTIN.
* :class:`VanillaRAGBaseline` -- same ONNX embeddings + same top-k, but ICE's
  enterprise attention layer OFF. Isolates what the attention layer adds.
* :class:`TruncationBaseline` -- no retrieval; most recent turns that fit.
* :class:`NoMemoryBaseline`   -- question only. Floor.
"""

from __future__ import annotations

import asyncio
import os
import re
import uuid
from contextlib import contextmanager
from typing import Any, Protocol

from .core import bootstrap_ice
from .datasets import Conversation

# ICE imported lazily inside _ensure_kernel() bootstrap runs first.
_KERNEL: Any = None
_LOOP: asyncio.AbstractEventLoop | None = None


def _loop() -> asyncio.AbstractEventLoop:
    global _LOOP
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
    return _LOOP


def _run(coro):
    return _loop().run_until_complete(coro)


@contextmanager
def _compression_threshold(value: float | None):
    """Temporarily set ICE_COMPRESSION_THRESHOLD for ICE pager."""
    if value is None:
        yield
        return
    key = "ICE_COMPRESSION_THRESHOLD"
    prev = os.environ.get(key)
    os.environ[key] = str(value)
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev


# --------------------------------------------------------------------------- #
# Protocol
# --------------------------------------------------------------------------- #

class System(Protocol):
    name: str
    def ingest(self, conversation: Conversation) -> None: ...
    def context(self, question: str) -> str: ...
    def reset(self) -> None: ...


# --------------------------------------------------------------------------- #
# Common ICE bootstrap
# --------------------------------------------------------------------------- #

def _ensure_kernel(mode: str = "sandbox") -> Any:
    """Boot single shared ICEKernel whole run."""
    global _KERNEL
    if _KERNEL is not None:
        return _KERNEL
    bootstrap_ice(mode)
    from ice.config import settings

    settings.ICE_MODE = mode
    settings.ICE_SKU = "ICE-ENTERPRISE"  # enables U-Shape / compression pager
    if mode == "sandbox":
        settings.DATABASE_URL = None
        settings.REDIS_URL = None
        try:
            settings.ICE_USE_ARQ = False
        except Exception:  # noqa: BLE001 attribute read-only some builds
            pass
    from ice.kernel import ICEKernel

    k = ICEKernel()
    _run(k.connect())
    _KERNEL = k
    return k


# --------------------------------------------------------------------------- #
# Enterprise ICEAdapter (pgvector/ONNX + U-Shape + saliency + anchors)
# --------------------------------------------------------------------------- #

class ICEAdapter:
    """Full ICE Enterprise pipeline (default reference system)."""

    def __init__(
        self,
        *,
        mode: str = "sandbox",
        top_k: int = 6,
        context_mode: str = "packed",
        compression_threshold: float | None = 0.1,
        model_id: str = "gpt-4o-mini",
        max_input_tokens: int = 8192,
    ):
        self.name = "ice"
        self.mode = mode
        self.top_k = top_k
        self.context_mode = context_mode
        self.compression_threshold = compression_threshold
        self.model_id = model_id
        self.max_input_tokens = max_input_tokens
        self.tenant = str(uuid.uuid4())
        self.user = "bench_user"
        self.session = str(uuid.uuid4())
        self.kernel = _ensure_kernel(mode)

    def ingest(self, conversation: Conversation) -> None:
        async def _go() -> None:
            for turn in conversation.turns:
                await self.kernel.ingest(
                    content=turn.content,
                    tenant_id=self.tenant,
                    session_id=self.session,
                    user_id=self.user,
                    metadata=turn.metadata or {},
                )
        _run(_go())

    def _retrieve(self, question: str):
        async def _go():
            qv = await self.kernel.embed(question)
            hits = await self.kernel.retrieve(
                self.tenant, qv, self.session, user_id=self.user, limit=self.top_k
            )
            hist = await self.kernel.history(
                self.tenant, self.session, user_id=self.user, limit=100
            )
            return qv, hits, hist
        return _run(_go())

    def context(self, question: str) -> str:
        with _compression_threshold(self.compression_threshold):
            return self._context(question)

    def _context(self, question: str) -> str:
        qv, hits, hist = self._retrieve(question)
        if self.context_mode == "hits":
            # Feed reader ICE's retrieved turns directly, skipping the
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
        # pager returns [system_instruction, context_message, ...history, user].
        # Keep only organised context payload, not ICE's answer-scaffold
        # instruction. payload = system message carrying context
        # markers ("### PROVIDED CONTEXT ###" / "PROVIDED CONTEXT").
        sys_msgs = [m.get("content", "") for m in messages if m.get("role") == "system"]
        payload = ""
        for c in sys_msgs:
            if "### PROVIDED CONTEXT" in c.lstrip().startswith("###"):
                payload = c
                break
        if not payload and len(sys_msgs) > 1:
            payload = "\n\n".join(sys_msgs[1:])
        payload = re.sub(r"#+\s*(END\s+)?(PROVIDED\s+)?CONTEXT\s*#+", "", payload, flags=re.I)
        payload = re.sub(r"#+\s*FRAGMENT[0-9a-f-]*\s*#+", "", payload, flags=re.I)
        if not payload.strip():
            # Fall back: raw hits — ICE never handed empty context.
            payload = "\n".join(f"- {h.get('content', '')}" for h in hits)
        return payload.strip()

    def reset(self) -> None:
        async def _go() -> None:
            try:
                await self.kernel.episodic.purge_user(self.tenant, self.user)
            except Exception:  # noqa: BLE001
                pass
        _run(_go())
        self.tenant = str(uuid.uuid4())


# --------------------------------------------------------------------------- #
# CommunityICEAdapter — ICE-COMMUNITY SKU
# --------------------------------------------------------------------------- #

class CommunityICEAdapter:
    """
    ICE-COMMUNITY SKU adapter. Works on community/oss branch code.
    Falls back gracefully when Enterprise features (U-Shape, saliency, anchors)
    are unavailable. Uses IndexlessContextClient on community branch.
    Registers as "ice_community" in _BUILTIN.
    """

    def __init__(
        self,
        *,
        mode: str = "sandbox",
        top_k: int = 6,
        context_mode: str = "packed",
        compression_threshold: float | None = 0.1,
        model_id: str = "gpt-4o-mini",
        max_input_tokens: int = 8192,
    ):
        self.name = "ice_community"
        self.mode = mode
        self.top_k = top_k
        self.context_mode = context_mode
        self.compression_threshold = compression_threshold
        self.model_id = model_id
        self.max_input_tokens = max_input_tokens
        self.tenant = str(uuid.uuid4())
        self.user = "bench_user"
        self.session = str(uuid.uuid4())
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize the community client (IndexlessContextClient)."""
        bootstrap_ice(self.mode)
        try:
            import ice
            # Try community branch client first
            if hasattr(ice, "IndexlessContextClient"):
                kernel = ice.get_client() if hasattr(ice, "get_client") else ice.init(mode=self.mode)
                self.client = ice.IndexlessContextClient(kernel)
            elif hasattr(ice, "IndexlessContextClient"):
                # Fallback to OSS client if community client not available
                kernel = ice.get_client() if hasattr(ice, "get_client") else ice.init(mode=self.mode)
                self.client = ice.IndexlessContextClient(kernel)
            else:
                raise RuntimeError("No suitable ICE client found in community branch")
        except Exception:
            # Graceful fallback: if community features unavailable,
            # fall back to basic retrieval (VanillaRAG-like behavior)
            self.client = None
            self._fallback_mode = True

    def ingest(self, conversation: Conversation) -> None:
        if not self.client:
            # No-op in fallback mode - VanillaRAGBaseline handles basic retrieval
            return
        async def _go() -> None:
            for turn in conversation.turns:
                await self.client.ingest(
                    file_path=turn.content,  # Using content as file_path for text
                    session_id=self.session,
                    x_user_id=self.user,
                    metadata=turn.metadata or {},
                )
        _run(_go())

    def _retrieve(self, question: str):
        if not self.client:
            return None, [], []
        async def _go():
            # Use the client's retrieval method
            qv = await self.client.kernel.embed(question)
            hits = await self.client.kernel.retrieve(
                self.tenant, qv, self.session, user_id=self.user, limit=self.top_k
            )
            hist = await self.client.kernel.history(
                self.tenant, self.session, user_id=self.user, limit=100
            )
            return qv, hits, hist
        return _run(_go())

    def context(self, question: str) -> str:
        if not self.client:
            # Fallback: return empty context - runner will handle fallback
            return ""
        with _compression_threshold(self.compression_threshold):
            return self._context(question)

    def _context(self, question: str) -> str:
        qv, hits, hist = self._retrieve(question)
        if not qv:
            return ""
        if self.context_mode == "hits":
            return "\n".join(f"- {h.get('content', '')}" for h in hits).strip()
        messages, _tokens, _budget = self.client.kernel.pager.assemble_prompt(
            current_request=[{"role": "user", "content": question}],
            historical_messages=hist,
            retrieved_insights=hits,
            model_id=self.model_id,
            max_input_tokens=self.max_input_tokens,
            query_vector=qv,
        )
        sys_msgs = [m.get("content", "") for m in messages if m.get("role") == "system"]
        payload = ""
        for c in sys_msgs:
            if "### PROVIDED CONTEXT" in c.lstrip().startswith("###"):
                payload = c
                break
        if not payload and len(sys_msgs) > 1:
            payload = "\n\n".join(sys_msgs[1:])
        payload = re.sub(r"#+\s*(END\s+)?(PROVIDED\s+)?CONTEXT\s*#+", "", payload, flags=re.I)
        payload = re.sub(r"#+\s*FRAGMENT[0-9a-f-]*\s*#+", "", payload, flags=re.I)
        if not payload.strip():
            payload = "\n".join(f"- {h.get('content', '')}" for h in hits)
        return payload.strip()

    def reset(self) -> None:
        if not self.client:
            self.tenant = str(uuid.uuid4())
            return
        async def _go() -> None:
            try:
                await self.client.kernel.episodic.purge_user(self.tenant, self.user)
            except Exception:  # noqa: BLE001
                pass
        _run(_go())
        self.tenant = str(uuid.uuid4())


# --------------------------------------------------------------------------- #
# OSSICEAdapter — ICE-OSS SKU (ice_nexus package, zero-config)
# --------------------------------------------------------------------------- #

class OSSICEAdapter:
    """
    ICE-OSS SKU adapter. Works on oss branch ice_nexus package (zero-config).
    Uses IndexlessContextClient on OSS branch. Registers as "ice_oss" in _BUILTIN.
    """

    def __init__(
        self,
        *,
        mode: str = "sandbox",
        top_k: int = 6,
        context_mode: str = "packed",
        compression_threshold: float | None = 0.1,
        model_id: str = "gpt-4o-mini",
        max_input_tokens: int = 8192,
    ):
        self.name = "ice_oss"
        self.mode = mode
        self.top_k = top_k
        self.context_mode = context_mode
        self.compression_threshold = compression_threshold
        self.model_id = model_id
        self.max_input_tokens = max_input_tokens
        self.tenant = str(uuid.uuid4())
        self.user = "bench_user"
        self.session = str(uuid.uuid4())
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize the OSS client (IndexlessContextClient)."""
        bootstrap_ice(self.mode)
        try:
            import ice
            if hasattr(ice, "IndexlessContextClient"):
                kernel = ice.get_client() if hasattr(ice, "get_client") else ice.init(mode=self.mode)
                self.client = ice.IndexlessContextClient(kernel)
            elif hasattr(ice, "IndexlessContextClient"):
                # Fallback to community client if OSS client not available
                kernel = ice.get_client() if hasattr(ice, "get_client") else ice.init(mode=self.mode)
                self.client = ice.IndexlessContextClient(kernel)
            else:
                raise RuntimeError("No suitable ICE client found in OSS branch")
        except Exception:
            self.client = None
            self._fallback_mode = True

    def ingest(self, conversation: Conversation) -> None:
        if not self.client:
            return
        async def _go() -> None:
            for turn in conversation.turns:
                await self.client.ingest(
                    file_path=turn.content,
                    session_id=self.session,
                    x_user_id=self.user,
                    metadata=turn.metadata or {},
                )
        _run(_go())

    def _retrieve(self, question: str):
        if not self.client:
            return None, [], []
        async def _go():
            qv = await self.client.kernel.embed(question)
            hits = await self.client.kernel.retrieve(
                self.tenant, qv, self.session, user_id=self.user, limit=self.top_k
            )
            hist = await self.client.kernel.history(
                self.tenant, self.session, user_id=self.user, limit=100
            )
            return qv, hits, hist
        return _run(_go())

    def context(self, question: str) -> str:
        if not self.client:
            return ""
        with _compression_threshold(self.compression_threshold):
            return self._context(question)

    def _context(self, question: str) -> str:
        qv, hits, hist = self._retrieve(question)
        if not qv:
            return ""
        if self.context_mode == "hits":
            return "\n".join(f"- {h.get('content', '')}" for h in hits).strip()
        messages, _tokens, _budget = self.client.kernel.pager.assemble_prompt(
            current_request=[{"role": "user", "content": question}],
            historical_messages=hist,
            retrieved_insights=hits,
            model_id=self.model_id,
            max_input_tokens=self.max_input_tokens,
            query_vector=qv,
        )
        sys_msgs = [m.get("content", "") for m in messages if m.get("role") == "system"]
        payload = ""
        for c in sys_msgs:
            if "### PROVIDED CONTEXT" in c.lstrip().startswith("###"):
                payload = c
                break
        if not payload and len(sys_msgs) > 1:
            payload = "\n\n".join(sys_msgs[1:])
        payload = re.sub(r"#+\s*(END\s+)?(PROVIDED\s+)?CONTEXT\s*#+", "", payload, flags=re.I)
        payload = re.sub(r"#+\s*FRAGMENT[0-9a-f-]*\s*#+", "", payload, flags=re.I)
        if not payload.strip():
            payload = "\n".join(f"- {h.get('content', '')}" for h in hits)
        return payload.strip()

    def reset(self) -> None:
        if not self.client:
            self.tenant = str(uuid.uuid4())
            return
        async def _go() -> None:
            try:
                await self.client.kernel.episodic.purge_user(self.tenant, self.user)
            except Exception:  # noqa: BLE001
                pass
        _run(_go())
        self.tenant = str(uuid.uuid4())


# --------------------------------------------------------------------------- #
# Vanilla RAG Baseline (ONNX embeddings + pgvector top-k, NO enterprise layer)
# --------------------------------------------------------------------------- #

class VanillaRAGBaseline:
    """Same ONNX embeddings + same top-k, but ICE's enterprise attention layer OFF."""

    def __init__(self, *, mode: str = "sandbox", top_k: int = 6):
        self.name = "vanilla_rag"
        self.mode = mode
        self.top_k = top_k
        self.tenant = str(uuid.uuid4())
        self.user = "bench_user"
        self.session = str(uuid.uuid4())
        self.kernel = _ensure_kernel(mode)

    def ingest(self, conversation: Conversation) -> None:
        async def _go() -> None:
            for turn in conversation.turns:
                await self.kernel.ingest(
                    content=turn.content,
                    tenant_id=self.tenant,
                    session_id=self.session,
                    user_id=self.user,
                    metadata=turn.metadata or {},
                )
        _run(_go())

    def context(self, question: str) -> str:
        async def _go() -> str:
            qv = await self.kernel.embed(question)
            hits = await self.kernel.retrieve(
                self.tenant, qv, self.session, user_id=self.user, limit=self.top_k
            )
            return "\n".join(f"- {h.get('content', '')}" for h in hits)
        return _run(_go())

    def reset(self) -> None:
        async def _go() -> None:
            try:
                await self.kernel.episodic.purge_user(self.tenant, self.user)
            except Exception:  # noqa: BLE001
                pass
        _run(_go())
        self.tenant = str(uuid.uuid4())


# --------------------------------------------------------------------------- #
# Truncation Baseline (no retrieval, most recent turns that fit)
# --------------------------------------------------------------------------- #

class TruncationBaseline:
    """No retrieval; most recent turns that fit within token budget."""

    def __init__(self):
        self.name = "recency_truncation"
        self.history: list[dict] = []

    def ingest(self, conversation: Conversation) -> None:
        self.history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": t.content}
            for i, t in enumerate(conversation.turns)
        ]

    def context(self, question: str) -> str:
        # Simply return the most recent history (no retrieval)
        recent = self.history[-10:]  # last 10 turns
        return "\n".join(f"{m['role']}: {m['content']}" for m in recent)

    def reset(self) -> None:
        self.history = []


# --------------------------------------------------------------------------- #
# No-Memory Baseline (question only)
# --------------------------------------------------------------------------- #

class NoMemoryBaseline:
    """Question only. Floor."""

    def __init__(self):
        self.name = "no_memory"

    def ingest(self, conversation: Conversation) -> None:
        pass

    def context(self, question: str) -> str:
        return ""

    def reset(self) -> None:
        pass


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #

def _ice_hits(**kw):
    return ICEAdapter(
        mode=kw.get("mode", "sandbox"),
        top_k=max(kw.get("top_k", 6), 30),
        context_mode="hits",
    )


def _ice_tuned(**kw):
    """ICE full pipeline calibrated (compression threshold 0.1)."""
    return ICEAdapter(
        mode=kw.get("mode", "sandbox"),
        top_k=max(kw.get("top_k", 6), 30),
        context_mode="packed",
        compression_threshold=float(kw.get("compression_threshold", 0.1)),
    )


def _ice_community(**kw):
    """CommunityICEAdapter factory."""
    return CommunityICEAdapter(
        mode=kw.get("mode", "sandbox"),
        top_k=kw.get("top_k", 6),
        context_mode=kw.get("context_mode", "packed"),
        compression_threshold=kw.get("compression_threshold"),
    )


def _ice_oss(**kw):
    """OSSICEAdapter factory."""
    return OSSICEAdapter(
        mode=kw.get("mode", "sandbox"),
        top_k=kw.get("top_k", 6),
        context_mode=kw.get("context_mode", "packed"),
        compression_threshold=kw.get("compression_threshold"),
    )


_BUILTIN = {
    "ice": lambda **kw: ICEAdapter(**{k: v for k, v in kw.items() if k != "compression_threshold"}),
    "ice_tuned": _ice_tuned,
    "ice_hits": _ice_hits,
    "ice_community": _ice_community,
    "ice_oss": _ice_oss,
    "vanilla_rag": lambda **kw: VanillaRAGBaseline(mode=kw.get("mode", "sandbox"), top_k=kw.get("top_k", 6)),
    "recency_truncation": lambda **kw: TruncationBaseline(),
    "no_memory": lambda **kw: NoMemoryBaseline(),
}


def build_systems(names: list[str], mode: str = "sandbox", top_k: int = 6) -> list[System]:
    """Instantiate named systems for the runner."""
    systems = []
    for n in names:
        if n not in _BUILTIN:
            raise ValueError(f"Unknown system: {n}. Available: {list(_BUILTIN.keys())}")
        systems.append(_BUILTIN[n](mode=mode, top_k=top_k))
    return systems


def shutdown() -> None:
    """Release shared kernel if held."""
    global _KERNEL, _LOOP
    if _KERNEL is not None and hasattr(_KERNEL, "disconnect"):
        _run(_KERNEL.disconnect())
    _KERNEL = None
    if _LOOP is not None:
        _LOOP.close()
        _LOOP = None
