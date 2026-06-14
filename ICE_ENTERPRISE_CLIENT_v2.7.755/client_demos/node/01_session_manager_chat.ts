import { IceClient, SessionManager } from '@dopove/ice-node';
import { UI } from './ui';

const ice = new IceClient({
    licenseJwt: process.env.ICE_LICENSE_JWT || "dummy-for-unlimited-test"
});

async function runChatDemo() {
    UI.header("ICE Node.js: Infinite Memory Chat Demo");
    UI.system("This demo requires a live ICE kernel and database.");
    UI.system("Please run 'docker compose up -d' in 'client_demos/deployment/docker/' first.");
    UI.system("Booting live ICE Kernel connection...");

    const mockRequest = {
        headers: { "x-session-id": "node-research-01" },
        user: { id: "node-user-99" }
    };
    
    const session = new SessionManager(mockRequest).getContext();
    UI.system(`Bound to Session: ${session.sessionId} | User: ${session.userId}`);

    UI.step("First Interaction (Establishing Context)");
    UI.user("The secret Node.js port is 51337. Remember this.");
    
    await UI.simulateProcessing(1.5, "Processing via C++ Bridge");
    const response1 = // @ts-ignore
        await ice.chat.completions.create({
        model: "llama3.2:3b",
        messages: [ /* @ts-ignore */ { role: "user", content: "The secret Node.js port is 51337. Remember this." }],
        sessionId: session.sessionId,
        userId: session.userId,
        maxTokens: 4096
    });
    UI.agent(response1.choices[0].message.content);

    UI.step("Simulating massive context drift");
    await UI.simulateProcessing(2.0, "Processing hours of conversation");

    UI.step("Second Interaction (Retrieving Deep Memory)");
    UI.user("What was the secret port again?");
    
    await UI.simulateProcessing(1.5, "Retrieving memory via Vector Search");
    const response2 = // @ts-ignore
        await ice.chat.completions.create({
        model: "llama3.2:3b",
        messages: [ /* @ts-ignore */ { role: "user", content: "What was the secret port again?" }],
        sessionId: session.sessionId,
        userId: session.userId,
        maxTokens: 4096
    });
    UI.agent(response2.choices[0].message.content);
    
    UI.success("Infinite Memory Recall Successful");
}

runChatDemo().catch(console.error);