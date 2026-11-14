<!-- Draft. Not published. No real data yet -- see "What's needed" below. -->

# GenAI-Perf multi-client load test

**Status: blocked on real data. Hook (50 clients, ICE sustains 2,400 tok/s
vs naive OOM at 128k) is a target from the ticket, not a measurement.**

## What this post needs that doesn't exist yet

1. A running inference server (vLLM, per the tool's typical use) serving the
   model under test, plus GPU hardware to host it.
2. NVIDIA GenAI-Perf itself, configured for 10/25/50/100 concurrent clients.
3. The same "naive full-context vs ICE dynamic context" comparison as
   SAR-132, but under concurrent load instead of single-request latency —
   sustained throughput, p99 TTFT, error rate, VRAM per client, KV-cache hit
   rate, and a cost-per-1M-tokens comparison.

Same domain gap as SAR-132: this is inference-serving load testing, not
memory-retrieval quality. Depends on SAR-132's infra being stood up first
(same GPU/serving stack, different load pattern).

**Platforms**: LinkedIn + Reddit r/LocalLLaMA + r/MachineLearning.
