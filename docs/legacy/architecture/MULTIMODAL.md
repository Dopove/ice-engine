# 🖼️ ICE Multimodal Spec: Agnostic File Processing (v3.0.0)

The Infinite Context Engine (ICE) is engineered to be **File-Agnostic**. It treats all external data—whether a 500-page PDF, a thermal image, or a SQL dump—as high-fidelity semantic fragments.

---

## 1. Supported Multimodal Formats
ICE utilizes the **RAG-Anything** pipeline to decompose files into a unified `ContentList`.

| Data Type | Supported Formats | Core Extraction Engine |
| :--- | :--- | :--- |
| **Complex Docs** | `.pdf`, `.docx`, `.pptx`, `.xlsx` | **Docling** / **MinerU** (LaTeX support) |
| **Standard Text** | `.txt`, `.md`, `.json`, `.csv`, `.py`, `.c` | Native UTF-8 Stream Parser |
| **Vision/Images** | `.png`, `.jpg`, `.jpeg`, `.webp` | Vision Extraction (Normalized to 255 tokens) |
| **Web/URL** | `https://...`, `youtube.com/...` | Firecrawl / Playwright Bridge |

---

## 2. Technical Lifecycle of a File
When you call `ice_client.ingest("my_file.pdf")`, the kernel executes the **Multimodal Decomposition Loop**:

1.  **Format Detection**: ICE identifies the MIME type and routes it to the optimal parser.
2.  **Semantic Partitioning**: 
    *   **Text**: Partitioned into `ICE_CHUNK_SIZE` (default 12,000 chars) with overlap.
    *   **Tables**: Converted to high-fidelity Markdown blocks to preserve structure.
    *   **Images**: Encoded into Base64 and assigned a fixed **255-token budget** in the sliding window.
3.  **PII Masking (Compliance)**: If enabled, the **Financial Security Tier** scrubs PAN, Aadhaar, and Credit Card numbers from the text fragments.
4.  **Ledger Persistence**: All fragments are indexed into the `pgvector` episodic ledger using the host's physical node ID.

---

## 3. Advanced Customization: Swapping Engines
You can tune the multimodal performance via environment variables in your `docker-compose.yml` or `ice_config.py`.

### A. Tuning the Parser
If you are dealing with complex academic papers with heavy LaTeX, switch to MinerU:
```bash
# Environment Variable
ICE_RAG_PARSER=miniru
```

### B. High-Fidelity OCR
For low-quality scans, enable the OCR enhancement:
```python
ice_client = InfiniteContextClient(
    rag_parser="paddleocr",
    enable_images=True,
    enable_tables=True
)
```

---

## 4. Usage Examples for Different File Types

### Ingesting a Massive PDF (Staff-Engineer Strategy)
```python
# ICE handles the OCR, Table extraction, and Equation parsing automatically
await ice_client.ingest("./legal_contract_500_pages.pdf", session_id="contract-review-99")
```

### Ingesting Vision Data
```python
# ICE persists the image in the 100B Token horizon
await ice_client.ingest("./security_footage_frame_01.png", session_id="incident-report")
```

### Ingesting a YouTube Transcript
```python
# ICE uses its internal web bridge to pull and index the transcript
await ice_client.ingest("https://www.youtube.com/watch?v=...", session_id="learning-session")
```

---
## 🏁 Multimodal Robustness Guarantee
ICE v3.0.0 includes a **Structural Integrity Guard**. If a file format is unrecognized, ICE will attempt a raw binary-stream extraction to capture any readable strings, ensuring that no data is ever "silently lost."

---
**DOPOVE PRIVATE LIMITED** (CIN: U62011TZ2026PTC037599) | [dopove.com](https://www.dopove.com/) | info@dopove.com  
**(c) 2026 DOPOVE PRIVATE LIMITED**
