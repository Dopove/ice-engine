---
type: subsystem
title: SDK, Wrapper & Client Libraries
description: The three in-process consumption surfaces — ice/sdk.py's IndexlessContextClient, ice/wrapper.py's drop-in ICEWrapper, and the Node.js bridge/native-addon pair — and how the Node.js package is disconnected from the Python bridge it appears to pair with.
tags: [sdk, wrapper, node-bridge, ffi, ipc, client-libraries]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T09:24:22.215Z
sources:
  - id: openwiki-source-18c3bd981226321e55e47fa9
    resource: repo://clients/node/ice-client/package.json
  - id: openwiki-source-e5c015e066dfbc08024db2f8
    resource: repo://clients/node/ice-client/src/native.cpp
  - id: openwiki-source-b54efa544b36baee439ad319
    resource: repo://clients/node/ice-client/src/parser.ts
  - id: openwiki-source-cd4faa00fd9de6123ca0e699
    resource: repo://ice/node_bridge.py
  - id: openwiki-source-fd3918231f495ef0c662fd39
    resource: repo://ice/parser.py
  - id: openwiki-source-ecda5ab2a5d26aabcc134de4
    resource: repo://ice/sdk.py
  - id: openwiki-source-75d0e846003d86a50fbd4ca8
    resource: repo://ice/wrapper.py
generated: { by: "claude-code", at: "2026-09-08T09:24:22.215Z" }
---

## `ice/sdk.py`: the "full" SDK surface

`IndexlessContextClient` (obtained via `await ice.sdk.init(...)`, a module-level singleton also retrievable later with `get_client()`) is the richer of the two Python entry points, exposing `.chat.completions.create(...)` (OpenAI-compatible, via `ChatInterface`/`CompletionsInterface`), `.ingest(...)`, `.health()`, and `.shutdown()`. Its construction and request paths have several breaking gaps already covered in [[overview]] and [[ingestion-and-rag]] — `init()` fails at `ICEKernel` construction (`SecurityManager` argument/method mismatch), `create()` fails on a missing `time` import, and `.ingest()` calls a nonexistent `IngestionPipeline.ingest_path`. This page covers the remaining surface: `SessionManager`, error handling, and how the two other client entry points (`ICEWrapper`, the Node bridge) relate to this one.

`ICEError` carries a `code` (default `"ICE_ERR_GENERIC"`, e.g. `"ICE_ERR_UPSTREAM"` when an upstream error chunk is seen, `"ICE_ERR_UNINITIALIZED"` from `get_client()` before `init()`) and an optional `trace_id`, giving SDK consumers a structured way to distinguish failure classes without parsing message strings.

`SessionManager(request)` is a small helper for web frameworks: it duck-types its way through several request shapes to derive a `user_id` (checks `request.user.id`, falls back to `request.state.user_id`, else `"anonymous"`) and a `session_id` (checks an `X-Session-Id` header, falls back to a Starlette-style `request.session` dict — generating and persisting a new session ID into it if absent — else a fresh ephemeral ID), returning both as the `x_user_id`/`x_session_id` kwargs `CompletionsInterface.create` expects. It supports FastAPI/Starlette-style request objects most directly; the WSGI/ASGI generality claimed in its docstring depends on the passed object happening to expose compatible `.user`/`.state`/`.headers`/`.session` attributes.

## `ice/wrapper.py`: the drop-in `ICEWrapper`

The README's "3-line drop-in" pattern: `ICEWrapper(existing_openai_or_anthropic_client)` needs no ICE server, kernel, or database — it wraps an already-constructed provider SDK client via `__getattr__` proxying and intercepts only `.chat.completions.create(...)` calls through a synthesized `ChatProxy`.

