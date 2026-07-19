# 🌐 ICE Federated Search Architecture: Stacked Memory for Global Scale

The Indexless Context Engine (ICE) supports a federated search architecture, allowing an aggregator ICE node to seamlessly unify memory from multiple peer ICE nodes. This enables distributed memory ledgers across different cloud providers, geographic regions, or isolated environments, presenting a single, coherent "stacked memory" view to your Large Language Models.

---

## 1. Architecture Overview: The Aggregator and Peers

In a federated setup, you deploy multiple ICE instances:

*   **Peer Nodes (Tier 1):** These are standard ICE instances, each connected to their own PostgreSQL (Semantic Ledger) and Redis (Hot Cache). They function as local memory providers.
*   **Aggregator Node (Tier 2):** This is a central ICE instance that acts as the primary API endpoint for your applications. When a request comes in, the Aggregator queries its own local memory AND concurrently dispatches search queries to all configured Peer Nodes. It then collects, merges, and re-ranks all results before assembling the final prompt for the LLM.

```
       Your Application/LLM Client
                |
                v
        [ Aggregator ICE Node ]
           (Local DB + Redis)
            |           |
            v           v
  [ Peer ICE Node 1 ]   [ Peer ICE Node 2 ]
    (Local DB + Redis)    (Local DB + Redis)
```

### Key Advantages:

*   **Distributed Memory:** Scale memory horizontally across an unlimited number of nodes and databases.
*   **Data Locality/Residency:** Store sensitive data in specific regions or providers while still enabling global access from a central point.
*   **Resilience:** If one peer node is unavailable, the Aggregator can still function with other available memory sources.
*   **Unified Context:** Your LLMs interact with a single, massive, virtual memory space, abstracting away the underlying distributed complexity.

---

## 2. Configuration for Federated Search

To enable federated search, you need to configure both the Aggregator and its Peer Nodes.

### A. Peer Nodes Configuration

Each Peer Node operates as a standard ICE instance. The only specific configuration required is to ensure its `/v1/internal/search` endpoint is accessible by the Aggregator and protected by the internal API key.

*   **`ICE_INTERNAL_API_KEY`**: A shared secret that the Aggregator will use to authenticate with the Peers. This **must be identical** across the Aggregator and all Peer Nodes.
*   **Network Accessibility:** Ensure the Aggregator can reach the Peer Nodes via their configured host/port.

### B. Aggregator Node Configuration

The Aggregator Node requires two primary environment variables:

*   **`ICE_PEER_NODES`**: A comma-separated list of the base URLs of all Peer Nodes (e.g., `http://ice-peer-1:8080,http://ice-peer-2:8080`). The Aggregator will send internal search requests to these URLs.
*   **`ICE_INTERNAL_API_KEY`**: The same shared secret used by the Peer Nodes to authenticate internal requests.

---

## 3. Internal Search API (`POST /v1/internal/search`)

This endpoint is crucial for federated communication. It is **not intended for direct client access**.

*   **Method:** `POST`
*   **Path:** `/v1/internal/search`
*   **Authentication:** Requires an `X-Internal-API-Key` header matching `ICE_INTERNAL_API_KEY`.
*   **Payload (`InternalSearchRequest`):**
    ```json
    {
      "query_vector": [0.1, 0.2, ...],  // The embedding vector of the search query
      "tenant_id": "your-tenant-id",
      "user_id": "your-user-id",
      "session_id": "your-session-id",
      "limit": 5                      // Number of results requested from this peer
    }
    ```
*   **Response:**
    ```json
    {
      "results": ["Fragment from this peer 1", "Fragment from this peer 2", ...]
    }
    ```

---

## 4. Security Considerations

*   **`ICE_INTERNAL_API_KEY`:** Treat this key as a sensitive secret. Store it securely (e.g., Kubernetes Secrets, AWS Secrets Manager).
*   **Network Isolation:** Ideally, internal federated traffic should occur over a private, encrypted network (e.g., VPC Peering, VPN, private subnets) to minimize exposure.
*   **RLS Enforcement:** Each peer node still enforces PostgreSQL Row-Level Security based on the `tenant_id` and `user_id` passed in the internal search request, ensuring data isolation even in a federated setup.

---

## 5. Example Docker Compose Blueprints

See `docs/examples/infrastructure/federated/docker-compose.yml` for a working example of a two-node federated ICE deployment. This blueprint demonstrates:

*   Setting up multiple `ice-engine` services.
*   Configuring `ICE_PEER_NODES` on the aggregator.
*   Defining `ICE_INTERNAL_API_KEY` across all nodes.
*   Using separate PostgreSQL and Redis instances for each peer's memory.

---

By leveraging Federated Search, ICE provides unparalleled flexibility for managing vast, distributed memory landscapes for your AI applications.