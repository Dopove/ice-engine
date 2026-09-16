"""External comparison row: LangMem (https://github.com/langchain-ai/langmem).

Kept at the same arm's length as :mod:`mem0_adapter`:

* ``import langmem`` is lazy -- only pulled when a run asks for the
  ``langmem`` system.
* LangMem's own memory-extraction LLM is pointed at a **local Ollama** by
  default (``BENCH_LANGMEM_*`` env), never at the OpenRouter reader key --
  the free-tier budget stays reserved for the measured answer generation,
  identical for every row (same rule as Mem0's row).
* Storage is LangGraph's ``InMemoryStore`` with a local Ollama embedding
  index, wiped between conversations. LangMem ships this as its documented
  standalone-store setup (no Postgres/service required); we disclose that
  choice in the write-up rather than presenting it as LangMem's
  production-recommended (Postgres-backed) deployment.

If LangMem or its backing Ollama models are unavailable, construction raises
``RuntimeError`` with a setup hint; :func:`benchmarks.harness.adapters.build_systems`
downgrades that to a recorded skip so the rest of the run still completes.
"""

from __future__ import annotations

import os
import uuid

from .datasets import Conversation

_INSTALL_HINT = (
    "LangMem row requested but unavailable. `pip install langmem langgraph "
    "langchain-ollama` and run a local Ollama (`ollama serve` + "
    f"`ollama pull {os.environ.get('BENCH_LANGMEM_LLM_MODEL', 'qwen2.5:7b')}` + "
    f"`ollama pull {os.environ.get('BENCH_LANGMEM_EMBED_MODEL', 'nomic-embed-text')}`), "
    "or drop 'langmem' from --systems."
)


class LangMemAdapter:
    name = "langmem"

    def __init__(self, top_k: int = 6) -> None:
        try:
            from langchain_ollama import ChatOllama, OllamaEmbeddings
            from langgraph.store.memory import InMemoryStore
            from langmem import create_memory_manager
            from langmem.knowledge.extraction import Memory
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(_INSTALL_HINT) from exc

        self.top_k = top_k
        ollama_url = os.environ.get("BENCH_LANGMEM_OLLAMA_URL", "http://localhost:11434")
        llm_model = os.environ.get("BENCH_LANGMEM_LLM_MODEL", "qwen2.5:7b")
        embed_model = os.environ.get("BENCH_LANGMEM_EMBED_MODEL", "nomic-embed-text")

        try:
            embeddings = OllamaEmbeddings(model=embed_model, base_url=ollama_url)
            dims = len(embeddings.embed_query("dimension probe"))
            self.store = InMemoryStore(index={"dims": dims, "embed": embeddings})
            self._chat = ChatOllama(model=llm_model, base_url=ollama_url, temperature=0)
            self._memory_schema = Memory
            self.uid = f"u-{uuid.uuid4().hex[:8]}"
            self.namespace = ("memories", self.uid)
            self.manager = create_memory_manager(
                self._chat,
                schemas=[Memory],
                enable_updates=True,
                enable_deletes=False,
            )
        except Exception as exc:  # noqa: BLE001 - service/config problems
            raise RuntimeError(f"{_INSTALL_HINT}\n  underlying error: {exc!r}") from exc

    def ingest(self, conversation: Conversation) -> None:
        # Feed the conversation in speaker-tagged chunks so the extractor has
        # dialogue structure to work with (mirrors Mem0's row).
        msgs = [
            {"role": "user", "content": f"{t.speaker}: {t.text}" if t.speaker else t.text}
            for t in conversation.turns
        ]
        for i in range(0, len(msgs), 8):
            chunk = msgs[i : i + 8]
            try:
                extracted = self.manager.invoke({"messages": chunk})
            except AttributeError as exc:
                # trustcall's validation-repair ("patch") node crashes
                # (`'ExtractionState' object has no attribute 'tool_call_id'`,
                # a real upstream bug present even on the pinned 0.0.38) when
                # the extraction model emits a malformed tool call and
                # trustcall tries to self-correct it. Weaker local models
                # trigger this often; skip the chunk rather than losing the
                # whole conversation's memories to one bad tool call.
                if "tool_call_id" not in str(exc):
                    raise
                continue
            for mem in extracted:
                self.store.put(
                    self.namespace,
                    mem.id,
                    {"content": mem.content.content, "index": ["content"]},
                )

    def context(self, question: str) -> str:
        items = self.store.search(self.namespace, query=question, limit=self.top_k)
        lines = []
        for it in items:
            body = it.value.get("content", it.value)
            if isinstance(body, dict):
                body = body.get("content", body)
            lines.append(f"- {body}")
        return "\n".join(lines)

    def reset(self) -> None:
        try:
            for it in self.store.search(self.namespace, limit=1000):
                self.store.delete(self.namespace, it.key)
        except Exception:  # noqa: BLE001
            pass
        self.uid = f"u-{uuid.uuid4().hex[:8]}"
        self.namespace = ("memories", self.uid)
