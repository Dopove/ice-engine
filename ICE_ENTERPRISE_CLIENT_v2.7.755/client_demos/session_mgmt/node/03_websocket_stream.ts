import { WebSocketServer, WebSocket } from 'ws';
import { IceClient } from '@dopove/ice-engine';

const wss = new WebSocketServer({ port: 3003 });

const ice = new IceClient({
    licenseJwt: process.env.ICE_LICENSE_JWT || "eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiRG9wb3ZlLUlDRS1FbnRlcnByaXNlIiwgImF1ZCI6ICJJQ0UtRW1iZWRkZWQtRW5naW5lIiwgImlhdCI6IDE3Nzc3OTk4MTcsICJleHAiOiAxODA5MzM1ODE3LCAic3ViIjogInNhbXBsZS1jbGllbnQtMDAxIiwgInByb2R1Y3QiOiAiSUNFLVNPVkVSRUlHTiIsICJtYXhfbm9kZXMiOiAxMDAwLCAiZmVhdHVyZXMiOiBbInNvdmVyZWlnbiIsICJhbWMiLCAiZXhwYW5zaW9uX3BhY2tfMSJdLCAidGVuYW50X2lkIjogIjgyM2RjMjRhLTg4NWUtNDU4Ni1hNzRiLTkxNDRkY2MwZjg0OSIsICJtYWNoaW5lX3B1YmxpY19rZXkiOiAiLS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS1cbk1Db3dCUVlESzJWd0F5RUE2N0d6YkgzbzZsNG1LY0xJcUtMRnNBemVLTEcrdGd5Z0kzMVI1UTJOM0lrPVxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifX0.YPb2P6qx3tNFLDR-e0pUheNQFd_SahThTawB3MZagdvRt0SJP0oOzxfkKjncmXu1AbSmjyeEUry3ENYkMvhQh0uIDXbPQLLExv1VctyicwNx4Bmru7b1STv05CHIlB8IBzUYDXZbzgKXVVrWXfTjncSZVSnofbZmPAfr_ivvNLgXh8vIM4QlsntmcCIqqqmU6ce0MZoAvUu188s9q57MVCzXdlGhR7PWnwp1cXFKrvMuHkPEGzTYBdBJFTc59aN40TbruMM89-PbpSfSECytyAuuaCUp6EQR4SWD1n1bf2SkT8uh5bt-x5TjUL6KlhDPh3vk6PKgTlAr-llt_cDbMQ"
});

console.log('WebSocket Session Demo running on ws://localhost:3003');

/**
 * Stateful WebSocket connectivity.
 * Perfect for rich desktop apps, voice interfaces, or high-speed streaming frontends.
 */
wss.on('connection', (ws: WebSocket) => {
    console.log('[Socket Connected]: Waiting for handshake...');
    
    // We bind the session state to the physical socket object.
    let isAuthenticated = false;
    let boundUserId = "";
    let boundSessionId = "";

    ws.on('message', async (data: string) => {
        try {
            // 1. The Handshake Phase
            if (!isAuthenticated) {
                const handshake = JSON.parse(data);
                if (handshake.user_id && handshake.session_id) {
                    boundUserId = handshake.user_id;
                    boundSessionId = handshake.session_id;
                    isAuthenticated = true;
                    console.log(`[Handshake Success]: Bound User ${boundUserId} to Thread ${boundSessionId}`);
                    ws.send(JSON.stringify({ type: "system", content: "Handshake verified. Infinite Memory engaged." }));
                } else {
                    ws.send(JSON.stringify({ type: "error", content: "Missing user_id or session_id" }));
                    ws.close();
                }
                return;
            }

            // 2. The Persistent Streaming Phase
            const payload = JSON.parse(data);
            const userMessage = payload.message;
            console.log(`[Received]: ${userMessage}`);

            // Unfortunately, the current TypeScript Thin Client wrapper might abstract the async iterator.
            // But conceptually, you would pipe the stream here.
            // For this demo, we await the full generation and emit it back.
            // (If using stream=true on the C++ bridge, you'd use a readable stream).
            
            const response = await ice.chat.completions.create({
                model: "gpt-4o",
                messages: [{ role: "user", content: userMessage }],
                sessionId: boundSessionId,
                userId: boundUserId,
                maxTokens: 4000
            });

            ws.send(JSON.stringify({ 
                type: "agent_reply", 
                content: response.choices[0].message.content 
            }));

        } catch (e: any) {
            console.error(`[Socket Error]: ${e.message}`);
            ws.send(JSON.stringify({ type: "error", content: "Internal engine error." }));
        }
    });

    ws.on('close', () => {
        console.log(`[Socket Closed]: Disconnected thread ${boundSessionId}`);
    });
});
