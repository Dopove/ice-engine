<!-- Draft. Not published. No real data yet -- see "What's needed" below. -->

# llama-bench real workload results

**Status: blocked on real data. Hook (ICE adds <2ms latency while cutting
context tokens 80%) is a target from the ticket, not a measurement — no
llama-bench run exists in this repo.**

## What this post needs that doesn't exist yet

1. GPU hardware (A100/H100/RTX 5090 per the spec) — not available to this
   benchmark harness, which is CPU/API-based (`benchmarks/harness/` talks to
   an OpenAI-compatible reader endpoint, never loads model weights locally).
2. `llama-bench` itself (from llama.cpp), plus quantized model weights
   (Llama-3-70B/8B, FP8/Q4_K_M).
3. A real integration wiring "naive context stuffing" vs "ICE dynamic
   context loading" into the same llama-bench harness, at 8k/32k/64k/128k
   context configs, measuring TTFT/TPS/VRAM/KV-cache-hit-rate for each.

This is a different benchmarking domain entirely (local inference serving)
from what `benchmarks/` does (memory-retrieval quality via a hosted reader
API). Needs GPU infra and a new harness, not a CI config change.

**Platforms**: LinkedIn + Reddit r/LocalLLaMA + r/MachineLearning.
