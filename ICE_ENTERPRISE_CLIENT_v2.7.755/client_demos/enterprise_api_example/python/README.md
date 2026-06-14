# Comprehensive Enterprise API Example

This project provides a full-fledged FastAPI server demonstrating how to perfectly integrate the Infinite Context Engine (ICE) into a production-grade Python application. It showcases all core ICE features and customization options, following the "Singleton Kernel" architectural mandate.

---

## 🚀 Quickstart

1.  **Start ICE Infrastructure:**
    Navigate to `client_demos/deployment/docker` and bring up PostgreSQL and Redis.
    ```bash
    cd client_demos/deployment/docker
    docker compose up -d
    ```
2.  **Install Dependencies:**
    Navigate to this example's root (`client_demos/enterprise_api_example/python`) and install dependencies.
    ```bash
    cd client_demos/enterprise_api_example/python
    pip install -r requirements.txt
    ```
3.  **Configure Environment Variables:**
    Create a `.env` file in `client_demos/enterprise_api_example/python` with your required ICE configurations.
    
    ```dotenv
    # Required for production licensing
    ICE_LICENSE_JWT="<YOUR_ENTERPRISE_LICENSE_ARN_OR_JWT>" \

    # Upstream LLM (e.g., local Ollama instance)
    UPSTREAM_API_URL="http://localhost:11434/v1/chat/completions" 
    
    # Customization Example (See app/core/ice_config.py for all options)
    ICE_MEMORY_CAP_GB=32.0
    ICE_POST_COMPRESSION_LIMIT=32768
    ICE_RETENTION_DAYS=365
    ICE_RAG_ENABLE_COMPLIANCE=true
    ICE_RAG_COMPLIANCE_LEVEL=strict
    ```
4.  **Run the API Server:**
    ```bash
    python -m app.main
    ```
    The server will start on `http://localhost:8000`.

---

## 📚 Endpoints

*   **`GET /health`**: Checks API server and ICE Kernel status.
*   **`POST /v1/chat`**: Chat completions with Infinite Memory.
*   **`POST /v1/ingest`**: Document ingestion into the Semantic Ledger.
*   **`GET /v1/config`**: Returns the live, active configuration of the ICE Kernel, proving that all custom tunables have been applied.

## Code Structure

*   `app/main.py`: FastAPI application entry point.
*   `app/core/ice_config.py`: **The central hub for all ICE customizations.** Reads environment variables and initializes the ICE Kernel singleton. Contains extensive comments explaining each setting.
*   `app/api/endpoints/ice_endpoints.py`: Defines the `/chat` and `/ingest` API routes.

---

**For detailed explanations of each ICE customization variable, refer to `docs/installation/CONFIGURATION.md`.**
