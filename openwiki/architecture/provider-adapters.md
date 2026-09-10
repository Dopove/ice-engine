---
type: subsystem
title: LLM Provider Adapters
description: The core/providers/* adapter abstraction that translates inbound Anthropic/Gemini client requests into ICE's internal OpenAI-style format, and how that differs from the separate, adapter-less outbound upstream dispatch in resolve_routing.
tags: [provider-adapters, openai, anthropic, gemini, multimodal, upstream-routing]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-08T09:24:22.215Z
sources:
  - id: openwiki-source-256e159d1012de3a631e3987
    resource: repo://ice/core/providers/__init__.py
  - id: openwiki-source-a83a2449a9e407f3c5d1cc3d
    resource: repo://ice/core/providers/anthropic.py
  - id: openwiki-source-f2cb7051c0da2325f716cd3f
    resource: repo://ice/core/providers/google.py
  - id: openwiki-source-4246bce5d3524d5c54a6bdf2
    resource: repo://ice/main.py
generated: { by: "claude-code", at: "2026-09-08T09:24:22.215Z" }
---

## Two different "provider" concerns, easy to conflate

The name "provider adapter" in this codebase refers only to **inbound** request translation — turning a client's Anthropic- or Gemini-shaped request into ICE's internal OpenAI-style message list. It has nothing to do with **outbound** dispatch to the actual upstream LLM API, which is a separate, adapter-less mechanism (`resolve_routing` in `ice/main.py`). The two are easy to conflate because both branch on "is this an Anthropic model," but they solve different problems and live in different files.

## The adapter abstraction (`ice/core/providers/`)

`BaseProvider` defines a single method, `map_multimodal_content(content) -> str | list[dict]`, that every adapter must implement. `get_provider_adapter(model_name=None, provider_hint=None)` is a small factory: it returns `AnthropicAdapter` if `provider_hint == "anthropic"` or the model name contains `"claude"`/`"anthropic"`, `GeminiAdapter` for `"google"`/model names containing `"gemini"`/`"google"`, and `OpenAIAdapter` for everything else (explicitly including Ollama and generic OpenAI-compatible endpoints, since their wire format already matches ICE's internal format). In practice, `ice/main.py`'s routes always call it with `provider_hint` set explicitly (`"anthropic"` for `/v1/messages`, `"google"` for the Gemini routes) rather than relying on model-name sniffing — the `model_name` parameter path exists but isn't exercised by the current call sites.

- **`OpenAIAdapter.map_multimodal_content`** is a pure pass-through — the incoming content is already in ICE's internal format, so nothing is transformed.
- **`AnthropicAdapter.map_multimodal_content`** converts Anthropic content blocks: `text` blocks map directly; `image` blocks (base64 source) become an OpenAI-style `image_url` data URI; `tool_use` and `tool_result` blocks are *not* mapped to OpenAI's native `tool_calls`/`tool` message format — instead they're serialized into inline pseudo-XML text markers (`<tool_call id='...'>name(args)</tool_call>`, `<tool_result tool_use_id='...'>...</tool_result>`) embedded directly in the text content. This means tool-calling context from an Anthropic client is preserved for the LLM to read, but not represented in a way the downstream OpenAI-compatible request payload's own `tools`/`tool_choice` mechanism would recognize as structured tool state.
- **`GeminiAdapter.map_multimodal_content`** converts Gemini `parts`: `text` parts map directly; `inline_data` (base64 + MIME type) becomes an `image_url` data URI; `functionCall`/`functionResponse` parts are likewise flattened into inline `<functionCall>...</functionCall>`/`<functionResponse>...</functionResponse>` text markers rather than structured tool messages, mirroring the Anthropic adapter's approach.

All three adapters are stateless (no `__init__`, no instance data) — `get_provider_adapter()` constructs a fresh instance per call.

## Outbound upstream dispatch is separate, and always OpenAI-shaped

Independent of which adapter translated the *inbound* request, `generate_ice_chunks` in `ice/main.py` (see [[gateway-api]]) picks the **outbound** upstream endpoint via its own `resolve_routing(model_id)` closure — keyword-matching the model id against `gpt-4`/`gpt-3.5`/`openai` (OpenAI), `claude`/`anthropic` (Anthropic), `gemini`/`google` (Gemini), falling back to a local Ollama endpoint otherwise. Each match returns an upstream URL, an API key (env var, overridable by the client's own key), and the matching `CircuitBreaker` for that provider (see [[gateway-api]]).

Regardless of which upstream URL is chosen, the outbound request body built by `generate_ice_chunks` is **always** an OpenAI chat-completions-shaped JSON payload (`{"model", "messages", "stream": true, "temperature", "max_tokens", ...}`), and the streamed response is parsed assuming OpenAI-shaped SSE chunks (`chunk["choices"][0]["delta"]["content"]`). This is correct for OpenAI itself, Ollama, and Gemini's OpenAI-compatibility endpoint (`generativelanguage.googleapis.com/v1beta/openai/chat/completions`, which the default `GEMINI_API_URL` explicitly targets) — but the Anthropic branch routes to `https://api.anthropic.com/v1/messages`, Anthropic's **native** Messages API endpoint, which does not accept an OpenAI-shaped `messages`+`stream` request body and does not emit `choices[].delta.content`-shaped SSE chunks (it uses its own `content_block_delta` event format with a `delta.text` field). There is no outbound adapter analogous to `AnthropicAdapter`/`GeminiAdapter` that translates ICE's internal OpenAI-shaped payload into Anthropic's native wire format before this dispatch, or translates Anthropic's native SSE stream back — the `core/providers/*` adapters only ever run on the inbound side.

`headers` construction does special-case Anthropic slightly (`x-api-key` + `anthropic-version` instead of `Authorization: Bearer`), which reduces but does not close this gap — the header shape matches Anthropic's expectations, but the request/response body shape does not.
