import { IceClient, SessionManager } from '@dopove/ice-node';
import { UI } from './ui';

const ice = new IceClient({
    licenseJwt: process.env.ICE_LICENSE_JWT || "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzc3OTk4MTcsICJleHAiOiAxODA5MzMzNTgxNywgInN1YiI6InNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLVNPVkVSRUlHTiIsICJtYXhfbm9kZXMiOiAxMDAwLCAiZmVhdHVyZXMiOiBbInNvdmVyZWlnbiIsICJhbWMiLCAiZXhwYW5zaW9uX3BhY2tfMSJdLCAidGVuYW50X2lkIjogIjgyM2RjMjRhLTg4NWUtNDU4Ni1hNzRiLTkxNDRkY2MwZjg0OSIsICJtYWNoaW5lX3B1YmxpY19rZXkiOiAiLS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS1cbk1Db3dCUVlESzJWd0F5RUE2N0d6YkgzbzZsNG1LY0xJcUtMRnNBemVLTEcrdGd5Z0kzMVI1UTJOM0lrPVxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifX0.YPb2P6qx3tNFLDR-e0pUheNQFd_SahThTawB3MZagdvRt0SJP0oOzxfkKjncmXu1AbSmjyeEUry3ENYkMvhQh0uIDXbPQLLExv1VctyicwNx4Bmru7b1STv05CHIlB8IBzUYDXZbzgKXVVrWXfTjncSZVSnofbZmPAfr_ivvNLgXh8vIM4QlsntmcCIqqqmU6ce0MZoAvUu188s9q57MVCzXdlGhR7PWnwp1cXFKrvMuHkPEGzTYBdBJFTc59aN40TbruMM89-PbpSfSECytyAuuaCUp6EQR4SWD1n1bf2SkT8uh5bt-x5TjUL6KlhDPh3vk6PKgTlAr-llt_cDbMQ"
});

async function runAdvancedToolCalling() {
    UI.header("ICE Node.js: Advanced Agentic Tool Calling Demo");
    console.log("This demo proves ICE can handle multiple tools, parse arguments flawlessly,");
    console.log("and prevent 'Agentic Amnesia' by pinning tool results.\n");

    UI.system("This demo requires a live ICE kernel and database.");
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.");
    UI.system("Booting live ICE Kernel connection...");

    const session = new SessionManager({ headers: { "x-session-id": "complex-agent-task-001" } }).getContext();

    const tools = [
        {
            type: "function",
            function: {
                name: "search_database",
                description: "Search the corporate database for a user.",
                parameters: { type: "object", properties: { "email": { type: "string" } }, required: ["email"] }
            }
        },
        {
            type: "function",
            function: {
                name: "reset_password",
                description: "Trigger a password reset email.",
                parameters: { type: "object", properties: { "user_id": { type: "string" } }, required: ["user_id"] }
            }
        }
    ];

    UI.step("TURN 1: The Request");
    UI.user("Find the user 'alex@example.com' and reset their password.");

    await UI.simulateProcessing(1.5, "Agent Reasoning");
    const response1 = // @ts-ignore
        await ice.chat.completions.create({
        model: "llama3.2:3b",
        messages: [ /* @ts-ignore */ { role: "user", content: "Find the user 'alex@example.com' and reset their password." }],
        tools: tools,
        sessionId: session.sessionId,
        userId: session.userId
    });

    const toolCalls1 = response1.choices[0].message.tool_calls;

    // --- TURN 2: Tool Execution (Search) ---
    if (toolCalls1 && toolCalls1[0].function.name === "search_database") {
        UI.agent(`I need to call 'search_database' with ${toolCalls1[0].function.arguments}`);
        
        UI.step("TURN 2: Tool Execution (Search)");
        UI.system("Executing search_database...");
        await UI.simulateProcessing(1.0, "Searching DB");
        const dbResult = '{"user_id": "U-9942", "status": "active"}';

        UI.system("Returning database result to ICE. Notice how ICE seamlessly parses the ongoing thread.");
        await UI.simulateProcessing(1.5, "Agent Reasoning");
        const response2 = // @ts-ignore
        await ice.chat.completions.create({
            model: "llama3.2:3b",
            messages: [ /* @ts-ignore */ 
                { role: "assistant", content: null, tool_calls: toolCalls1 },
                { role: "tool", name: "search_database", content: dbResult }
            ],
            tools: tools,
            sessionId: session.sessionId,
            userId: session.userId
        });

        const toolCalls2 = response2.choices[0].message.tool_calls;

        // --- TURN 3: Tool Execution (Reset) ---
        if (toolCalls2 && toolCalls2[0].function.name === "reset_password") {
            UI.agent(`Now I need to call 'reset_password' with ${toolCalls2[0].function.arguments}`);
            
            UI.step("TURN 3: Tool Execution (Reset)");
            UI.system("Executing reset_password...");
            await UI.simulateProcessing(1.0, "Sending Email");
            const resetResult = '{"status": "success", "email_sent": true}';

            await UI.simulateProcessing(1.5, "Agent Synthesizing");
            const response3 = // @ts-ignore
            await ice.chat.completions.create({
                model: "llama3.2:3b",
                messages: [ /* @ts-ignore */ 
                    { role: "assistant", content: null, tool_calls: toolCalls2 },
                    { role: "tool", name: "reset_password", content: resetResult }
                ],
                sessionId: session.sessionId,
                userId: session.userId
            });

            UI.agent(`Final Answer: ${response3.choices[0].message.content}`);
            UI.success("ICE managed a multi-step tool chain, parsed JSON perfectly, and retained context across turns.");
        }
    }
}

runAdvancedToolCalling().catch(console.error);