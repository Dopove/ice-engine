# ICE Python SDK
## High-Level Virtual Memory Management

The ICE Python SDK provides an idiomatic interface to the Embedded Engine, abstracting the complexities of KV-Cache management and multimodal parsing.

### Core Implementation
```python
from ice import IceClient

client = IceClient(api_key="...")

# Recursive Generation 2.0 ensures sub-millisecond continuation
response = client.generate(
    prompt="Analyze the 100B token dataset...",
    session_id="enterprise_session_001"
)
```

### Direct Content List Insertion
The SDK supports raw content insertion for multimodal workloads, allowing direct piping of Modality-Aware tokens.

### Configuration
The SDK respects the standard `ICE_*` environment variables for local overrides, though production values are enforced at the Engine level.

---
**DOPOVE PRIVATE LIMITED** (CIN: U62011TZ2026PTC037599) | [dopove.com](https://www.dopove.com/) | info@dopove.com
**(c) 2026 DOPOVE PRIVATE LIMITED**
