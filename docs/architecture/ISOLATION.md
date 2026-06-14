# 🛡️ Enterprise Data Isolation: Sessions, Projects & Tenants

The Infinite Context Engine (ICE) is designed from the ground up for massive, multi-tenant B2B/B2C SaaS platforms. 

To ensure absolute data security and prevent cross-contamination (where one user accidentally sees another user's data), ICE implements a rigorous isolation model using **PostgreSQL Row-Level Security (RLS)** and strict ID routing.

---

## The Isolation Hierarchy

ICE isolates data across three distinct cryptographic boundaries:

1.  **Tenant ID (The Organization)**: The highest level of isolation. (e.g., "Acme Corp" vs. "Globex Inc.").
2.  **User ID (The Individual)**: Isolation within an organization. (e.g., "Alice" vs. "Bob").
3.  **Session ID (The Project/Thread)**: Isolation of specific contexts for a single user. (e.g., "Marketing Brainstorm" vs. "Code Refactoring").

### 1. Tenant Isolation (Hardware/Network Bound)
If you deploy ICE in a multi-tenant SaaS, you provision a unique `ICE_LICENSE_JWT` or API Key per tenant. 
When Tenant A makes a request, ICE mathematically binds all PostgreSQL operations to Tenant A's UUID using RLS. **It is physically impossible for a query in Tenant A to retrieve vectors belonging to Tenant B**, even if the ICE core is compromised.

### 2. User Isolation (Application Bound)
Passed via the `X-User-Id` header (or `userId` parameter in SDKs). 
If Alice and Bob belong to the same Tenant, ICE ensures that Alice's RAG queries only search embeddings tagged with Alice's `user_id` (or globally shared tenant documents). Alice cannot accidentally retrieve Bob's private chat history.

### 3. Session / Project Isolation (Context Bound)
Passed via the `X-Session-Id` header (or `sessionId` parameter in SDKs).
This solves "Context Bleed." If Alice is working on "Project A" and "Project B" simultaneously, she doesn't want the agent talking about Project A's architecture when she is asking questions in the Project B chat window. 

By passing a unique `session_id` for each project workspace, ICE creates hermetically sealed chronological timelines.

---

## Practical Examples: How to Utilize Project Isolation

### Scenario: A Developer Tool (IDE Plugin)
If you are building an IDE plugin powered by ICE, you want the agent to remember the codebase of the specific project the developer has open.

**Solution:** Use the absolute path of the project as the `session_id`.
*   When the user opens `/Users/alice/projects/frontend`, pass `session_id = "/Users/alice/projects/frontend"`. ICE will only retrieve history and RAG documents ingested for the frontend.
*   When they switch to `/Users/alice/projects/backend`, pass `session_id = "/Users/alice/projects/backend"`. ICE instantly switches contexts. The agent completely "forgets" the frontend and focuses solely on the backend memory ledger.

### Scenario: A Customer Support Dashboard
If a support agent is handling multiple customer tickets at once.

**Solution:** Use the Ticket ID as the `session_id`.
*   Ticket `#1044` -> `session_id = "ticket-1044"`.
*   Ticket `#1045` -> `session_id = "ticket-1045"`.
*   The ICE agent will never mix up the details of the two different angry customers.

---

## 🎓 Demonstrations
Check the `client_demos/` folder for code examples proving this isolation:
*   **Python**: `client_demos/python/06_session_isolation.py`
*   **Node.js**: `client_demos/node/05_session_isolation.ts`
