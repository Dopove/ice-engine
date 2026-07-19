# 📄 Multimodal Document Ingestion (RAG)

ICE natively handles the ingestion of massive files—including PDFs, codebases, and Markdown documents—directly into its Semantic Ledger. 

You do not need to integrate LangChain, set up Pinecone, or write chunking logic. ICE's ingestion engine processes the document and associates the knowledge with a specific User and Session.

---

## Using the `/v1/ingest` Endpoint

The simplest way to feed data to ICE is via the `/v1/ingest` HTTP endpoint or the native SDK `ingest()` method.

### 1. Place the File in the Upload Directory
For security, ICE operates within a sandboxed directory (configured via `ICE_UPLOAD_DIR`, defaulting to `./uploads`). Ensure the file you want to ingest is present in this directory on the host running the ICE Engine.

### 2. Execute the Ingestion Command

**Python SDK (Native)**
```python
import asyncio
from ice.sdk import init

async def main():
    ice = await init()
    
    # Ingest the 500-page PDF into Alice's 'finance' session
    await ice.ingest(
        file_path="annual_report_2026.pdf", # Relative to ICE_UPLOAD_DIR
        x_user_id="user-alice",
        x_session_id="finance-analysis"
    )
    print("Ingestion complete!")

asyncio.run(main())
```



### 3. Query the Knowledge

Once ingested, the knowledge is permanently bound to the `X-Session-Id`. You can now chat with the document using the standard completions endpoint.

**Python SDK (Native)**
```python
response = await ice.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Summarize Q3 revenue from the report."}],
    x_user_id="user-alice",
    x_session_id="finance-analysis" # ICE automatically queries the ingested document
)
print(response.choices[0].message.content)
```

---

## Supported File Types

Depending on your parser configuration (`ICE_RAG_PARSER`), ICE natively extracts and embeds knowledge from:

*   **Text & Code:** `.txt`, `.md`, `.py`, `.js`, `.json`, `.csv`
*   **Documents:** `.pdf`, `.docx`
*   **Complex Multimodal (via Docling/MinerU):** Extracts tables, LaTeX equations, and charts embedded inside PDFs.

## Configuration Tuning

If you are ingesting massive codebases or legal contracts, you can tune the geometric slicing logic of the ingestion engine using environment variables:

*   `ICE_CHUNK_SIZE`: Default is 8000 characters. Increase to 15000+ for dense legal documents to preserve context boundaries.
*   `ICE_CHUNK_OVERLAP`: Default is 500 characters. Increase to 1000+ for codebases to ensure function definitions aren't split incorrectly.