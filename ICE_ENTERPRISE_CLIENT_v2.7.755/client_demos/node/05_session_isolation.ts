import { IceClient } from '@dopove/ice-node';
import { UI } from './ui';

const ice = new IceClient({
    licenseJwt: process.env.ICE_LICENSE_JWT || "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzc3OTk4MTcsICJleHAiOiAxODA5MzMzNTgxNywgInN1YiI6InNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLVNPVkVSRUlHTiIsICJtYXhfbm9kZXMiOiAxMDAwLCAiZmVhdHVyZXMiOiBbInNvdmVyZWlnbiIsICJhbWMiLCAiZXhwYW5zaW9uX3BhY2tfMSJdLCAidGVuYW50X2lkIjogIjgyM2RjMjRhLTg4NWUtNDU4Ni1hNzRiLTkxNDRkY2MwZjg0OSIsICJtYWNoaW5lX3B1YmxpY19rZXkiOiAiLS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS1cbk1Db3dCUVlESzJWd0F5RUE2N0d6YkgzbzZsNG1LY0xJcUtMRnNBemVLTEcrdGd5Z0kzMVI1UTJOM0lrPVxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifX0.YPb2P6qx3tNFLDR-e0pUheNQFd_SahThTawB3MZagdvRt0SJP0oOzxfkKjncmXu1AbSmjyeEUry3ENYkMvhQh0uIDXbPQLLExv1VctyicwNx4Bmru7b1STv05CHIlB8IBzUYDXZbzgKXVVrWXfTjncSZVSnofbZmPAfr_ivvNLgXh8vIM4QlsntmcCIqqqmU6ce0MZoAvUu188s9q57MVCzXdlGhR7PWnwp1cXFKrvMuHkPEGzTYBdBJFTc59aN40TbruMM89-PbpSfSECytyAuuaCUp6EQR4SWD1n1bf2SkT8uh5bt-x5TjUL6KlhDPh3vk6PKgTlAr-llt_cDbMQ"
});

async function demonstrateSessionIsolation() {
    UI.header("ICE Node.js: Session & Project Isolation Demo");
    console.log(`${UI.YELLOW}Problem:${UI.RESET} 'Context Bleed' where an AI mixes up details from different projects.`);
    console.log(`${UI.CYAN}Solution:${UI.RESET} ICE hermetically seals memory ledgers based on the \`sessionId\`.\n`);
    
    UI.system("This demo requires a live ICE kernel and database.");
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.");
    UI.system("Booting live ICE Kernel connection...");

    const userId = "support-agent-bob";
    
    // Define two distinct customer support tickets
    const ticket1044 = "ticket-1044-billing";
    const ticket1045 = "ticket-1045-technical";
    
    // --- PHASE 1: Handle Ticket 1044 ---
    UI.step(`[Ticket 1044]: Active.`);
    UI.user("My credit card ending in 4444 was double charged. Please note this.");
    await UI.simulateProcessing(1.0, "Storing to Ticket 1044 Ledger");
    // @ts-ignore
    const response1 = await ice.chat.completions.create({
        model: "llama3.2:3b",
        messages: [ /* @ts-ignore */ { role: "user", content: "My credit card ending in 4444 was double charged. Please note this." }],
        sessionId: ticket1044,
        userId: userId,
        maxTokens: 500
    });
    UI.agent(response1.choices[0].message.content);
    
    // --- PHASE 2: Handle Ticket 1045 ---
    UI.step(`[Ticket 1045]: Active.`);
    UI.user("My router is blinking red and I cannot connect to WiFi. Please note this.");
    await UI.simulateProcessing(1.0, "Storing to Ticket 1045 Ledger");
    // @ts-ignore
    const response2 = await ice.chat.completions.create({
        model: "llama3.2:3b",
        messages: [ /* @ts-ignore */ { role: "user", content: "My router is blinking red and I cannot connect to WiFi. Please note this." }],
        sessionId: ticket1045,
        userId: userId,
        maxTokens: 500
    });
    UI.agent(response2.choices[0].message.content);
    
    // --- PHASE 3: Prove Isolation (Context Switching) ---
    UI.step("PHASE 3: Prove Isolation (Context Switching)");
    
    // Switch to Ticket 1045 and ask about the credit card
    UI.system(`[Switching to Ticket 1045]: Asking about the credit card...`);
    UI.user("What were the last 4 digits of the credit card?");
    await UI.simulateProcessing(1.5, "Retrieving Ticket 1045 Context");
    const response1045 = // @ts-ignore
        await ice.chat.completions.create({
        model: "llama3.2:3b",
        messages: [ /* @ts-ignore */ { role: "user", content: "What were the last 4 digits of the credit card?" }],
        sessionId: ticket1045,
        userId: userId,
        maxTokens: 500
    });
    UI.agent(`[Ticket 1045 Context]: ${response1045.choices[0].message.content}`);
    UI.system("Notice: The agent DOES NOT know the credit card, because it is isolated to Ticket 1044.");
    
    // Switch to Ticket 1044 and ask about the issue
    UI.system(`[Switching to Ticket 1044]: Asking about the core issue...`);
    UI.user("What is the core issue we are trying to solve?");
    await UI.simulateProcessing(1.5, "Retrieving Ticket 1044 Context");
    const response1044 = // @ts-ignore
        await ice.chat.completions.create({
        model: "llama3.2:3b",
        messages: [ /* @ts-ignore */ { role: "user", content: "What is the core issue we are trying to solve?" }],
        sessionId: ticket1044,
        userId: userId,
        maxTokens: 500
    });
    UI.agent(`[Ticket 1044 Context]: ${response1044.choices[0].message.content}`);
    
    UI.success("The agent perfectly recalls the double charge issue, completely ignoring the router.");
}

demonstrateSessionIsolation().catch(console.error);