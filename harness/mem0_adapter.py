"""External comparison row: Mem0 (https://github.com/mem0ai/mem0).

Kept deliberately at arm's length:

* ``import mem0`` is lazy -- the dependency is optional and only pulled when a
  run asks for the ``mem0`` system.
* Mem0's own extraction / summarisation LLM is pointed at a **local Ollama** by
  default (``BENCH_MEM0_*`` env), never at the OpenRouter key -- the free-tier
  budget is reserved for the measured answer generation, identical for every row.
* The vector store is a local on-disk Chroma collection, wiped between
  conversations.

If Mem0 or its backing services are unavailable, construction raises
``RuntimeError`` with a setup hint; :func:`benchmarks.harness.adapters.build_systems`
downgrades that to a recorded skip so the rest of the run still completes.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from typing import Any

from .datasets import Conversation

_INSTALL_HINT = (
    "Mem0 row requested but unavailable. `pip install mem0ai chromadb` and run a "
    "local Ollama (`ollama serve` + `ollama pull "
    f"{os.environ.get('BENCH_MEM0_LLM_MODEL', 'qwen2.5:7b')}`), or drop 'mem0' from --systems."
)


def _mem0_config(store_path: str) -> dict[str, Any]:
    provider = os.environ.get("BENCH_MEM0_LLM_PROVIDER", "ollama")
    ollama_url = os.environ.get("BENCH_MEM0_OLLAMA_URL", "http://localhost:11434")
    llm_model = os.environ.get("BENCH_MEM0_LLM_MODEL", "qwen2.5:7b")
    embed_model = os.environ.get("BENCH_MEM0_EMBED_MODEL", "nomic-embed-text")

    if provider == "ollama":
        llm = {"provider": "ollama", "config": {"model": llm_model, "ollama_base_url": ollama_url}}
        embedder = {
            "provider": "ollama",
            "config": {"model": embed_model, "ollama_base_url": ollama_url},
        }
    else:  # allow an OpenAI-compatible endpoint if the operator really wants it
        llm = {
            "provider": "openai",
            "config": {
                "model": llm_model,
                "openai_base_url": os.environ.get("BENCH_MEM0_OPENAI_BASE_URL", ollama_url),
                "api_key": os.environ.get("BENCH_MEM0_OPENAI_API_KEY", "ollama"),
                # mem0 defaults to max_tokens=2000; small free-tier OTPM caps
                # (e.g. Groq) reject that outright, so cap it explicitly.
                "max_tokens": int(os.environ.get("BENCH_MEM0_MAX_TOKENS", "800")),
            },
        }
        embedder = {
            "provider": "huggingface",
            "config": {"model": "sentence-transformers/all-MiniLM-L6-v2"},
        }

    return {
        "llm": llm,
        "embedder": embedder,
        "vector_store": {
            "provider": "chroma",
            "config": {"collection_name": "ice_bench", "path": store_path},
        },
    }


_REASONING_PATCHED = False


def _patch_strip_reasoning_wrapper() -> None:
    """Monkey-patch mem0's OpenAI response parser to strip a leading
    ``<reasoning>...</reasoning>`` block, in place, without touching the
    installed package.

    Some OpenAI-compatible endpoints for "harmony"-format models (e.g.
    Bedrock's openai.gpt-oss-20b-1:0 -- as opposed to Groq's hosting of the
    same open-weight model, which puts the chain-of-thought in its own
    ``reasoning`` field) return the *entire* chain-of-thought inline in
    ``message.content``, followed by the real answer:
    ``<reasoning>...long thinking...</reasoning>{"facts": [...]}``. mem0's
    ``OpenAILLM._parse_response`` returns that string as-is and its caller
    does a bare ``json.loads()`` on it, which fails with "Expecting value:
    line 1 column 1" since the string starts with ``<``, not ``{``.
    """
    global _REASONING_PATCHED
    if _REASONING_PATCHED:
        return
    import re

    from mem0.llms.openai import OpenAILLM

    _strip = re.compile(r"^\s*<reasoning>.*?</reasoning>\s*", re.DOTALL)
    _orig = OpenAILLM._parse_response

    def _parse_response(self, response, tools):
        result = _orig(self, response, tools)
        if isinstance(result, str):
            return _strip.sub("", result)
        if isinstance(result, dict) and isinstance(result.get("content"), str):
            result["content"] = _strip.sub("", result["content"])
        return result

    OpenAILLM._parse_response = _parse_response
    _REASONING_PATCHED = True


class Mem0Adapter:
    name = "mem0"

    def __init__(self, top_k: int = 6) -> None:
        try:
            from mem0 import Memory

            _patch_strip_reasoning_wrapper()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(_INSTALL_HINT) from exc

        self._Memory = Memory
        self.top_k = top_k
        self._store_root = tempfile.mkdtemp(prefix="ice_bench_mem0_")
        self.uid = f"u-{uuid.uuid4().hex[:8]}"
        try:
            self.mem = Memory.from_config(_mem0_config(self._store_root))
        except Exception as exc:  # noqa: BLE001 - service/config problems
            raise RuntimeError(f"{_INSTALL_HINT}\n  underlying error: {exc!r}") from exc

    def ingest(self, conversation: Conversation) -> None:
        # Feed the conversation in speaker-tagged pairs so Mem0's extractor has
        # dialogue structure to work with.
        msgs = [
            {"role": "user", "content": f"{t.speaker}: {t.text}" if t.speaker else t.text}
            for t in conversation.turns
        ]
        # Mem0 handles batching internally; chunk to keep prompts bounded.
        # Configurable because free-tier ITPM caps vary a lot by provider/model
        # (e.g. Groq's smaller free tiers reject an 8-turn LoCoMo chunk outright).
        chunk = int(os.environ.get("BENCH_MEM0_CHUNK_SIZE", "8"))
        for i in range(0, len(msgs), chunk):
            self.mem.add(msgs[i : i + chunk], user_id=self.uid)

    def context(self, question: str) -> str:
        res = self.mem.search(
            question, filters={"user_id": self.uid}, limit=self.top_k
        )
        items = res.get("results", res) if isinstance(res, dict) else res
        return "\n".join(f"- {it.get('memory', it)}" for it in items)

    def reset(self) -> None:
        try:
            self.mem.delete_all(user_id=self.uid)
        except Exception:  # noqa: BLE001
            pass
        self.uid = f"u-{uuid.uuid4().hex[:8]}"

    def __del__(self) -> None:  # best-effort temp cleanup
        shutil.rmtree(getattr(self, "_store_root", ""), ignore_errors=True)
