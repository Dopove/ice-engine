import { IceClient, SessionManager } from '@dopove/ice-node';
import { UI } from './ui';

const ice = new IceClient({
    licenseJwt: process.env.ICE_LICENSE_JWT || "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzc3OTk4MTcsICJleHAiOiAxODA5MzMzNTgxNywgInN1YiI6InNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLVNPVkVSRUlHTiIsICJtYXhfbm9kZXMiOiAxMDAwLCAiZmVhdHVyZXMiOiBbInNvdmVyZWlnbiIsICJhbWMiLCAiZXhwYW5zaW9uX3BhY2tfMSJdLCAidGVuYW50X2lkIjogIjgyM2RjMjRhLTg4NWUtNDU4Ni1hNzRiLTkxNDRkY2MwZjg0OSIsICJtYWNoaW5lX3B1YmxpY19rZXkiOiAiLS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS1cbk1Db3dCUVlESzJWd0F5RUE2N0d6YkgzbzZsNG1LY0xJcUtMRnNBemVLTEcrdGd5Z0kzMVI1UTJOM0lrPVxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifX0.YPb2P6qx3tNFLDR-e0pUheNQFd_SahThTawB3MZagdvRt0SJP0oOzxfkKjncmXu1AbSmjyeEUry3ENYkMvhQh0uIDXbPQLLExv1VctyicwNx4Bmru7b1STv05CHIlB8IBzUYDXZbzgKXVVrWXfTjncSZVSnofbZmPAfr_ivvNLgXh8vIM4QlsntmcCIqqqmU6ce0MZoAvUu188s9q57MVCzXdlGhR7PWnwp1cXFKrvMuHkPEGzTYBdBJFTc59aN40TbruMM89-PbpSfSECytyAuuaCUp6EQR4SWD1n1bf2SkT8uh5bt-x5TjUL6KlhDPh3vk6PKgTlAr-llt_cDbMQ"
});

async function demonstrateMcpIntegration() {
    UI.header("ICE Node.js: Model Context Protocol (MCP) Integration Demo");
    console.log("This demo simulates how ICE interacts with an MCP Server.");
    console.log("Because ICE has infinite memory, it can handle thousands of MCP tool results.\n");

    UI.system("This demo requires a live ICE kernel and database.");
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.");
    UI.system("Booting live ICE Kernel connection...");

    const session = new SessionManager({ headers: { "x-session-id": "mcp-workspace-01" } }).getContext();

    UI.system("Discovering tools from local MCP Server (Github-MCP)...");
    const mcpTools = [
        {
            type: "function",
            function: {
                name: "mcp_github_read_file",
                description: "Read a file from a GitHub repository.",
                parameters: { type: "object", properties: { "repo": { type: "string" }, "path": { type: "string" } }, required: ["repo", "path"] }
            }
        }
    ];
    UI.system(`Found tool: ${mcpTools[0].function.name}`);

    UI.user("Read the 'main.py' file from 'dopove/ice-core'.");
    
    await UI.simulateProcessing(1.5, "Agent Reasoning");
    const response1 = // @ts-ignore
        await ice.chat.completions.create({
        model: "llama3.2:3b",
        messages: [ /* @ts-ignore */ { role: "user", content: "Read the 'main.py' file from 'dopove/ice-core'." }],
        tools: mcpTools,
        sessionId: session.sessionId,
        userId: session.userId
    });

    const toolCalls = response1.choices[0].message.tool_calls;

    if (toolCalls && toolCalls[0].function.name === "mcp_github_read_file") {
        UI.agent(`Calling MCP Tool '${toolCalls[0].function.name}' with ${toolCalls[0].function.arguments}`);
        
        UI.system("Executing via MCP Client...");
        await new Promise(r => setTimeout(r, 1000)); // Simulate delay
        const mcpResult = '{"content": "def main():\\n    print(\'Hello ICE\')\\n"}';
        UI.system("MCP Server returned file content.");

        UI.system("Pushing MCP result into ICE's Infinite Memory Horizon...");
        await UI.simulateProcessing(1.5, "Agent Synthesizing");
        const response2 = // @ts-ignore
        await ice.chat.completions.create({
            model: "llama3.2:3b",
            messages: [ /* @ts-ignore */ 
                { role: "assistant", content: null, tool_calls: toolCalls as any },
                { role: "tool", name: "mcp_github_read_file", content: mcpResult }
            ],
            sessionId: session.sessionId,
            userId: session.userId
        });

        UI.agent(`Final Answer: ${response2.choices[0].message.content}`);
        UI.success("MCP Integration Successful");
    }
}

demonstrateMcpIntegration().catch(console.error);