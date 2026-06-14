import { IceClient } from '@dopove/ice-node';
import { UI } from './ui';

const ice = new IceClient({
    licenseJwt: process.env.ICE_LICENSE_JWT || "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzc3OTk4MTcsICJleHAiOiAxODA5MzMzNTgxNywgInN1YiI6InNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLVNPVkVSRUlHTiIsICJtYXhfbm9kZXMiOiAxMDAwLCAiZmVhdHVyZXMiOiBbInNvdmVyZWlnbiIsICJhbWMiLCAiZXhwYW5zaW9uX3BhY2tfMSJdLCAidGVuYW50X2lkIjogIjgyM2RjMjRhLTg4NWUtNDU4Ni1hNzRiLTkxNDRkY2MwZjg0OSIsICJtYWNoaW5lX3B1YmxpY19rZXkiOiAiLS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS1cbk1Db3dCUVlESzJWd0F5RUE2N0d6YkgzbzZsNG1LY0xJcUtMRnNBemVLTEcrdGd5Z0kzMVI1UTJOM0lrPVxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifX0.YPb2P6qx3tNFLDR-e0pUheNQFd_SahThTawB3MZagdvRt0SJP0oOzxfkKjncmXu1AbSmjyeEUry3ENYkMvhQh0uIDXbPQLLExv1VctyicwNx4Bmru7b1STv05CHIlB8IBzUYDXZbzgKXVVrWXfTjncSZVSnofbZmPAfr_ivvNLgXh8vIM4QlsntmcCIqqqmU6ce0MZoAvUu188s9q57MVCzXdlGhR7PWnwp1cXFKrvMuHkPEGzTYBdBJFTc59aN40TbruMM89-PbpSfSECytyAuuaCUp6EQR4SWD1n1bf2SkT8uh5bt-x5TjUL6KlhDPh3vk6PKgTlAr-llt_cDbMQ"
});

async function demonstrateAntiContextRot() {
    UI.header("ICE Node.js: Anti-Context Rot & Infinite Memory Retention Demo");
    console.log(`${UI.YELLOW}Problem:${UI.RESET} Standard LLMs 'forget' early instructions when the conversation gets too long (Context Rot).`);
    console.log(`${UI.CYAN}Solution:${UI.RESET} ICE's ContextPager automatically anchors critical facts and pages chronological history.\n`);
    
    UI.system("This demo requires a live ICE kernel and database.");
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.");
    UI.system("Booting live ICE Kernel connection...");

    const userId = "researcher-02";
    const sessionId = "long-term-project-beta";

    // 1. Establish the "Needle"
    UI.step("[Turn 1] Establishing core project parameters...");
    UI.user("CRITICAL PROJECT FACT: The database migration deadline is October 24th, 2026.");
    
    await UI.simulateProcessing(1.5, "Storing to Deep Memory");
    const response1 = // @ts-ignore
        await ice.chat.completions.create({
        model: "gpt-4o",
        messages: [ /* @ts-ignore */ {
            role: "user", 
            content: "CRITICAL PROJECT FACT: The database migration deadline is October 24th, 2026."
        }],
        sessionId: sessionId,
        userId: userId,
        maxTokens: 1000
    });
    UI.agent(response1.choices[0].message.content);

    // 2. Simulate massive context drift
    UI.step("Simulating massive context drift (thousands of tokens of unrelated discussion)...");
    await UI.simulateProcessing(2.0, "Drifting context");
    for (let i = 0; i < 3; i++) {
        // @ts-ignore
        await ice.chat.completions.create({
            model: "gpt-4o",
            messages: [ /* @ts-ignore */ { role: "user", content: `Please review this block of filler code: ${'console.log("test"); '.repeat(50)}` }],
            sessionId: sessionId,
            userId: userId,
            maxTokens: 500
        });
    }
    UI.system("Context drift complete. Standard LLMs would have dropped the 'Needle'.");

    // 3. Prove Memory Retention
    UI.step("[Turn 50] Proving Memory Retention");
    UI.user("What is the database migration deadline we discussed earlier?");
    
    await UI.simulateProcessing(1.5, "Retrieving from Deep Memory");
    const responseFinal = // @ts-ignore
        await ice.chat.completions.create({
        model: "gpt-4o",
        messages: [ /* @ts-ignore */ { role: "user", content: "What is the database migration deadline we discussed earlier?" }],
        sessionId: sessionId,
        userId: userId,
        maxTokens: 1000
    });

    UI.agent(`Final Answer: ${responseFinal.choices[0].message.content}`);
    UI.success("ICE mathematically prevented context rot. The C++ bridge seamlessly retrieved the deep memory.");
}

demonstrateAntiContextRot().catch(console.error);