# 👑 ICE Unlimited: Founder's Kernel Manual (v2.7.756)

This folder contains the documentation and build instructions specifically for the **Unlimited Edition** of the Infinite Context Engine. This version is for the Founder's personal use and internal high-performance swarms only.

## 🔓 The Unlimited Advantage
Unlike the Enterprise/Standard variants, the Unlimited Edition is compiled with **Zero Hardware Locks**.
- **DRM Bypass**: All `ICE_LICENSE_JWT` checks are mathematically removed during the C-compilation phase.
- **Unrestricted SKU**: Identifies itself as `ICE-UNLIMITED`, unlocking all "Financial Security" and "High-Fidelity" tiers without requiring a license heartbeat.
- **Maximum Performance**: No CPU-ID overhead during the recursive stitching loop.

## 🚀 Building the Unlimited Variants

### A. Standalone Binary (Personal Executable)
To generate the hardened, license-free binary:
```bash
python3 build_unlimited.py
```
**Saved Location**: `dist/ice-unlimited`

### B. Unlimited Python Wheel (Embedded SDK)
To generate the license-free library for use in your other Python projects:
```bash
source .ice_build_env/bin/activate
python3 scripts/build_wheels.py
```
**Saved Location**: `dist/python/ice_unlimited-2.7.756-py3-none-any.whl`

### C. Unlimited Node.js SDK (Thin Client)
To pack the license-free Node.js package for internal TypeScript swarms:
```bash
cd clients/node/ice-unlimited
npm install && npm run build && npm pack --pack-destination ../../../dist/node
```
**Saved Location**: `dist/node/dopove-ice-unlimited-2.7.756.tgz`
**Features**: Optimized `SessionManager` for auto-session tracking in internal dev-tools.

## 🛠️ Internal Customizations
You can use the following "Internal-Only" variables to stress test the kernel:

| Variable | Description | Use Case |
| :--- | :--- | :--- |
| `ICE_ALLOW_DEFAULT_KEY`| Set to `1` to bypass all tenant/RLS checks. | Local dev speed. |
| `ICE_DEGRADED_MODE` | Forces "Hot as Lava" mode regardless of DB health. | Stress testing upstream routing. |
| `ICE_SECRET_KEY` | Overrides the cryptographic salt for the hardware seal. | Manual seal generation. |

## 📍 Multi-Protocol Verification
Use the internal test suite to verify the Universal Protocol Architecture:
```bash
# Verify Gemini-CLI & Protected Tool Calling
pytest tests/integration/test_enterprise_agentic.py -v

# Verify Multimodal Persistence
PYTHONPATH=. python3 tests/test_multimodal_logic.py
```

---
**🔐 SECURITY NOTICE**: Do not distribute this folder or the `ice_unlimited` assets to clients. These bypass the $5 Billion Hypergraph-Native IP protection measures.
