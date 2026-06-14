import { IceClient, SessionManager } from '@dopove/ice-node';
import { UI } from './ui';

const ice = new IceClient({
    licenseJwt: process.env.ICE_LICENSE_JWT || "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzc3OTk4MTcsICJleHAiOiAxODA5MzMzNTgxNywgInN1YiI6InNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLVNPVkVSRUlHTiIsICJtYXhfbm9kZXMiOiAxMDAwLCAiZmVhdHVyZXMiOiBbInNvdmVyZWlnbiIsICJhbWMiLCAiZXhwYW5zaW9uX3BhY2tfMSJdLCAidGVuYW50X2lkIjogIjgyM2RjMjRhLTg4NWUtNDU4Ni1hNzRiLTkxNDRkY2MwZjg0OSIsICJtYWNoaW5lX3B1YmxpY19rZXkiOiAiLS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS1cbk1Db3dCUVlESzJWd0F5RUE2N0d6YkgzbzZsNG1LY0xJcUtMRnNBemVLTEcrdGd5Z0kzMVI1UTJOM0lrPVxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifX0.YPb2P6qx3tNFLDR-e0pUheNQFd_SahThTawB3MZagdvRt0SJP0oOzxfkKjncmXu1AbSmjyeEUry3ENYkMvhQh0uIDXbPQLLExv1VctyicwNx4Bmru7b1STv05CHIlB8IBzUYDXZbzgKXVVrWXfTjncSZVSnofbZmPAfr_ivvNLgXh8vIM4QlsntmcCIqqqmU6ce0MZoAvUu188s9q57MVCzXdlGhR7PWnwp1cXFKrvMuHkPEGzTYBdBJFTc59aN40TbruMM89-PbpSfSECytyAuuaCUp6EQR4SWD1n1bf2SkT8uh5bt-x5TjUL6KlhDPh3vk6PKgTlAr-llt_cDbMQ"
});

async function runAgenticWorkflow() {
    UI.header("ICE Node.js: Agentic Workflow & Syntax Defense");
    UI.system("This demo requires a live ICE kernel and database.");
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.");
    UI.system("Booting live ICE Kernel connection...");

    const session = new SessionManager({ headers: { "x-session-id": "agent-task-02" } }).getContext();

    const tools = [
        {
            type: "function",
            function: {
                name: "fetch_database_metrics",
                description: "Fetch CPU and Memory metrics for the database.",
                parameters: {
                    type: "object",
                    properties: { "region": { type: "string" } },
                    required: ["region"]
                }
            }
        }
    ];

    UI.step("First Turn: Agent decides to call a tool");
    UI.user("Check the database metrics for 'us-east-1'.");

    await UI.simulateProcessing(1.5, "Processing via C++ Bridge");
    const response1 = // @ts-ignore
        await ice.chat.completions.create({
        model: "llama3.2:3b",
        messages: [ /* @ts-ignore */ { role: "user", content: "Check the database metrics for 'us-east-1'." }],
        tools: tools,
        toolChoice: "auto",
        sessionId: session.sessionId,
        userId: session.userId
    });

    const toolCalls = response1.choices[0].message.tool_calls;
    UI.agent(`Tool Call Request: \n${JSON.stringify(toolCalls, null, 2)}`);

    if (toolCalls && toolCalls.length > 0) {
        UI.step("Second Turn: Provide the tool result");
        UI.system("Executing local function 'fetch_database_metrics'...");
        await UI.simulateProcessing(1.0, "Fetching metrics");
        const toolResult = '{"cpu": "85%", "memory": "92%", "status": "critical"}';
        
        UI.system(`Sending tool result back to ICE...`);
        await UI.simulateProcessing(1.5, "Agent Synthesizing");
        const response2 = // @ts-ignore
        await ice.chat.completions.create({
            model: "llama3.2:3b",
            messages: [ /* @ts-ignore */ 
                { role: "assistant", content: null, tool_calls: toolCalls as any },
                { role: "tool", name: "fetch_database_metrics", content: toolResult }
            ],
            sessionId: session.sessionId,
            userId: session.userId
        });

        UI.agent(`Final Answer: ${response2.choices[0].message.content}`);
        UI.success("Agentic Workflow Completed Successfully");
    }
}

runAgenticWorkflow().catch(console.error);