# ⚙️ Operations & Troubleshooting

## 1. Security Faults
The `ICE` engine is designed to be "self-defending." If any component detects tampering, unauthorized hardware, or a license violation, it will trigger an immediate, fatal `SystemExit`.

### 🛑 `[ICE SECURITY FAULT]`
If your application exits with this message, check the following:

- **Missing License:** Ensure `os.environ["ICE_API_KEY"]` is set or that `~/.ice/license.jwt` exists.
- **Machine Binding:** The license token is cryptographically bound to the machine's Hardware-ID (via the `.ice/machine.key`). If you move the license to a different server, it will fail.
- **SKU Mismatch:** You are attempting to run an `ICE-ENTERPRISE` feature with an `ICE-COMMUNITY` license.
- **Tampered Token:** The JWT signature has been modified.

**To debug:**
1. Check the local logs in `~/.ice/logs/`.
2. Inspect the `ICE_API_KEY` environment variable.
3. Ensure the binary (in `ice/core/`) has not been modified (tamper detection).

## 2. Memory Guardian
The `GodModeScheduler` automatically monitors VRAM pressure.

### ⚠️ `[Memory Guardian] OOM Prevention Triggered`
This is a warning that ICE has detected VRAM pressure that would lead to a system crash.
- **Action:** ICE automatically down-quantizes (reduces bit-precision) to keep your process alive.
- **Tuning:** If this happens frequently, increase `max_vram_mb` in your `CognitiveBudget` or lower your `post_limit` to reduce the memory footprint of your LLM prompts.

## 3. Performance & Logging
- **Standard Logging:** ICE uses the standard Python `logging` library. 
    ```python
    import logging
    logging.basicConfig(level=logging.INFO)
    ```
- **Audit Logging:** Every interaction is recorded by the `ClientTelemetryRouter` to the configured `ICE_CLIENT_TELEMETRY_SINK`. Check this sink for full, PII-scrubbed interaction history.