- `ICEWrapper.__init__` builds a `MemoryStore` (the DuckDB-backed local store from `ice/store/base.py` — see [[ingestion-and-rag]]) and constructs an `IceStreamParser` instance as `self.parser`, but **`self.parser` is never actually called anywhere in `ChatProxy.create`** — the streaming branch's own comment notes "Here we would use the IceStreamParser... For now, just yield the content" and simply forwards each raw chunk untouched. Reasoning-tag extraction (splitting `<reasoning>...</reasoning>` spans out of streamed content) is therefore not currently applied on this path, unlike the gateway's `ReasoningExtractor` (see [[episodic-memory]]), which is a separate, unrelated implementation.
- `ChatProxy.create` retrieves memories via `self._wrapper.memory.retrieve(last_user_message)` (always the 5 most recent DuckDB rows — see [[ingestion-and-rag]] for why the `query` argument is ignored), prepends them as a single `[Recalled Memory]: ...` prefix onto the last user message if any were found, forwards the call unmodified otherwise, and saves the assistant's full response back via `memory.save("assistant", full_response)` after the call completes (accumulating streamed deltas first if `stream=True`).
- `ICEWrapper.__getattr__`/`_create_chat_proxy` dynamically copies every other attribute off the wrapped client's `.chat` object onto a synthetic `ChatContainer`, so only `chat.completions.create` is actually intercepted — other `.chat.*` surface (e.g. a `chat.completions.list` if the underlying SDK has one) passes through to the real client untouched.

`ice/parser.py`'s Python `IceStreamParser` (`parse_chunk`, snake_case) and `clients/node/ice-client/src/parser.ts`'s TypeScript `IceStreamParser` (`parseChunk`, camelCase) implement the same `<reasoning>` tag-detection logic independently in each language, with no shared source — a change to the tag-detection rule in one would need to be manually mirrored in the other.

## The Node.js bridge (`ice/node_bridge.py`)

A standalone script, not a FastAPI route or SDK class — designed to be spawned as a child process and communicate over stdin/stdout rather than a network socket, avoiding HTTP overhead for an embedded Node.js integration:

- At import time, `sys.stdout` is reassigned to `sys.stderr`, and the original stdout handle is kept as `original_stdout`. This means any `print()`/logging output produced while importing `ice.sdk` (which imports `ice.main`, triggering all of that module's import-time OpenTelemetry setup and its `print(f"DEBUG: App object created...")` — see [[gateway-api]]) is redirected to stderr, keeping stdout reserved exclusively for the explicit `original_stdout.write(...)` calls that emit the actual JSON/SSE response — the documented contract being "Node.js expects exactly one JSON object on stdout" (or an SSE stream of `data: ...` lines for streaming requests).
- `main()` reads one JSON payload from stdin (`sdk_params` + `completion_params`), calls `ice.sdk.init(**sdk_params)` and `get_client()`, then `handle_request` calls `ice_client.chat.completions.create(**completion_params)` — inheriting every construction/runtime failure documented for that call path in [[overview]] (the `time` import gap breaks this immediately).
- Failures are caught with a bare `except BaseException` (which also catches `SystemExit`/`KeyboardInterrupt`, not just ordinary exceptions), serialized as `{"error": {"type": ..., "message": ...}}` to stderr, and the process exits with code 1 — giving the parent Node.js process a way to detect failure via exit code plus a structured error on stderr, separate from the stdout data channel.

## The Node.js native package (`clients/node/ice-client/`) is disconnected from the bridge

Despite living alongside `node_bridge.py` and sharing the same "IceStreamParser" concept, `clients/node/ice-client` does **not** spawn or communicate with `ice/node_bridge.py` anywhere in this tree:

- `src/native.cpp` is an N-API addon whose own comment states it exists "to test the binding" — its one exported function, `getVersion()`, returns a hardcoded literal string `"ICE-CORE-3.0.0-MOCK"` rather than querying any real native core or spawning a Python process.
- `src/parser.ts` only exports the `IceStreamParser` chunk-parsing utility described above — no process-spawning, stdin/stdout, or IPC code exists anywhere in `clients/node/ice-client/src/`.
- `package.json` declares `"main": "dist/index.js"`, but no `dist/` directory and no `src/index.ts` (or any other entrypoint source file) exist in this tree to produce it — the package's declared entrypoint cannot currently be built or resolved.

As committed, the Node.js client package and the Python `node_bridge.py` IPC script appear to be two ends of an intended integration that were never actually wired together.
